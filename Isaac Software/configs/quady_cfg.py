"""Isaac Lab articulation config for Quady.

This is the first simulation config for the current 8-servo Quady CAD export.
The joint positions are in radians and are measured from the imported CAD pose.
"""

from __future__ import annotations

from pathlib import Path

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import ArticulationCfg


ISAAC_SOFTWARE_DIR = Path(__file__).resolve().parents[1]
QUADY_USD_PATH = ISAAC_SOFTWARE_DIR / "usd" / "quady_5" / "quady.usda"

HIP_NEUTRAL_RAD = 0.349066  # 20 degrees
KNEE_NEUTRAL_RAD = -0.785398  # -45 degrees

HIP_JOINTS = [
    "front_left_hip_pitch",
    "front_right_hip_pitch",
    "rear_left_hip_pitch",
    "rear_right_hip_pitch",
]

KNEE_JOINTS = [
    "front_left_knee_pitch",
    "front_right_knee_pitch",
    "rear_left_knee_pitch",
    "rear_right_knee_pitch",
]

NEUTRAL_JOINT_POS = {
    **{joint_name: HIP_NEUTRAL_RAD for joint_name in HIP_JOINTS},
    **{joint_name: KNEE_NEUTRAL_RAD for joint_name in KNEE_JOINTS},
}

QUADY_CFG = ArticulationCfg(
    prim_path="/World/Quady",
    spawn=sim_utils.UsdFileCfg(
        usd_path=str(QUADY_USD_PATH),
        activate_contact_sensors=True,
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            disable_gravity=False,
            linear_damping=0.0,
            angular_damping=0.0,
            max_linear_velocity=1000.0,
            max_angular_velocity=1000.0,
            max_depenetration_velocity=1.0,
        ),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=False,
            solver_position_iteration_count=8,
            solver_velocity_iteration_count=2,
        ),
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        pos=(0.0, 0.0, 0.25),
        joint_pos=NEUTRAL_JOINT_POS,
    ),
    actuators={
        "legs": ImplicitActuatorCfg(
            joint_names_expr=[".*_hip_pitch", ".*_knee_pitch"],
            effort_limit_sim=3.0,
            velocity_limit_sim=5.0,
            stiffness=20.0,
            damping=2.0,
            armature=0.01,
        ),
    },
    soft_joint_pos_limit_factor=1.0,
)

