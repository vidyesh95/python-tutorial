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
    raise NotImplementedError


class Subscription:
    def __init__(self, qos: Qos, connected: bool) -> None:
        self.qos, self.connected = qos, connected
        self.queue: deque[Any] = deque(maxlen=qos.depth)
        self.dropped = 0

    def deliver(self, msg: Any) -> None:
        """Append `msg`. If the queue already holds `qos.depth` items, the OLDEST is evicted
        and `self.dropped` increases by one.
        """
        raise NotImplementedError

    def take(self) -> list[Any]:
        """Return all queued messages oldest-first and empty the queue."""
        raise NotImplementedError


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
        raise NotImplementedError

    def publish(self, msg: Any) -> int:
        """If the publisher is TRANSIENT_LOCAL remember `msg` in `self.history`. Deliver to
        every CONNECTED subscription. Return how many subscriptions received it.
        """
        raise NotImplementedError


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
    raise NotImplementedError


def decode_imu(
    typestore: Any, raw: bytes
) -> tuple[int, str, tuple[float, float, float], tuple[float, float, float]]:
    """Inverse of encode_imu: return (stamp_ns, frame_id, accel, gyro)."""
    raise NotImplementedError


def compose_2d(
    parent_from_mid: tuple[float, float, float], mid_from_child: tuple[float, float, float]
) -> tuple[float, float, float]:
    """Compose poses (x, y, yaw): the child pose expressed in the parent frame.
    x = a.x + cos(a.yaw)*b.x - sin(a.yaw)*b.y; y = a.y + sin(a.yaw)*b.x + cos(a.yaw)*b.y;
    yaw = a.yaw + b.yaw.
    """
    raise NotImplementedError
