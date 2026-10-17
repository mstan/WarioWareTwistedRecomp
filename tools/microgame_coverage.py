"""Reproducible, save-isolated USA Spindex cheats and differential coverage.

No ROM, BIOS, player save, or snapshot belongs in version control. See
docs/native-coverage.md for the menu route and the limits of this experiment.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
from queue import Queue
import struct

from coverage_session import ROOT, ROM_SHA1, Session, patch_state_ram, snapshot_memory


def u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def catalog():
    rom = (ROOT / "variants/warioware_twisted/roms/warioware_twisted_usa.gba").read_bytes()
    if hashlib.sha1(rom).hexdigest() != ROM_SHA1:
        raise ValueError("Expected WarioWare: Twisted! USA revision 0")
    entries = []
    # 0x08016F44 selects the world descriptor; 0x08017334 reads its ID list.
    # 0x080173B8 indexes the game catalog as base + 24 * game_id.
    for category in range(10):
        world = rom[0x930188 + category * 4]
        descriptor = u32(rom, 0x930A48 + world * 4) - 0x08000000
        count = rom[descriptor]
        ids = u32(rom, descriptor + 4) - 0x08000000
        for slot in range(count):
            game_id = struct.unpack_from("<H", rom, ids + slot * 2)[0]
            callbacks = u32(rom, 0x92A1D8 + game_id * 24)
            targets = [u32(rom, callbacks - 0x08000000 + offset)
                       for offset in (0, 8, 16, 24)]
            if not all(0x080001F8 <= (pc & ~1) < 0x08133CFC for pc in targets):
                raise ValueError(f"Unexpected callback record for game {game_id}")
            entries.append(dict(category=category, world=world, slot=slot,
                                game_id=game_id, callbacks=callbacks, targets=targets))
    if len(entries) != 223 or len({entry["game_id"] for entry in entries}) != 223:
        raise ValueError("Unexpected Spindex roster")
    return entries


def unlock(args):
    ewram = snapshot_memory(args.snapshot)["ewram"]
    # Save getters/setters at 0x080008A4/0x080008C8 and 0x0800091C/0x08000940
    # identify the seen/cleared bits. Preserve scores and the other flag bits.
    patches = [(0x02000024 + i * 8, 1, ewram[0x24 + i * 8] | 3) for i in range(16)]
    patches += [(0x020000A4 + i, 1, ewram[0xA4 + i] | 5) for i in range(0x600)]
    patch_state_ram(args.snapshot, args.output, patches)


def capture(args):
    """Capture the real delayed launch after selecting A in Spindex."""
    with Session(args.output, interpreter=True, executable=args.executable,
                 bios=args.bios, port=args.port) as session:
        session.call("savestate_load", path=str(args.snapshot.resolve()))
        for _ in range(10):
            session.call("run_frames", n=1, keyinput=0x3FE)
            iwram = session.read("iwram")
            local = u32(iwram, 0x3B58)
            if not 0x02000000 <= local <= 0x0203FD60:
                break
            callback = int.from_bytes(bytes.fromhex(session.call(
                "read_ewram", addr=local - 0x02000000 + 0x290, len=4)["data"]), "little")
            if callback == 0x08017089:
                session.checkpoint("queued")
                print(f"Launch snapshot: {session.output / 'queued.state'}")
                return
    raise ValueError("Expected an unlocked Spindex microgame selector snapshot")


def prepare(args):
    args.output.mkdir(parents=True, exist_ok=False)
    iwram = snapshot_memory(args.snapshot)["iwram"]
    ewram = snapshot_memory(args.snapshot)["ewram"]
    local = u32(iwram, 0x3B58)
    if not 0x02000000 <= local <= 0x0203FD60:
        raise ValueError("Expected the Spindex menu's EWRAM local object")
    offset = local - 0x02000000
    # 0x080149B8 stores the delayed callback and its argument at +0x290/+0x294.
    # A queued 0x08017089 calls the real loader with the argument as the game ID.
    if u32(ewram, offset + 0x290) != 0x08017089:
        raise ValueError("Capture immediately after A queues a Spindex launch")
    entries = catalog()
    for entry in entries:
        path = args.output / f"game-{entry['game_id']:03d}.state"
        patch_state_ram(args.snapshot, path, [
            (local + 0x294, 4, entry["game_id"]),
            (0x03003BA2, 1, entry["category"]),
            (0x03003BA3, 1, entry["slot"]),
        ])
        entry["snapshot"] = path.name
        entry["snapshot_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (args.output / "cases.json").write_text(json.dumps(entries, indent=2) + "\n")
    print(f"Prepared {len(entries)} RAM-only launch cheats in {args.output}")


def run(args):
    entries = json.loads((args.cases / "cases.json").read_text())
    executable = args.executable or ROOT / "build-coverage/WarioWareTwistedRecomp.exe"
    bios = args.bios or ROOT / "gbarecomp/bios/gba_bios.bin"
    metadata = dict(backend=args.backend, executable=str(executable.resolve()),
                    executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
                    config_sha256=hashlib.sha256((ROOT / "variants/warioware_twisted/game.toml").read_bytes()).hexdigest(),
                    cases_sha256=hashlib.sha256((args.cases / "cases.json").read_bytes()).hexdigest(),
                    bios_sha256=hashlib.sha256(bios.read_bytes()).hexdigest(),
                    frames=args.frames, gyro=args.gyro, input_model="60-frame-neutral-then-A-v1")
    args.output.mkdir(parents=True, exist_ok=args.resume)
    manifest = args.output / "run.json"
    if args.resume and json.loads(manifest.read_text()) != metadata:
        raise ValueError("Resume requires the same executable, cases, config and inputs")
    manifest.write_text(json.dumps(metadata, indent=2) + "\n")
    reports = {}
    ports = Queue()
    for port in range(args.port, args.port + args.jobs):
        ports.put(port)

    def run_case(entry):
        game_id = entry["game_id"]
        directory = args.output / f"game-{game_id:03d}"
        snapshot = (args.cases / entry["snapshot"]).resolve()
        if "snapshot_sha256" in entry and hashlib.sha256(snapshot.read_bytes()).hexdigest() != entry["snapshot_sha256"]:
            raise ValueError(f"Changed input snapshot for game {game_id}")
        if args.resume and (directory / "result.json").is_file():
            result = json.loads((directory / "result.json").read_text())
            if result["game_id"] != game_id:
                raise ValueError(f"Mismatched completed case: {directory}")
            return result
        if directory.exists():
            raise ValueError(f"Incomplete case directory: {directory}; move it before resuming")
        # A fresh process resets external gyro sequence/GPIO state for every
        # case. Those devices are not part of the current snapshot container.
        port = ports.get()
        try:
            with Session(directory, interpreter=args.backend == "interpreter",
                         executable=executable, bios=bios, gyro=args.gyro, port=port) as session:
                session.call("savestate_load", path=str(snapshot))
                for offset in range(0, args.frames, 60):
                    count = min(60, args.frames - offset)
                    session.call("run_frames", n=count, keyinput=0x3FE if offset // 60 % 2 else 0x3FF)
                report = session.checkpoint("final")
                iwram = snapshot_memory(directory / "final.state")["iwram"]
                report.update(game_id=game_id,
                              loaded_game_id=struct.unpack_from("<H", iwram, 0x38D4)[0],
                              expected_callbacks=entry["callbacks"],
                              loaded_callbacks=u32(iwram, 0x4CE8))
                (directory / "result.json").write_text(json.dumps(report, indent=2) + "\n")
                return report
        finally:
            ports.put(port)

    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {executor.submit(run_case, entry): index
                   for index, entry in enumerate(entries[:args.limit])}
        for future in as_completed(futures):
            report = future.result()
            reports[futures[future]] = report
            ordered = [reports[index] for index in sorted(reports)]
            (args.output / "results.json").write_text(json.dumps(ordered, indent=2) + "\n")
            status = ("reference completed" if args.backend == "interpreter" else
                      f"misses={report['distinct_misses']} interpreted={report['interpreted_insns']}")
            print(f"{args.backend} {len(reports)}/{min(len(entries), args.limit)} "
                  f"ID={report['game_id']} {status}", flush=True)
    reports = [reports[index] for index in sorted(reports)]
    mismatched = [r["game_id"] for r in reports if r["loaded_game_id"] != r["game_id"]
                  or r.get("loaded_callbacks") != r.get("expected_callbacks")]
    if mismatched:
        raise SystemExit(f"Wrong loaded game IDs: {mismatched}")
    if args.require_static and any(r["distinct_misses"] or r["interpreted_insns"] for r in reports):
        raise SystemExit("The run still used interpreter fallback; see results.json")


def compare(args):
    if (args.reference / "run.json").exists() and (args.candidate / "run.json").exists():
        source = json.loads((args.reference / "run.json").read_text())
        target = json.loads((args.candidate / "run.json").read_text())
        for key in ("cases_sha256", "frames", "gyro", "input_model"):
            if source[key] != target[key]:
                raise ValueError(f"Run inputs differ: {key}")
    reference = json.loads((args.reference / "results.json").read_text())
    candidate = json.loads((args.candidate / "results.json").read_text())
    if [r["game_id"] for r in reference] != [r["game_id"] for r in candidate]:
        raise ValueError("Run lists differ")
    differences = []
    for report in reference:
        name = f"game-{report['game_id']:03d}"
        for suffix in ("-iwram.bin", "-ewram.bin", "-vram.bin", "-pal.bin", "-oam.bin", ".png"):
            source = args.reference / name / ("final" + suffix)
            target = args.candidate / name / ("final" + suffix)
            if source.read_bytes() != target.read_bytes():
                differences.append(dict(game_id=report["game_id"], region=suffix))
    summary = dict(cases=len(reference), differences=differences,
                   static_cases=sum(r["execution_backend"] == "native" and
                                    r["distinct_misses"] == 0 and r["interpreted_insns"] == 0
                                    for r in candidate),
                   interpreted_insns=sum(r["interpreted_insns"] for r in candidate),
                   healed_native=sum(r["healed_native"] for r in candidate))
    print(json.dumps(summary, indent=2))
    if args.output:
        args.output.write_text(json.dumps(summary, indent=2) + "\n")
    if differences:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    unlocked = commands.add_parser("unlock", help="Set seen/cleared flags in a snapshot COPY")
    unlocked.add_argument("--snapshot", type=Path, required=True)
    unlocked.add_argument("--output", type=Path, required=True)
    unlocked.set_defaults(action=unlock)
    captured = commands.add_parser("capture", help="Queue A from a Spindex microgame selector snapshot")
    captured.add_argument("--snapshot", type=Path, required=True)
    captured.add_argument("--output", type=Path, required=True)
    captured.add_argument("--executable", type=Path)
    captured.add_argument("--bios", type=Path)
    captured.add_argument("--port", type=int, default=19976)
    captured.set_defaults(action=capture)
    prepared = commands.add_parser("prepare", help="Create the 223 individual launch snapshots")
    prepared.add_argument("--snapshot", type=Path, required=True)
    prepared.add_argument("--output", type=Path, required=True)
    prepared.set_defaults(action=prepare)
    running = commands.add_parser("run", help="Run every case with neutral/A input and test gyro")
    running.add_argument("--cases", type=Path, required=True)
    running.add_argument("--output", type=Path, required=True)
    running.add_argument("--backend", choices=("interpreter", "native"), required=True)
    running.add_argument("--executable", type=Path)
    running.add_argument("--bios", type=Path)
    running.add_argument("--gyro", default="sweep")
    running.add_argument("--frames", type=int, default=600)
    running.add_argument("--limit", type=int, default=223)
    running.add_argument("--port", type=int, default=19976)
    running.add_argument("--jobs", type=int, default=4)
    running.add_argument("--resume", action="store_true")
    running.add_argument("--require-static", action="store_true")
    running.set_defaults(action=run)
    comparison = commands.add_parser("compare", help="Compare five memory regions and screenshots")
    comparison.add_argument("--reference", type=Path, required=True)
    comparison.add_argument("--candidate", type=Path, required=True)
    comparison.add_argument("--output", type=Path)
    comparison.set_defaults(action=compare)
    args = parser.parse_args()
    if args.command == "run" and (args.frames < 1 or not 1 <= args.limit <= 223
                                   or not 1 <= args.jobs <= 16
                                   or not 1024 <= args.port <= 65535 - args.jobs + 1):
        parser.error("Invalid frames, limit (1..223), jobs (1..16), or TCP port range")
    if args.command == "run" and args.require_static and args.backend != "native":
        parser.error("--require-static requires the native backend")
    if getattr(args, "executable", None):
        args.executable = args.executable.resolve()
    args.action(args)


if __name__ == "__main__":
    main()
