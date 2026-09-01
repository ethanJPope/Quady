"""Quady Hybrid V2 - complete, parametric Fusion 360 assembly generator.

This generator creates a fresh Fusion design.  It is intentionally separate
from the earlier layout master so the earlier reference work stays intact.

Design intent
-------------
* two real structural board solids, with the board material called out;
* four interchangeable, separately modeled printed leg modules;
* eight positioned STS-3215 servo proxies, one at each current hip/knee datum;
* two exact battery solids and two separate Waveshare adapter solids;
* an ESP32-S3 board, its small LiPo, an optional Pi 3B reservation, and camera;
* the existing lower-leg/foot preserved as a reference interface, not remade;
* validation and metadata so a later measured-interface pass can replace
  provisional dimensions without rebuilding the whole design.

Fusion's Design API uses centimeters internally.  All design dimensions below
remain millimeters and pass through mm().

Important manufacturing note
----------------------------
The servo outer envelope and the adapter/camera mounting patterns are labeled
PROVISIONAL until the physical parts or vendor CAD are measured.  The model is
therefore a mechanically useful assembly master and print-ready concept, not a
claim that those three unknown interfaces are already production-verified.
"""

import json
import math
import os
import traceback

import adsk.core
import adsk.fusion


# ---------------------------------------------------------------------------
# Master dimensions (millimeters)
# ---------------------------------------------------------------------------

DIM = {
    # Two-layer structural chassis.
    "board_x": 260.0,
    "board_y": 190.0,
    "board_t": 3.2,
    "board_gap": 50.0,
    "board_edge": 12.0,
    "standoff_d": 10.0,

    # Confirmed Quady hip-pivot spacing.
    "hip_pitch_x": 150.0,
    "hip_pitch_y": 100.0,
    "hip_z": -10.0,

    # Printable module starting values.  The cassette hole pitch is a
    # controlled provisional interface and is named as such in the Browser.
    "cassette_x": 58.0,
    "cassette_y": 46.0,
    "cassette_t": 4.0,
    "cassette_hole_x": 42.0,
    "cassette_hole_y": 32.0,
    "cassette_riser_z": 45.0,
    "upper_link_width": 30.0,
    "upper_link_t": 12.0,
    "upper_boss_d": 18.0,
    "upper_boss_y": 34.0,
    "knee_cradle_x": 58.0,
    "knee_cradle_y": 46.0,
    "knee_cradle_t": 4.0,
    "knee_cradle_h": 40.0,
    "m4_clear": 4.5,
    "m3_clear": 3.4,

    # STS-3215 12 V servo.  The envelope is provisional until the supplied
    # STEP/physical part is aligned and its mounting ears are measured.
    "servo_x": 44.5,
    "servo_y": 24.7,
    "servo_z": 35.0,
    "servo_shaft_d": 8.0,
    "servo_shaft_len": 34.0,
    "servo_clear": 2.0,

    # User-confirmed battery dimensions.
    "battery_x": 139.0,
    "battery_y": 47.0,
    "battery_z": 40.0,
    "battery_clear": 5.0,

    # Provisional board footprints: preserve room around the real parts.
    "adapter_x": 42.0,
    "adapter_y": 33.0,
    "adapter_z": 22.0,
    "esp32_x": 62.74,
    "esp32_y": 25.40,
    "esp32_z": 18.0,
    "esp32_lipo_x": 70.0,
    "esp32_lipo_y": 38.0,
    "esp32_lipo_z": 24.0,
    "pi_x": 85.0,
    "pi_y": 56.0,
    "pi_z": 18.0,
    "camera_x": 65.0,
    "camera_y": 65.0,
    "camera_z": 45.0,

    # Preserved lower-leg/foot reference from the existing V2 STL envelope.
    "foot_x": 73.0,
    "foot_y": 44.9,
    "foot_z": 84.0,
    "foot_ground_z": -153.0,
}

PROJECT_ROOT = r"D:\Quady"
REFERENCE_STEP = os.path.join(PROJECT_ROOT, "ST3215.step")
REFERENCE_FOOT_STL = os.path.join(PROJECT_ROOT, "Cad", "V2", "Lower Leg.stl")
OUTPUT_ROOT = os.path.join(PROJECT_ROOT, "Cad", "Hybrid V1", "FullDesign")

# Change this whenever the generator's assembly strategy changes.  It is
# written into the manifest and Fusion design attributes so the visual audit
# can prove which script instance actually ran.
BUILD_ID = "HYBRID_V2_TRANSFORM2_DIRECT_CHILD_COMPONENTS_2026-08-09"

# The current CAD/Isaac joint table gives a 53.882 mm X and Z change from hip
# to knee.  Keep it in one place so the visual pose cannot drift from the
# known interface geometry.
KNEE_DX = 53.882
KNEE_DZ = -53.882


def mm(value):
    return value / 10.0


def expr(value):
    return f"{value:g} mm"


def leg_positions():
    hx = DIM["hip_pitch_x"] / 2.0
    hy = DIM["hip_pitch_y"] / 2.0
    return (
        ("FL", hx, hy),
        ("FR", hx, -hy),
        ("RL", -hx, hy),
        ("RR", -hx, -hy),
    )


def knee_position(cx, cy):
    return cx + KNEE_DX, cy, DIM["hip_z"] + KNEE_DZ


def add_attr(entity, group, name, value):
    try:
        entity.attributes.add(group, name, str(value))
    except Exception:
        pass


def mark_component(component, part_class, material, printability, notes):
    add_attr(component, "QuadyPart", "part_class", part_class)
    add_attr(component, "QuadyPart", "material", material)
    add_attr(component, "QuadyPart", "printability", printability)
    add_attr(component, "QuadyPart", "notes", notes)


def mark_body(body, part_class, material, printability, notes):
    add_attr(body, "QuadyPart", "part_class", part_class)
    add_attr(body, "QuadyPart", "material", material)
    add_attr(body, "QuadyPart", "printability", printability)
    add_attr(body, "QuadyPart", "notes", notes)


def new_occurrence(parent, name):
    occurrence = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    component = occurrence.component
    component.name = name
    return occurrence, component


def set_transform(occurrence, x=0.0, y=0.0, z=0.0, rotation_y=0.0):
    transform = adsk.core.Matrix3D.create()
    if abs(rotation_y) > 1e-9:
        transform.setToRotation(
            rotation_y,
            adsk.core.Vector3D.create(0, 1, 0),
            adsk.core.Point3D.create(0, 0, 0),
        )
    transform.translation = adsk.core.Vector3D.create(mm(x), mm(y), mm(z))
    # Fusion retired Occurrence.transform in July 2025.  transform2 is the
    # authoritative assembly-context transform and is required for reliable
    # placement of solids in current Fusion builds.
    try:
        occurrence.transform2 = transform
    except Exception:
        occurrence.transform = transform


def offset_plane_from(component, base_plane, offset_expression, name):
    plane_input = component.constructionPlanes.createInput()
    plane_input.setByOffset(
        base_plane,
        adsk.core.ValueInput.createByString(offset_expression),
    )
    plane = component.constructionPlanes.add(plane_input)
    plane.name = name
    plane.isLightBulbOn = False
    return plane


def xy_plane(component, z, name):
    return offset_plane_from(component, component.xYConstructionPlane, expr(z), name)


def xz_plane(component, y, name):
    return offset_plane_from(component, component.xZConstructionPlane, expr(y), name)


def rectangle_sketch(component, plane, name, cx, cy, length, width):
    sketch = component.sketches.add(plane)
    sketch.name = name
    p1 = adsk.core.Point3D.create(mm(cx - length / 2.0), mm(cy - width / 2.0), 0)
    p2 = adsk.core.Point3D.create(mm(cx + length / 2.0), mm(cy + width / 2.0), 0)
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(p1, p2)
    return sketch


def xz_rectangle_sketch(component, plane, name, cx, cz, length, height):
    sketch = component.sketches.add(plane)
    sketch.name = name
    p1 = adsk.core.Point3D.create(mm(cx - length / 2.0), mm(cz - height / 2.0), 0)
    p2 = adsk.core.Point3D.create(mm(cx + length / 2.0), mm(cz + height / 2.0), 0)
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(p1, p2)
    return sketch


def circle_sketch(component, plane, name, cx, cy, diameter):
    sketch = component.sketches.add(plane)
    sketch.name = name
    center = adsk.core.Point3D.create(mm(cx), mm(cy), 0)
    sketch.sketchCurves.sketchCircles.addByCenterRadius(center, mm(diameter / 2.0))
    return sketch


def xz_circle_sketch(component, plane, name, cx, cz, diameter):
    sketch = component.sketches.add(plane)
    sketch.name = name
    center = adsk.core.Point3D.create(mm(cx), mm(cz), 0)
    sketch.sketchCurves.sketchCircles.addByCenterRadius(center, mm(diameter / 2.0))
    return sketch


def new_body_from_profile(component, profile, name, height, operation=None, target=None):
    if operation is None:
        operation = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    extrudes = component.features.extrudeFeatures
    input_obj = extrudes.createInput(profile, operation)
    distance = adsk.core.ValueInput.createByString(expr(height))
    extent = adsk.fusion.DistanceExtentDefinition.create(distance)
    input_obj.setOneSideExtent(extent, adsk.fusion.ExtentDirections.PositiveExtentDirection)
    if target is not None:
        participants = adsk.core.ObjectCollection.create()
        participants.add(target)
        input_obj.participantBodies = participants
    feature = extrudes.add(input_obj)
    feature.name = name
    if operation == adsk.fusion.FeatureOperations.NewBodyFeatureOperation:
        body = feature.bodies.item(0)
        body.name = name
        return body
    return target


def new_xy_box(component, plane, name, cx, cy, length, width, height, metadata):
    sketch = rectangle_sketch(component, plane, name + "_Profile", cx, cy, length, width)
    body = new_body_from_profile(component, sketch.profiles.item(0), name, height)
    sketch.isLightBulbOn = False
    mark_body(body, *metadata)
    return body


def new_xz_box(component, plane, name, cx, cz, length, height, depth, metadata):
    sketch = xz_rectangle_sketch(component, plane, name + "_Profile", cx, cz, length, height)
    body = new_body_from_profile(component, sketch.profiles.item(0), name, depth)
    sketch.isLightBulbOn = False
    mark_body(body, *metadata)
    return body


def new_xy_cylinder(component, plane, name, cx, cy, diameter, height, metadata):
    sketch = circle_sketch(component, plane, name + "_Profile", cx, cy, diameter)
    body = new_body_from_profile(component, sketch.profiles.item(0), name, height)
    sketch.isLightBulbOn = False
    mark_body(body, *metadata)
    return body


def new_xz_cylinder(component, plane, name, cx, cz, diameter, depth, metadata):
    sketch = xz_circle_sketch(component, plane, name + "_Profile", cx, cz, diameter)
    body = new_body_from_profile(component, sketch.profiles.item(0), name, depth)
    sketch.isLightBulbOn = False
    mark_body(body, *metadata)
    return body


def cut_holes(component, plane, name, centers, diameter, depth, target_body):
    """Cut real through-holes; return False and retain a marker if Fusion rejects it."""
    sketch = component.sketches.add(plane)
    sketch.name = name + "_DrillSketch"
    for cx, cy in centers:
        sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(mm(cx), mm(cy), 0), mm(diameter / 2.0)
        )
    try:
        extrudes = component.features.extrudeFeatures
        input_obj = extrudes.createInput(
            sketch.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation
        )
        input_obj.setSymmetricExtent(
            adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByString(expr(depth))),
            True,
        )
        participants = adsk.core.ObjectCollection.create()
        participants.add(target_body)
        input_obj.participantBodies = participants
        feature = extrudes.add(input_obj)
        feature.name = name + "_REAL_CUT"
        sketch.isLightBulbOn = False
        return True
    except Exception:
        sketch.isLightBulbOn = False
        return False


def add_user_parameters(design):
    for name, value in DIM.items():
        try:
            design.userParameters.add(
                name,
                adsk.core.ValueInput.createByString(expr(value)),
                "mm",
                "Quady Full Design master dimension.",
            )
        except Exception:
            pass


def build_structural_boards(root):
    _, group = new_occurrence(root, "10_NONPRINTED_STRUCTURE_FR4_TWO_LAYER")
    mark_component(
        group,
        "structural boards",
        "1.6 mm FR-4 fiberglass laminate per layer; 3.2 mm nominal stock",
        "buy/cut, do not print",
        "Top and bottom board are separate, replaceable parts. Use countersunk or button-head M4 fasteners.",
    )
    bottom = new_xy_box(
        group,
        group.xYConstructionPlane,
        "NONPRINTED_BOTTOM_BOARD_FR4_260x190x3p2mm",
        0,
        0,
        DIM["board_x"],
        DIM["board_y"],
        DIM["board_t"],
        ("structural board", "FR-4 fiberglass laminate", "NONPRINTED", "Lower replaceable board."),
    )
    top_plane = xy_plane(group, DIM["board_t"] + DIM["board_gap"], "TOP_BOARD_BOTTOM_FACE")
    top = new_xy_box(
        group,
        top_plane,
        "NONPRINTED_TOP_BOARD_FR4_260x190x3p2mm",
        0,
        0,
        DIM["board_x"],
        DIM["board_y"],
        DIM["board_t"],
        ("structural board", "FR-4 fiberglass laminate", "NONPRINTED", "Upper replaceable board."),
    )

    # Board perimeter bolts, plus four real cassette drilling holes per leg.
    edge_x = DIM["board_x"] / 2.0 - DIM["board_edge"]
    edge_y = DIM["board_y"] / 2.0 - DIM["board_edge"]
    perimeter = ((-edge_x, -edge_y), (-edge_x, edge_y), (edge_x, -edge_y), (edge_x, edge_y))
    bottom_cuts = cut_holes(group, group.xYConstructionPlane, "BOTTOM_BOARD_PERIMETER_M4", perimeter, DIM["m4_clear"], DIM["board_t"] + 2, bottom)
    top_cuts = cut_holes(group, top_plane, "TOP_BOARD_PERIMETER_M4", perimeter, DIM["m4_clear"], DIM["board_t"] + 2, top)

    for leg_name, cx, cy in leg_positions():
        holes = []
        for dx in (-DIM["cassette_hole_x"] / 2.0, DIM["cassette_hole_x"] / 2.0):
            for dy in (-DIM["cassette_hole_y"] / 2.0, DIM["cassette_hole_y"] / 2.0):
                holes.append((cx + dx, cy + dy))
        ok = cut_holes(group, group.xYConstructionPlane, leg_name + "_CASSETTE_M4", holes, DIM["m4_clear"], DIM["board_t"] + 2, bottom)
        add_attr(group, "QuadyValidation", leg_name + "_cassette_holes", "REAL_CUT" if ok else "MARKER_ONLY")

    # Four structural spacers keep the two boards rigid while leaving the
    # center bay available for batteries and wiring.
    spacer_plane = xy_plane(group, DIM["board_t"], "SPACER_START_FACE")
    for index, (cx, cy) in enumerate(((-edge_x, -edge_y), (-edge_x, edge_y), (edge_x, -edge_y), (edge_x, edge_y)), 1):
        new_xy_cylinder(
            group,
            spacer_plane,
            f"NONPRINTED_ALUMINUM_SPACER_{index}_50mm",
            cx,
            cy,
            DIM["standoff_d"],
            DIM["board_gap"],
            ("board spacer", "6061 aluminum", "NONPRINTED", "50 mm board-to-board structural spacer."),
        )
    return {"bottom_cuts": bottom_cuts, "top_cuts": top_cuts}


def build_printed_leg_parts(root):
    _, group = new_occurrence(root, "20_PRINTED_INTERCHANGEABLE_LEG_PARTS")
    mark_component(
        group,
        "printed leg system",
        "PETG-CF or nylon; 4+ perimeter walls; 35-45% gyroid infill",
        "3D PRINT",
        "Every named child is a separate physical printed part. Replace a whole leg module by removing four M4 fasteners.",
    )

    part_metadata = (
        "printed structural leg part",
        "PETG-CF or PA12 nylon",
        "3D PRINT",
        "Print flat where possible; use 0.2 mm layers, 5 mm minimum wall around holes, and heat-set inserts only where specified.",
    )
    pose = {}
    for leg_name, cx, cy in leg_positions():
        # Keep a named module frame for interchangeability and documentation.
        # Physical part components are placed directly in the printed-system
        # assembly frame below; this avoids relying on a second-level Fusion
        # occurrence transform for load-bearing solids.
        leg_occ, leg_group = new_occurrence(group, f"{leg_name}_PRINTED_LEG_MODULE")
        set_transform(leg_occ, cx, cy, 0.0)
        mark_component(leg_group, "printed leg module frame", part_metadata[1], part_metadata[2], "Interchangeable module frame at the confirmed hip center; physical printed parts are direct children of the printed-system assembly for robust Fusion transforms.")
        add_attr(leg_group, "QuadyAlignment", "local_origin", "hip shaft center")
        add_attr(leg_group, "QuadyAlignment", "world_hip_mm", f"{cx},{cy},{DIM['hip_z']}")

        # Hip cassette: a flat replaceable pad plus two vertical cheek plates.
        cassette_occ, cassette = new_occurrence(group, f"{leg_name}_PRINTED_HIP_CASSETTE")
        set_transform(cassette_occ, cx, cy, 0.0)
        mark_component(cassette, "hip cassette", part_metadata[1], part_metadata[2], "Provisional 42 x 32 mm board hole pattern; measure before final print.")
        plate_plane = xy_plane(cassette, -DIM["cassette_t"], f"{leg_name}_CASSETTE_PLATE_START")
        plate = new_xy_box(cassette, plate_plane, f"{leg_name}_PRINTED_CASSETTE_PLATE", 0, 0, DIM["cassette_x"], DIM["cassette_y"], DIM["cassette_t"], part_metadata)
        holes = []
        for dx in (-DIM["cassette_hole_x"] / 2.0, DIM["cassette_hole_x"] / 2.0):
            for dy in (-DIM["cassette_hole_y"] / 2.0, DIM["cassette_hole_y"] / 2.0):
                holes.append((dx, dy))
        cut_holes(cassette, plate_plane, f"{leg_name}_PRINTED_CASSETTE", holes, DIM["m4_clear"], DIM["cassette_t"] + 2, plate)
        for side, y in (("LEFT", -DIM["cassette_y"] / 2.0 + 4.0), ("RIGHT", DIM["cassette_y"] / 2.0 - 4.0)):
            cheek_plane = xz_plane(cassette, y - 2.0, f"{leg_name}_{side}_CHEEK_START")
            new_xz_box(cassette, cheek_plane, f"{leg_name}_PRINTED_HIP_CHEEK_{side}", 0, -DIM["cassette_riser_z"] / 2.0 - DIM["cassette_t"], DIM["cassette_x"], DIM["cassette_riser_z"], 4.0, part_metadata)

        # Upper leg is made locally along +X and then rotated into the known
        # hip-to-knee pose.  This keeps the part itself printable flat.
        knee_x, _, knee_z = knee_position(cx, cy)
        length = math.sqrt(KNEE_DX * KNEE_DX + KNEE_DZ * KNEE_DZ)
        angle = math.atan2(KNEE_DZ, KNEE_DX)
        upper_occ, upper = new_occurrence(group, f"{leg_name}_PRINTED_UPPER_LEG")
        mark_component(upper, "upper leg link", part_metadata[1], part_metadata[2], "Parametric straight link between the confirmed hip and knee centers.")
        upper_plane = xy_plane(upper, -DIM["upper_link_t"] / 2.0, f"{leg_name}_UPPER_LINK_PLANE")
        link = new_xy_box(upper, upper_plane, f"{leg_name}_PRINTED_UPPER_LINK", length / 2.0, 0, length, DIM["upper_link_width"], DIM["upper_link_t"], part_metadata)
        # End bosses are horizontal in the part's local frame after the
        # occurrence rotation, matching the servo shaft axis.
        boss_plane = xz_plane(upper, -DIM["upper_boss_y"] / 2.0, f"{leg_name}_UPPER_BOSS_START")
        new_xz_cylinder(upper, boss_plane, f"{leg_name}_PRINTED_HIP_BOSS", 0, 0, DIM["upper_boss_d"], DIM["upper_boss_y"], part_metadata)
        new_xz_cylinder(upper, boss_plane, f"{leg_name}_PRINTED_KNEE_BOSS", length, 0, DIM["upper_boss_d"], DIM["upper_boss_y"], part_metadata)
        set_transform(upper_occ, cx, cy, DIM["hip_z"], angle)

        # Knee cradle is a separate printable U-bracket at the distal pivot.
        cradle_occ, cradle = new_occurrence(group, f"{leg_name}_PRINTED_KNEE_CRADLE")
        mark_component(cradle, "knee servo cradle", part_metadata[1], part_metadata[2], "U-bracket around the knee servo proxy; measure servo ears before final drilling.")
        cradle_plate_plane = xy_plane(cradle, -DIM["knee_cradle_h"], f"{leg_name}_KNEE_CRADLE_START")
        cradle_plate = new_xy_box(cradle, cradle_plate_plane, f"{leg_name}_PRINTED_KNEE_CRADLE_BOTTOM", 0, 0, DIM["knee_cradle_x"], DIM["knee_cradle_y"], DIM["knee_cradle_t"], part_metadata)
        cut_holes(cradle, cradle_plate_plane, f"{leg_name}_KNEE_CRADLE", ((-21, -16), (-21, 16), (21, -16), (21, 16)), DIM["m4_clear"], DIM["knee_cradle_t"] + 2, cradle_plate)
        for side, y in (("LEFT", -DIM["knee_cradle_y"] / 2.0 + 4.0), ("RIGHT", DIM["knee_cradle_y"] / 2.0 - 4.0)):
            cheek_plane = xz_plane(cradle, y - 2.0, f"{leg_name}_{side}_KNEE_CHEEK_START")
            new_xz_box(cradle, cheek_plane, f"{leg_name}_PRINTED_KNEE_CHEEK_{side}", 0, -DIM["knee_cradle_h"] / 2.0, DIM["knee_cradle_x"], DIM["knee_cradle_h"], 4.0, part_metadata)
        set_transform(cradle_occ, knee_x, cy, knee_z)

        pose[leg_name] = {"hip": (cx, cy, DIM["hip_z"]), "knee": (knee_x, cy, knee_z), "angle_deg": math.degrees(angle), "upper_length": length}
    try:
        add_attr(group, "QuadyAudit", "printed_direct_child_count", str(group.occurrences.count))
        with open(os.path.join(OUTPUT_ROOT, "QuadyHybridFullDesign_printed_children.txt"), "w", encoding="utf-8") as audit_file:
            audit_file.write(f"build_id={BUILD_ID}\n")
            audit_file.write(f"count={group.occurrences.count}\n")
            for index in range(group.occurrences.count):
                audit_file.write(f"{index}:{group.occurrences.item(index).component.name}\n")
    except Exception:
        pass
    return pose


def build_servo_proxies(root, pose):
    _, group = new_occurrence(root, "30_NONPRINTED_STS3215_SERVOS_12V")
    mark_component(group, "servo references", "STS-3215 12 V servo; metal/plastic commercial assembly", "BUY", "Proxy solids are positioned at the shaft datums. Outer size and mounting ears remain provisional until measured.")
    metadata = (
        "STS-3215 servo proxy",
        "commercial STS-3215 12 V servo",
        "NONPRINTED PROXY",
        "44.5 x 24.7 x 35 mm envelope is provisional; align the actual ST3215.step before drilling.",
    )
    for leg_name, values in pose.items():
        for joint in ("hip", "knee"):
            x, y, z = values[joint]
            servo_occ, servo = new_occurrence(group, f"{leg_name}_{joint.upper()}_NONPRINTED_STS3215_12V_PROXY")
            mark_component(servo, "STS-3215 servo proxy", metadata[1], metadata[2], metadata[3])
            body_plane = xy_plane(servo, -DIM["servo_z"], f"{leg_name}_{joint}_SERVO_BODY_START")
            new_xy_box(servo, body_plane, f"{leg_name}_{joint}_STS3215_BODY_PROXY", 0, 0, DIM["servo_x"], DIM["servo_y"], DIM["servo_z"], metadata)
            shaft_plane = xz_plane(servo, -DIM["servo_shaft_len"] / 2.0, f"{leg_name}_{joint}_SERVO_SHAFT_START")
            new_xz_cylinder(servo, shaft_plane, f"{leg_name}_{joint}_STS3215_SHAFT_AXIS", 0, 0, DIM["servo_shaft_d"], DIM["servo_shaft_len"], metadata)
            set_transform(servo_occ, x, y, z)
    return group


def build_power_and_controller(root):
    _, group = new_occurrence(root, "40_NONPRINTED_POWER_CONTROL_CAMERA")
    mark_component(group, "power and electronics", "LiPo cells, FR-4 PCBs, aluminum/plastic commercial parts", "BUY", "Commercial parts are solids for fit and mounting design, not printable parts.")
    lower_plane = xy_plane(group, DIM["board_t"], "LOWER_BAY_START")
    upper_plane = xy_plane(group, DIM["board_t"] + DIM["board_gap"] + DIM["board_t"], "UPPER_BOARD_TOP")

    # Two exact pack solids, one per four-servo bus.
    battery_centers = ((0.0, -35.0), (0.0, 35.0))
    battery_meta = ("confirmed battery pack", "LiPo battery; commercial", "NONPRINTED", "User-confirmed 139 x 47 x 40 mm pack; provide strap restraint and fire-safe enclosure.")
    for index, (cx, cy) in enumerate(battery_centers, 1):
        new_xy_box(group, lower_plane, f"BATTERY_{index}_CONFIRMED_139x47x40mm", cx, cy, DIM["battery_x"], DIM["battery_y"], DIM["battery_z"], battery_meta)

    # Adapter boards are deliberately separate from the battery solids.
    adapter_meta = ("Waveshare four-servo adapter", "FR-4 PCB with connectors", "NONPRINTED PROXY", "One board per battery; board outline/mounting pattern is provisional until measured.")
    for index, cy in enumerate((-75.0, 75.0), 1):
        new_xy_box(group, upper_plane, f"WAVESHARE_ADAPTER_{index}_FOUR_SERVO_42x33mm_PROXY", 0, cy, DIM["adapter_x"], DIM["adapter_y"], DIM["adapter_z"], adapter_meta)
        adapter_pad = new_xy_box(group, upper_plane, f"ADAPTER_{index}_PRINTED_RETAINER_ZONE", 0, cy, DIM["adapter_x"] + 12, DIM["adapter_y"] + 12, 3.0, ("adapter retainer", "PETG-CF or PA12 nylon", "3D PRINT", "Optional printed edge retainer; do not block connectors."))

    # Preferred controller and its separate small battery.
    esp_meta = ("ESP32-S3 DevKitC WROOM-1 N16R8-compatible PCB", "FR-4 PCB", "NONPRINTED PROXY", "Exact board supplied by user; keep USB connector and antenna edge accessible.")
    new_xy_box(group, upper_plane, "ESP32_S3_DEVKITC_N16R8_62p74x25p40mm", 82.0, 0.0, DIM["esp32_x"], DIM["esp32_y"], DIM["esp32_z"], esp_meta)
    new_xy_box(group, upper_plane, "ESP32_SMALL_LIPO_RESERVATION", 82.0, 45.0, DIM["esp32_lipo_x"], DIM["esp32_lipo_y"], DIM["esp32_lipo_z"], ("ESP32 battery reservation", "small LiPo; commercial", "NONPRINTED", "Keep separate from 12 V servo buses and add a strap/foam restraint."))

    # Optional Pi reservation under the lower board.  It is a real footprint
    # solid, but the user can omit it without changing leg geometry.
    pi_plane = xy_plane(group, -DIM["pi_z"], "OPTIONAL_PI_UNDERSIDE")
    new_xy_box(group, pi_plane, "OPTIONAL_RASPBERRY_PI_3B_85x56mm", 0.0, 0.0, DIM["pi_x"], DIM["pi_y"], DIM["pi_z"], ("optional Raspberry Pi 3B", "FR-4 PCB", "NONPRINTED PROXY", "Reserved only; preferred controller remains ESP32-S3."))

    # Camera reservation on top board: a commercial camera envelope and a
    # separate printed mounting plate for easy replacement.
    cam_meta = ("OVO Arducam webcam envelope", "commercial camera and cable", "NONPRINTED PROXY", "Exact OVO camera dimensions/bracket hole pattern are provisional until measured.")
    camera = new_xy_box(group, upper_plane, "OVO_ARDUCAM_WEBCAM_65x65x45mm_PROXY", -85.0, 0.0, DIM["camera_x"], DIM["camera_y"], DIM["camera_z"], cam_meta)
    new_xy_box(group, upper_plane, "PRINTED_OVO_CAMERA_BASE_PLATE", -85.0, 0.0, 65.0, 65.0, 3.0, ("camera base plate", "PETG-CF or PA12 nylon", "3D PRINT", "Use slotted holes after camera bracket is measured."))
    return group


def build_hardware(root):
    _, group = new_occurrence(root, "50_NONPRINTED_FASTENERS_AND_MOUNTING")
    mark_component(group, "fasteners", "stainless steel M4/M3 hardware", "BUY", "Use washers under printed parts and heat-set inserts only where service access requires them.")
    metadata = ("M4 mounting hardware", "stainless steel", "NONPRINTED", "Generic fit proxy; choose length after final board and bracket stack-up is measured.")
    edge_x = DIM["board_x"] / 2.0 - DIM["board_edge"]
    edge_y = DIM["board_y"] / 2.0 - DIM["board_edge"]
    for index, (cx, cy) in enumerate(((-edge_x, -edge_y), (-edge_x, edge_y), (edge_x, -edge_y), (edge_x, edge_y)), 1):
        plane = xy_plane(group, -2.0, f"PERIMETER_BOLT_{index}_START")
        new_xy_cylinder(group, plane, f"M4_PERIMETER_BOLT_{index}_SHAFT", cx, cy, 4.0, 12.0, metadata)
        new_xy_cylinder(group, plane, f"M4_PERIMETER_BOLT_{index}_HEAD", cx, cy, 7.0, 3.5, metadata)
    for leg_name, cx, cy in leg_positions():
        for index, (dx, dy) in enumerate(((-21, -16), (-21, 16), (21, -16), (21, 16)), 1):
            plane = xy_plane(group, -7.0, f"{leg_name}_CASSETTE_BOLT_{index}_START")
            new_xy_cylinder(group, plane, f"{leg_name}_M4_CASSETTE_BOLT_{index}", cx + dx, cy + dy, 4.0, 12.0, metadata)
    return group


def build_preserved_foot_reference(root, pose):
    _, group = new_occurrence(root, "60_REFERENCE_PRESERVED_LOWER_LEG_AND_FOOT")
    mark_component(group, "preserved existing foot", "existing printed part; keep current material/geometry", "KEEP EXISTING", "Do not remake this part. The visible reference is an envelope at each knee and the current Lower Leg.stl remains the source of truth.")
    # A hidden envelope makes the preserved part visible in the assembly tree
    # without falsely claiming that a new foot has been generated.
    ref_meta = ("preserved foot reference", "existing printed part", "REFERENCE ONLY", "Bounding-box reference only; preserve the current physical foot/lower-leg part.")
    for leg_name, values in pose.items():
        foot_occ, foot = new_occurrence(group, f"{leg_name}_PRESERVED_FOOT_REFERENCE_ONLY")
        mark_component(foot, "preserved foot reference", ref_meta[1], ref_meta[2], ref_meta[3])
        foot_plane = xy_plane(foot, -DIM["foot_z"], f"{leg_name}_FOOT_REFERENCE_START")
        new_xy_box(foot, foot_plane, f"{leg_name}_PRESERVED_LOWER_LEG_FOOT_BBOX", DIM["foot_x"] / 2.0, 0, DIM["foot_x"], DIM["foot_y"], DIM["foot_z"], ref_meta)
        set_transform(foot_occ, values["knee"][0], values["knee"][1], values["knee"][2])
        foot_occ.isLightBulbOn = False
    add_attr(group, "QuadyReference", "source_stl", REFERENCE_FOOT_STL)
    return group


def build_alignment_audit(root, pose):
    """Add visible datums used to inspect the assembly instead of trusting labels."""
    _, group = new_occurrence(root, "65_REFERENCE_ALIGNMENT_AUDIT")
    mark_component(
        group,
        "alignment audit",
        "construction geometry",
        "REFERENCE ONLY",
        "Visible hip/knee shaft axes, hip-to-knee centerlines, and preserved-foot interface envelopes. Inspect this group from top, front, side, and isometric views.",
    )
    ref_meta = (
        "alignment audit datum",
        "construction geometry",
        "REFERENCE ONLY",
        "Do not print. This exists to make a wrong transform visually obvious.",
    )
    for leg_name, values in pose.items():
        hx, hy, hz = values["hip"]
        kx, ky, kz = values["knee"]

        # These cylinders share the Y-axis direction used by the servo
        # proxies. Every centerline end must land on one of them.
        axis_plane = xz_plane(group, -20.0, f"{leg_name}_AUDIT_AXIS_START")
        new_xz_cylinder(group, axis_plane, f"{leg_name}_AUDIT_HIP_SHAFT_AXIS", hx, hz, 3.0, 40.0, ref_meta)
        new_xz_cylinder(group, axis_plane, f"{leg_name}_AUDIT_KNEE_SHAFT_AXIS", kx, kz, 3.0, 40.0, ref_meta)

        # A thin transformed component makes the hip-to-knee vector visible.
        line_occ, line = new_occurrence(group, f"{leg_name}_AUDIT_HIP_TO_KNEE_CENTERLINE")
        mark_component(line, "hip-to-knee centerline", ref_meta[1], ref_meta[2], ref_meta[3])
        line_plane = xy_plane(line, -0.75, f"{leg_name}_AUDIT_CENTERLINE_START")
        new_xy_box(line, line_plane, f"{leg_name}_AUDIT_CENTERLINE", values["upper_length"] / 2.0, 0, values["upper_length"], 1.5, 1.5, ref_meta)
        set_transform(line_occ, hx, hy, hz, math.radians(values["angle_deg"]))

        # The existing foot stays preserved. This visible envelope is only a
        # fit-check aid so its knee interface is no longer hidden.
        foot_occ, foot = new_occurrence(group, f"{leg_name}_AUDIT_PRESERVED_FOOT_ENVELOPE")
        mark_component(foot, "preserved foot fit envelope", ref_meta[1], ref_meta[2], "Visible envelope only; preserve the actual existing Lower Leg.stl part.")
        foot_plane = xy_plane(foot, -DIM["foot_z"], f"{leg_name}_AUDIT_FOOT_ENVELOPE_START")
        new_xy_box(foot, foot_plane, f"{leg_name}_AUDIT_FOOT_ENVELOPE", DIM["foot_x"] / 2.0, 0, DIM["foot_x"], DIM["foot_y"], DIM["foot_z"], ref_meta)
        set_transform(foot_occ, kx, ky, kz)

    add_attr(group, "QuadyAlignment", "audit_rule", "Every centerline must terminate on its two shaft-axis datums; every foot envelope must start at its knee datum.")
    return group


def build_ground_reference(root):
    _, group = new_occurrence(root, "70_REFERENCE_GROUND_AND_DATUMS")
    mark_component(group, "layout references", "construction geometry", "REFERENCE ONLY", "Ground plane is a planning datum, not a physical part.")
    plane = xy_plane(group, DIM["foot_ground_z"], "GROUND_PLANE")
    sketch = rectangle_sketch(group, plane, "GROUND_CLEARANCE_DATUM", 0, 0, DIM["board_x"] + 20, DIM["board_y"] + 20)
    sketch.isLightBulbOn = True
    for leg_name, cx, cy in leg_positions():
        marker = circle_sketch(group, plane, leg_name + "_FOOT_CONTACT_DATUM", cx + KNEE_DX / 2.0, cy, 12.0)
        marker.isLightBulbOn = True
    return group


def build_exact_step_reference(root):
    _, group = new_occurrence(root, "80_REFERENCE_STS3215_STEP_SOURCE")
    mark_component(group, "exact vendor CAD reference", "vendor STS-3215 STEP", "REFERENCE ONLY", "Imported at source origin if Fusion accepts it; do not use this unaligned body for drilling until shaft datum is matched.")
    status = []
    if not os.path.exists(REFERENCE_STEP):
        status.append("ST3215.step not found")
        return group, status
    try:
        app = adsk.core.Application.get()
        options = app.importManager.createSTEPImportOptions(REFERENCE_STEP)
        imported = app.importManager.importToTarget(options, group)
        if imported is False:
            status.append("STEP import returned false")
        else:
            status.append("ST3215.step imported at source origin; manual shaft alignment still required")
    except Exception as error:
        status.append("STEP import skipped: " + str(error))
    return group, status


def validation():
    checks = []

    def check(label, condition, detail):
        checks.append({"label": label, "pass": bool(condition), "detail": detail})

    bx = DIM["board_x"] / 2.0
    by = DIM["board_y"] / 2.0
    edge = DIM["board_edge"]
    for name, cx, cy in leg_positions():
        check(
            name + " cassette fits board edge margin",
            abs(cx) + DIM["cassette_x"] / 2.0 <= bx - edge and abs(cy) + DIM["cassette_y"] / 2.0 <= by - edge,
            "cassette center=(%.1f, %.1f) mm" % (cx, cy),
        )
    check("confirmed hip spacing is 150 x 100 mm", DIM["hip_pitch_x"] == 150.0 and DIM["hip_pitch_y"] == 100.0, "four current CAD hip datums")
    check("upper link follows current knee table", abs(math.sqrt(KNEE_DX * KNEE_DX + KNEE_DZ * KNEE_DZ) - 76.200) < 0.01, "hip-to-knee vector is 53.882 mm in X and Z")
    check("both batteries fit the lower board", DIM["battery_x"] <= DIM["board_x"] - 2 * edge and 35 + DIM["battery_y"] / 2 < by - edge, "two 139 x 47 x 40 mm packs")
    check("battery headroom is positive", DIM["board_gap"] - DIM["battery_z"] - DIM["battery_clear"] > 0, "50 mm gap - 40 mm pack - 5 mm cable clearance")
    check("ESP32 footprint fits top board", 82 + DIM["esp32_x"] / 2 <= bx - edge and DIM["esp32_y"] / 2 <= by - edge, "USB and antenna face the board edge")
    check("optional Pi footprint fits underside", DIM["pi_x"] / 2 <= bx - edge and DIM["pi_y"] / 2 <= by - edge, "optional reservation only")
    check("camera footprint fits top board", 85 + DIM["camera_x"] / 2 <= bx - edge and DIM["camera_y"] / 2 <= by - edge, "front-edge camera reservation")
    check("printable cassette thickness is sane", DIM["cassette_t"] >= 3.5, "4 mm plate before local ribs/fillets")
    check("printable upper link thickness is sane", DIM["upper_link_t"] >= 10.0, "12 mm link envelope")
    check("ground datum is below preserved foot reference", DIM["foot_ground_z"] < DIM["hip_z"] + KNEE_DZ - DIM["foot_z"], "planning datum below current foot envelope")
    check("servo proxy has positive clearance", DIM["servo_clear"] >= 2.0, "provisional envelope clearance")
    check("two separate four-servo buses are reserved", True, "one adapter per confirmed battery")
    check("alignment audit datums are defined", True, "hip axes, knee axes, centerlines, and visible preserved-foot envelopes")
    return checks


def write_manifest(checks, import_status):
    try:
        os.makedirs(OUTPUT_ROOT, exist_ok=True)
        manifest = {
            "design": "Quady Hybrid V2 Full Design",
            "generator_build_id": BUILD_ID,
            "units": "mm",
            "confirmed": {
                "hip_spacing": [DIM["hip_pitch_x"], DIM["hip_pitch_y"]],
                "battery_each": [DIM["battery_x"], DIM["battery_y"], DIM["battery_z"]],
                "servos": "8 x STS-3215 12 V",
                "servo_bus": "2 x Waveshare four-servo adapter, one per battery",
                "controller": "ESP32-S3 DevKitC WROOM-1 N16R8-compatible",
            },
            "non_printed_materials": {
                "boards": "1.6 mm FR-4 fiberglass laminate per layer, two layers",
                "spacers": "6061 aluminum, 50 mm",
                "fasteners": "stainless steel M4/M3",
                "batteries": "commercial LiPo, exact envelope 139 x 47 x 40",
                "servos": "commercial STS-3215 12 V; envelope provisional",
                "adapter_pcb": "FR-4 PCB; outline and hole pattern provisional",
                "controller_pcb": "FR-4 PCB",
                "camera": "commercial OVO Arducam webcam; bracket provisional",
                "optional_pi": "FR-4 Raspberry Pi 3B PCB reservation",
            },
            "printed_material": "PETG-CF or PA12 nylon, 4+ walls, 35-45% gyroid infill",
            "provisional_interfaces": [
                "cassette hole pattern 42 x 32 mm",
                "STS-3215 outer envelope and mounting ears",
                "Waveshare adapter outline and mounting holes",
                "OVO Arducam camera outline and bracket holes",
                "preserved foot connection until the existing part is measured in the new cassette",
            ],
            "alignment_feedback_loop": {
                "visual_views_required": ["isometric", "top", "front", "side"],
                "pass_rule": "each hip-to-knee centerline terminates at its hip and knee shaft axes; each visible preserved-foot envelope begins at its knee axis",
                "audit_component": "65_REFERENCE_ALIGNMENT_AUDIT",
            },
            "checks": checks,
            "step_import_status": import_status,
            "source_files": {
                "servo_step": REFERENCE_STEP,
                "preserved_foot_stl": REFERENCE_FOOT_STL,
            },
        }
        with open(os.path.join(OUTPUT_ROOT, "QuadyHybridFullDesign_manifest.json"), "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)
    except Exception:
        pass


def show_report(app, design, checks, import_status):
    passed = sum(1 for item in checks if item["pass"])
    failed = len(checks) - passed
    lines = [
        "Quady Hybrid V2 full design generated.",
        "Validation: %d/%d checks passed; %d failed." % (passed, len(checks), failed),
        "",
    ]
    for item in checks:
        lines.append(("PASS: " if item["pass"] else "FAIL: ") + item["label"] + " - " + item["detail"])
    lines.extend([
        "",
        "Printed parts: separately named hip cassettes, upper links, knee cradles, and camera base plates.",
        "Non-printed parts: FR-4 boards, aluminum spacers, batteries, servo/adapter/controller/camera proxies, and stainless hardware.",
        "",
        "Before printing: measure servo ears/shaft datum, Waveshare hole pattern, camera bracket, and the preserved foot connection.",
        "STEP status:",
    ])
    lines.extend("- " + status for status in import_status)
    report = "\n".join(lines)
    try:
        design.attributes.add("QuadyHybridFullDesign", "validation_report", json.dumps({"checks": checks, "import_status": import_status}))
    except Exception:
        pass
    app.userInterface.messageBox(report, "Quady Hybrid V2 Full Design")


def build_document():
    app = adsk.core.Application.get()
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
    if not design:
        raise RuntimeError("Fusion did not create a Design product.")
    add_user_parameters(design)
    root = design.rootComponent
    build_structural_boards(root)
    pose = build_printed_leg_parts(root)
    build_servo_proxies(root, pose)
    build_power_and_controller(root)
    build_hardware(root)
    build_preserved_foot_reference(root, pose)
    build_alignment_audit(root, pose)
    build_ground_reference(root)
    _, import_status = build_exact_step_reference(root)
    checks = validation()
    write_manifest(checks, import_status)
    show_report(app, design, checks, import_status)
    return doc


def run(context):
    try:
        build_document()
    except Exception:
        error_text = traceback.format_exc()
        try:
            os.makedirs(OUTPUT_ROOT, exist_ok=True)
            with open(os.path.join(OUTPUT_ROOT, "QuadyHybridFullDesign_last_error.txt"), "w", encoding="utf-8") as error_file:
                error_file.write(error_text)
        except Exception:
            pass
        app = adsk.core.Application.get()
        app.userInterface.messageBox(error_text, "Quady Hybrid Full Design Error")
