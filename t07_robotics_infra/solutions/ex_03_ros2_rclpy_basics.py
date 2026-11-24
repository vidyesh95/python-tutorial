"""Exercise 03: ROS 2 topics, QoS and message serialization (in-process model).

`Qos`, `Reliability`, `Durability` and the class skeletons are given. Fill in the stubs.

Tasks
1. qos_compatible: can a subscriber with QoS `sub` connect to a publisher with QoS `pub`?
2. Subscription.deliver / Subscription.take: a KEEP_LAST(depth) queue that counts drops.
3. Topic.subscribe / Topic.publish: connect subscribers, deliver, and keep history for
   TRANSIENT_LOCAL late joiners.
4. encode_imu / decode_imu: sensor_msgs/msg/Imu <-> CDR bytes with `rosbags`.
5. compose_2d: compose two 2D poses (x, y, yaw), the core of a tf2 lookup.

Run: uv run pytest t07_robotics_infra -k ros2_rclpy
"""

import math
from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


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


def qos_compatible(pub: Qos, sub: Qos) -> bool:
    """RELIABLE subscriber + BEST_EFFORT publisher is incompatible; TRANSIENT_LOCAL
    subscriber + VOLATILE publisher is incompatible. Everything else connects.
    """
    if sub.reliability is Reliability.RELIABLE and pub.reliability is Reliability.BEST_EFFORT:
        return False
    return not (
        sub.durability is Durability.TRANSIENT_LOCAL and pub.durability is Durability.VOLATILE
    )


class Subscription:
    def __init__(self, qos: Qos, connected: bool) -> None:
        self.qos, self.connected = qos, connected
        self.queue: deque[Any] = deque(maxlen=qos.depth)
        self.dropped = 0

    def deliver(self, msg: Any) -> None:
        """Append `msg`. If the queue already holds `qos.depth` items, the OLDEST is evicted
        and `self.dropped` increases by one.
        """
        if len(self.queue) == self.queue.maxlen:
            self.dropped += 1
        self.queue.append(msg)

    def take(self) -> list[Any]:
        """Return all queued messages oldest-first and empty the queue."""
        items = list(self.queue)
        self.queue.clear()
        return items


class Topic:
    def __init__(self, name: str, pub_qos: Qos) -> None:
        self.name, self.pub_qos = name, pub_qos
        self.subs: list[Subscription] = []
        self.history: deque[Any] = deque(maxlen=pub_qos.depth)

    def subscribe(self, qos: Qos) -> Subscription:
        """Create a Subscription with connected=qos_compatible(pub_qos, qos) and register it.
        If it is connected and `qos.durability` is TRANSIENT_LOCAL, deliver the retained
        `self.history` (oldest first) to it right away.
        """
        sub = Subscription(qos, qos_compatible(self.pub_qos, qos))
        self.subs.append(sub)
        if sub.connected and qos.durability is Durability.TRANSIENT_LOCAL:
            for old in self.history:
                sub.deliver(old)
        return sub

    def publish(self, msg: Any) -> int:
        """If the publisher is TRANSIENT_LOCAL remember `msg` in `self.history`. Deliver to
        every CONNECTED subscription. Return how many subscriptions received it.
        """
        if self.pub_qos.durability is Durability.TRANSIENT_LOCAL:
            self.history.append(msg)
        delivered = 0
        for sub in self.subs:
            if sub.connected:
                sub.deliver(msg)
                delivered += 1
        return delivered


def encode_imu(
    typestore: Any,
    stamp_ns: int,
    frame_id: str,
    accel: tuple[float, float, float],
    gyro: tuple[float, float, float],
) -> bytes:
    """Build a sensor_msgs/msg/Imu (header stamp split into sec/nanosec, identity
    orientation w=1, zero covariances as numpy float64[9]) and return its CDR bytes.
    `typestore` comes from `get_typestore(Stores.ROS2_JAZZY)`.
    """
    import numpy as np

    Time = typestore.types["builtin_interfaces/msg/Time"]
    Header = typestore.types["std_msgs/msg/Header"]
    Quat = typestore.types["geometry_msgs/msg/Quaternion"]
    Vec3 = typestore.types["geometry_msgs/msg/Vector3"]
    Imu = typestore.types["sensor_msgs/msg/Imu"]
    sec, nanosec = divmod(stamp_ns, 1_000_000_000)
    msg = Imu(
        header=Header(stamp=Time(sec=sec, nanosec=nanosec), frame_id=frame_id),
        orientation=Quat(x=0.0, y=0.0, z=0.0, w=1.0),
        orientation_covariance=np.zeros(9),
        angular_velocity=Vec3(x=gyro[0], y=gyro[1], z=gyro[2]),
        angular_velocity_covariance=np.zeros(9),
        linear_acceleration=Vec3(x=accel[0], y=accel[1], z=accel[2]),
        linear_acceleration_covariance=np.zeros(9),
    )
    return bytes(typestore.serialize_cdr(msg, "sensor_msgs/msg/Imu"))


def decode_imu(
    typestore: Any, raw: bytes
) -> tuple[int, str, tuple[float, float, float], tuple[float, float, float]]:
    """Inverse of encode_imu: return (stamp_ns, frame_id, accel, gyro)."""
    msg = typestore.deserialize_cdr(raw, "sensor_msgs/msg/Imu")
    stamp = msg.header.stamp
    a, g = msg.linear_acceleration, msg.angular_velocity
    return (
        stamp.sec * 1_000_000_000 + stamp.nanosec,
        msg.header.frame_id,
        (a.x, a.y, a.z),
        (g.x, g.y, g.z),
    )


def compose_2d(
    parent_from_mid: tuple[float, float, float], mid_from_child: tuple[float, float, float]
) -> tuple[float, float, float]:
    """Compose poses (x, y, yaw): the child pose expressed in the parent frame.
    x = a.x + cos(a.yaw)*b.x - sin(a.yaw)*b.y; y = a.y + sin(a.yaw)*b.x + cos(a.yaw)*b.y;
    yaw = a.yaw + b.yaw.
    """
    ax, ay, ayaw = parent_from_mid
    bx, by, byaw = mid_from_child
    c, s = math.cos(ayaw), math.sin(ayaw)
    return (ax + c * bx - s * by, ay + s * bx + c * by, ayaw + byaw)
