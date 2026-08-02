# WarioWare: Twisted! Recomp

> **Experimental preview.** This recompilation is a byproduct of developing
> [gbarecomp](https://github.com/mstan/gbarecomp): the games are the proving
> ground, while the reusable framework is the larger goal. This is not a
> finished commercial port, so expect rough edges and please report problems.
> For more context, read
> [Recomp + AI: 5 Months Later »](https://1379.tech/recomp-ai-5-months-later/).

Static recompilation of **WarioWare: Twisted!** for Windows and Android, with
native motion controls for the cartridge's built-in gyroscope.

The game ROM and Nintendo GBA BIOS are **not included**. You must provide your
own legally obtained dumps.

## Status

The game boots and runs on Windows and Android, including its menus,
microgames, cartridge saves, and gyro-controlled stages. Android has been
tested on a Galaxy S22 Ultra. The initial `v0.0.1` builds are experimental, so
back up important saves and report repeatable crashes or motion-control
problems.

## Quick start

### Android

1. Download the experimental APK from
   [Android Releases](../../releases/tag/android-v0.0.1) and install it.
2. Open the app and select your **WarioWare: Twisted! (USA)** ROM and retail
   GBA BIOS.
3. Hold the phone in landscape, configure the launcher if desired, and select
   **Play**.
4. Twist the phone like the original cartridge to control gyro microgames.

The Android launcher uses the system file picker and remembers valid files.
Enable **Skip launcher on boot** to start the game directly on later launches.

### Windows

1. Download the Windows zip from
   [Windows Releases](../../releases/tag/v0.0.1) and extract it.
2. Run `WarioWareTwistedRecomp.exe`.
3. Select your matching ROM and retail GBA BIOS, configure controls, and
   select **Play**.

On Windows, a compatible controller's motion sensor provides gyro input.
Holding the left mouse button and dragging horizontally is the fallback.

## Features

- Native Windows x64 and Android arm64 builds
- Phone gyro and supported controller-motion input
- Mouse-drag gyro fallback on Windows
- Touch-friendly Android launcher and in-game menu
- ROM and BIOS setup through the shared
  [recomp-ui](https://github.com/mstan/recomp-ui) launcher
- Keyboard, controller, and touchscreen controls
- Windowed and fullscreen desktop play
- Cartridge saves and save states

## Controls

| GBA control | Keyboard |
|---|---|
| D-Pad | Arrow keys |
| A / B | X / Z |
| Start | Enter |
| Select | Right Shift |
| L / R | C / V |

Controllers are detected automatically. Gyro sensitivity and button mappings
can be changed from the launcher. On Android, use the on-screen controls and
the phone's motion sensor.

## Building from source

Windows development requires CMake, Ninja, MSYS2 MinGW64, and SDL2:

```powershell
git clone --recurse-submodules `
  https://github.com/mstan/WarioWareTwistedRecomp.git
cd WarioWareTwistedRecomp

cmake -S gbarecomp -B gbarecomp/build-native -G Ninja
cmake --build gbarecomp/build-native --target gba_recompile
pwsh tools/regen.ps1
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --target WarioWareTwistedRecomp
```

Android build and device-validation instructions live in
[`android/README.md`](android/README.md).

Generation requires the supported ROM revision and a retail GBA BIOS. Their
identities and local development paths are documented in
[`variants/warioware_twisted/game.toml`](variants/warioware_twisted/game.toml).
ROM-derived generated code, copyrighted inputs, saves, caches, and build output
remain local and are never included in public releases.

Contributors can run `pwsh tools/verify-attract.ps1` for the automated desktop
acceptance route and `pwsh tools/make_release.ps1 -Version 0.0.1` to build a
sanitized Windows package.

## Legal

This is an unofficial, non-commercial preservation and research project. It
is not affiliated with or endorsed by Nintendo. WarioWare and related names,
characters, artwork, and game data are trademarks or copyrights of their
respective owners.

No copyrighted game ROM or Nintendo BIOS data is distributed by this project.

---

Part of the **R.A.I.D. — Retro AI Development** static-recompilation
community.
