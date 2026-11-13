"""Package an already built native Linux x86_64 game, without player data."""
import argparse
from pathlib import Path
import shutil
import struct
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAME = "WarioWareTwistedRecomp"


def elf_x64(path):
    with path.open("rb") as source:
        header = source.read(20)
    if header[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", header, 18)[0] != 62:
        raise ValueError("Expected a native Linux x86_64 ELF: " + str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sdl-library", type=Path, required=True)
    parser.add_argument("--sdl-license", type=Path, required=True)
    parser.add_argument("--sdl3-library", type=Path, required=True)
    parser.add_argument("--sdl3-license", type=Path, required=True)
    args = parser.parse_args()
    binary = args.build_dir / NAME
    elf_x64(binary)
    elf_x64(args.sdl_library)
    elf_x64(args.sdl3_library)
    if args.output.exists():
        raise FileExistsError("Choose a new staging output; existing archives are preserved")
    if not (args.build_dir / "assets/img").is_dir():
        raise FileNotFoundError("Built launcher assets are missing")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wwt-linux-", dir=args.output.parent) as temp:
        stage = Path(temp) / (NAME + "-linux-x86_64")
        stage.mkdir()
        shutil.copy2(binary, stage / NAME)
        subprocess.run(["strip", "--strip-unneeded", str(stage / NAME)], check=True)
        (stage / NAME).chmod(0o755)
        shutil.copytree(args.build_dir / "assets", stage / "assets")
        config = stage / "variants/warioware_twisted"
        config.mkdir(parents=True)
        shutil.copy2(ROOT / "variants/warioware_twisted/game.toml", config / "game.toml")
        (stage / "lib").mkdir()
        shutil.copy2(args.sdl_library, stage / "lib/libSDL2-2.0.so.0")
        # The SDK's SDL2-compat loads SDL3 with dlopen, so ldd alone cannot
        # establish that the standalone runtime is complete.
        shutil.copy2(args.sdl3_library, stage / "lib/libSDL3.so.0")
        licenses = stage / "licenses"
        licenses.mkdir()
        shutil.copy2(args.sdl_license, licenses / "SDL2.txt")
        shutil.copy2(args.sdl3_license, licenses / "SDL3.txt")
        font_licenses = licenses / "fonts"
        font_licenses.mkdir()
        for name in ("LatoLatin-OFL.txt", "NotoSansSymbols2-OFL.txt", "OpenMoji-LICENSE.txt"):
            target = font_licenses / name
            shutil.copy2(ROOT / "tools/release-licenses" / name, target)
            target.chmod(0o644)
        shutil.copy2(ROOT / "LICENSE", licenses / "WarioWareTwistedRecomp.txt")
        shutil.copy2(ROOT / "PERMISSIONS.md", licenses / "PERMISSIONS.md")
        for relative, name in (("gbarecomp", "gbarecomp"),
                               ("recomp-ui", "recomp-ui"),
                               ("gbarecomp/external/arm-recomp-core", "arm-recomp-core"),
                               ("gbarecomp/external/rbengine", "rbengine")):
            shutil.copy2(ROOT / relative / "LICENSE", licenses / (name + ".txt"))
        shutil.copy2(ROOT / "linux/README.md", stage / "README.md")
        script = stage / "run.sh"
        script.write_text('''#!/bin/sh
set -eu
app=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# Keep a Steam runtime's selected libraries ahead of the standalone fallback.
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}$app/lib"
cd "$app"
exec "$app/WarioWareTwistedRecomp" "$@"
''')
        script.chmod(0o755)
        forbidden = {".gba", ".agb", ".bin", ".sav", ".srm", ".state", ".ini", ".cfg", ".log", ".apk"}
        for path in stage.rglob("*"):
            if path.is_symlink() or (path.is_file() and path.suffix.lower() in forbidden):
                raise ValueError("Unexpected player/development data in package: " + str(path))
        with tarfile.open(args.output, "x:gz") as archive:
            def public_metadata(info):
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                return info
            archive.add(stage, arcname=stage.name, filter=public_metadata)
    print(args.output)


if __name__ == "__main__":
    main()
