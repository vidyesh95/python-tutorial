# ROS 2 Nodes, Topics and rclpy
"""
ROS 2 is a middleware: many small processes (NODES) exchange typed messages over named
TOPICS (publish/subscribe) without knowing about each other. Underneath is DDS; you pick the
delivery behaviour per topic with QoS (Quality of Service) profiles.

Vocabulary
- Node: one process-level unit (`rclpy.node.Node`) that owns publishers, subscriptions,
  timers, services, actions and parameters.
- Topic: a named, typed stream (`/imu/data` of `sensor_msgs/msg/Imu`). Many publishers and
  subscribers are allowed; the type must match.
- Message: a generated struct from a `.msg` file, serialized on the wire as CDR.
- Executor: `rclpy.spin(node)` runs callbacks (subscriptions, timers). A single-threaded
  executor runs ONE callback at a time, so a slow callback delays all the others.
- QoS: history (KEEP_LAST depth N / KEEP_ALL), reliability (RELIABLE retries, BEST_EFFORT
  may drop), durability (VOLATILE vs TRANSIENT_LOCAL: late joiners get the last N samples).
  A subscription only connects if its QoS is COMPATIBLE with the publisher's: a RELIABLE
  subscriber cannot talk to a BEST_EFFORT publisher, and a TRANSIENT_LOCAL subscriber needs
  a TRANSIENT_LOCAL publisher. Mismatch = silently no data (only a warning in the logs).
- Typical presets: sensors use `qos_profile_sensor_data` (BEST_EFFORT, small depth: fresh
  beats complete); configuration/map topics use TRANSIENT_LOCAL depth 1 ("latched").
- Workspace: sources live in `ws/src/<package>`, built with `colcon build`, activated with
  `source install/setup.bash`. Packages declare dependencies in `package.xml`.
- tf2: a tree of coordinate frames (`map -> odom -> base_link -> lidar`) broadcast on
  `/tf` and `/tf_static`; you ask "where is frame A in frame B" and tf2 composes the chain.

rclpy is NOT on PyPI. It comes from a ROS 2 install (Ubuntu apt, RoboStack/conda, or the
`ros:jazzy` Docker image) and is tied to that install's Python. So this lesson shows real
rclpy code that only runs when `import rclpy` works, plus an in-process model of the same
semantics (QoS depth, drops, late joiners, tf) that runs anywhere. Real message types are
serialized offline with the `rosbags` package.

Common mistakes
- QoS mismatch: subscribing RELIABLE to a BEST_EFFORT sensor driver. Use sensor_data QoS.
- Doing heavy work in a callback on the single-threaded executor; offload or use callback
  groups with a MultiThreadedExecutor.
- Forgetting `rclpy.shutdown()` / `node.destroy_node()`, or calling `rclpy.init` twice.
- Using wall-clock time in nodes that should follow simulation time (`use_sim_time`).
- Publishing a fresh `Header.stamp` of 0: downstream tf and sync filters then fail.

Production notes
- Watchdog: every consumer of a sensor topic needs a "no message for X ms" timeout that
  triggers a safe state. Silence is the most common failure and looks like "no data".
- Never trust a message blindly: check frame_id, NaN/inf, covariance, and stamp age.
- Keep emergency stop OUTSIDE ROS graph latency: a hardware e-stop, not a topic.
- Namespaces and remapping let you run N robots on one network; set ROS_DOMAIN_ID per
  fleet or use DDS discovery limits so robots do not see each other.
"""

import math
import random
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

try:
    import numpy as np
    from rosbags.typesys import Stores, get_typestore

    HAVE_ROSBAGS = True
except ImportError:  # keep the pure-Python parts runnable without the robotics group
    HAVE_ROSBAGS = False


# Example 1: the real rclpy API (runs only if a ROS 2 install is on the Python path)
def run_real_rclpy_demo(timeout_s: float = 1.0) -> bool:
    try:
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import Imu
    except ImportError:
        return False

    class ImuLoop(Node):
        def __init__(self) -> None:
            super().__init__("imu_loop")
            self.received: list[Imu] = []
            self.pub = self.create_publisher(Imu, "imu/data", qos_profile_sensor_data)
            self.create_subscription(Imu, "imu/data", self.received.append, qos_profile_sensor_data)
            self.create_timer(0.05, self.tick)  # periodic publisher

        def tick(self) -> None:
            msg = Imu()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "imu_link"
            msg.linear_acceleration.z = 9.81
            self.pub.publish(msg)

    rclpy.init()
    node = ImuLoop()
    try:
        deadline = node.get_clock().now().nanoseconds + int(timeout_s * 1e9)
        while not node.received and node.get_clock().now().nanoseconds < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        print("rclpy: received", len(node.received), "Imu messages")
        return bool(node.received)
    finally:
        node.destroy_node()
        rclpy.shutdown()


# Example 2: real ROS 2 message types, offline: serialize sensor_msgs/msg/Imu to CDR bytes
def imu_cdr_roundtrip() -> tuple[int, str, float]:
    """Return (cdr_size_bytes, frame_id, accel_z) after a serialize/deserialize round trip."""
    ts = get_typestore(Stores.ROS2_JAZZY)
    Time = ts.types["builtin_interfaces/msg/Time"]
    Header = ts.types["std_msgs/msg/Header"]
    Quat = ts.types["geometry_msgs/msg/Quaternion"]
    Vec3 = ts.types["geometry_msgs/msg/Vector3"]
    Imu = ts.types["sensor_msgs/msg/Imu"]
    cov = np.zeros(9)  # float64[9] fields are numpy arrays
    msg = Imu(
        header=Header(stamp=Time(sec=12, nanosec=500), frame_id="imu_link"),
        orientation=Quat(x=0.0, y=0.0, z=0.0, w=1.0),
        orientation_covariance=cov,
        angular_velocity=Vec3(x=0.0, y=0.0, z=0.1),
        angular_velocity_covariance=cov,
        linear_acceleration=Vec3(x=0.0, y=0.0, z=9.81),
        linear_acceleration_covariance=cov,
    )
    raw = bytes(ts.serialize_cdr(msg, Imu.__msgtype__))  # what DDS puts on the wire
    back = ts.deserialize_cdr(raw, "sensor_msgs/msg/Imu")
    return len(raw), back.header.frame_id, back.linear_acceleration.z


# Example 3: an in-process model of topics + QoS (history depth, reliability, durability)
class Reliability(StrEnum):
    RELIABLE = "reliable"
    BEST_EFFORT = "best_effort"


class Durability(StrEnum):
    VOLATILE = "volatile"
    TRANSIENT_LOCAL = "transient_local"


@dataclass(frozen=True)
class Qos:
    depth: int = 10
    reliability: Reliability = Reliability.RELIABLE
    durability: Durability = Durability.VOLATILE


SENSOR_DATA = Qos(depth=5, reliability=Reliability.BEST_EFFORT)  # ~ qos_profile_sensor_data
LATCHED = Qos(depth=1, durability=Durability.TRANSIENT_LOCAL)  # ~ maps / static config


def qos_compatible(pub: Qos, sub: Qos) -> bool:
    if sub.reliability is Reliability.RELIABLE and pub.reliability is Reliability.BEST_EFFORT:
        return False
    return not (
        sub.durability is Durability.TRANSIENT_LOCAL and pub.durability is Durability.VOLATILE
    )


class Subscription:
    def __init__(self, qos: Qos, callback: Callable[[Any], None] | None, connected: bool) -> None:
        self.qos, self.callback, self.connected = qos, callback, connected
        self.queue: deque[Any] = deque(maxlen=qos.depth)  # KEEP_LAST depth
        self.dropped = 0

    def deliver(self, msg: Any) -> None:
        if len(self.queue) == self.queue.maxlen:
            self.dropped += 1  # the oldest sample is evicted
        self.queue.append(msg)

    def spin_once(self) -> int:
        """Run the callback for everything queued (what an executor does)."""
        handled = 0
        while self.queue:
            msg = self.queue.popleft()
            if self.callback:
                self.callback(msg)
            handled += 1
        return handled


class Topic:
    def __init__(self, name: str, pub_qos: Qos, loss_rate: float = 0.0, seed: int = 0) -> None:
        self.name, self.pub_qos, self.loss_rate = name, pub_qos, loss_rate
        self.subs: list[Subscription] = []
        self.history: deque[Any] = deque(maxlen=pub_qos.depth)
        self.rng = random.Random(seed)  # seeded so "lossy radio" runs are repeatable

    def subscribe(self, qos: Qos, callback: Callable[[Any], None] | None = None) -> Subscription:
        sub = Subscription(qos, callback, qos_compatible(self.pub_qos, qos))
        self.subs.append(sub)
        if sub.connected and qos.durability is Durability.TRANSIENT_LOCAL:
            for old in self.history:  # late joiner receives the retained samples
                sub.deliver(old)
        return sub

    def publish(self, msg: Any) -> None:
        if self.pub_qos.durability is Durability.TRANSIENT_LOCAL:
            self.history.append(msg)
        for sub in self.subs:
            if not sub.connected:
                continue
            lossy = self.pub_qos.reliability is Reliability.BEST_EFFORT
            if lossy and self.rng.random() < self.loss_rate:
                continue  # BEST_EFFORT: the radio ate it, nobody retries
            sub.deliver(msg)


# Example 4: tf2 in 2D: a tree of frames; lookup composes transforms along the tree
@dataclass(frozen=True)
class Transform2D:
    """Pose of a child frame expressed in its parent: maps child points into the parent."""

    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0

    def compose(self, other: Transform2D) -> Transform2D:  # self applied after other
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        return Transform2D(
            self.x + c * other.x - s * other.y,
            self.y + s * other.x + c * other.y,
            self.yaw + other.yaw,
        )

    def inverse(self) -> Transform2D:
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        return Transform2D(-(c * self.x + s * self.y), s * self.x - c * self.y, -self.yaw)


class TfBuffer:
    def __init__(self) -> None:
        self.parents: dict[str, tuple[str, Transform2D]] = {}

    def set(self, parent: str, child: str, tf: Transform2D) -> None:
        self.parents[child] = (parent, tf)

    def _ancestors(self, frame: str) -> dict[str, Transform2D]:
        chain, tf = {frame: Transform2D()}, Transform2D()
        while frame in self.parents:
            parent, edge = self.parents[frame]
            tf = edge.compose(tf)  # accumulate: original frame expressed in `parent`
            chain[parent], frame = tf, parent
        return chain

    def lookup(self, target: str, source: str) -> Transform2D:
        """Transform that maps points in `source` into `target`."""
        up_target, up_source = self._ancestors(target), self._ancestors(source)
        for frame, source_in_frame in up_source.items():
            if frame in up_target:
                return up_target[frame].inverse().compose(source_in_frame)
        raise LookupError(f"no path between {target!r} and {source!r}")


def run_demo() -> None:
    print("real rclpy ran:", run_real_rclpy_demo() or "no (rclpy not installed; using the model)")
    if HAVE_ROSBAGS:
        print("Imu CDR round trip:", imu_cdr_roundtrip())

    imu = Topic("/imu/data", SENSOR_DATA, loss_rate=0.3, seed=1)
    slow = imu.subscribe(Qos(depth=3, reliability=Reliability.BEST_EFFORT))
    strict = imu.subscribe(Qos(depth=3))  # RELIABLE subscriber vs BEST_EFFORT publisher
    for i in range(20):
        imu.publish({"seq": i})
    print(f"slow sub kept {[m['seq'] for m in slow.queue]}, dropped {slow.dropped}")
    print("strict sub connected:", strict.connected, "(QoS mismatch: it gets nothing)")

    map_topic = Topic("/map", LATCHED)
    map_topic.publish("map v1")
    map_topic.publish("map v2")
    late = map_topic.subscribe(LATCHED)  # joins after the publish and still gets the latest
    print("late joiner got:", list(late.queue))

    tf = TfBuffer()
    tf.set("map", "odom", Transform2D(10.0, 0.0, 0.0))
    tf.set("odom", "base_link", Transform2D(1.0, 2.0, math.pi / 2))
    tf.set("base_link", "lidar", Transform2D(0.5, 0.0, 0.0))
    print("lidar in map:", tf.lookup("map", "lidar"))


if __name__ == "__main__":
    run_demo()
