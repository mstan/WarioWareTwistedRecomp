# Android prototype

This target is an unreleased experiment. It is not a production packaging
path and must not be published.

The initial ROM/BIOS bundling task was deliberately removed. A future Android
release must use a first-launch document picker, verify user-supplied assets,
and store them in the app's private directory. APK files are ignored by Git.

## Controls

- Rotate the phone around its screen-normal axis for cartridge gyro input.
- A connected controller, including DualSense motion, remains supported.
- Touch controls provide the GBA D-pad, A, B, L, R, Start, and Select.
- Long-press an unused part of the game screen for 650 ms to open settings.
- Gyro sensitivity defaults to 0.25x and can be adjusted in Motion settings.
