"""Spawn Quady in Isaac Lab and hold a neutral pose.

Run from the Isaac Lab checkout:

    isaaclab.bat -p "D:/Quady/Isaac Software/scripts/spawn_quady.py" --viz kit

Use this as a smoke test before building training environments.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description="Spawn Quady and hold a neutral pose.")
parser.add_argument("--num_steps", type=int, default=240, help="Steps to run before closing in headless mode.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


import isaaclab.sim as sim_utils
from isaaclab.sim import SimulationContext


ISAAC_SOFTWARE_DIR = Path(__file__).resolve().parents[1]
if str(ISAAC_SOFTWARE_DIR) not in sys.path:
    sys.path.insert(0, str(ISAAC_SOFTWARE_DIR))

from configs.quady_cfg import NEUTRAL_JOINT_POS  # noqa: E402
from scripts.quady_sim_utils import print_quady_summary, reset_quady_to_default, spawn_quady_scene  # noqa: E402


def main() -> None:
    """Run the Quady spawn smoke test."""
    sim_cfg = sim_utils.SimulationCfg(dt=0.005, device=args_cli.device)
    sim = SimulationContext(sim_cfg)
    sim.set_camera_view(eye=[0.65, -0.65, 0.45], target=[0.0, 0.0, 0.08])

    robot = spawn_quady_scene()
    sim.reset()

    print("[INFO] Quady setup complete.")
    print_quady_summary(robot)
    print(f"[INFO] Neutral joint targets: {NEUTRAL_JOINT_POS}")

    joint_pos_target = reset_quady_to_default(robot)
    sim_dt = sim.get_physics_dt()
    step_count = 0

    while simulation_app.is_running():
        robot.set_joint_position_target_index(target=joint_pos_target)
        robot.write_data_to_sim()
        sim.step()
        robot.update(sim_dt)

        if step_count % 120 == 0:
            joint_pos = robot.data.joint_pos.torch.detach().cpu().numpy()[0]
            print(f"[INFO] step={step_count} joint_pos={joint_pos.round(3).tolist()}")

        step_count += 1
        if args_cli.headless and step_count >= args_cli.num_steps:
            break


if __name__ == "__main__":
    main()
    simulation_app.close()
