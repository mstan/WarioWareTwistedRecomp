# Android experimental release

This target is an experimental Android port for 64-bit ARM devices running
Android 9 or newer, distributed as a debug-signed APK for sideload testing.
Version 0.0.4 uses native execution by default, including the expanded Spindex
microgame corpus and ROM-backed routines copied into RAM. Uncovered paths
still report interpreter fallback; the recorded coverage applies to tested
routes, not every possible game variation.

The Android shell (SDL2, `org.gbarecomp` setup and game activities, manifest,
native CMake root, payload staging) is shared by every gbarecomp game and lives
in the engine at `gbarecomp/platform/android/`. This directory only holds the
game metadata (`app/build.gradle`), `game_android.toml` and resources. Build
and validate with the engine scripts:

```powershell
..\gbarecomp\platform\android\tools\build-apk.ps1 -GameAndroidDir .\android
..\gbarecomp\platform\android\tools\android-validate.ps1 `
  -Package com.mstan.wariowaretwisted -Launch -PullArtifacts
.\tools\validate-s22.ps1   # physical Galaxy S22 Ultra pass
```

See `gbarecomp/platform/android/tools/README.md` for all options (ABIs,
engine/recomp-ui worktree roots, AVD bootstrap).

The device validation scripts use a debuggable QA APK so `adb run-as` can read
diagnostics. `tools/validate-s22.ps1` expects the native backend by default;
`-ExpectedBackend interpreter` supports historical diagnostic builds. Normal
interactive QA launches retain normal audio.

For the orientation regression, use an emulator started with `-no-audio` and
with the ROM/BIOS already configured:

```powershell
python tools/validate-orientation.py --serial emulator-5554 --activity setup --output release-stage/orientation-setup
python tools/validate-orientation.py --serial emulator-5554 --activity game --output release-stage/orientation-game
```

The check injects physical acceleration through landscape, reverse landscape,
portrait and upside-down poses with system auto-rotate both off and on. It
asserts fixed display rotation and orientation requests, records screenshots
and Android dumps, and restores the original rotation settings and acceleration.
Use `--expect-flip` with the previous build to reproduce the original bug.

Normal builds use a first-launch document picker, verify user-supplied assets,
and store them in the app's private directory. The public APK contains neither
file. APK files are ignored by Git.

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

- Gameplay stays in a fixed landscape direction, including when the phone
  is upside down. Android auto-rotate does not change the game display.
- Rotate the phone around its screen-normal axis for cartridge gyro input.
- A connected controller, including DualSense motion, remains supported.
- Touch controls provide the GBA D-pad, A, B, L, R, Start, and Select.
- Long-press an unused part of the game screen for 650 ms, three-finger tap,
  or press Back to open settings.
- Gyro sensitivity defaults to the calibrated 1.00x baseline and can be
  adjusted in Motion settings.
