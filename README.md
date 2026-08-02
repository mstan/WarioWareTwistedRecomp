# WarioWareTwistedRecomp

PC bring-up of **WarioWare: Twisted!** (Game Boy Advance, USA) on
[`gbarecomp`](https://github.com/mstan/gbarecomp).

The ROM identity gate, SRAM save, 16-shard generated translation, native runner,
and cartridge gyro/rumble wire protocol are in place. SDL controller motion
sensors (including the PlayStation 5 DualSense) drive the gyro on PC, horizontal
mouse dragging remains a fallback, and headless tests can use a deterministic
sensor sweep.

Static cart recompilation is the default. Code copied to EWRAM/IWRAM at runtime
uses gbarecomp's RAM dispatch/self-heal path. Set `GBARECOMP_FORCE_INTERP=1`
only when the reference interpreter is useful for diagnostics.

## Pinned cartridge

| Field | Value |
|---|---|
| Header title | `WARIOTWISTED` |
| Game code | `RZWE` |
| Region / revision | USA / 0 |
| Size | 16 MiB |
| SHA-1 | `f0102d0d6f7596fe853d5d0a94682718278e083a` |
| MD5 | `89579f4dfe1ed24a7cd16a6a61a72a17` |
| Save signature | `SRAM_V113` (32 KiB) |

The ROM and GBA BIOS are user-provided, gitignored assets and must never be
committed.

## Local layout

- Engine: `gbarecomp/` (git submodule)
- Launcher: `recomp-ui/` (git submodule)
- Game ROM: `variants/warioware_twisted/roms/warioware_twisted_usa.gba`
- Game config: `variants/warioware_twisted/game.toml`
- Generated translation: `variants/warioware_twisted/generated/`

## Build

From PowerShell with CMake, Ninja, MinGW-w64, and SDL2 available:

```powershell
git submodule update --init --recursive

& C:\msys64\mingw64\bin\cmake.exe `
    -S .\gbarecomp `
    -B .\gbarecomp\build-native -G Ninja
& C:\msys64\mingw64\bin\cmake.exe `
    --build .\gbarecomp\build-native `
    --target gba_recompile

.\tools\regen.ps1

& C:\msys64\mingw64\bin\cmake.exe -S . -B build -G Ninja `
    -DCMAKE_BUILD_TYPE=Release
& C:\msys64\mingw64\bin\cmake.exe `
    --build build --target WarioWareTwistedRecomp --parallel 2
```

To make the Windows release zip (desktop only):

```powershell
.\tools\make_release.ps1 -Version 0.0.1
```

The release packager rejects ROM, BIOS, save, and APK files before creating
the archive. It stages only the compiled DLL portion of the validated warm
overlay cache under both supported compiler backends; ROM-derived cache source
and logs are excluded. Android is distributed as a separate experimental APK
and is not part of desktop releases.

Run from the project root so the relative config and asset paths resolve:

```powershell
.\build\WarioWareTwistedRecomp.exe `
    variants\warioware_twisted\game.toml
```

Windowed runs open the shared `recomp-ui` pre-boot launcher. Use
`--no-launcher` to skip it once or `--launcher` to override a persisted
skip-launcher preference.

Controls:

- Keyboard D-pad: arrow keys
- Keyboard A / B: `X` / `Z`
- Keyboard Start / Select: Enter / Right Shift
- Controller: D-pad, south/east face buttons, Options/Create, and L1/R1
- Controller gyro: twist the controller like a steering wheel. A supported
  sensor is detected and enabled automatically.
- Mouse gyro fallback: hold the left button and drag horizontally.

The launcher's `CONTROLLER -> Configure -> MOTION` card controls gyro
sensitivity from `0.25x` to `4.00x` and persists it beside the executable.
The equivalent command-line option is `--gyro-sensitivity <value>`. On Android,
the displayed 1.00x setting uses WarioWare's device-calibrated 0.75x response.

For a reproducible headless gyro run:

```powershell
$env:GBARECOMP_GYRO_TEST = "sweep"
.\build\WarioWareTwistedRecomp.exe `
    variants\warioware_twisted\game.toml `
    --no-window --frames 60
```

`GBARECOMP_GYRO_TEST` also accepts a numeric signed sensor offset. The
cartridge rumble output line is modeled and covered by a unit test, but it is
not connected to host vibration yet. Android uses the device motion sensor for
cartridge gyro input; the provider boundary is described in
[`docs/gyro-plan.md`](docs/gyro-plan.md).

## Attract-mode verification

The deterministic acceptance route dismisses the health-and-safety screen at
frame 300, skips the opening story at frame 620, keeps the gyro centered through
the cartridge's calibration screen, reaches the title by frame 1,200, then
leaves input neutral. The title times out into its animated attract loop by
frame 3,000.

```powershell
.\tools\verify-attract.ps1
```

The script requires the native executable to be built. It runs with an isolated
temporary SRAM file and the normal development self-heal cache, requires zero
unmapped and unhandled I/O accesses, checks the final PPU frame count, and
verifies the rendered attract framebuffer hash. Static recompilation is
verified by default; pass `-Interpreter` to compare the reference backend.
Pass `-ColdCache` to audit first-run static coverage with a new cache. Artifacts
are written under `build/attract-verify/`.

A completely cold self-heal cache currently reaches an unresolved static
coverage bridge around ROM addresses `0x080013EC`/`0x080013F8` during startup.
The normal development-cache static route and the reference interpreter both
reach attract mode; closing this cold-cache gap is the next engine task.

## Current validation

- ROM generation: 2,839 functions (4 ARM, 2,835 Thumb), 16 shards
- Native MinGW/SDL executable builds successfully
- ARM interpreter and cartridge GPIO tests pass
- 60-frame real-BIOS and HLE-BIOS headless runs complete with no unmapped or
  unhandled I/O accesses
- A rendered frame reaches the WarioWare health-and-safety screen
- Static recompilation reaches the title at frame 1,200 and the animated
  no-input attract loop at frame 3,000 with a framebuffer matching the
  reference interpreter
