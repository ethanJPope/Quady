"""Shared Isaac Lab helpers for Quady scripts."""

from __future__ import annotations

import torch

import isaaclab.sim as sim_utils
from isaaclab.assets import Articulation
from isaaclab.sim import SimulationContext

from configs.quady_cfg import QUADY_CFG


def spawn_quady_scene() -> Articulation:
    """Create ground, light, and the Quady articulation."""
    ground_cfg = sim_utils.GroundPlaneCfg()
    ground_cfg.func("/World/defaultGroundPlane", ground_cfg)

    light_cfg = sim_utils.DomeLightCfg(intensity=2500.0, color=(0.8, 0.8, 0.8))
    light_cfg.func("/World/Light", light_cfg)

    return Articulation(QUADY_CFG)


def reset_quady_to_default(robot: Articulation) -> torch.Tensor:
    """Reset Quady to the configured default pose and return the joint target tensor."""
    root_pose = robot.data.default_root_pose.torch.clone()
    root_pose[:, 2] = 0.25
    robot.write_root_pose_to_sim_index(root_pose=root_pose)
    robot.write_root_velocity_to_sim_index(root_velocity=robot.data.default_root_vel.torch.clone())

    joint_pos = robot.data.default_joint_pos.torch.clone()
    joint_vel = torch.zeros_like(robot.data.default_joint_vel.torch)
    robot.write_joint_position_to_sim_index(position=joint_pos)
    robot.write_joint_velocity_to_sim_index(velocity=joint_vel)
    robot.reset()
    return joint_pos


def print_quady_summary(robot: Articulation) -> None:
    """Print the key names Isaac Lab found in the articulation."""
    print(f"[INFO] Spawned USD: {QUADY_CFG.spawn.usd_path}")
    print(f"[INFO] Body names: {robot.data.body_names}")
    print(f"[INFO] Joint names: {robot.data.joint_names}")

