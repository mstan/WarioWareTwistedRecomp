"""Muted native Android validation using an installed, debuggable QA APK.

Uses the normal mobile debug-args hook and a separate test save. Never installs
an APK, embeds assets, or alters the owner's cartridge save. Output includes
private snapshots and must stay in an ignored build/release-stage directory.
"""

import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time

from coverage_session import png, snapshot_memory


PACKAGE = "com.mstan.wariowaretwisted"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="C:/Android/Sdk/platform-tools/adb.exe")
    parser.add_argument("--serial", required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=600)
    parser.add_argument("--limit", type=int, default=223)
    parser.add_argument("--game-ids", help="Comma-separated roster IDs for a bounded device check")
    parser.add_argument("--port", type=int, default=20200)
    args = parser.parse_args()
    if args.frames < 1 or not 1 <= args.limit <= 223:
        parser.error("frames must be positive and limit must be 1..223")
    args.output.mkdir(parents=True, exist_ok=False)

    def adb(*command, check=True):
        return subprocess.run([args.adb, "-s", args.serial, *command],
                              capture_output=True, check=check)

    def read(path, check=True):
        return adb("exec-out", "run-as", PACKAGE, "cat", path, check=check)

    transfer = f"/data/local/tmp/warioware-native-{args.port}.bin"

    def write(path, content):
        # Windows adb stdin treats Ctrl-Z as EOF, including with shell -T.
        # Push a complete binary, copy as the app UID, then verify its hash.
        local = args.output / "transfer.bin"
        local.write_bytes(content)
        adb("push", str(local), transfer)
        adb("shell", "run-as", PACKAGE, "cp", transfer, path)
        expected = hashlib.sha256(content).hexdigest()
        actual = adb("shell", "run-as", PACKAGE, "sha256sum", path).stdout.decode().split()[0]
        if actual != expected:
            raise ValueError(f"Incomplete transfer to {path}")

    def player_save_hash():
        result = adb("shell", "run-as", PACKAGE, "sha256sum",
                     "files/saves/warioware_twisted_usa.sav", check=False)
        return result.stdout.decode().split()[0] if result.returncode == 0 else None

    adb("shell", "run-as", PACKAGE, "pwd")  # Fail before mutation if not debuggable.
    exists = adb("shell", "run-as", PACKAGE, "test", "-f", "files/debug-args.txt", check=False)
    # exec-out does not propagate the remote command's exit status. Test
    # existence with shell-v2 before reading the file's raw bytes.
    original_args = read("files/debug-args.txt").stdout if exists.returncode == 0 else None
    before_save = player_save_hash()
    if original_args is not None:
        (args.output / "original-debug-args.txt").write_bytes(original_args)
    adb("shell", "am", "force-stop", PACKAGE)
    report = dict(serial=args.serial, frames_per_case=args.frames, cases=[], completed=False,
                  audio_output="zero volume, diagnostic launch only",
                  gyro="neutral; no SDL motion provider in command-driven mode",
                  player_save_before=before_save,
                  device_abis=adb("shell", "getprop", "ro.product.cpu.abilist").stdout.decode().strip())
    connection = stream = None
    try:
        write("files/debug-args.txt",
              b"--no-window --tcp 19876 --volume 0 --save-path coverage-native-test.sav\n")
        adb("forward", f"tcp:{args.port}", "tcp:19876")
        adb("shell", "am", "start", "-n", PACKAGE + "/org.gbarecomp.GbaSetupActivity",
            "--ez", "org.gbarecomp.extra.AUTOSTART", "true")
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                connection = socket.create_connection(("127.0.0.1", args.port), timeout=2)
                connection.settimeout(2)
                stream = connection.makefile("rwb")
                stream.write(b'{"cmd":"ping"}\n')
                stream.flush()
                if b"gbarecomp_native" in stream.readline():
                    break
            except OSError:
                pass
            if stream:
                stream.close()
            if connection:
                connection.close()
            stream = connection = None
            time.sleep(0.2)
        else:
            raise TimeoutError("Android TCP server did not start; inspect runtime.log")
        connection.settimeout(120)

        def call(command, **parameters):
            stream.write((json.dumps(dict(cmd=command, **parameters)) + "\n").encode())
            stream.flush()
            reply = stream.readline()
            if not reply:
                raise RuntimeError(f"Android disconnected during {command}")
            result = json.loads(reply)
            if not result.get("ok"):
                raise RuntimeError(result)
            return result

        def checkpoint(directory):
            directory.mkdir(parents=True, exist_ok=False)
            call("savestate_save", path="coverage-native-output.state")
            state = directory / "final.state"
            state.write_bytes(read("files/coverage-native-output.state").stdout)
            memory = snapshot_memory(state)
            for region, data in memory.items():
                (directory / f"final-{region}.bin").write_bytes(data)
            pixels = call("screenshot")
            png(directory / "final.png", pixels["data"], pixels.get("w", 240), pixels.get("h", 160))
            coverage = call("misses")
            (directory / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
            if coverage["distinct_misses"] or coverage["interpreted_insns"] or coverage["enabled"]:
                raise RuntimeError(f"Native Android fallback detected; see {directory / 'coverage.json'}")
            return memory, coverage

        call("run_frames", n=900, keyinput=0x3FF)
        _, report["boot_coverage"] = checkpoint(args.output / "boot")
        runtime = read("files/android-runtime.log").stdout.decode(errors="replace")
        if "cpu_backend=static-recompiled" not in runtime:
            raise RuntimeError("The Android process is not using the native backend")
        cases = json.loads((args.cases / "cases.json").read_text())
        if args.game_ids:
            ids = [int(item) for item in args.game_ids.split(",")]
            by_id = {case["game_id"]: case for case in cases}
            if len(set(ids)) != len(ids) or not set(ids).issubset(by_id):
                raise ValueError("Expected distinct IDs from the verified Spindex roster")
            cases = [by_id[game_id] for game_id in ids]
        cases = cases[:args.limit]
        report["requested_cases"] = len(cases)
        for case in cases:
            game_id = case["game_id"]
            data = (args.cases / case["snapshot"]).read_bytes()
            if "snapshot_sha256" in case and hashlib.sha256(data).hexdigest() != case["snapshot_sha256"]:
                raise ValueError(f"Changed input snapshot for {game_id}")
            write("files/coverage-native-input.state", data)
            call("savestate_load", path="coverage-native-input.state")
            for offset in range(0, args.frames, 60):
                call("run_frames", n=min(60, args.frames - offset),
                     keyinput=0x3FE if offset // 60 % 2 else 0x3FF)
            memory, coverage = checkpoint(args.output / f"game-{game_id:03d}")
            iwram = memory["iwram"]
            loaded_id = int.from_bytes(iwram[0x38D4:0x38D6], "little")
            loaded_callbacks = int.from_bytes(iwram[0x4CE8:0x4CEC], "little")
            if loaded_id != game_id or loaded_callbacks != case["callbacks"]:
                raise ValueError(f"Wrong microgame loaded: {game_id}, {loaded_id}, {loaded_callbacks:#x}")
            report["cases"].append(dict(game_id=game_id, callbacks=loaded_callbacks,
                                       coverage=coverage["coverage"], dispatch_misses=0,
                                       interpreted_insns=0))
            (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
            print(f"{args.serial}: {len(report['cases'])}/{len(cases)} ID={game_id} FULLY_STATIC", flush=True)
        report["final_coverage"] = call("misses")
        report["completed"] = True
        call("quit")
    finally:
        if stream:
            stream.close()
        if connection:
            connection.close()
        adb("shell", "am", "force-stop", PACKAGE, check=False)
        runtime = read("files/android-runtime.log", check=False)
        (args.output / "runtime.log").write_bytes(runtime.stdout)
        report["player_save_after"] = player_save_hash()
        report["player_save_preserved"] = report["player_save_after"] == before_save
        if original_args is None:
            adb("shell", "run-as", PACKAGE, "rm", "-f", "files/debug-args.txt")
        else:
            write("files/debug-args.txt", original_args)
        adb("shell", "run-as", PACKAGE, "rm", "-f",
            "files/coverage-native-input.state", "files/coverage-native-output.state",
            "files/coverage-native-test.sav", check=False)
        adb("shell", "rm", "-f", transfer, check=False)
        adb("forward", "--remove", f"tcp:{args.port}", check=False)
        (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
        if not report["player_save_preserved"]:
            raise RuntimeError("The player's save changed during isolated QA")


if __name__ == "__main__":
    main()
