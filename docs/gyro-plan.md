# Gyro and rumble status

WarioWare: Twisted! uses a cartridge gyroscope and rumble motor on the GBA GPIO
pins. The engine keeps the cartridge wire protocol separate from host input so
the same game build can eventually accept PC mouse, controller, automated, or
Android sensor providers.

Implemented:

- `GbaGyro`, attached through the engine's `GpioDevice` / `GpioPort` seam
- RZWE/RZWJ/RZWP cartridge detection
- 16-bit, MSB-first gyro samples with a calibrated center of `0x700`
- Cartridge sample, clock, data, and rumble-pin behavior
- Unit coverage for center sample serialization, rumble, and cart detection
- PC input: left-button horizontal mouse motion maps to a bounded angular rate
- Headless input: `GBARECOMP_GYRO_TEST=sweep` provides a deterministic triangle
  wave; a numeric value supplies a fixed signed offset

The game performs a real cartridge calibration during startup and explicitly
asks the player not to move the system. Use `GBARECOMP_GYRO_TEST=0` through
that screen. Starting the continuous sweep at boot intentionally looks like a
moving handheld and prevents calibration from completing.

Remaining:

- Tune PC sensitivity and calibration from playtesting
- Add optional keyboard/controller gyro bindings
- Route the modeled rumble output to SDL gamepad haptics
- Implement an Android provider using platform rotation/gyroscope APIs
- Route the rumble output to Android device vibration

Android should feed the existing host-neutral signed sample interface. GPIO
timing, serialization, calibration center, and rumble signaling stay in the
game-agnostic engine.
