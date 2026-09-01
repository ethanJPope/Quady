"""Quady Hybrid V1 - complete Fusion 360 assembly generator.

This script creates a new Fusion design. It does not open, modify, or
overwrite Quady V1/V2 files.

The result is a high-quality layout master for the hybrid robot:

* two structural board layers;
* four interchangeable leg-cassette interfaces at the confirmed 150 x 100
  mm hip-pivot spacing;
* two 139 x 47 x 40 mm hidden pack references inside larger clearance bays;
* two Waveshare four-servo-adapter envelopes;
* an ESP32-S3 area, optional Raspberry Pi 3B area, and camera area;
* board mounting and hardware reference geometry;
* a clearly labeled preserved-foot bounding-box reference and optional
  STS-3215 STEP reference;
* a validation report that calls out unresolved hardware dimensions.

Fusion Design API geometry uses centimeters internally. Every raw coordinate
in this file therefore passes through mm(). User parameters remain expressed
as millimeter strings so they are readable and editable in Fusion.
"""

import json
import os
import traceback

import adsk.core
import adsk.fusion


# ---------------------------------------------------------------------------
# Master dimensions
# ---------------------------------------------------------------------------

DIMENSIONS = {
    # Structural system.
    "board_length": 260.0,
    "board_width": 190.0,
    "board_thickness": 3.2,
    "board_clear_gap": 50.0,
    "ground_clearance": 70.0,
    "board_edge_margin": 12.0,

    # Confirmed current Quady leg layout.
    "hip_spacing_x": 150.0,
    "hip_spacing_y": 100.0,

    # Interchangeable leg-cassette interface. These are explicit starting
    # values, not claimed measurements of the unknown servo bracket pattern.
    "cassette_length": 58.0,
    "cassette_width": 46.0,
    "cassette_thickness": 4.0,
    "cassette_hole_pitch_x": 42.0,
    "cassette_hole_pitch_y": 32.0,
    "hip_axis_diameter": 4.5,
    "cassette_mount_diameter": 4.5,
    "servo_reference_length": 55.0,
    "servo_reference_width": 30.0,
    "servo_reference_height": 20.0,
    "servo_reference_clearance": 3.0,

    # Confirmed battery dimensions and conservative bay envelope.
    "battery_length": 139.0,
    "battery_width": 47.0,
    "battery_height": 40.0,
    "battery_bay_length": 155.0,
    "battery_bay_width": 60.0,
    "battery_bay_height": 45.0,
    "battery_bay_gap": 10.0,

    # Waveshare adapter dimensions are kept as a replaceable envelope until
    # the exact board revision and mounting-hole pattern are measured.
    "adapter_reference_length": 42.0,
    "adapter_reference_width": 33.0,
    "adapter_zone_length": 55.0,
    "adapter_zone_width": 45.0,
    "adapter_zone_height": 22.0,

    # Exact-board-compatible ESP32 envelope from the supplied listing, with
    # connector and hand-access clearance around the nominal PCB.
    "esp32_board_length": 62.74,
    "esp32_board_width": 25.40,
    "esp32_zone_length": 78.0,
    "esp32_zone_width": 42.0,
    "esp32_zone_height": 18.0,
    "esp32_lipo_zone_length": 70.0,
    "esp32_lipo_zone_width": 38.0,
    "esp32_lipo_zone_height": 24.0,

    # Optional Raspberry Pi 3B reservation.
    "pi3b_board_length": 85.0,
    "pi3b_board_width": 56.0,
    "pi3b_zone_length": 105.0,
    "pi3b_zone_width": 76.0,
    "pi3b_zone_height": 28.0,

    # Camera reservation; exact OVO Arducam bracket geometry remains a later
    # measured interface, so this is intentionally a mounting envelope.
    "camera_zone_length": 65.0,
    "camera_zone_width": 65.0,
    "camera_zone_height": 45.0,
    "camera_plate_thickness": 3.0,

    # Hardware and the preserved lower-leg/foot reference envelope.
    "m3_clearance": 3.4,
    "m4_clearance": 4.5,
    "standoff_diameter": 8.0,
    "standoff_height": 12.0,
    "foot_reference_length": 73.0,
    "foot_reference_width": 44.9,
    "foot_reference_height": 84.0,
}


PARAMETER_INFO = {
    "board_length": "Overall structural board length.",
    "board_width": "Overall structural board width.",
    "board_thickness": "Nominal two-layer board stock thickness.",
    "board_clear_gap": "Clear vertical gap between the two board faces.",
    "ground_clearance": "Target ground clearance below the lower board.",
    "board_edge_margin": "Reserved edge margin for drilling and hardware.",
    "hip_spacing_x": "Confirmed current front-to-rear hip pivot spacing.",
    "hip_spacing_y": "Confirmed current left-to-right hip pivot spacing.",
    "cassette_length": "Replaceable leg-cassette plate length; verify physically.",
    "cassette_width": "Replaceable leg-cassette plate width; verify physically.",
    "cassette_thickness": "Printed or sheet cassette plate thickness.",
    "cassette_hole_pitch_x": "Placeholder cassette mounting-hole pitch; measure.",
    "cassette_hole_pitch_y": "Placeholder cassette mounting-hole pitch; measure.",
    "hip_axis_diameter": "Hip axis/fastener clearance marker.",
    "cassette_mount_diameter": "Cassette-to-board fastener clearance marker.",
    "servo_reference_length": "Placeholder STS-3215 reference envelope length.",
    "servo_reference_width": "Placeholder STS-3215 reference envelope width.",
    "servo_reference_height": "Placeholder STS-3215 reference envelope height.",
    "servo_reference_clearance": "Extra clearance around the servo reference envelope.",
    "battery_length": "Confirmed battery pack length.",
    "battery_width": "Confirmed battery pack width.",
    "battery_height": "Confirmed battery pack height.",
    "battery_bay_length": "Battery bay envelope length including retention clearance.",
    "battery_bay_width": "Battery bay envelope width including retention clearance.",
    "battery_bay_height": "Battery bay reserved height including wiring clearance.",
    "battery_bay_gap": "Clear gap between the two battery bays.",
    "adapter_reference_length": "Placeholder Waveshare adapter board length.",
    "adapter_reference_width": "Placeholder Waveshare adapter board width.",
    "adapter_zone_length": "Waveshare adapter keepout length.",
    "adapter_zone_width": "Waveshare adapter keepout width.",
    "adapter_zone_height": "Waveshare adapter keepout height.",
    "esp32_board_length": "Nominal ESP32-S3 PCB length from supplied listing.",
    "esp32_board_width": "Nominal ESP32-S3 PCB width from supplied listing.",
    "esp32_zone_length": "ESP32 connector and hand-access keepout length.",
    "esp32_zone_width": "ESP32 connector and hand-access keepout width.",
    "esp32_zone_height": "ESP32 keepout height.",
    "esp32_lipo_zone_length": "Small ESP32 LiPo reservation length.",
    "esp32_lipo_zone_width": "Small ESP32 LiPo reservation width.",
    "esp32_lipo_zone_height": "Small ESP32 LiPo reservation height.",
    "pi3b_board_length": "Nominal Raspberry Pi 3B PCB length.",
    "pi3b_board_width": "Nominal Raspberry Pi 3B PCB width.",
    "pi3b_zone_length": "Raspberry Pi 3B connector and hand-access keepout length.",
    "pi3b_zone_width": "Raspberry Pi 3B connector and hand-access keepout width.",
    "pi3b_zone_height": "Raspberry Pi 3B keepout height.",
    "camera_zone_length": "Camera and bracket reservation length.",
    "camera_zone_width": "Camera and bracket reservation width.",
    "camera_zone_height": "Camera and bracket reservation height.",
    "camera_plate_thickness": "Printed camera bracket plate thickness.",
    "m3_clearance": "Nominal M3 through-hole clearance.",
    "m4_clearance": "Nominal M4 through-hole clearance.",
    "standoff_diameter": "Reference standoff outside diameter.",
    "standoff_height": "Reference standoff height.",
    "foot_reference_length": "Measured lower-leg STL reference length.",
    "foot_reference_width": "Measured lower-leg STL reference width.",
    "foot_reference_height": "Measured lower-leg STL reference height.",
}


def leg_positions():
    """Return the four cassette centers from the single spacing source."""
    x_half = DIMENSIONS["hip_spacing_x"] / 2.0
    y_half = DIMENSIONS["hip_spacing_y"] / 2.0
    return (
        ("FL", x_half, y_half),
        ("FR", x_half, -y_half),
        ("RL", -x_half, y_half),
        ("RR", -x_half, -y_half),
    )


def layout_centers():
    """Single source for replaceable electronics and adapter layout centers."""
    return {
        "adapter_y": -60.0,
        "adapter_x": (-75.0, 75.0),
        "esp32": (-75.0, 62.0),
        "esp32_lipo": (0.0, -10.0),
        "pi3b": (35.0, 42.0),
        "camera": (85.0, -5.0),
    }


# These paths are references only. The generator never writes to them.
PROJECT_ROOT = r"D:\Quady"
REFERENCE_STEP = os.path.join(PROJECT_ROOT, "ST3215.step")
REFERENCE_LOWER_LEG_STL = os.path.join(PROJECT_ROOT, "Cad", "V2", "Lower Leg.stl")

# Set false if you want the layout to open faster on a lower-power computer.
IMPORT_SERVO_STEP_REFERENCE = True


def mm(value):
    """Convert millimeters to Fusion's Design API internal centimeters."""
    return value / 10.0


def parameter_expression(name):
    return f"{DIMENSIONS[name]} mm"


def add_user_parameters(design):
    for name, value in DIMENSIONS.items():
        design.userParameters.add(
            name,
            adsk.core.ValueInput.createByString(parameter_expression(name)),
            "mm",
            PARAMETER_INFO.get(name, "Quady Hybrid V1 master parameter."),
        )


def new_component(root_component, name):
    occurrence = root_component.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    component = occurrence.component
    component.name = name
    return component


def offset_plane(component, offset_expression, name):
    plane_input = component.constructionPlanes.createInput()
    plane_input.setByOffset(
        component.xYConstructionPlane,
        adsk.core.ValueInput.createByString(offset_expression),
    )
    plane = component.constructionPlanes.add(plane_input)
    plane.name = name
    plane.isLightBulbOn = False
    return plane


def rectangle_sketch(component, plane, name, center_x, center_y, length, width):
    sketch = component.sketches.add(plane)
    sketch.name = name
    p1 = adsk.core.Point3D.create(
        mm(center_x - length / 2.0),
        mm(center_y - width / 2.0),
        0,
    )
    p2 = adsk.core.Point3D.create(
        mm(center_x + length / 2.0),
        mm(center_y + width / 2.0),
        0,
    )
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(p1, p2)
    return sketch


def circle_sketch(component, plane, name, center_x, center_y, diameter):
    sketch = component.sketches.add(plane)
    sketch.name = name
    center = adsk.core.Point3D.create(mm(center_x), mm(center_y), 0)
    sketch.sketchCurves.sketchCircles.addByCenterRadius(center, mm(diameter / 2.0))
    return sketch


def extrude_profile(component, profile, name, height_expression):
    extrudes = component.features.extrudeFeatures
    extrude_input = extrudes.createInput(
        profile,
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
    )
    distance = adsk.core.ValueInput.createByString(height_expression)
    extent = adsk.fusion.DistanceExtentDefinition.create(distance)
    extrude_input.setOneSideExtent(
        extent,
        adsk.fusion.ExtentDirections.PositiveExtentDirection,
    )
    feature = extrudes.add(extrude_input)
    feature.name = name
    body = feature.bodies.item(0)
    body.name = name
    return body


def extrude_rectangle(
    component,
    plane,
    name,
    center_x,
    center_y,
    length,
    width,
    height_expression,
):
    sketch = rectangle_sketch(
        component,
        plane,
        f"{name}_Profile",
        center_x,
        center_y,
        length,
        width,
    )
    body = extrude_profile(component, sketch.profiles.item(0), name, height_expression)
    sketch.isLightBulbOn = False
    return body


def extrude_cylinder(
    component,
    plane,
    name,
    center_x,
    center_y,
    diameter,
    height_expression,
):
    sketch = circle_sketch(component, plane, f"{name}_Profile", center_x, center_y, diameter)
    body = extrude_profile(component, sketch.profiles.item(0), name, height_expression)
    sketch.isLightBulbOn = False
    return body


def add_label_marker(component, plane, name, center_x, center_y, diameter=4.0):
    """Create a visible, non-subtractive reference marker."""
    sketch = circle_sketch(component, plane, name, center_x, center_y, diameter)
    sketch.isLightBulbOn = True
    return sketch


def add_board_edge_reference(component, plane):
    sketch = rectangle_sketch(
        component,
        plane,
        "Board_Edge_Margin_Reference",
        0,
        0,
        DIMENSIONS["board_length"] - 2 * DIMENSIONS["board_edge_margin"],
        DIMENSIONS["board_width"] - 2 * DIMENSIONS["board_edge_margin"],
    )
    sketch.isLightBulbOn = True
    return sketch


def add_board_mount_markers(component, plane):
    inset = DIMENSIONS["board_edge_margin"] + 3.0
    x = DIMENSIONS["board_length"] / 2.0 - inset
    y = DIMENSIONS["board_width"] / 2.0 - inset
    for index, (cx, cy) in enumerate(((-x, -y), (-x, y), (x, -y), (x, y)), start=1):
        extrude_cylinder(
            component,
            plane,
            f"Board_M4_Reference_{index}",
            cx,
            cy,
            DIMENSIONS["m4_clearance"],
            "board_thickness + 2 mm",
        )


def build_leg_cassettes(root):
    cassettes = new_component(root, "20_Interchangeable_Leg_Cassettes")
    plane = offset_plane(
        cassettes,
        "board_clear_gap + board_thickness * 2",
        "Cassette_Mount_Surface",
    )
    positions = leg_positions()

    for leg_name, cx, cy in positions:
        pad_name = f"{leg_name}_Leg_Cassette_Pad"
        extrude_rectangle(
            cassettes,
            plane,
            pad_name,
            cx,
            cy,
            DIMENSIONS["cassette_length"],
            DIMENSIONS["cassette_width"],
            "cassette_thickness",
        )

        # The center marker is the interface datum for the preserved leg.
        add_label_marker(
            cassettes,
            plane,
            f"{leg_name}_Preserved_Hip_Axis_Datum",
            cx,
            cy,
            DIMENSIONS["hip_axis_diameter"],
        )
        for hole_index, dx in enumerate(
            (-DIMENSIONS["cassette_hole_pitch_x"] / 2.0,
             DIMENSIONS["cassette_hole_pitch_x"] / 2.0),
            start=1,
        ):
            for side, dy in enumerate(
                (-DIMENSIONS["cassette_hole_pitch_y"] / 2.0,
                 DIMENSIONS["cassette_hole_pitch_y"] / 2.0),
                start=1,
            ):
                extrude_cylinder(
                    cassettes,
                    plane,
                    f"{leg_name}_Cassette_M4_Clearance_Reference_Solid_{hole_index}{side}",
                    cx + dx,
                    cy + dy,
                    DIMENSIONS["cassette_mount_diameter"],
                    "cassette_thickness + 2 mm",
                )

        # This is a transparent planning envelope for the two STS-3215s in
        # the leg module. It is not a substitute for the measured bracket.
        extrude_rectangle(
            cassettes,
            plane,
            f"{leg_name}_STS3215_Pair_Reference_Envelope",
            cx,
            cy,
            DIMENSIONS["servo_reference_length"] + DIMENSIONS["servo_reference_clearance"],
            DIMENSIONS["servo_reference_width"] + DIMENSIONS["servo_reference_clearance"],
            "servo_reference_height",
        )

    pivots = cassettes.sketches.add(plane)
    pivots.name = "Confirmed_Hip_Pivot_Spacing_150x100mm"
    circles = pivots.sketchCurves.sketchCircles
    for _, cx, cy in positions:
        circles.addByCenterRadius(
            adsk.core.Point3D.create(mm(cx), mm(cy), 0),
            mm(DIMENSIONS["hip_axis_diameter"] / 2.0),
        )
    pivots.isLightBulbOn = True
    return cassettes


def build_battery_and_power(root):
    power = new_component(root, "30_Power_and_Servo_Buses")
    battery_plane = offset_plane(power, "board_thickness", "Battery_Top_Surface")
    adapter_plane = offset_plane(
        power,
        "board_clear_gap + board_thickness * 2",
        "Top_Board_Electronics_Surface",
    )

    battery_y = (DIMENSIONS["battery_bay_width"] + DIMENSIONS["battery_bay_gap"]) / 2.0
    for index, cy in enumerate((-battery_y, battery_y), start=1):
        extrude_rectangle(
            power,
            battery_plane,
            f"Battery_{index}_Clearance_Bay_155x60x50mm",
            0,
            cy,
            DIMENSIONS["battery_bay_length"],
            DIMENSIONS["battery_bay_width"],
            "battery_bay_height",
        )
        pack = extrude_rectangle(
            power,
            battery_plane,
            f"Battery_{index}_Confirmed_Pack_139x47x40mm_REFERENCE",
            0,
            cy,
            DIMENSIONS["battery_length"],
            DIMENSIONS["battery_width"],
            "battery_height",
        )
        pack.isLightBulbOn = False

    # Two separate four-servo bus envelopes, one per confirmed battery.
    centers = layout_centers()
    for index, cx in enumerate(centers["adapter_x"], start=1):
        extrude_rectangle(
            power,
            adapter_plane,
            f"Waveshare_Servo_Adapter_{index}_Four_Servo_Zone",
            cx,
            centers["adapter_y"],
            DIMENSIONS["adapter_zone_length"],
            DIMENSIONS["adapter_zone_width"],
            "adapter_zone_height",
        )
        adapter_reference = extrude_rectangle(
            power,
            adapter_plane,
            f"Waveshare_Servo_Adapter_{index}_Board_Reference_42x33mm",
            cx,
            centers["adapter_y"],
            DIMENSIONS["adapter_reference_length"],
            DIMENSIONS["adapter_reference_width"],
            "adapter_zone_height",
        )
        adapter_reference.isLightBulbOn = False
        add_label_marker(
            power,
            adapter_plane,
            f"Adapter_{index}_Mounting_Datum",
            cx,
            centers["adapter_y"],
            4.0,
        )

    return power


def build_control_and_camera(root):
    electronics = new_component(root, "40_Control_Camera_and_Optional_Pi")
    top_plane = offset_plane(
        electronics,
        "board_clear_gap + board_thickness * 2",
        "Control_Board_Top_Surface",
    )
    underside_plane = offset_plane(
        electronics,
        "-pi3b_zone_height",
        "Optional_Pi_Underside_Surface",
    )
    centers = layout_centers()
    esp32_x, esp32_y = centers["esp32"]
    lipo_x, lipo_y = centers["esp32_lipo"]
    pi_x, pi_y = centers["pi3b"]
    camera_x, camera_y = centers["camera"]

    # The ESP32 is the preferred controller; this is its primary zone.
    extrude_rectangle(
        electronics,
        top_plane,
        "ESP32_S3_WROOM1_N16R8_Preferred_Controller_Zone",
        esp32_x,
        esp32_y,
        DIMENSIONS["esp32_zone_length"],
        DIMENSIONS["esp32_zone_width"],
        "esp32_zone_height",
    )
    esp32_reference = extrude_rectangle(
        electronics,
        top_plane,
        "ESP32_S3_Nominal_PCB_Reference_62_74x25_40mm",
        esp32_x,
        esp32_y,
        DIMENSIONS["esp32_board_length"],
        DIMENSIONS["esp32_board_width"],
        "esp32_zone_height",
    )
    esp32_reference.isLightBulbOn = False
    extrude_rectangle(
        electronics,
        top_plane,
        "ESP32_S3_Small_LiPo_Zone",
        lipo_x,
        lipo_y,
        DIMENSIONS["esp32_lipo_zone_length"],
        DIMENSIONS["esp32_lipo_zone_width"],
        "esp32_lipo_zone_height",
    )

    # Optional Pi reservation. It is deliberately present without requiring
    # a Pi in the build, so the preferred smaller controller remains clear.
    extrude_rectangle(
        electronics,
        underside_plane,
        "OPTIONAL_Raspberry_Pi_3B_Zone",
        pi_x,
        pi_y,
        DIMENSIONS["pi3b_zone_length"],
        DIMENSIONS["pi3b_zone_width"],
        "pi3b_zone_height",
    )
    pi_reference = extrude_rectangle(
        electronics,
        underside_plane,
        "OPTIONAL_Raspberry_Pi_3B_Nominal_PCB_Reference_85x56mm",
        pi_x,
        pi_y,
        DIMENSIONS["pi3b_board_length"],
        DIMENSIONS["pi3b_board_width"],
        "pi3b_zone_height",
    )
    pi_reference.isLightBulbOn = False

    # Camera bracket reservation near the front edge. The plate is a printed
    # interface part; the board itself remains a separate, replaceable item.
    extrude_rectangle(
        electronics,
        top_plane,
        "OVO_Arducam_Webcam_Mounting_Zone",
        camera_x,
        camera_y,
        DIMENSIONS["camera_zone_length"],
        DIMENSIONS["camera_zone_width"],
        "camera_zone_height",
    )
    extrude_rectangle(
        electronics,
        top_plane,
        "OVO_Arducam_Printed_Bracket_Plate_Reference",
        camera_x,
        camera_y,
        DIMENSIONS["camera_zone_length"],
        DIMENSIONS["camera_zone_width"],
        "camera_plate_thickness",
    )
    return electronics


def build_hardware_references(root):
    hardware = new_component(root, "50_Hardware_and_Standoffs")
    top_plane = offset_plane(
        hardware,
        "board_clear_gap + board_thickness * 2",
        "Hardware_Reference_Plane",
    )
    pi_plane = offset_plane(
        hardware,
        "-pi3b_zone_height",
        "Pi_Underside_Hardware_Reference_Plane",
    )
    centers = layout_centers()

    # Generic standoffs for the Pi reservation and ESP32 zone. These show
    # access and height, not a final hole pattern.
    for name, cx, cy, length, width in (
        (
            "ESP32",
            centers["esp32"][0],
            centers["esp32"][1],
            DIMENSIONS["esp32_zone_length"],
            DIMENSIONS["esp32_zone_width"],
        ),
        (
            "Pi3B",
            centers["pi3b"][0],
            centers["pi3b"][1],
            DIMENSIONS["pi3b_zone_length"],
            DIMENSIONS["pi3b_zone_width"],
        ),
    ):
        plane = pi_plane if name == "Pi3B" else top_plane
        for index, (dx, dy) in enumerate(
            ((-length / 2.0 + 8.0, -width / 2.0 + 8.0),
             (-length / 2.0 + 8.0, width / 2.0 - 8.0),
             (length / 2.0 - 8.0, -width / 2.0 + 8.0),
             (length / 2.0 - 8.0, width / 2.0 - 8.0)),
            start=1,
        ):
            extrude_cylinder(
                hardware,
                plane,
                f"{name}_Standoff_Reference_{index}",
                cx + dx,
                cy + dy,
                DIMENSIONS["standoff_diameter"],
                "standoff_height",
            )

    add_board_mount_markers(hardware, top_plane)
    return hardware


def build_preserved_foot_reference(root):
    references = new_component(root, "60_Preserved_Foot_and_Servo_References")
    plane = offset_plane(
        references,
        "board_clear_gap + board_thickness * 2",
        "Preserved_Foot_Reference_Plane",
    )

    # The foot/lower-leg part is intentionally not redesigned. This envelope
    # keeps its measured outer volume visible while the interface is verified.
    foot = extrude_rectangle(
        references,
        plane,
        "PRESERVED_Lower_Leg_Foot_STL_Bounding_Box_REFERENCE_ONLY",
        75.0,
        -50.0,
        DIMENSIONS["foot_reference_length"],
        DIMENSIONS["foot_reference_width"],
        "foot_reference_height",
    )
    foot.isLightBulbOn = False

    import_status = []
    if IMPORT_SERVO_STEP_REFERENCE and os.path.exists(REFERENCE_STEP):
        try:
            app = adsk.core.Application.get()
            options = app.importManager.createSTEPImportOptions(REFERENCE_STEP)
            if options:
                imported = app.importManager.importToTarget(options, references)
                if imported is False:
                    import_status.append("STS-3215 STEP reference import failed")
                else:
                    import_status.append(
                        "STS-3215 STEP reference imported at source origin; manual alignment required"
                    )
            else:
                import_status.append("STS-3215 STEP options could not be created")
        except Exception as error:
            import_status.append(f"STS-3215 STEP reference skipped: {error}")
    else:
        import_status.append("STS-3215 STEP reference not found or disabled")

    if os.path.exists(REFERENCE_LOWER_LEG_STL):
        import_status.append(
            "Lower Leg.stl found; actual mesh mating geometry is not imported, "
            "so the labeled bounding box remains reference-only"
        )
    else:
        import_status.append("Lower Leg.stl not found; bounding-box reference remains active")

    return references, import_status


def add_ground_reference(root):
    ground = new_component(root, "70_Ground_Clearance_Reference")
    plane = offset_plane(ground, "-ground_clearance", "Ground_Plane_70mm_Below_Lower_Board")
    sketch = rectangle_sketch(
        ground,
        plane,
        "Ground_Clearance_Reference_Rectangle",
        0,
        0,
        DIMENSIONS["board_length"] - 2.0,
        DIMENSIONS["board_width"] - 2.0,
    )
    sketch.isLightBulbOn = True
    return ground


def validate_layout():
    checks = []

    def check(label, condition, detail):
        checks.append({"label": label, "pass": bool(condition), "detail": detail})

    bx = DIMENSIONS["board_length"] / 2.0
    by = DIMENSIONS["board_width"] / 2.0
    edge = DIMENSIONS["board_edge_margin"]

    for name, cx, cy in leg_positions():
        inside = abs(cx) + DIMENSIONS["cassette_length"] / 2.0 <= bx - edge
        inside = inside and abs(cy) + DIMENSIONS["cassette_width"] / 2.0 <= by - edge
        check(
            f"{name} cassette fits board edge margin",
            inside,
            f"center=({cx:g},{cy:g}) mm, margin={edge:g} mm",
        )

    battery_y = (DIMENSIONS["battery_bay_width"] + DIMENSIONS["battery_bay_gap"]) / 2.0
    battery_ok = (
        DIMENSIONS["battery_bay_length"] <= DIMENSIONS["board_length"] - 2 * edge
        and abs(battery_y) + DIMENSIONS["battery_bay_width"] / 2.0 <= by - edge
    )
    check("two battery bays fit the lower board", battery_ok, "two confirmed 139x47x40 mm packs")

    check(
        "two-layer clearance is positive",
        DIMENSIONS["board_clear_gap"] > 2 * DIMENSIONS["servo_reference_clearance"],
        f"clear gap={DIMENSIONS['board_clear_gap']:g} mm",
    )
    check(
        "battery bay leaves upper-board headroom",
        DIMENSIONS["board_clear_gap"] - DIMENSIONS["battery_bay_height"] > 0,
        f"headroom={DIMENSIONS['board_clear_gap'] - DIMENSIONS['battery_bay_height']:g} mm",
    )
    check(
        "ground clearance is positive",
        DIMENSIONS["ground_clearance"] > 0,
        f"target={DIMENSIONS['ground_clearance']:g} mm",
    )
    check(
        "confirmed hip spacing is represented",
        DIMENSIONS["hip_spacing_x"] == 150.0 and DIMENSIONS["hip_spacing_y"] == 100.0,
        "four pivot datums at 150 x 100 mm",
    )
    centers = layout_centers()
    pi_x, pi_y = centers["pi3b"]
    camera_x, camera_y = centers["camera"]
    check(
        "Pi reservation stays inside board",
        abs(pi_x) + DIMENSIONS["pi3b_zone_length"] / 2.0 <= bx - edge
        and abs(pi_y) + DIMENSIONS["pi3b_zone_width"] / 2.0 <= by - edge,
        "Pi zone is optional and allocated to the underside of the lower board",
    )
    check(
        "camera reservation stays inside board",
        abs(camera_x) + DIMENSIONS["camera_zone_length"] / 2.0 <= bx - edge
        and abs(camera_y) + DIMENSIONS["camera_zone_width"] / 2.0 <= by - edge,
        "camera is kept near the front edge with drilling margin",
    )

    def overlap_area(first, second):
        _, first_x, first_y, first_length, first_width = first
        _, second_x, second_y, second_length, second_width = second
        x_overlap = max(
            0.0,
            min(first_x + first_length / 2.0, second_x + second_length / 2.0)
            - max(first_x - first_length / 2.0, second_x - second_length / 2.0),
        )
        y_overlap = max(
            0.0,
            min(first_y + first_width / 2.0, second_y + second_width / 2.0)
            - max(first_y - first_width / 2.0, second_y - second_width / 2.0),
        )
        return x_overlap * y_overlap

    required_zones = (
        (
            "Adapter 1",
            centers["adapter_x"][0],
            centers["adapter_y"],
            DIMENSIONS["adapter_zone_length"],
            DIMENSIONS["adapter_zone_width"],
        ),
        (
            "Adapter 2",
            centers["adapter_x"][1],
            centers["adapter_y"],
            DIMENSIONS["adapter_zone_length"],
            DIMENSIONS["adapter_zone_width"],
        ),
        (
            "ESP32 LiPo",
            centers["esp32_lipo"][0],
            centers["esp32_lipo"][1],
            DIMENSIONS["esp32_lipo_zone_length"],
            DIMENSIONS["esp32_lipo_zone_width"],
        ),
        (
            "Camera",
            centers["camera"][0],
            centers["camera"][1],
            DIMENSIONS["camera_zone_length"],
            DIMENSIONS["camera_zone_width"],
        ),
    )
    for index, first in enumerate(required_zones):
        for second in required_zones[index + 1:]:
            area = overlap_area(first, second)
            check(
                f"{first[0]} and {second[0]} do not overlap",
                area == 0.0,
                f"intersection area={area:g} mm^2",
            )
    return checks


def show_validation(app, design, checks, import_status):
    passed = sum(1 for check in checks if check["pass"])
    failed = len(checks) - passed
    lines = [
        "Quady Hybrid V1 assembly generated.",
        f"Validation: {passed}/{len(checks)} checks passed; {failed} failed.",
        "",
    ]
    for check in checks:
        state = "PASS" if check["pass"] else "FAIL"
        lines.append(f"{state}: {check['label']} — {check['detail']}")
    lines.extend([
        "",
        "Important unresolved interfaces:",
        "- Cassette hole pitch and servo bracket geometry are explicit placeholders.",
        "- Waveshare adapter hole pattern and OVO Arducam bracket must be measured.",
        "- The preserved foot box is an STL bounding-box reference only; do not print it.",
        "",
        "Reference import status:",
    ])
    lines.extend(f"- {status}" for status in import_status)
    report = "\n".join(lines)
    try:
        design.attributes.add(
            "QuadyHybridAssembly",
            "validation_report",
            json.dumps({"checks": checks, "import_status": import_status}),
        )
    except Exception:
        pass
    app.userInterface.messageBox(report, "Quady Hybrid Assembly")


def build_document():
    app = adsk.core.Application.get()
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
    if not design:
        raise RuntimeError("Fusion did not create a Design product.")

    # Fusion's root component name is read-only; the numbered child
    # components below carry the assembly structure and labels.
    add_user_parameters(design)
    root = design.rootComponent

    structural = new_component(root, "10_Structural_Two_Layer_Boards")
    bottom_plane = structural.xYConstructionPlane
    top_plane = offset_plane(
        structural,
        "board_clear_gap + board_thickness",
        "Top_Board_Bottom_Face_Plane",
    )
    extrude_rectangle(
        structural,
        bottom_plane,
        "Bottom_Structural_Board_260x190x3p2mm",
        0,
        0,
        DIMENSIONS["board_length"],
        DIMENSIONS["board_width"],
        "board_thickness",
    )
    extrude_rectangle(
        structural,
        top_plane,
        "Top_Structural_Board_260x190x3p2mm",
        0,
        0,
        DIMENSIONS["board_length"],
        DIMENSIONS["board_width"],
        "board_thickness",
    )
    add_board_edge_reference(structural, bottom_plane)
    add_board_edge_reference(structural, top_plane)

    build_leg_cassettes(root)
    build_battery_and_power(root)
    build_control_and_camera(root)
    build_hardware_references(root)
    references, import_status = build_preserved_foot_reference(root)
    add_ground_reference(root)

    checks = validate_layout()
    show_validation(app, design, checks, import_status)
    return doc


def run(context):
    try:
        build_document()
    except Exception:
        app = adsk.core.Application.get()
        app.userInterface.messageBox(traceback.format_exc(), "Quady Hybrid Assembly Error")
