# Quady Hybrid V1 Fusion script

`QuadyHybridSkeleton.py` creates a new Fusion 360 design for the first hybrid
base-layout check. It does not open or modify the existing Quady V1/V2 CAD.

## What it creates

- Two 260 x 190 mm structural board bodies.
- A 50 mm plane-to-plane board layout offset (46.8 mm clear space between
  3.2 mm board solids).
- Four leg-pivot markers at the current 150 x 100 mm spacing.
- Two 139 x 47 x 40 mm battery keepouts.
- Two Waveshare adapter keepout zones.
- A 75 x 40 mm ESP32-S3 DevKitC-style placeholder envelope around the
  62.74 x 25.40 mm board footprint.
- An optional Raspberry Pi 3B zone.
- An adjustable Arducam camera zone.
- Named millimeter user parameters in Fusion. These drive the initial
  generation; post-run edits are not yet fully associative.

## Run it in Fusion 360

1. Open Fusion 360.
2. Open **Utilities > Add-Ins > Scripts and Add-Ins**.
3. Choose the **Scripts** tab.
4. Click the **+** button and choose **Script or add-in from device**.
5. Select this folder:

   `D:\Quady\Cad\Hybrid V1\FusionScript`

6. Select `QuadyHybridSkeleton.py` and click **Run**.
7. Confirm the new document contains the four named Browser components and
   visible board, battery, electronics, and pivot-marker geometry.

The output is a layout skeleton. Do not use it as a manufacturing file yet. We
will next add the real leg-cassette mounting interface and inspect the physical
clearances. Fusion's Personal plan may show a document-limit read-only banner;
the script remains the reproducible source until the generated document can be
saved.
