#include <cstdio>
#include <cstring>

#include "runtime.h"

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

void print_usage() {
    std::printf(
        "WarioWareTwistedRecomp [--bios <path>] [--rom <path>] "
        "[game.toml]\n"
        "The BIOS and ROM must match the SHA-1 identities in game.toml.\n"
        "Hold the left mouse button and drag horizontally to simulate gyro "
        "motion.\n"
        "Static recompilation is the default; set GBARECOMP_FORCE_INTERP=1 "
        "for the reference interpreter diagnostic backend.\n");
}

}  // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--help") == 0 ||
            std::strcmp(argv[i], "-h") == 0) {
            print_usage();
            return 0;
        }
    }

    gbarecomp::RunOptions opts;
    opts.builtin_game_name = GBARECOMP_BUILTIN_NAME;
    opts.builtin_rom_sha1 = GBARECOMP_BUILTIN_SHA1;
    opts.builtin_rom_crc32 = GBARECOMP_BUILTIN_CRC32;
    opts.launcher_region = GBARECOMP_BUILTIN_REGION;
    opts.launcher_game_config = GBARECOMP_DEFAULT_GAME_CONFIG;
    opts.launcher_save_path =
        "saves/warioware_twisted_usa.sav";

    return gbarecomp::run_game(argc, argv, opts);
}
