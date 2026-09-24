# Android experimental release

This target is an experimental Android port for 64-bit ARM devices running
Android 9 or newer, distributed as a debug-signed APK for sideload testing.

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

- Rotate the phone around its screen-normal axis for cartridge gyro input.
- A connected controller, including DualSense motion, remains supported.
- Touch controls provide the GBA D-pad, A, B, L, R, Start, and Select.
- Long-press an unused part of the game screen for 650 ms, three-finger tap,
  or press Back to open settings.
- Gyro sensitivity defaults to the calibrated 1.00x baseline and can be
  adjusted in Motion settings.
