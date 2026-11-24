import math

import pytest

from _loader import load

ex = load("t07_robotics_infra", "ex_03_ros2_rclpy_basics")
R, D, Qos = ex.Reliability, ex.Durability, ex.Qos


def test_qos_compatibility_matrix():
    reliable, best = Qos(reliability=R.RELIABLE), Qos(reliability=R.BEST_EFFORT)
    assert ex.qos_compatible(reliable, reliable) is True
    assert ex.qos_compatible(best, best) is True
    assert ex.qos_compatible(reliable, best) is True  # reliable pub, best-effort sub is fine
    assert ex.qos_compatible(best, reliable) is False  # reliable sub needs a reliable pub
    latched, volatile = Qos(durability=D.TRANSIENT_LOCAL), Qos(durability=D.VOLATILE)
    assert ex.qos_compatible(latched, latched) is True
    assert ex.qos_compatible(latched, volatile) is True
    assert ex.qos_compatible(volatile, latched) is False


def test_subscription_keeps_last_depth_and_counts_drops():
    sub = ex.Subscription(Qos(depth=3), connected=True)
    for i in range(5):
        sub.deliver(i)
    assert sub.dropped == 2
    assert sub.take() == [2, 3, 4]
    assert sub.take() == []


def test_topic_delivers_to_connected_only():
    topic = ex.Topic("/imu", Qos(depth=5, reliability=R.BEST_EFFORT))
    ok = topic.subscribe(Qos(depth=5, reliability=R.BEST_EFFORT))
    bad = topic.subscribe(Qos(depth=5, reliability=R.RELIABLE))
    assert ok.connected is True and bad.connected is False
    assert topic.publish("a") == 1
    assert ok.take() == ["a"]
    assert bad.take() == []


def test_transient_local_late_joiner_gets_last_depth():
    topic = ex.Topic("/map", Qos(depth=2, durability=D.TRANSIENT_LOCAL))
    for name in ("v1", "v2", "v3"):
        topic.publish(name)
    late = topic.subscribe(Qos(depth=5, durability=D.TRANSIENT_LOCAL))
    volatile = topic.subscribe(Qos(depth=5, durability=D.VOLATILE))
    assert late.take() == ["v2", "v3"]
    assert volatile.take() == []  # volatile subscribers never get history
    topic.publish("v4")
    assert late.take() == ["v4"] and volatile.take() == ["v4"]


def test_volatile_publisher_keeps_no_history():
    topic = ex.Topic("/x", Qos(depth=5))
    topic.publish(1)
    assert topic.subscribe(Qos()).take() == []


def test_imu_cdr_round_trip():
    pytest.importorskip("rosbags")
    pytest.importorskip("numpy")
    from rosbags.typesys import Stores, get_typestore

    ts = get_typestore(Stores.ROS2_JAZZY)
    raw = ex.encode_imu(ts, 12_000_000_500, "imu_link", (0.0, 0.5, 9.81), (0.1, 0.0, -0.2))
    assert isinstance(raw, bytes) and len(raw) > 100
    assert raw[:2] == b"\x00\x01"  # CDR little-endian header
    stamp, frame, accel, gyro = ex.decode_imu(ts, raw)
    assert (stamp, frame) == (12_000_000_500, "imu_link")
    assert accel == pytest.approx((0.0, 0.5, 9.81))
    assert gyro == pytest.approx((0.1, 0.0, -0.2))
    msg = ts.deserialize_cdr(raw, "sensor_msgs/msg/Imu")
    assert msg.header.stamp.sec == 12 and msg.header.stamp.nanosec == 500
    assert msg.orientation.w == 1.0 and len(msg.orientation_covariance) == 9


def test_compose_2d():
    assert ex.compose_2d((1.0, 2.0, 0.0), (3.0, 0.0, 0.0)) == pytest.approx((4.0, 2.0, 0.0))
    got = ex.compose_2d((1.0, 0.0, math.pi / 2), (1.0, 0.0, 0.0))
    assert got == pytest.approx((1.0, 1.0, math.pi / 2))
    # chain: map -> odom -> base_link -> lidar (matches the lesson's tf demo)
    odom = ex.compose_2d((10.0, 0.0, 0.0), (1.0, 2.0, math.pi / 2))
    assert ex.compose_2d(odom, (0.5, 0.0, 0.0)) == pytest.approx((11.0, 2.5, math.pi / 2))
