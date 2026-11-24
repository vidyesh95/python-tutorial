"""Exercise 08: PD control and step-response metrics.

Tasks 1-4 are pure numpy (no simulator needed). Task 5 uses MuJoCo.

Tasks
1. pd_torque: PD control law with a torque clamp.
2. simulate_mass_pd: simulate a unit mass under PD control (semi-implicit Euler).
3. overshoot_percent: how far past the target the response went.
4. settling_time: last time the response was outside the tolerance band.
5. rollout_pendulum: run a MuJoCo pendulum under PD control and return (t, pos).

Run: uv run pytest t07_robotics_infra -k simulation
"""

import numpy as np


def pd_torque(
    kp: float, kd: float, target: float, pos: float, vel: float, limit: float = float("inf")
) -> float:
    """Return kp * (target - pos) - kd * vel, clipped to [-limit, +limit].

    Example: pd_torque(10, 2, target=1.0, pos=0.5, vel=1.0) == 3.0
    """
    raw = kp * (target - pos) - kd * vel
    return max(-limit, min(limit, raw))


def simulate_mass_pd(
    kp: float, kd: float, target: float, dt: float = 0.001, duration: float = 2.0
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate a unit mass (acceleration == torque) starting at rest at position 0.

    For i in range(round(duration / dt)): u = pd_torque(kp, kd, target, x, v);
    v += u * dt; x += v * dt (semi-implicit Euler: update v FIRST, then x with the new v).
    Record time t = (i + 1) * dt and x AFTER each update.
    Return (t, x) as float numpy arrays of equal length.
    """
    steps = round(duration / dt)
    t = np.empty(steps)
    xs = np.empty(steps)
    x = v = 0.0
    for i in range(steps):
        u = pd_torque(kp, kd, target, x, v)
        v += u * dt
        x += v * dt
        t[i], xs[i] = (i + 1) * dt, x
    return t, xs


def overshoot_percent(y: np.ndarray, target: float) -> float:
    """Percent by which the response went past `target` (target != 0, either sign).

    Work in the direction of travel: for target > 0 use max(y), for target < 0 use min(y).
    overshoot = max(0, (peak_excursion - |target|)) / |target| * 100. A response that never
    reaches the target has overshoot 0.0.
    Example: y=[0, 1.2, 1.0], target=1.0 -> 20.0 (about); y=[0, -1.5], target=-1 -> 50.0.
    """
    sign = 1.0 if target > 0 else -1.0
    excursion = float((sign * np.asarray(y)).max())
    return max(0.0, excursion - abs(target)) / abs(target) * 100.0


def settling_time(t: np.ndarray, y: np.ndarray, target: float, tol: float = 0.02) -> float | None:
    """Time after which `y` stays inside |y - target| <= tol * |target|.

    - If y is never outside the band, return float(t[0]).
    - If the LAST sample is outside the band, the response never settled: return None.
    - Otherwise return float(t[k + 1]) where k is the index of the last sample outside.
    """
    outside = np.flatnonzero(np.abs(np.asarray(y) - target) > tol * abs(target))
    if len(outside) == 0:
        return float(t[0])
    if outside[-1] == len(y) - 1:
        return None
    return float(t[outside[-1] + 1])


def rollout_pendulum(
    xml: str, kp: float, kd: float, target: float, duration: float = 3.0, limit: float = 5.0
) -> tuple[np.ndarray, np.ndarray]:
    """Run a MuJoCo model (one hinge joint, one motor actuator, <jointpos> then <jointvel>
    sensors) under PD control.

    Build model/data with mujoco.MjModel.from_xml_string / MjData. For each of
    round(duration / model.opt.timestep) steps: read angle = data.sensordata[0] and
    velocity = data.sensordata[1], set data.ctrl[0] = pd_torque(..., limit=limit), call
    mujoco.mj_step, and record data.time and data.qpos[0] AFTER stepping.
    Return (t, pos) numpy arrays. Import mujoco inside the function.
    """
    import mujoco

    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    steps = round(duration / model.opt.timestep)
    t = np.empty(steps)
    pos = np.empty(steps)
    for i in range(steps):
        angle, velocity = data.sensordata[0], data.sensordata[1]
        data.ctrl[0] = pd_torque(kp, kd, target, float(angle), float(velocity), limit)
        mujoco.mj_step(model, data)
        t[i], pos[i] = data.time, data.qpos[0]
    return t, pos
