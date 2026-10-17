"""Local, muted TCP runner for WarioWare coverage experiments.

Each session owns its output directory and disposable save. ROMs, BIOSes,
snapshots and memory dumps stay in ignored build directories.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import time
import zlib


ROOT = Path(__file__).resolve().parents[1]
ROM_SHA1 = "f0102d0d6f7596fe853d5d0a94682718278e083a"


def snapshot_bus(source):
    """Validate a USA v2 snapshot and locate its serialized bus payload."""
    blob = bytearray(Path(source).read_bytes())
    if len(blob) < 52:
        raise ValueError("Truncated snapshot")
    if blob[:4] != b"GBAS" or struct.unpack_from("<I", blob, 4)[0] != 2:
        raise ValueError("Expected a v2 GBAS snapshot")
    if blob[8:48].decode("ascii") != ROM_SHA1:
        raise ValueError("Snapshot ROM identity does not match WarioWare USA")
    count = struct.unpack_from("<I", blob, 48)[0]
    offset, sections = 52, {}
    for _ in range(count):
        if offset + 8 > len(blob):
            raise ValueError("Truncated snapshot section header")
        tag, size = struct.unpack_from("<4sI", blob, offset)
        offset += 8
        if tag in sections or offset + size > len(blob):
            raise ValueError("Invalid snapshot section table")
        sections[tag] = (offset, size)
        offset += size
    if offset != len(blob) or b"BUS0" not in sections:
        raise ValueError("Incomplete snapshot container")
    bus, size = sections[b"BUS0"]
    if size < 0x60800:
        raise ValueError("Truncated bus memory payload")
    return blob, bus


def snapshot_memory(source):
    blob, bus = snapshot_bus(source)
    result = {}
    for region, size in (("ewram", 0x40000), ("iwram", 0x8000),
                         ("pal", 0x400), ("vram", 0x18000), ("oam", 0x400)):
        result[region] = bytes(blob[bus:bus + size])
        bus += size
    return result


def patch_state_ram(source, destination, patches):
    """Apply explicit RAM-only test cheats to a separate, audited snapshot."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError("Cheats require a separate output snapshot")
    blob, bus = snapshot_bus(source)
    changes = []
    for address, width, value in patches:
        if width not in (1, 2, 4) or not 0 <= value < 1 << (width * 8):
            raise ValueError("Invalid cheat width/value")
        if 0x02000000 <= address < 0x03000000:
            relative, limit, prefix = address & 0x3FFFF, 0x40000, 0
        elif 0x03000000 <= address < 0x04000000:
            relative, limit, prefix = address & 0x7FFF, 0x8000, 0x40000
        else:
            raise ValueError("Cheats may only change EWRAM or IWRAM")
        if relative + width > limit:
            raise ValueError("Cheat crosses a RAM mirror boundary")
        start = bus + prefix + relative
        before = bytes(blob[start:start + width])
        after = value.to_bytes(width, "little")
        blob[start:start + width] = after
        changes.append({"address": hex(address), "width": width, "before": before.hex(), "after": after.hex()})
    destination.write_bytes(blob)
    destination.with_suffix(destination.suffix + ".cheats.json").write_text(json.dumps({
        "source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "patched_sha256": hashlib.sha256(blob).hexdigest(), "patches": changes,
    }, indent=2) + "\n")
    return destination


def png(path, data, width=240, height=160):
    def chunk(tag, content):
        return struct.pack(">I", len(content)) + tag + content + struct.pack(">I", zlib.crc32(tag + content))

    pixels = bytes.fromhex(data)
    assert len(pixels) == width * height * 3
    rows = b"".join(b"\0" + pixels[y * width * 3:(y + 1) * width * 3] for y in range(height))
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


class Session:
    def __init__(self, output, *, interpreter=False, executable=None, save=None,
                 bios=None, port=19976, gyro="0"):
        # Refuse a port already owned by another game/debug session.
        with socket.socket() as probe:
            if os.name == "nt":
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            probe.bind(("127.0.0.1", port))
        self.output = Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=False)
        self.interpreter = interpreter
        rom = ROOT / "variants/warioware_twisted/roms/warioware_twisted_usa.gba"
        assert hashlib.sha1(rom.read_bytes()).hexdigest() == ROM_SHA1
        env = os.environ.copy()
        for name in ("GBARECOMP_INPUT_REPLAY", "GBARECOMP_HEAL_CACHE"):
            env.pop(name, None)
        env.update({
            "PATH": "C:/msys64/mingw64/bin;" + env["PATH"],
            "SDL_AUDIODRIVER": "dummy",
            "GBARECOMP_FORCE_INTERP": "1" if interpreter else "0",
            "GBARECOMP_SELFHEAL_RECOMPILE": "0",
            "GBARECOMP_SELFHEAL_VERBOSE": "1",
            "GBARECOMP_GYRO_TEST": str(gyro),
            "GBARECOMP_MISS_FRAG": str(self.output / "misses.toml.frag"),
            "GBARECOMP_COVERAGE_JSON": str(self.output / "coverage.json"),
        })
        save_path = self.output / "test.sav"
        if save:
            shutil.copyfile(save, save_path)
        args = [
            str(executable or ROOT / "build-coverage/WarioWareTwistedRecomp.exe"),
            "--config", str(ROOT / "variants/warioware_twisted/game.toml"),
            "--bios", str(Path(bios).resolve() if bios else ROOT / "gbarecomp/bios/gba_bios.bin"),
            "--rom", str(rom), "--save-path", str(save_path),
            "--gyro-sensitivity", "1.0", "--no-window", "--no-launcher", "--tcp", str(port),
        ]
        self.log = (self.output / "runtime.log").open("wb")
        self.process = subprocess.Popen(args, cwd=self.output, env=env, stdout=self.log, stderr=self.log,
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        (self.output / "process.json").write_text(json.dumps({"pid": self.process.pid, "args": args}, indent=2))
        (self.output / "backend.json").write_text(json.dumps({
            "backend": "reference-interpreter" if interpreter else "native",
            "runtime_healing": False, "audio_output": "dummy",
            "gyro": str(gyro), "rom_sha1": ROM_SHA1,
            "note": "The raw engine miss counters cover dispatch fallback only; they do not count forced interpreter execution.",
        }, indent=2) + "\n")
        for _ in range(100):
            if self.process.poll() is not None:
                raise RuntimeError((self.output / "runtime.log").read_text(errors="replace"))
            try:
                self.socket = socket.create_connection(("127.0.0.1", port), timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        else:
            self.process.terminate()
            self.process.wait()
            self.log.close()
            raise TimeoutError("Coverage test server did not start")
        self.socket.settimeout(90)
        # Buffer the large JSON memory replies: unbuffered readline() performs
        # a socket read for each byte and makes a sweep needlessly slow.
        self.stream = self.socket.makefile("rwb")
        assert self.call("ping")["who"] == "gbarecomp_native"

    def call(self, command, **parameters):
        self.stream.write((json.dumps({"cmd": command, **parameters}) + "\n").encode())
        self.stream.flush()
        reply = self.stream.readline()
        if not reply:
            raise RuntimeError(f"Test process disconnected during {command}; see {self.output / 'runtime.log'}")
        result = json.loads(reply)
        if not result.get("ok"):
            raise RuntimeError(result)
        return result

    def frames(self, count, keys=0x3FF):
        result = self.call("run_frames", n=count, keyinput=keys)
        print(json.dumps(result), flush=True)
        return result["frame"]

    def read(self, region):
        sizes = {"iwram": 32768, "ewram": 262144, "pal": 1024, "oam": 1024, "vram": 98304}
        return bytes.fromhex(self.call("read_" + region, addr=0, len=sizes[region])["data"])

    def checkpoint(self, name):
        snapshot = self.output / f"{name}.state"
        self.call("savestate_save", path=str(snapshot))
        for region, data in snapshot_memory(snapshot).items():
            (self.output / f"{name}-{region}.bin").write_bytes(data)
        result = self.call("screenshot")
        png(self.output / f"{name}.png", result["data"], result.get("w", 240), result.get("h", 160))
        coverage = self.call("misses")
        coverage["execution_backend"] = "reference-interpreter" if self.interpreter else "native"
        if self.interpreter:
            coverage["coverage"] = "FORCED_INTERPRETER"
        (self.output / f"{name}-coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
        return coverage

    def close(self):
        try:
            if self.process.poll() is None:
                self.call("quit")
                self.process.wait(timeout=15)
        finally:
            if self.process.poll() is None:
                self.process.terminate()
                self.process.wait()
            self.stream.close()
            self.socket.close()
            self.log.close()

    def __enter__(self):
        return self

    def __exit__(self, *error):
        self.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=900)
    parser.add_argument("--interpreter", action="store_true")
    parser.add_argument("--save", type=Path)
    parser.add_argument("--bios", type=Path)
    args = parser.parse_args()
    with Session(args.output, interpreter=args.interpreter, save=args.save, bios=args.bios) as session:
        session.frames(args.frames)
        print(json.dumps(session.checkpoint(f"frame-{args.frames}")), flush=True)


if __name__ == "__main__":
    main()
