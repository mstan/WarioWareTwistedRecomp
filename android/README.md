# Android prototype

This target is an unreleased experiment. It is not a production packaging
path and must not be published.

Normal builds use a first-launch document picker, verify user-supplied assets,
and store them in the app's private directory. APK files are ignored by Git.

For a private sideload build, Gradle can embed local verified assets without
copying them into the source tree:

```powershell
.\gradlew.bat :app:assembleDebug `
  -PprivateBios=F:\path\to\gba_bios.bin `
  -PprivateRom=F:\path\to\warioware_twisted_usa.gba
```

Both properties are required together. The resulting APK is private and must
not be published or attached to a public release.

## Controls

- Rotate the phone around its screen-normal axis for cartridge gyro input.
- A connected controller, including DualSense motion, remains supported.
- Touch controls provide the GBA D-pad, A, B, L, R, Start, and Select.
- Long-press an unused part of the game screen for 650 ms to open settings.
- Gyro sensitivity defaults to 0.25x and can be adjusted in Motion settings.
