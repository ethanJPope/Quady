# Quady

Quady is my 8-servo 3D-printed quadruped robot dog project. The goal is to build a real walking robot from scratch, then eventually connect the physical design to simulation and AI training with NVIDIA Isaac Sim / Isaac Lab. This project mixes the parts of engineering I enjoy most: CAD, 3D printing, electronics, programming, and robotics. It is still a work in progress, but the main goal is to get a first version walking and learn enough from it to make the next version better.

## Project Goals

- Build a compact 8-servo quadruped robot dog.
- Design and print the body and legs myself.
- Control the servos through serial bus servo hardware.
- Develop basic movement tests before trying more advanced walking.
- Use simulation and AI training later once the physical design is far enough along.
- Document the process honestly, including the mistakes and redesigns.

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

Quick build and wiring notes are in [ASSEMBLY.md](ASSEMBLY.md).

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
