# Quady Quick Assembly Notes

These are current first-version assembly notes for Quady. They are meant to get the physical robot assembled and wired far enough for safe servo ID checks, range checks, and early movement tests.

## Current Version

- 8-servo quadruped
- 2 powered joints per leg
- Feetech STS3215 12 V serial bus servos
- 2x Waveshare Bus Servo Adapter boards
- ESP32 / ESP32-S3 controller
- 3D-printed body, lower legs, upper legs, and servo clips

CAD files for the current printed version are in `Cad/V2/`.

## Parts To Print

Print these from `Cad/V2/`:

- `Body.stl`
- `Upper Leg.stl` x4
- `Lower Leg.stl` x4
- `ServoClip.stl` as needed for retaining the servos

Use the STEP assembly in `Cad/V2/Quady Assembly.step` as the visual reference while assembling.

## Before Mechanical Assembly

1. Label the servos before installing them.
2. Give each servo a unique ID from `1` to `8`.
3. Keep IDs `1-4` on bus 1 and IDs `5-8` on bus 2.
4. Test each servo by itself before putting it into the body.
5. Do not force a servo horn through the printed joint travel. If it binds, stop and fix the print, alignment, or range.

The important idea: make every servo known-good before it becomes hard to reach.

## Suggested Servo Layout

Use this as the starting ID map unless you decide to change the gait code later:

| Servo ID | Bus | Suggested joint |
|---|---:|---|
| 1 | 1 | front left hip/shoulder |
| 2 | 1 | front left knee |
| 3 | 1 | rear left hip/shoulder |
| 4 | 1 | rear left knee |
| 5 | 2 | front right hip/shoulder |
| 6 | 2 | front right knee |
| 7 | 2 | rear right hip/shoulder |
| 8 | 2 | rear right knee |

If the physical layout makes a different map cleaner, update this table and the code together.

## Mechanical Assembly

1. Install the servos into the body.
2. Add servo clips or retainers so the servos cannot slide out under load.
3. Attach each upper leg to its hip/shoulder servo.
4. Attach each lower leg to its knee servo.
5. Move each leg by hand through its expected range before powering anything.
6. Check that wires can move without getting pulled, pinched, or wrapped around a joint.
7. Keep the robot supported while testing. Do not let the full weight sit on an uncalibrated pose yet.

## Wiring Overview

Quady uses serial bus servos, so the Waveshare boards are acting as the servo bus interface between the ESP32 and the STS3215 servos.

Each bus needs:

- ESP32 TX to adapter RX
- ESP32 RX to adapter TX
- ESP32 GND to adapter GND
- External servo power connected to the servo power input
- Servos daisy-chained on the matching bus

The servo power supply must be separate from the ESP32 USB power. The grounds must still be connected.

## Current Two-Bus ESP32 Wiring

The current multi-bus sketches, including `ServoTester/ServoTester.ino` and `ID_Checker/ID_Checker.ino`, use this pinout:

| Bus | ESP32 TX | ESP32 RX | Servo IDs |
|---|---:|---:|---|
| Bus 1 | GPIO 9 | GPIO 10 | 1-4 |
| Bus 2 | GPIO 11 | GPIO 12 | 5-8 |

Wire each Waveshare adapter like this:

| ESP32 | Waveshare bus servo adapter |
|---|---|
| GPIO 9 | Bus 1 RX |
| GPIO 10 | Bus 1 TX |
| GPIO 11 | Bus 2 RX |
| GPIO 12 | Bus 2 TX |
| GND | GND on both adapters |

Then connect servos `1-4` to the first adapter and servos `5-8` to the second adapter.

## Older Utility Sketch Pinouts

Some older single-bus test sketches use different pins:

| Sketch | TX | RX |
|---|---:|---:|
| `One_Servo_Test/One_Servo_Test.ino` | GPIO 17 | GPIO 18 |
| `ID_Editor/ID_Editor.ino` | GPIO 17 | GPIO 18 |

`ServoID_Recovery/ServoID_Recovery.ino` uses:

| Bus | TX | RX |
|---|---:|---:|
| Bus 1 | GPIO 17 | GPIO 18 |
| Bus 2 | GPIO 15 | GPIO 16 |

Before uploading a sketch, check the pin definitions at the top of the file and make sure the wiring matches that sketch.

## Power Safety

1. Use a 12 V supply that can handle servo current.
2. Power the ESP32 from USB or its normal logic input.
3. Power the STS3215 servos from the servo power input on the adapter.
4. Connect grounds together between the ESP32, both adapters, and the servo power supply.
5. Do not power the servos only from the ESP32.
6. During first tests, keep one hand near the power switch or unplug point.

If a servo gets hot, chatters, or drives into a hard stop, kill power and fix the range before continuing.

## Bring-Up Order

1. Upload `One_Servo_Test/One_Servo_Test.ino` and verify one loose servo moves safely.
2. Use `ID_Editor/ID_Editor.ino` or `ServoID_Recovery/ServoID_Recovery.ino` to assign unique IDs.
3. Upload `ID_Checker/ID_Checker.ino` and confirm all IDs respond on the expected bus.
4. Upload `ServoTester/ServoTester.ino`.
5. Use the serial monitor at `115200` baud.
6. Type `help` to see commands.
7. Use `list` to check saved ranges.
8. Use `nudge <id> <ticks>` for tiny movements.
9. Use `mark <id> a` and `mark <id> b` to save safe endpoints.
10. Use `test <id>` only after a servo has a known safe range.

Start with the robot lifted off the table so a wrong direction cannot make the leg jam into the ground.

## First Full-Body Test

1. Confirm every servo ID responds.
2. Confirm every joint has a saved safe range.
3. Move each servo to roughly center position.
4. Install the legs in a neutral stance.
5. Run one joint at a time with a small buffer.
6. Watch for mirrored legs moving opposite directions.
7. Fix the ID map, horn orientation, or range before trying full poses.

The first goal is not walking. The first goal is reliable, boring, repeatable joint control.

## Current Open Items

- Finalize the real servo ID to leg/joint map.
- Decide whether the current default ESP32 pins should stay `9/10` and `11/12`, or whether all utility sketches should be standardized around another pinout.
- Add photos of the assembled wiring once the layout is locked in.
- Add a final standing pose procedure after joint ranges are calibrated.
