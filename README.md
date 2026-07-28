# WarioWareTwistedRecomp

PC bring-up of **WarioWare: Twisted!** (Game Boy Advance, USA) on
[`gbarecomp`](https://github.com/mstan/gbarecomp).

The ROM identity gate, SRAM save, 16-shard generated translation, native runner,
and cartridge gyro/rumble wire protocol are in place. PC gyro input is simulated
with horizontal mouse dragging, and headless tests can use a deterministic
sensor sweep.

The interpreter backend is temporarily selected by the game launcher because
the current static translation stalls during early boot. This is a compatibility
bring-up mode: the native runtime, PPU, audio, input, save, BIOS, and cartridge
devices remain active while ARM instructions use the reference interpreter.
Set `GBARECOMP_FORCE_INTERP=0` to exercise the experimental static path.

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

- Engine worktree: `../gbarecomp-warioware-twisted`
- Game ROM: `variants/warioware_twisted/roms/warioware_twisted_usa.gba`
- Game config: `variants/warioware_twisted/game.toml`
- Generated translation: `variants/warioware_twisted/generated/`

## Build

From PowerShell with CMake, Ninja, MinGW-w64, and SDL2 available:

```powershell
& C:\msys64\mingw64\bin\cmake.exe `
    -S ..\gbarecomp-warioware-twisted `
    -B ..\gbarecomp-warioware-twisted\build-native -G Ninja
& C:\msys64\mingw64\bin\cmake.exe `
    --build ..\gbarecomp-warioware-twisted\build-native `
    --target gba_recompile

.\tools\regen.ps1

& C:\msys64\mingw64\bin\cmake.exe -S . -B build -G Ninja
& C:\msys64\mingw64\bin\cmake.exe `
    --build build --target WarioWareTwistedRecomp
```

Run from the project root so the relative config and asset paths resolve:

```powershell
.\build\WarioWareTwistedRecomp.exe `
    variants\warioware_twisted\game.toml
```

Controls:

- D-pad: arrow keys
- A / B: `Z` / `X`
- Start / Select: Enter / Backspace
- Gyro: hold the left mouse button and drag horizontally; faster motion
  produces a larger angular-rate sample and releasing returns it to center

For a reproducible headless gyro run:

```powershell
$env:GBARECOMP_GYRO_TEST = "sweep"
.\build\WarioWareTwistedRecomp.exe `
    variants\warioware_twisted\game.toml `
    --no-window --frames 60
```

`GBARECOMP_GYRO_TEST` also accepts a numeric signed sensor offset. The
cartridge rumble output line is modeled and covered by a unit test, but it is
not connected to host vibration yet. Android sensor and haptics work remains
future work; the provider boundary is described in
[`docs/gyro-plan.md`](docs/gyro-plan.md).

## Current validation

- ROM generation: 2,839 functions (4 ARM, 2,835 Thumb), 16 shards
- Native MinGW/SDL executable builds successfully
- ARM interpreter and cartridge GPIO tests pass
- 60-frame real-BIOS and HLE-BIOS headless runs complete with no unmapped or
  unhandled I/O accesses
- A rendered frame reaches the WarioWare health-and-safety screen
