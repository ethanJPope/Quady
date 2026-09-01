"""Slowly wiggle Quady joints around the neutral pose.

Run from the Isaac Lab checkout:

    isaaclab.bat -p "D:/Quady/Isaac Software/scripts/wiggle_quady.py" --viz kit

This verifies joint signs and basic actuator stability before building RL.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description="Wiggle Quady around its neutral pose.")
parser.add_argument("--num_steps", type=int, default=1200, help="Steps to run before closing in headless mode.")
parser.add_argument("--hip_amp_deg", type=float, default=5.0, help="Hip wiggle amplitude in degrees.")
parser.add_argument("--knee_amp_deg", type=float, default=7.0, help="Knee wiggle amplitude in degrees.")
parser.add_argument("--period", type=float, default=4.0, help="Wiggle period in seconds.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import torch

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
    """Run the wiggle test."""
    sim_cfg = sim_utils.SimulationCfg(dt=0.005, device=args_cli.device)
    sim = SimulationContext(sim_cfg)
    sim.set_camera_view(eye=[0.65, -0.65, 0.45], target=[0.0, 0.0, 0.08])

    robot = spawn_quady_scene()
    sim.reset()

    print("[INFO] Quady wiggle setup complete.")
    print_quady_summary(robot)

    neutral_target = reset_quady_to_default(robot)
    hip_ids = joint_ids(robot, HIP_JOINTS)
    knee_ids = joint_ids(robot, KNEE_JOINTS)
    hip_amp = math.radians(args_cli.hip_amp_deg)
    knee_amp = math.radians(args_cli.knee_amp_deg)

    print(f"[INFO] hip_ids={hip_ids}, knee_ids={knee_ids}")
    print(f"[INFO] hip_amp={hip_amp:.4f} rad, knee_amp={knee_amp:.4f} rad, period={args_cli.period:.2f}s")

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

        if step_count % 120 == 0:
            joint_pos = robot.data.joint_pos.torch.detach().cpu().numpy()[0]
            target = joint_pos_target.detach().cpu().numpy()[0]
            print(
                "[INFO] "
                f"step={step_count} hip_offset={hip_offset:.3f} knee_offset={knee_offset:.3f} "
                f"target={target.round(3).tolist()} actual={joint_pos.round(3).tolist()}"
            )

        step_count += 1
        if args_cli.headless and step_count >= args_cli.num_steps:
            break


if __name__ == "__main__":
    main()
    simulation_app.close()

