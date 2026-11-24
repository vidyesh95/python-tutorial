import pytest

np = pytest.importorskip("numpy")

from _loader import load  # noqa: E402

ex = load("t07_robotics_infra", "ex_08_simulation_mujoco_pybullet")

PENDULUM_XML = """
<mujoco>
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <body pos="0 0 1">
      <joint name="hinge" type="hinge" axis="0 1 0" damping="0.05"/>
      <geom type="capsule" fromto="0 0 0 0 0 -0.5" size="0.02" mass="1"/>
    </body>
  </worldbody>
  <actuator><motor joint="hinge" gear="1" ctrllimited="true" ctrlrange="-5 5"/></actuator>
  <sensor><jointpos joint="hinge"/><jointvel joint="hinge"/></sensor>
</mujoco>
"""


def test_pd_torque_basic_and_clamp():
    assert ex.pd_torque(10, 2, target=1.0, pos=0.5, vel=1.0) == pytest.approx(3.0)
    assert ex.pd_torque(100, 0, target=1.0, pos=0.0, vel=0.0, limit=5.0) == 5.0
    assert ex.pd_torque(100, 0, target=-1.0, pos=0.0, vel=0.0, limit=5.0) == -5.0


def test_simulate_mass_shapes_and_time():
    t, x = ex.simulate_mass_pd(kp=100, kd=20, target=1.0, dt=0.01, duration=1.0)
    assert len(t) == len(x) == 100
    assert t[0] == pytest.approx(0.01)
    assert t[-1] == pytest.approx(1.0)


def test_underdamped_overshoots_critically_damped_does_not():
    _, under = ex.simulate_mass_pd(kp=100, kd=2, target=1.0)  # zeta = 0.1
    _, crit = ex.simulate_mass_pd(kp=100, kd=20, target=1.0)  # zeta = 1.0
    assert 60 < ex.overshoot_percent(under, 1.0) < 80
    assert ex.overshoot_percent(crit, 1.0) < 2.0


def test_overshoot_percent_values():
    assert ex.overshoot_percent(np.array([0, 1.2, 1.0]), 1.0) == pytest.approx(20.0)
    assert ex.overshoot_percent(np.array([0, 0.5, 0.9]), 1.0) == 0.0
    assert ex.overshoot_percent(np.array([0, -1.5, -1.0]), -1.0) == pytest.approx(50.0)


def test_settling_time_cases():
    t = np.arange(10, dtype=float)
    y = np.array([0, 0.5, 1.5, 1.1, 0.99, 1.0, 1.0, 1.01, 1.0, 1.0])
    # last sample outside the 2% band is index 3 -> settles at t[4]
    assert ex.settling_time(t, y, 1.0) == 4.0
    assert ex.settling_time(t, np.ones(10), 1.0) == 0.0
    never = np.array([0, 0.5, 0.7, 0.8, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9])
    assert ex.settling_time(t, never, 1.0) is None


def test_settling_time_on_simulated_response():
    t, x = ex.simulate_mass_pd(kp=100, kd=20, target=1.0)
    st = ex.settling_time(t, x, 1.0)
    assert st is not None and 0.1 < st < 1.0


def test_mujoco_pendulum_reaches_target():
    pytest.importorskip("mujoco")
    t, pos = ex.rollout_pendulum(PENDULUM_XML, kp=50, kd=6, target=0.5, duration=3.0)
    assert len(t) == len(pos) == 1500
    assert abs(pos[-1] - 0.5) < 0.05  # small gravity-induced steady-state error
    assert abs(pos[0]) < 0.01  # starts near 0 and moves smoothly


def test_mujoco_rollout_is_deterministic_and_clamped():
    pytest.importorskip("mujoco")
    a = ex.rollout_pendulum(PENDULUM_XML, 50, 6, 0.5, 1.0)[1]
    b = ex.rollout_pendulum(PENDULUM_XML, 50, 6, 0.5, 1.0)[1]
    assert np.array_equal(a, b)
    # A tiny torque limit cannot lift the pole to the target: clamping is applied.
    weak = ex.rollout_pendulum(PENDULUM_XML, 50, 6, 0.5, 1.0, limit=0.1)[1]
    assert abs(weak[-1]) < 0.1
