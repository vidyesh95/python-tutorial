# Track 07 — Robotics Infrastructure

**Who it's for:** Robotics and infrastructure engineers who move sensor, telemetry, and fleet data reliably

## Goals

- Decode binary and serial/CAN protocols and talk to ROS 2 nodes
- Build async telemetry pipelines with bounded queues and durable time-series storage
- Simulate, record (MCAP), orchestrate, and deploy inference on robot fleets

## Prerequisite tracks

- t01_fundamentals, t02_intermediate, t04_fastapi_backend (for the capstone)

## Setup

```bash
uv sync --group robotics
```

Note: ROS 2 is installed through the system package or RoboStack (conda-based), not pip. The Python packages in the `robotics` group cover everything else. Serial and CAN lessons need hardware or a virtual bus; simulated examples are provided.

## Lessons

| File | Topic | Status |
|---|---|---|
| `m_01_binary_protocols_struct.py` | Binary Protocols with struct | STUB |
| `m_02_serial_and_can_bus.py` | Serial and CAN Bus I/O | STUB |
| `m_03_ros2_rclpy_basics.py` | ROS 2 Nodes, Topics and rclpy | STUB |
| `m_04_ros2_services_actions.py` | ROS 2 Services and Actions | STUB |
| `m_05_async_telemetry_pipelines.py` | Async Telemetry Pipelines | STUB |
| `m_06_time_series_storage.py` | Time-Series Storage | STUB |
| `m_07_rosbag_mcap_data.py` | Recording Data with rosbag2 and MCAP | STUB |
| `m_08_simulation_mujoco_pybullet.py` | Simulation with MuJoCo and PyBullet | STUB |
| `m_09_fleet_orchestration.py` | Fleet Orchestration | STUB |
| `m_10_on_device_inference_onnx.py` | On-Device Inference with ONNX Runtime | STUB |

## Checklist

- [ ] m_01: Binary Protocols with struct
- [ ] m_02: Serial and CAN Bus I/O
- [ ] m_03: ROS 2 Nodes, Topics and rclpy
- [ ] m_04: ROS 2 Services and Actions
- [ ] m_05: Async Telemetry Pipelines
- [ ] m_06: Time-Series Storage
- [ ] m_07: Recording Data with rosbag2 and MCAP
- [ ] m_08: Simulation with MuJoCo and PyBullet
- [ ] m_09: Fleet Orchestration
- [ ] m_10: On-Device Inference with ONNX Runtime

## Capstone project

Build a robot telemetry ingest service: a FastAPI app that accepts batched telemetry frames (struct-encoded binary and JSON) from simulated robots, validates them with Pydantic, writes samples to a time-series database, and archives raw streams as MCAP files. Requirements: a bounded asyncio queue that applies backpressure, health and ingest-rate endpoints, a replay test that feeds a recorded MCAP file through the service, and a Dockerfile. The service must run with pip-installable packages only; ROS 2 is needed only for the bridge example.
