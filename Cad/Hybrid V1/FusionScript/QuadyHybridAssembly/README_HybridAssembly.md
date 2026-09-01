# Quady Hybrid V1 — complete Fusion assembly generator

File: `QuadyHybridAssembly.py`

This generator creates a new Fusion design and leaves the existing V1/V2
files untouched. It is the single layout/reference master for the proposed
hybrid build. It is not yet the final printable part set: the foot mating
geometry, servo bracket pattern, adapter pattern, and camera bracket still
need measured interfaces.

- two 260 × 190 × 3.2 mm structural boards;
- 50 mm clear space between the board faces;
- four interchangeable leg-cassette pads at the confirmed 150 × 100 mm hip
  spacing;
- two editable battery clearance bays plus hidden 139 × 47 × 40 mm pack
  reference solids;
- two separate four-servo Waveshare adapter envelopes;
- ESP32-S3 and small ESP32 LiPo reservations;
- optional Raspberry Pi 3B reservation on the underside of the lower board;
- OVO Arducam camera reservation and printed bracket plate;
- hardware/standoff references;
- ground-clearance reference at 70 mm;
- labeled preserved-foot STL bounding-box and STS-3215 reference geometry;
- an in-Fusion validation report.

## Run it

1. Open Fusion 360.
2. Open **Utilities → Add-Ins → Scripts and Add-Ins**.
3. Import this folder as a Fusion script if it is not already listed.
4. Select `QuadyHybridAssembly` and click **Run**.
5. In the generated document, expand the numbered components in the Browser.
6. Open **Modify → Change Parameters** to change the named dimensions.
7. Rerun the generator after changing a design assumption. It always creates a
   fresh document so the prior generated result remains available for review.
   Fusion Personal may limit how many unsaved documents can be open, so close
   an old test document before repeated runs if Fusion reports a document-limit
   warning.

## What is exact versus provisional

Confirmed inputs currently encoded:

- battery outer dimensions: 139 × 47 × 40 mm;
- four legs, two STS-3215 servos per leg;
- two battery-to-adapter power groups;
- hip pivot spacing: 150 × 100 mm;
- nominal ESP32-S3 PCB envelope: 62.74 × 25.40 mm.

Provisional values are intentionally named in the Browser and in the script:

- cassette hole pitch and printed cassette thickness;
- STS-3215 bracket/servo mounting pattern;
- Waveshare adapter board mounting pattern;
- OVO Arducam camera bracket and lens keepout;
- small ESP32 LiPo outer dimensions;
- actual board stock/material and final fastener sizes.

The printed `PRESERVED_Lower_Leg_Foot_STL_Bounding_Box_REFERENCE_ONLY` is a
disabled visual bounding box based on the existing STL dimensions. It is not a
printable replacement for the existing foot and does not prove the mating
interface. Measure the real foot and cassette interface before making final
printed parts.

The battery bays and Waveshare/ESP32/Pi zones are clearance geometry. Hidden
reference solids show the nominal board or pack dimensions. The cassette
mount cylinders are additive clearance-reference solids, not subtractive
holes; the final cassette must be cut from the board using the measured hole
pattern.

The optional Pi reservation is intentionally on the underside of the lower
board, so it can occupy the same plan-view footprint as upper-board camera
hardware without being treated as a same-layer collision.

## Material starting point

The generator intentionally does not bake in a purchase decision. The two
board layers are represented as solids with editable thickness. Start with
3.2 mm FR-4, birch plywood, or another stiff sheet that can be drilled cleanly;
choose only after checking the final mass, fastener pull-through, and access
to both faces. The design's board thickness parameter makes that comparison
easy without rewriting the layout.

## Safety and review gates before printing

1. Measure the actual Waveshare adapter outline and hole pattern.
2. Measure one STS-3215 body, horn center, bolt pattern, and cable exit.
3. Measure the existing foot's mating faces and preserve those datums.
4. Replace the cassette placeholders with those measurements.
5. Confirm battery retention, connector bend radius, and center of mass.
6. Confirm that the two board layers cannot pinch servo wires or battery leads.
7. Print only a single cassette test coupon before printing all four.

The default battery bay is 45 mm tall inside the 50 mm board gap, leaving a
nominal 5 mm upper-board headroom margin. That is a layout margin, not a
guarantee of connector bend-radius or wire-pinch clearance; verify the actual
battery leads before locking the board spacing.
