# WarioWare: Twisted! — native Linux x86_64

This experimental package runs natively, without Proton. Physical Steam Deck
motion, controls, audio and fullscreen qualification are still pending.

Extract the archive into a writable folder and run `./run.sh`. Keep the binary,
`assets`, `lib`, and `variants` together. Supply your own WarioWare: Twisted! USA
ROM and retail GBA BIOS in the launcher. Neither input is included.

The launcher stores its settings beside the executable and the game uses the
`saves` folder. When updating, preserve those files. The archive never includes
player settings, imported inputs or saves.

The standalone package includes SDL2 and needs glibc 2.31 or newer, a compatible
C++ runtime, OpenGL, FreeType, HarfBuzz and an X11 or Wayland desktop. A Steam
runtime's existing library selection takes precedence over the bundled SDL2.
The build targets Valve's Steam Linux Runtime 3 SDK.

## Controls and motion

Keyboard: arrows, X/Z for A/B, Enter for Start, Right Shift for Select, C/V for
L/R. Compatible SDL controllers supply buttons and gyro. Twist around the
controller's face normal. Holding the left mouse button and dragging
horizontally remains a motion fallback. Sensitivity is configurable in the
launcher.

For direct Deck motion, SDL must see the native sensor-capable controller.
If Steam Input exposes only a virtual controller without gyro, use the
per-game Steam Input setting to allow direct controller access, then restart
the game. Do not change system controller permissions or install a motion
server merely to run this package.

The startup log reports the selected controller and whether its gyro enabled.
For a useful diagnostic log, run `./run.sh 2>controller.log`. Check actual game
response in both twist directions; a controller name alone does not establish
motion support. No controller is required for the mouse fallback.

SDL selects the desktop video driver normally. To select a backend explicitly,
use `SDL_VIDEODRIVER=wayland ./run.sh` or `SDL_VIDEODRIVER=x11 ./run.sh`.
Fullscreen and windowed modes are available in the display settings.

## Building and packaging

Use a Linux C++20 compiler, CMake, Ninja and the SDL2, OpenGL, FreeType and
HarfBuzz development packages. For distribution, build in the official
[Steam Runtime SDK](https://github.com/ValveSoftware/steam-runtime) rather than
linking against a newer development machine's libraries.

From the source checkout, initialize its submodules and provide the supported
ROM at `variants/warioware_twisted/roms/warioware_twisted_usa.gba` and BIOS at
`gbarecomp/bios/gba_bios.bin`. Build the pinned compiler and regenerate both
native corpora:

```sh
cmake -S gbarecomp -B build-compiler -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build-compiler --target gba_recompile --parallel 2
build-compiler/gba_recompile --bios gbarecomp/bios/gba_bios.bin \
  --config gbarecomp/bios/gba_bios.toml --out gbarecomp/src/runtime/generated_bios
build-compiler/gba_recompile \
  --rom variants/warioware_twisted/roms/warioware_twisted_usa.gba \
  --config variants/warioware_twisted/game.toml \
  --out variants/warioware_twisted/generated
cmake -S . -B build-linux -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DGBARECOMP_SELFHEAL_RECOMPILE_DEFAULT=OFF
cmake --build build-linux --target WarioWareTwistedRecomp --parallel 2
python3 tools/package_linux.py --build-dir build-linux \
  --sdl-library /usr/lib/x86_64-linux-gnu/libSDL2-2.0.so.0 \
  --sdl-license /usr/share/doc/libsdl2-2.0-0/copyright \
  --output WarioWareTwistedRecomp-linux-x86_64-review.tar.gz
```

Use the SDK's GCC toolchain. Its older Clang 11/libstdc++ 10 combination cannot
parse the C++20 ranges headers. Do not include generated code, ROMs, BIOS files,
test snapshots or imported user data in the distribution.
