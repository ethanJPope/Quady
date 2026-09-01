# Quady

Quady is my 8-servo 3D-printed quadruped robot dog project. The goal is to build a real walking robot from scratch, then eventually connect the physical design to simulation and AI training with NVIDIA Isaac Sim / Isaac Lab. This project mixes the parts of engineering I enjoy most: CAD, 3D printing, electronics, programming, and robotics. It is still a work in progress, but the main goal is to get a first version walking and learn enough from it to make the next version better.

<<<<<<< Updated upstream
## Project Goals
=======
- `Servo_ID_Pairing/Servo_ID_Pairing.ino` - two-bus Serial Monitor tool that
  detects a hand-moved servo, asks for its intended ID, refuses occupied IDs,
  and writes only after an explicit `yes` confirmation.
- `ServoID_Recovery/ServoID_Recovery.ino` - menu-driven SCServo ID recovery tool for two servo controllers.
- Final right bus: RX 14, TX 13 (expected IDs 1-4)
- Final left bus: RX 12, TX 11 (expected IDs 5-8)

### Pairing commands

- `scan` scans IDs 0-20 on both sides and begins movement detection.
- `scan full` scans IDs 0-253 when an address is outside the quick range.
- `list` shows the detected side/ID addresses.
- `watch` resets the movement baselines.
- `cancel` aborts a selected servo or pending EEPROM write.
- `isolated` runs the required full-bus proof after all other servos on the
  selected side have been physically disconnected. The sketch will not write
  an ID without this one-address isolation check and a following `yes`.
- With the Waveshare Bus Servo Adapter (A), use UART jumper position A and
  connect the UART labels RX-to-RX and TX-to-TX as documented by Waveshare.

Tested compile environment for this draft:

- Board FQBN: `esp32:esp32:esp32s3`
- Espressif ESP32 platform: `3.3.10`
- Installed SCServo library: `1.0.2` (`workloads/scservo` package metadata)
>>>>>>> Stashed changes

- Build a compact 8-servo quadruped robot dog.
- Design and print the body and legs myself.
- Control the servos through serial bus servo hardware.
- Develop basic movement tests before trying more advanced walking.
- Use simulation and AI training later once the physical design is far enough along.
- Document the process honestly, including the mistakes and redesigns.

<<<<<<< Updated upstream
## Current Design

Quady is currently an 8-servo robot dog, which means each leg has two powered joints. This keeps the first version simpler than a 12-servo design while still being complex enough to learn real quadruped mechanics and control.

<img width="4080" height="3072" alt="IMG_20260611_183636071_AE" src="https://github.com/user-attachments/assets/1cd2bef3-71bd-4ee5-9695-c7bdd2eb0b95" />

The current plan is:

- 4 legs
- 2 servos per leg
- 8 total servos
- 3D-printed frame and leg parts
- Serial bus servo control
- Future simulation/training work in Isaac Sim and Isaac Lab

## Hardware

Known hardware for the current version:

| Part | Notes |
|---|---|
| Feetech STS3215 servos | 12V serial bus servos |
| Waveshare Bus Servo Adapter | Used to interface with the servos |
| 3D-printed frame and legs | Designed and iterated through CAD |
| External power | Needed for reliable servo testing |

This section will get more specific as the electronics and final mechanical layout become locked in.

In depth assembly instructions can be found here. [ASSEMBLY.md](ASSEMBLY.md).

## Software

The software side is being built in stages:

1. Basic servo communication.
2. Individual joint testing.
3. Leg movement tests.
4. Full-body pose control.
5. Simple walking patterns.
6. Simulation and AI training experiments.

The early focus is on making the real robot move reliably before making the software too complicated.

## Roadmap

- [ ] Finish first complete CAD version.
- [ ] Print and assemble the first full robot body.
- [ ] Test each servo and joint individually.
- [ ] Create basic standing poses.
- [ ] Add simple movement patterns.
- [ ] Record a first walking demo.
- [ ] Start Isaac Sim / Isaac Lab setup.
- [ ] Experiment with AI training once the mechanical design is usable.

## Why I Am Building This

I wanted a project that combines hardware and programming in a way that actually feels challenging. A robot dog is a good target because it forces me to deal with mechanical design, electronics, control systems, and eventually simulation.

This is also a project I want to be able to show as real engineering work, not just a quick demo. The first version does not need to be perfect, but it needs to teach me enough to keep improving it.

## Status

Quady is under active development. The design has changed from a 12-servo robot dog to an 8-servo robot dog to make the first version more realistic and easier to finish.

More build notes, photos, CAD exports, wiring details, and control code will be added as the project develops.
=======
- `scan 1` or `scan 2`
- `scan all`
- `scanraw 1` or `scanraw 2`
- `set <bus> <currentId> <newId>`
- `wizard <bus>`
- `ping` uses a lighter retry test; `scan` is stricter.
- Scans now require repeated consistent replies before reporting a servo.
- `scanraw` is a looser mode for diagnosing flaky wiring or bus timing.
- The tool will refuse to write a new ID if that ID is already responding on the same bus.
>>>>>>> Stashed changes
