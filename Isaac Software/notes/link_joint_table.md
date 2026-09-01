# Quady Link And Joint Table

This file is the planning map for turning Quady from CAD into a robot articulation for URDF, USD, Isaac Sim, and Isaac Lab.

Rule: one link name should represent one rigid physical thing that moves as a single piece.

Current Quady design note: Ethan is using 2 servos per leg, 8 servos total. Earlier 12-DOF assumptions should not be used unless the CAD changes again.

Current CAD organization note: the Fusion assembly is not organized with CAD joints yet. The URDF joint axes are being inferred from the physical servo shaft directions and visual CAD screenshots.

## Link Inventory

- base_body

### Front Left Leg

- front_left_upper_leg
- front_left_lower_leg

### Front Right Leg

- front_right_upper_leg
- front_right_lower_leg

### Rear Left Leg

- rear_left_upper_leg
- rear_left_lower_leg

### Rear Right Leg

- rear_right_upper_leg
- rear_right_lower_leg

## Joint Table

Use this table to record the real CAD joint layout before writing the URDF.

Axis should use the robot coordinate frame:

- `1 0 0` = rotates around X
- `0 1 0` = rotates around Y
- `0 0 1` = rotates around Z

Recommended robot frame:

- X = forward
- Y = left
- Z = up

Axis conclusion for the current 8-servo design:

- Each hip and knee is a pitch joint.
- If the robot frame above is used, the pitch axis is `0 1 0` because the servo shaft points left-right across the robot.
- This was visually checked against side, top, and perspective CAD screenshots on 2026-06-15.

Origin measurement note:

- `fusion_geometry_dump.json` was generated from the open Fusion design on 2026-06-15.
- Fusion API geometry values are in centimeters; table values below are converted to meters.
- The origins below are assembly-frame coordinates from the current Fusion model.
- Current naming assumes the higher-X leg pair is the front pair and positive Y is the left side. Flip front/rear names if Fusion's forward direction is later defined the other way.

| Joint name | Parent link | Child link | Joint type | Axis | Origin xyz, meters | Origin notes | Limits |
|---|---|---|---|---|---|---|---|
| front_left_hip_pitch | base_body | front_left_upper_leg | revolute | `0 1 0` | `-0.025500 0.090975 0.000000` | inferred from upper-leg hip pivot cylinder | TBD |
| front_left_knee_pitch | front_left_upper_leg | front_left_lower_leg | revolute | `0 1 0` | `0.028382 0.090975 -0.053882` | inferred from matching upper/lower-leg knee pivot cylinders | TBD |
| front_right_hip_pitch | base_body | front_right_upper_leg | revolute | `0 1 0` | `-0.025500 -0.009025 0.000000` | inferred from upper-leg hip pivot cylinder | TBD |
| front_right_knee_pitch | front_right_upper_leg | front_right_lower_leg | revolute | `0 1 0` | `0.028382 -0.009025 -0.053882` | inferred from matching upper/lower-leg knee pivot cylinders | TBD |
| rear_left_hip_pitch | base_body | rear_left_upper_leg | revolute | `0 1 0` | `-0.175500 0.090975 0.000000` | inferred from upper-leg hip pivot cylinder | TBD |
| rear_left_knee_pitch | rear_left_upper_leg | rear_left_lower_leg | revolute | `0 1 0` | `-0.121618 0.090975 -0.053882` | inferred from matching upper/lower-leg knee pivot cylinders | TBD |
| rear_right_hip_pitch | base_body | rear_right_upper_leg | revolute | `0 1 0` | `-0.175500 -0.009025 0.000000` | inferred from upper-leg hip pivot cylinder | TBD |
| rear_right_knee_pitch | rear_right_upper_leg | rear_right_lower_leg | revolute | `0 1 0` | `-0.121618 -0.009025 -0.053882` | inferred from matching upper/lower-leg knee pivot cylinders | TBD |

## Mesh Export Checklist

Each final link should get a visual mesh. Collision meshes started as matching STL files, but the active URDF now uses simple primitive box collisions because the full visual STL collisions made Isaac Sim contact behavior look weird.

| Link | Visual mesh | Collision mesh | Exported? | Notes |
|---|---|---|---|---|
| base_body | meshes/visual/base_body.stl | meshes/collision/base_body.stl | yes | Exported from Fusion root body `Body` |
| front_left_upper_leg | meshes/visual/front_left_upper_leg.stl | meshes/collision/front_left_upper_leg.stl | yes | Exported from Fusion root body `Upper Leg (1)` |
| front_left_lower_leg | meshes/visual/front_left_lower_leg.stl | meshes/collision/front_left_lower_leg.stl | yes | Exported from Fusion root body `Lower Leg (1)` |
| front_right_upper_leg | meshes/visual/front_right_upper_leg.stl | meshes/collision/front_right_upper_leg.stl | yes | Exported from Fusion root body `Upper Leg` |
| front_right_lower_leg | meshes/visual/front_right_lower_leg.stl | meshes/collision/front_right_lower_leg.stl | yes | Exported from Fusion root body `Lower Leg` |
| rear_left_upper_leg | meshes/visual/rear_left_upper_leg.stl | meshes/collision/rear_left_upper_leg.stl | yes | Exported from Fusion root body `Upper Leg (1) (1) (1)` |
| rear_left_lower_leg | meshes/visual/rear_left_lower_leg.stl | meshes/collision/rear_left_lower_leg.stl | yes | Exported from Fusion root body `Lower Leg (1) (1) (1)` |
| rear_right_upper_leg | meshes/visual/rear_right_upper_leg.stl | meshes/collision/rear_right_upper_leg.stl | yes | Exported from Fusion root body `Upper Leg (1) (1)` |
| rear_right_lower_leg | meshes/visual/rear_right_lower_leg.stl | meshes/collision/rear_right_lower_leg.stl | yes | Exported from Fusion root body `Lower Leg (1) (1)` |

## URDF Status

- Initial URDF created at `urdf/quady.urdf`.
- XML validation passed on 2026-06-15.
- Mesh path check passed on the first mesh-based URDF: 18 mesh references, 0 missing files.
- Collision validation after the first Isaac Sim physics test: 9 primitive collision boxes, 0 collision mesh references.
- Primitive collision boxes are intentionally smaller than the visual meshes so the solver does not use detailed CAD surfaces as contact geometry.
- Current test hip limits are `0.0000` to `0.7854` rad, effort `3.0`, velocity `5.0`.
- Current test knee limits are `-1.5708` to `0.6981` rad, effort `3.0`, velocity `5.0`.
- These limits were set after Isaac Sim showed upper-leg geometry rotating through the base body with the earlier +/-90 and +/-60 degree placeholders.
- Inertial values are rough placeholders and should be tuned before serious simulation/training.

## USD Status

- URDF converted successfully with Isaac Lab on 2026-06-15.
- Main USD asset: `usd/quady/quady.usda`.
- Converter output includes PhysX and MuJoCo physics payloads.
- Generated USD inspection found 8 `PhysicsRevoluteJoint` entries with `physics:axis = "Y"`.
- First visual inspection in Isaac Sim: asset is visible and no warning text appeared on Play. It fell under gravity.
- Ethan's screen recording showed the legs stayed attached and rotated around the correct joints, but collision/contact looked weird. The likely cause was using full visual STL copies as collision meshes.
- The URDF was updated to use primitive box collisions and reconverted. The updated viewer stage now references `usd/quady_2/quady.usda`.
- `usd/quady_2/quady.usda` has position drives enabled from the URDF converter, using converter inputs `--joint-stiffness 20.0 --joint-damping 2.0 --joint-target-type position`. This makes joints act springy and snap back toward their target pose.
- `usd/quady_3/quady.usda` is the passive limited test asset, generated with `--joint-stiffness 0.0 --joint-damping 0.0 --joint-target-type none`. Use this for collision/range testing when manual dragging should not spring back.
- `usd/quady_4/quady.usda` is the current passive test asset with all 8 joints limited to 0 to +45 degrees.
- `usd/quady_5/quady.usda` is the current passive split-limit asset: hips 0 to +45 degrees, knees -90 to +40 degrees.
- `usd/quady_neutral_passive/quady.usda` is a copied passive split-limit asset with initial joint state positions set to hips +20 degrees and knees -45 degrees. Open it through `usd/quady_view_stage_neutral.usda`.
- Visible servo housings are not included in this first pass because only root body/leg bodies were exported into the URDF. Add visual-only ST3215 meshes later if needed.
- Troubleshooting note: `usd/quady/quady.usda` was once overwritten by Isaac Sim as an empty scene with `/World` and `/Environment`, which made frame-selection show nothing. It was restored and the empty overwritten file was backed up as `usd/quady/quady.empty-scene-backup.usda`.
- Safer visual-inspection stage: open `usd/quady_view_stage.usda`, which references the robot asset under `/World/Quady`.

## Open Questions

- Are the exported STL files in millimeters? If yes, the URDF mesh scale should probably be `0.001 0.001 0.001`.
- What are the real safe joint limits for the STS3215 servos in this mechanical design?
- Which direction is forward in the Fusion assembly?
- Confirm whether the higher-X leg pair should be named front or rear.
- Decide whether the URDF will use assembly-frame mesh coordinates or link-local mesh coordinates. This affects whether the table's assembly-frame origins can be used directly.
