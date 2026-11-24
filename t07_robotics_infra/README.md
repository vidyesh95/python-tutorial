# Track 07: Robotics Infrastructure

Goal: move sensor, telemetry and fleet data reliably. By the end you will encode and decode
binary protocols, talk over serial and CAN, understand ROS 2 nodes/topics/services/actions,
build async telemetry pipelines with backpressure, store time series, record and replay MCAP
files, test controllers in simulation, orchestrate a fleet with heartbeats and staged
rollouts, and run a model on-device with ONNX.

Prerequisites: `t01_fundamentals`, `t02_intermediate`, `t03_advanced` (asyncio) and
`t04_fastapi_backend` (the capstone and m_09 use FastAPI). Python 3.15, managed with `uv`.

## Setup

```bash
uv sync --group robotics
```

Every lesson, exercise and test runs OFFLINE with no hardware:
- Serial uses pyserial's in-memory `loop://` URL; CAN uses python-can's `virtual` interface
  and DBC definitions parsed from strings with `cantools`.
- MuJoCo models are built from XML strings and run headless (no viewer, no rendering).
- MCAP files and SQLite databases are written to temporary directories and deleted.
- ONNX models are built with `onnx.helper` and run with `onnx.reference.ReferenceEvaluator`.

### ROS 2 is not on PyPI

`rclpy` and the ROS 2 message packages are NOT pip-installable, so `uv sync` cannot give you
ROS 2. Lessons 03 and 04 therefore run a small asyncio re-implementation of topics, services
and actions so the semantics are visible, and show the real `rclpy` code, which only runs if
`import rclpy` succeeds. Message (de)serialization uses `rosbags` (pure Python) instead. To
try the real thing, pick one:

- Docker (easiest): `docker run -it --rm ros:jazzy` then `ros2 run demo_nodes_py talker`.
- Ubuntu 24.04: install the `ros-jazzy-desktop` apt package from the official ROS 2 repository
  and `source /opt/ros/jazzy/setup.bash`.
- macOS/Windows/any Linux: RoboStack (conda/mamba), for example `mamba create -n ros
  -c conda-forge -c robostack-jazzy ros-jazzy-desktop` then `mamba activate ros`.

Run `rclpy` code with the Python that ROS 2 provides, not with `uv run`.

### Wheel availability on Python 3.15

- `onnxruntime` has no Python 3.15 wheels yet, so the ONNX lesson uses the reference
  evaluator (correct but slow). On a real device use `onnxruntime` or TensorRT with a
  Python version it supports.
- `pybullet` has no 3.15 wheels either, so the simulation lesson uses MuJoCo and only
  describes PyBullet, Gazebo and Isaac.
- `torch` is optional (`uv sync --group ml-torch`); the one lesson that exports from it guards
  the import and skips the example if it is missing.

## Lessons

| #  | Lesson (`m_NN_*.py`)             | You learn                                                                 | Status |
|----|----------------------------------|---------------------------------------------------------------------------|--------|
| 01 | `m_01_binary_protocols_struct`   | struct formats, endianness, framing, CRC/XOR checksums, memoryview        | ✅ |
| 02 | `m_02_serial_and_can_bus`        | pyserial loopback, python-can virtual bus, DBC signals with cantools      | ✅ |
| 03 | `m_03_ros2_rclpy_basics`         | nodes, topics, QoS, rclpy code, message serialization with rosbags        | ✅ |
| 04 | `m_04_ros2_services_actions`     | services, actions with feedback and cancel, parameters, launch, tf2       | ✅ |
| 05 | `m_05_async_telemetry_pipelines` | bounded queues, backpressure, batching, drop policies, monotonic time     | ✅ |
| 06 | `m_06_time_series_storage`       | schema design, rollups and downsampling, SQLite, TimescaleDB/Influx/Parquet | ✅ |
| 07 | `m_07_rosbag_mcap_data`          | MCAP channels and schemas, indexed time-range reads, rosbag2 comparison   | ✅ |
| 08 | `m_08_simulation_mujoco_pybullet`| MuJoCo from XML, stepping, sensors, PD control, step-response metrics     | ✅ |
| 09 | `m_09_fleet_orchestration`       | device registry, heartbeats, OTA waves/canary, command queues, fleet API  | ✅ |
| 10 | `m_10_on_device_inference_onnx`  | building ONNX graphs, shape inference, quantization, latency budgets      | ✅ |

Each lesson has a matching exercise `exercises/ex_NN_*.py` (stubs that raise
`NotImplementedError`), a reference implementation `solutions/ex_NN_*.py`, and tests in
`tests/test_ex_NN_*.py`.

## How to work

1. Run the lesson and read the code next to its output.
2. Open the exercise, read the docstrings (they include examples), implement the stubs.
3. Run the tests for that exercise until they pass.
4. Only then compare with the solution.

### Run a lesson

```bash
uv run python -m t07_robotics_infra.m_01_binary_protocols_struct
```

### Run the tests

```bash
uv run pytest t07_robotics_infra                      # all exercises (fail until you implement them)
uv run pytest t07_robotics_infra -k can               # one exercise by keyword
uv run pytest t07_robotics_infra -x                   # stop at the first failure
SOLUTIONS=1 uv run pytest t07_robotics_infra          # test the reference solutions instead
```

Before you start, failures are `NotImplementedError`. That is expected.

### Lint and format

```bash
uv run ruff check t07_robotics_infra && uv run ruff format t07_robotics_infra
```

## Safety mindset

This track is about machines that move. In every exercise and in the capstone, practise the
habits: an emergency stop that overrides everything, watchdogs that stop the robot when
commands or heartbeats stop, timeouts on every read, validated and range-checked inputs
(never trust sensor data blindly), clamped outputs, and staged rollouts with a way back.

## Progress checklist

- [ ] 01 Binary protocols with struct: lesson read, exercise passing
- [ ] 02 Serial and CAN bus I/O: lesson read, exercise passing
- [ ] 03 ROS 2 nodes, topics and rclpy: lesson read, exercise passing
- [ ] 04 ROS 2 services and actions: lesson read, exercise passing
- [ ] 05 Async telemetry pipelines: lesson read, exercise passing
- [ ] 06 Time-series storage: lesson read, exercise passing
- [ ] 07 Recording data with rosbag2 and MCAP: lesson read, exercise passing
- [ ] 08 Simulation with MuJoCo: lesson read, exercise passing
- [ ] 09 Fleet orchestration: lesson read, exercise passing
- [ ] 10 On-device inference with ONNX: lesson read, exercise passing
- [ ] Capstone below finished, tested, and load tested
- [ ] `uv run ruff check t07_robotics_infra` is clean

## Capstone project: telemetry ingest service

Build the backend that a fleet of robots streams into. Put the work in its own folder (for
example `capstone_t07/`) so the lesson files stay untouched. Everything must run offline with
simulated devices; ROS 2 is optional (only for a bridge example).

### Requirements

1. **Wire format**: a binary telemetry frame (`struct`, little-endian, version byte, device id,
   monotonic timestamp, sensor fields) wrapped in COBS or length-prefixed framing with a CRC
   (m_01). A decoder that survives garbage, truncation and bit flips by resynchronising.
2. **Simulated devices**: an asyncio generator that produces frames from the MuJoCo pendulum
   (m_08) or a synthetic IMU, with configurable rate, noise, dropouts and clock skew.
3. **Async ingest**: a FastAPI WebSocket endpoint (`/ws/telemetry/{device_id}`) accepts
   frames and pushes them into a BOUNDED asyncio queue; when it is full, apply an explicit
   drop policy (drop oldest for telemetry) and count drops (m_05). Graceful shutdown drains
   the queue.
4. **Validation**: decode and validate each frame (checksum, version, device registered,
   timestamp plausible, values in physical range); quarantine bad frames with a reason
   instead of crashing or silently dropping them.
5. **Storage**: batch writes to a time-series store (SQLite as in m_06, or TimescaleDB /
   QuestDB if you want Docker) with a rollup table, and archive the raw frames of each
   session to an MCAP file with a schema (m_07). A retention job deletes old raw rows.
6. **Fleet endpoints**: `GET /fleet` (devices, last seen, state), `GET /devices/{id}/latest`,
   `GET /devices/{id}/series?from=&to=&step=` (rollup query), `GET /healthz`, and `GET
   /metrics` with ingest rate, queue depth and drop counts (m_09).
7. **Alerting**: a background task marks a device OFFLINE after N missed heartbeats and
   emits an alert event once (not on every check), then a recovery event when it returns.
8. **Command channel (stretch)**: a per-device command queue with ack/timeout and an
   emergency-stop command that bypasses the queue.
9. **Tests**: unit tests for the codec (property-style with random corruption, seeded),
   a replay test that feeds a recorded MCAP file through the service with `TestClient`, and
   an alerting test with a fake clock.
10. **Load test**: a script (asyncio + `httpx`/websockets or `TestClient` in a loop) that
    drives 50 simulated devices at 50 Hz and reports sustained frames/s, p99 ingest
    latency, and drops. Show what happens when the store is artificially slowed down.
11. **Dockerfile**: multi-stage, non-root, pip-installable packages only, with a healthcheck.

### Suggested layout

```
capstone_t07/
├── ingest/
│   ├── codec.py           # struct + framing + CRC
│   ├── devices.py         # simulated devices
│   ├── pipeline.py        # bounded queue, batching, drop policy
│   ├── store.py           # time-series + rollups
│   ├── archive.py         # MCAP writer/reader
│   ├── fleet.py           # registry, heartbeats, alerts
│   └── app.py             # FastAPI app and WebSocket endpoint
├── scripts/
│   └── load_test.py
├── Dockerfile
└── tests/
    ├── test_codec.py
    ├── test_pipeline.py
    ├── test_replay.py     # MCAP -> service
    └── test_alerts.py
```

Stretch: a ROS 2 bridge node that republishes accepted telemetry as `sensor_msgs/msg/Imu`;
a staged-rollout endpoint (canary, then waves) for a model file checked by sha256 (m_09,
m_10); Grafana on top of TimescaleDB.
