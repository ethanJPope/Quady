# Quady

## Arduino tools

- `ServoID_Recovery/ServoID_Recovery.ino` - menu-driven SCServo ID recovery tool for two servo controllers.
- Bus 1: RX 18, TX 17
- Bus 2: RX 16, TX 15

### Recovery commands

- `scan 1` or `scan 2`
- `scan all`
- `scanraw 1` or `scanraw 2`
- `set <bus> <currentId> <newId>`
- `wizard <bus>`
- `ping` uses a lighter retry test; `scan` is stricter.
- Scans now require repeated consistent replies before reporting a servo.
- `scanraw` is a looser mode for diagnosing flaky wiring or bus timing.
- The tool will refuse to write a new ID if that ID is already responding on the same bus.