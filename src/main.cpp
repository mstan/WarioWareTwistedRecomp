#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "runtime.h"

#if defined(__ANDROID__)
#include <SDL_system.h>
#include <unistd.h>
#endif

#if defined(GBAGAME_RECOMP_UI)
#include "game_launcher_boot.h"
#endif

#ifndef GBARECOMP_BUILTIN_NAME
#define GBARECOMP_BUILTIN_NAME "GBA cartridge"
#endif
#ifndef GBARECOMP_BUILTIN_SHA1
#define GBARECOMP_BUILTIN_SHA1 ""
#endif
#ifndef GBARECOMP_BUILTIN_CRC32
#define GBARECOMP_BUILTIN_CRC32 0
#endif
#ifndef GBARECOMP_BUILTIN_REGION
#define GBARECOMP_BUILTIN_REGION ""
#endif
#ifndef GBARECOMP_DEFAULT_GAME_CONFIG
#define GBARECOMP_DEFAULT_GAME_CONFIG "game.toml"
#endif

namespace {

void set_environment_default(const char* name, const char* value) {
    if (std::getenv(name) != nullptr) return;
#if defined(_WIN32)
    _putenv_s(name, value);
#else
    setenv(name, value, 0);
#endif
}

void print_usage() {
    std::printf(
        "WarioWareTwistedRecomp [--bios <path>] [--rom <path>] "
        "[game.toml]\n"
        "The BIOS and ROM must match the SHA-1 identities in game.toml.\n"
        "Hold the left mouse button and drag horizontally to simulate gyro "
        "motion.\n"
        "Windowed play opens the recomp-ui launcher first; --no-launcher "
        "skips it once.\n"
        "Static recompilation is the default; set GBARECOMP_FORCE_INTERP=1 "
        "for the reference interpreter diagnostic backend.\n");
}

}  // namespace

int warioware_main(int argc, char** argv) {
#if defined(__ANDROID__)
    // SDLActivity installs assets in the app's private files directory. Make
    // that the process root so the existing desktop config/launcher seam can
    // use the same relative layout without Android-only path plumbing.
    if (const char* storage = SDL_AndroidGetInternalStoragePath())
        chdir(storage);
    // Android does not reliably surface native stdout/stderr in logcat. Keep a
    // small launch log beside the private payload so setup and boot failures
    // remain diagnosable with `adb shell run-as`.
    std::freopen("android-runtime.log", "w", stderr);
    std::freopen("android-runtime.log", "a", stdout);
    std::setvbuf(stderr, nullptr, _IONBF, 0);
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    set_environment_default("GBARECOMP_SELFHEAL_RECOMPILE", "0");
    // Android cannot use the desktop overlay compiler, and physical devices
    // reach timing-dependent indirect blocks that are not present in a cold
    // static corpus. Use the engine's validated interpreter CPU backend while
    // retaining native PPU/audio/input/gyro host services.
    setenv("GBARECOMP_FORCE_INTERP", "1", 1);
    std::fprintf(stderr, "android: CPU backend=interpreter (device-safe)\n");
#endif
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--help") == 0 ||
            std::strcmp(argv[i], "-h") == 0) {
            print_usage();
            return 0;
        }
    }

    // WarioWare: Twisted! legitimately spends long periods in polling loops.
    // The engine's instruction-level hang watchdog treats that as suspicious
    // and its trace capture can starve interactive audio. Keep it available as
    // an explicit diagnostic override, but disable it for normal play.
    set_environment_default("GBARECOMP_HANG_WATCHDOG", "0");

    // The current static real-BIOS route stalls at its cartridge handoff for
    // this title. Boot HLE skips only the intro; IRQs and unhandled SWIs still
    // dispatch through the real recompiled BIOS during gameplay.
    set_environment_default("GBARECOMP_BIOS_HLE", "1");

    // The engine's custom clock-domain bridge currently garbles this title's
    // otherwise-correct 65536 Hz mixer stream. Queue it directly and let SDL
    // perform only the host-device conversion.
    set_environment_default("GBARECOMP_AUDIO_DIRECT", "1");

    gbarecomp::RunOptions opts;
    opts.builtin_game_name = GBARECOMP_BUILTIN_NAME;
    opts.builtin_rom_sha1 = GBARECOMP_BUILTIN_SHA1;
    opts.builtin_rom_crc32 = GBARECOMP_BUILTIN_CRC32;
    opts.launcher_region = GBARECOMP_BUILTIN_REGION;
    opts.launcher_game_config = GBARECOMP_DEFAULT_GAME_CONFIG;
    opts.launcher_save_path =
        "saves/warioware_twisted_usa.sav";
    opts.launcher_expose_gyro = true;

#if defined(GBAGAME_RECOMP_UI)
    std::vector<std::string> args(argv, argv + argc);
#if defined(__ANDROID__)
    if (!args.empty()) args[0] = "./WarioWareTwistedRecomp";
    // SDLActivity supplies no command-line arguments. Point the runtime at the
    // staged per-game TOML explicitly so it can resolve the private BIOS, ROM,
    // and save paths relative to that file.
    args.emplace_back(GBARECOMP_DEFAULT_GAME_CONFIG);
    args.emplace_back("--no-launcher");
    args.emplace_back("--gyro-sensitivity");
    args.emplace_back("1.0");
#endif
    if (game_launcher_preboot(args, opts)) return 0;
    std::vector<char*> av;
    av.reserve(args.size());
    for (auto& arg : args) av.push_back(arg.data());
    return gbarecomp::run_game(static_cast<int>(av.size()), av.data(), opts);
#else
    return gbarecomp::run_game(argc, argv, opts);
#endif
}

#if defined(__ANDROID__)
extern "C" int SDL_main(int argc, char** argv) {
    return warioware_main(argc, argv);
}
#else
int main(int argc, char** argv) {
    return warioware_main(argc, argv);
}
#endif
