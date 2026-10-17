# WarioWare: Twisted! Android v0.0.3

- Fix the game flipping between landscape directions when the phone is turned
  upside down, even with Android auto-rotate disabled. Setup and gameplay now
  stay in one landscape direction while motion controls remain available.
- Preserve the display lock when SDL creates or resizes the game window.
- Keep the original Android signing certificate and application ID so this
  installs as an update, preserving imported ROM/BIOS files, settings and saves.

Experimental arm64 APK for Android 9 or newer. Supply your own matching USA
ROM and GBA BIOS; neither is included. Windows remains at v0.0.1.

# WarioWareTwistedRecomp Windows v0.0.1

Initial private Windows x64 release of **WarioWare: Twisted!** for the
`gbarecomp` runtime.

## Included

- Static GBA cartridge recompilation with SRAM saves.
- Stable MP2K audio defaults.
- DualSense and compatible SDL controller motion-sensor input.
- Adjustable gyro sensitivity in the shared `recomp-ui` launcher.
- Horizontal click-and-drag mouse input as a simulated gyro fallback.
- Windows x64 executable, required runtime DLLs, launcher assets, and the
  self-contained overlay toolchain.
- The validated warm overlay cache required by WarioWare's RAM-copied boot
  routines. Only compiled overlay DLLs are included; ROM-derived C/log
  diagnostics are excluded.

## Required user files

Supply your own legally-obtained:

- WarioWare: Twisted! (USA) ROM, SHA-1
  `f0102d0d6f7596fe853d5d0a94682718278e083a`
- GBA BIOS, SHA-1 `300c20df6731a33952ded8c436f7f186d25d3492`

Neither file is included in the repository or release.

## Android status

The Android project is an unreleased prototype. No APK, ROM-bundling helper,
or Android payload is included in v0.0.1.
