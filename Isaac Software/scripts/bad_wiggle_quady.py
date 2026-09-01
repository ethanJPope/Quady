"""Intentionally broken Quady motion script.

This is for simulation learning only. Do not use this pattern on real hardware.

The intentional bug is that hip_amp and knee_amp are treated as radians even
though the argument names say degrees. This makes the target motion far too
large, so the joints slam into their limits and the robot should behave badly.

Run from the Isaac Lab checkout:

    isaaclab.bat -p "D:/Quady/Isaac Software/scripts/bad_wiggle_quady.py" --viz kit
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description="Intentionally bad Quady wiggle test.")
parser.add_argument("--num_steps", type=int, default=1200, help="Steps to run before closing in headless mode.")
parser.add_argument("--hip_amp_deg", type=float, default=5.0, help="BUG: treated as radians, not degrees.")
parser.add_argument("--knee_amp_deg", type=float, default=7.0, help="BUG: treated as radians, not degrees.")
parser.add_argument("--period", type=float, default=0.35, help="Fast period in seconds to make the bug obvious.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import isaaclab.sim as sim_utils
from isaaclab.sim import SimulationContext


ISAAC_SOFTWARE_DIR = Path(__file__).resolve().parents[1]
if str(ISAAC_SOFTWARE_DIR) not in sys.path:
    sys.path.insert(0, str(ISAAC_SOFTWARE_DIR))

from configs.quady_cfg import HIP_JOINTS, KNEE_JOINTS  # noqa: E402
from scripts.quady_sim_utils import print_quady_summary, reset_quady_to_default, spawn_quady_scene  # noqa: E402


def joint_ids(robot, names: list[str]) -> list[int]:
    """Resolve joint names to Isaac Lab's internal joint order."""
    return [robot.data.joint_names.index(name) for name in names]


def main() -> None:
    """Run the intentionally broken wiggle test."""
    sim_cfg = sim_utils.SimulationCfg(dt=0.005, device=args_cli.device)
    sim = SimulationContext(sim_cfg)
    sim.set_camera_view(eye=[0.65, -0.65, 0.45], target=[0.0, 0.0, 0.08])

    robot = spawn_quady_scene()
    sim.reset()

    print("[INFO] Quady bad-wiggle setup complete.")
    print("[WARNING] This script intentionally has a units bug: degrees are used as radians.")
    print_quady_summary(robot)

    neutral_target = reset_quady_to_default(robot)
    hip_ids = joint_ids(robot, HIP_JOINTS)
    knee_ids = joint_ids(robot, KNEE_JOINTS)

    # INTENTIONAL BUG:
    # The correct script uses math.radians(args_cli.hip_amp_deg).
    # This broken script uses the raw number directly, so 5 degrees becomes
    # 5 radians, which is about 286 degrees.
    hip_amp = args_cli.hip_amp_deg
    knee_amp = args_cli.knee_amp_deg

    print(f"[INFO] hip_ids={hip_ids}, knee_ids={knee_ids}")
    print(f"[WARNING] broken hip_amp={hip_amp:.3f} rad, broken knee_amp={knee_amp:.3f} rad")

    sim_dt = sim.get_physics_dt()
    step_count = 0

    while simulation_app.is_running():
        t = step_count * sim_dt
        phase = 2.0 * math.pi * t / args_cli.period

        joint_pos_target = neutral_target.clone()
        hip_offset = hip_amp * math.sin(phase)
        knee_offset = knee_amp * math.sin(phase + math.pi / 2.0)

        joint_pos_target[:, hip_ids] += hip_offset
        joint_pos_target[:, knee_ids] += knee_offset

        robot.set_joint_position_target_index(target=joint_pos_target)
        robot.write_data_to_sim()
        sim.step()
        robot.update(sim_dt)

        if step_count % 60 == 0:
            target = joint_pos_target.detach().cpu().numpy()[0]
            actual = robot.data.joint_pos.torch.detach().cpu().numpy()[0]
            print(
                "[INFO] "
                f"step={step_count} hip_offset={hip_offset:.3f} knee_offset={knee_offset:.3f} "
                f"target={target.round(3).tolist()} actual={actual.round(3).tolist()}"
            )

        step_count += 1
        if args_cli.headless and step_count >= args_cli.num_steps:
            break


if __name__ == "__main__":
    main()
    simulation_app.close()

