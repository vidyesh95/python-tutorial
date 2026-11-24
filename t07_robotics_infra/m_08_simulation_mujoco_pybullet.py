# Simulation with MuJoCo (and PyBullet)
"""
Simulation lets you test control code, data pipelines and failure handling without risking
hardware: run thousands of rollouts in CI, inject faults on purpose, and replay them.

The simulator landscape
- MuJoCo: fast, accurate contact physics, models are MJCF XML (also loads URDF). Python
  bindings are the official `mujoco` package. Used here (it has wheels for Python 3.15).
- PyBullet: easy URDF loading, `pybullet.connect(pybullet.DIRECT)` for headless runs. It has
  NO Python 3.15 wheels at the time of writing, so it is only described here.
- Gazebo (with ROS 2): full-robot sim with sensors/plugins and ROS topics, heavy but the
  standard for ROS integration. NVIDIA Isaac Sim / Isaac Lab: GPU-parallel sim for RL and
  synthetic data. Pick by need: unit tests -> MuJoCo/PyBullet, ROS stack tests -> Gazebo.

MuJoCo vocabulary
- `MjModel` is the STATIC description (bodies, joints, actuators, sensors, timestep).
  `MjData` is the mutable STATE (qpos, qvel, ctrl, sensordata, time).
- `mujoco.mj_step(model, data)` advances ONE timestep (`model.opt.timestep`).
- Actuators read `data.ctrl`; you write torques/targets there BEFORE each step.
- Sensors declared in the XML (`<jointpos>`, `<jointvel>`, `<accelerometer>`...) fill
  `data.sensordata`. They are computed at the START of mj_step, so they lag the state by
  one step: just like a real sensor that always reports slightly old data.

PD control: torque = kp * (target - pos) - kd * vel. kp is the spring (faster, but
overshoots), kd is the damper (calms oscillation). Gravity acts like a constant
disturbance, so P-control alone leaves a STEADY-STATE ERROR; add an integral term or
feed-forward gravity compensation to remove it.

Step-response metrics (how you judge a controller automatically)
- overshoot %: how far past the target it went, relative to the target.
- settling time: the last moment the signal was outside +/- tolerance of the target.
- steady-state error: |target - final value|.

Common mistakes
- Comparing floats exactly in sim tests: assert with tolerances.
- Forgetting `mj_resetData` between rollouts, so state leaks from one test to the next.
- Using wall-clock time for the controller: use `data.time` / step counts. Sim is not
  real time and must be deterministic.
- Tuning only on the perfect sim, then being surprised by noise, latency and friction.

Production notes
- Sim-to-real gap: add sensor noise, control latency, and domain randomization (vary mass,
  damping, friction per rollout with a seeded RNG) so gains survive the real robot.
- Run sim in CI as regression tests: fixed seed, fixed duration, assert metrics.
- Safety is part of the controller: clamp torques (here `ctrlrange`), detect NaN/diverging
  state and stop, and keep a watchdog that zeroes output if commands stop arriving.
- Never trust a gain tuned in sim on hardware without a slow, low-torque first run and an
  e-stop within reach.
"""

from dataclasses import dataclass

import mujoco
import numpy as np

# A single pendulum: hinge at height 1 m, 1 kg rod, motor torque limited to +/-5 N*m.
PENDULUM_XML = """
<mujoco model="pendulum">
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <body name="pole" pos="0 0 1">
      <joint name="hinge" type="hinge" axis="0 1 0" damping="0.05"/>
      <geom type="capsule" fromto="0 0 0 0 0 -0.5" size="0.02" mass="1"/>
    </body>
  </worldbody>
  <actuator>
    <motor name="motor" joint="hinge" gear="1" ctrllimited="true" ctrlrange="-5 5"/>
  </actuator>
  <sensor>
    <jointpos name="angle" joint="hinge"/>
    <jointvel name="velocity" joint="hinge"/>
  </sensor>
</mujoco>
"""


# Example 1: load a model from a string and inspect it
def load_pendulum(xml: str = PENDULUM_XML) -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_string(xml)
    return model, mujoco.MjData(model)


def describe(model: mujoco.MjModel) -> dict[str, float | int]:
    return {
        "timestep_s": model.opt.timestep,
        "dofs": model.nv,
        "actuators": model.nu,
        "sensor_values": model.nsensordata,
    }


# Example 2: a PD controller with torque saturation (the safety clamp)
@dataclass
class PDController:
    kp: float
    kd: float
    limit: float = 5.0
    gravity_ff: float = 0.0  # feed-forward torque per sin(angle), 0 = disabled

    def torque(self, target: float, pos: float, vel: float) -> float:
        raw = self.kp * (target - pos) - self.kd * vel + self.gravity_ff * np.sin(target)
        return float(np.clip(raw, -self.limit, self.limit))


@dataclass
class Rollout:
    t: np.ndarray
    pos: np.ndarray
    vel: np.ndarray
    ctrl: np.ndarray


def rollout(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    controller: PDController,
    target: float,
    duration: float,
    noise_std: float = 0.0,
    seed: int = 0,
) -> Rollout:
    """Step the sim, reading the SENSORS (not qpos) so noise/latency can be injected."""
    rng = np.random.default_rng(seed)  # seeded: noisy runs are still reproducible
    mujoco.mj_resetData(model, data)
    steps = round(duration / model.opt.timestep)
    t, pos, vel, ctrl = (np.empty(steps) for _ in range(4))
    for i in range(steps):
        angle, velocity = data.sensordata[0], data.sensordata[1]
        angle += rng.normal(0.0, noise_std) if noise_std else 0.0
        u = controller.torque(target, angle, velocity)
        if not np.isfinite(u) or not np.all(np.isfinite(data.qpos)):
            raise RuntimeError("simulation diverged: stop and e-stop")  # safety check
        data.ctrl[0] = u
        mujoco.mj_step(model, data)
        t[i], pos[i], vel[i], ctrl[i] = data.time, data.qpos[0], data.qvel[0], u
    return Rollout(t, pos, vel, ctrl)


# Example 3: step-response metrics
@dataclass
class StepMetrics:
    overshoot_pct: float
    settling_time: float | None  # None = never settled
    steady_state_error: float


def step_metrics(t: np.ndarray, y: np.ndarray, target: float, tol: float = 0.02) -> StepMetrics:
    sign = 1.0 if target > 0 else -1.0  # work in the direction of travel
    overshoot = max(0.0, float((sign * y).max() - abs(target))) / abs(target) * 100.0
    band = tol * abs(target)
    outside = np.flatnonzero(np.abs(y - target) > band)
    if len(outside) == 0:
        settling: float | None = float(t[0])
    elif outside[-1] == len(y) - 1:
        settling = None  # still outside the band at the end
    else:
        settling = float(t[outside[-1] + 1])
    return StepMetrics(float(overshoot), settling, float(abs(target - y[-1])))


# Example 4: compare gain choices and a robustness sweep (domain randomization)
def randomized_masses(n: int, seed: int = 0) -> list[float]:
    rng = np.random.default_rng(seed)
    return [float(m) for m in rng.uniform(0.8, 1.2, size=n)]  # +/-20% around 1 kg


def run_demo() -> None:
    model, data = load_pendulum()
    print("model:", describe(model))
    target = 0.5  # radians

    for name, ctl in [
        ("P only      ", PDController(kp=50, kd=0)),
        ("PD          ", PDController(kp=50, kd=6)),
        ("PD + gravity", PDController(kp=50, kd=6, gravity_ff=2.45)),  # m*g*L/2
    ]:
        r = rollout(model, data, ctl, target, duration=3.0)
        m = step_metrics(r.t, r.pos, target)
        print(
            f"{name}: overshoot={m.overshoot_pct:5.1f}%  "
            f"settle={m.settling_time and round(m.settling_time, 3)}  ss_err={m.steady_state_error:.4f}"
        )

    # Noise makes the same controller look worse: always test with it.
    ctl = PDController(kp=50, kd=6, gravity_ff=2.45)
    noisy = rollout(model, data, ctl, target, 3.0, noise_std=0.01, seed=1)
    print("noisy ss_err:", round(step_metrics(noisy.t, noisy.pos, target).steady_state_error, 4))

    # Domain randomization: does the controller survive +/-20% mass?
    worst = 0.0
    for mass in randomized_masses(5):
        scale = mass / model.body_mass[1]
        model.body_mass[1] = mass
        model.body_inertia[1] *= scale  # inertia scales with mass
        r = rollout(model, data, ctl, target, 3.0)
        worst = max(worst, step_metrics(r.t, r.pos, target).steady_state_error)
    print(f"worst steady-state error across masses: {worst:.4f}")


if __name__ == "__main__":
    run_demo()
