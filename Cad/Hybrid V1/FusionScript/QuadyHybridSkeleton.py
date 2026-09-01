"""Quady Hybrid V1 - Fusion 360 master skeleton generator.

Run this as a Fusion 360 Python script. It creates a new Fusion design and
does not open, modify, or overwrite the existing Quady V1/V2 files.

This first version intentionally generates a clean layout skeleton rather than
trying to convert the existing STL parts into editable solids. The difficult
servo/foot interface will be added after this layout is checked physically.
"""

import traceback

import adsk.core
import adsk.fusion


# One source of truth for the first hybrid layout.
DIMENSIONS = {
    "plate_length": 260.0,
    "plate_width": 190.0,
    "plate_thickness": 3.2,
    "layer_gap": 50.0,
    "leg_spacing_front_rear": 150.0,
    "leg_spacing_left_right": 100.0,
    "ground_clearance": 70.0,
    "battery_length": 139.0,
    "battery_width": 47.0,
    "battery_height": 40.0,
    "battery_bay_length": 155.0,
    "battery_bay_width": 60.0,
    "battery_bay_height": 50.0,
    "esp_length": 62.74,
    "esp_width": 25.40,
    "esp_zone_length": 75.0,
    "esp_zone_width": 40.0,
    "pi_length": 85.0,
    "pi_width": 56.0,
    "pi_zone_length": 100.0,
    "pi_zone_width": 70.0,
    "adapter_length": 42.0,
    "adapter_width": 33.0,
    "adapter_zone_length": 55.0,
    "adapter_zone_width": 45.0,
    "camera_zone_length": 60.0,
    "camera_zone_width": 60.0,
    "m3_clearance": 3.4,
    "m4_clearance": 4.5,
    "edge_margin": 12.0,
    "default_fillet": 3.0,
}


PARAMETER_INFO = {
    "plate_length": "Overall structural plate length.",
    "plate_width": "Overall structural plate width.",
    "plate_thickness": "Nominal board stock thickness.",
    "layer_gap": "Bottom XY plane to top plate XY plane.",
    "leg_spacing_front_rear": "Current Quady hip-pivot spacing along X.",
    "leg_spacing_left_right": "Current Quady hip-pivot spacing along Y.",
    "ground_clearance": "Initial target clearance under the lower plate.",
    "battery_length": "Battery pack length.",
    "battery_width": "Battery pack width.",
    "battery_height": "Battery pack height.",
    "battery_bay_length": "Battery bay length including retention clearance.",
    "battery_bay_width": "Battery bay width including retention clearance.",
    "battery_bay_height": "Reserved vertical battery bay envelope.",
    "esp_length": "ESP32 board length.",
    "esp_width": "ESP32 board width.",
    "esp_zone_length": "ESP32 mounting/connector keepout length.",
    "esp_zone_width": "ESP32 mounting/connector keepout width.",
    "pi_length": "Optional Raspberry Pi board length.",
    "pi_width": "Optional Raspberry Pi board width.",
    "pi_zone_length": "Optional Raspberry Pi mounting/connector zone length.",
    "pi_zone_width": "Optional Raspberry Pi mounting/connector zone width.",
    "adapter_length": "Waveshare adapter board length.",
    "adapter_width": "Waveshare adapter board width.",
    "adapter_zone_length": "Waveshare adapter mounting/connector zone length.",
    "adapter_zone_width": "Waveshare adapter mounting/connector zone width.",
    "camera_zone_length": "Adjustable camera envelope length.",
    "camera_zone_width": "Adjustable camera envelope width.",
    "m3_clearance": "Nominal M3 through-hole clearance.",
    "m4_clearance": "Nominal M4 through-hole clearance.",
    "edge_margin": "Minimum fastener-to-edge design margin.",
    "default_fillet": "Starting printed-part edge fillet.",
}


def parameter_expression(name):
    return f"{DIMENSIONS[name]} mm"


def mm(value):
    """Convert a millimeter value to Fusion Design API database units (cm)."""
    return value / 10.0


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
    planes = component.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(
        component.xYConstructionPlane,
        adsk.core.ValueInput.createByString(offset_expression),
    )
    plane = planes.add(plane_input)
    plane.name = name
    plane.isLightBulbOn = False
    return plane


def rectangle_sketch(component, plane, name, center_x, center_y, length, width):
    sketch = component.sketches.add(plane)
    sketch.name = name
    lines = sketch.sketchCurves.sketchLines
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
    lines.addTwoPointRectangle(p1, p2)
    return sketch


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
    profile = sketch.profiles.item(0)
    extrudes = component.features.extrudeFeatures
    operation = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    extrude_input = extrudes.createInput(profile, operation)
    distance = adsk.core.ValueInput.createByString(height_expression)
    distance_extent = adsk.fusion.DistanceExtentDefinition.create(distance)
    extrude_input.setOneSideExtent(
        distance_extent,
        adsk.fusion.ExtentDirections.PositiveExtentDirection,
    )
    feature = extrudes.add(extrude_input)
    feature.name = name
    body = feature.bodies.item(0)
    body.name = name
    sketch.isLightBulbOn = False
    return body


def add_leg_pivot_markers(component):
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = "Leg_Pivot_Markers_150x100mm"
    circles = sketch.sketchCurves.sketchCircles
    x_half = DIMENSIONS["leg_spacing_front_rear"] / 2.0
    y_half = DIMENSIONS["leg_spacing_left_right"] / 2.0
    for x in (-x_half, x_half):
        for y in (-y_half, y_half):
            center = adsk.core.Point3D.create(mm(x), mm(y), 0)
            circles.addByCenterRadius(center, mm(4.0))
    return sketch


def build_document():
    app = adsk.core.Application.get()
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
    if not design:
        raise RuntimeError("Fusion did not create a Design product.")

    add_user_parameters(design)
    root = design.rootComponent

    structural = new_component(root, "01_Structural_Boards")
    bottom_plane = structural.xYConstructionPlane
    top_plane = offset_plane(structural, "layer_gap", "Top_Board_Plane")

    extrude_rectangle(
        structural,
        bottom_plane,
        "Bottom_Structural_Board",
        0,
        0,
        DIMENSIONS["plate_length"],
        DIMENSIONS["plate_width"],
        "plate_thickness",
    )
    extrude_rectangle(
        structural,
        top_plane,
        "Top_Structural_Board",
        0,
        0,
        DIMENSIONS["plate_length"],
        DIMENSIONS["plate_width"],
        "plate_thickness",
    )
    add_leg_pivot_markers(structural)

    batteries = new_component(root, "02_Battery_Keepouts")
    battery_plane = offset_plane(batteries, "plate_thickness", "Battery_Base_Plane")
    battery_y = (DIMENSIONS["battery_width"] + 10.0) / 2.0
    for index, y in enumerate((-battery_y, battery_y), start=1):
        extrude_rectangle(
            batteries,
            battery_plane,
            f"Battery_{index}_139x47x40mm",
            0,
            y,
            DIMENSIONS["battery_length"],
            DIMENSIONS["battery_width"],
            "battery_height",
        )

    electronics = new_component(root, "03_Electronics_Keepouts")
    electronics_plane = offset_plane(
        electronics,
        "layer_gap + plate_thickness",
        "Top_Electronics_Plane",
    )

    # Positions are deliberately conservative placeholders for the first layout.
    extrude_rectangle(
        electronics,
        electronics_plane,
        "ESP32_S3_DevKitC_N16R8_Zone",
        -70,
        55,
        DIMENSIONS["esp_zone_length"],
        DIMENSIONS["esp_zone_width"],
        "20 mm",
    )
    extrude_rectangle(
        electronics,
        electronics_plane,
        "Optional_Raspberry_Pi_3B_Zone",
        25,
        45,
        DIMENSIONS["pi_zone_length"],
        DIMENSIONS["pi_zone_width"],
        "20 mm",
    )
    extrude_rectangle(
        electronics,
        electronics_plane,
        "Waveshare_Adapter_1_Zone",
        -80,
        -20,
        DIMENSIONS["adapter_zone_length"],
        DIMENSIONS["adapter_zone_width"],
        "20 mm",
    )
    extrude_rectangle(
        electronics,
        electronics_plane,
        "Waveshare_Adapter_2_Zone",
        -20,
        -20,
        DIMENSIONS["adapter_zone_length"],
        DIMENSIONS["adapter_zone_width"],
        "20 mm",
    )
    camera_x = (
        DIMENSIONS["plate_length"] / 2.0
        - DIMENSIONS["edge_margin"]
        - DIMENSIONS["camera_zone_length"] / 2.0
    )
    camera_y = (
        -DIMENSIONS["plate_width"] / 2.0
        + DIMENSIONS["edge_margin"]
        + DIMENSIONS["camera_zone_width"] / 2.0
    )
    extrude_rectangle(
        electronics,
        electronics_plane,
        "Adjustable_Arducam_Camera_Zone",
        camera_x,
        camera_y,
        DIMENSIONS["camera_zone_length"],
        DIMENSIONS["camera_zone_width"],
        "25 mm",
    )

    info = new_component(root, "00_README_LAYOUT")
    info_sketch = info.sketches.add(info.xYConstructionPlane)
    info_sketch.name = "Layout_Origin_and_Axes"
    axes = info_sketch.sketchCurves.sketchLines
    axes.addByTwoPoints(
        adsk.core.Point3D.create(mm(-DIMENSIONS["plate_length"] / 2.0), 0, 0),
        adsk.core.Point3D.create(mm(DIMENSIONS["plate_length"] / 2.0), 0, 0),
    )
    axes.addByTwoPoints(
        adsk.core.Point3D.create(0, mm(-DIMENSIONS["plate_width"] / 2.0), 0),
        adsk.core.Point3D.create(0, mm(DIMENSIONS["plate_width"] / 2.0), 0),
    )

    return doc


def run(context):
    try:
        doc = build_document()
        app = adsk.core.Application.get()
        app.userInterface.messageBox(
            "Quady Hybrid V1 skeleton created.\n\n"
            "Check the Browser for the structural boards, battery keepouts, "
            "electronics zones, and 150 x 100 mm leg-pivot markers."
        )
    except Exception:
        app = adsk.core.Application.get()
        app.userInterface.messageBox(
            "Quady Hybrid V1 script failed:\n\n" + traceback.format_exc()
        )
