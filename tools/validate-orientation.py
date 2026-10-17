"""Check fixed landscape against emulated physical turns, with auto-rotate on/off.

Requires an emulator with the game and its user-supplied ROM/BIOS configured.
Run once with --expect-flip against the old build as a negative control, then
without that flag against the fixed build. The emulator must have host audio
disabled (launch it with -no-audio).
"""

import argparse
import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", required=True)
    parser.add_argument("--activity", choices=("setup", "game"), default="game")
    parser.add_argument("--expect-flip", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.serial.startswith("emulator-"):
        parser.error("Sensor injection is for emulators only; use physical phone QA separately")
    package = "com.mstan.wariowaretwisted"
    activity = "GbaSetupActivity" if args.activity == "setup" else "GbaGameActivity"
    args.output.mkdir(parents=True, exist_ok=True)

    def adb(*command, binary=False):
        result = subprocess.run(
            [args.adb, "-s", args.serial, *command], capture_output=True, check=True
        )
        return result.stdout if binary else result.stdout.decode("utf-8", errors="replace").strip()

    original_settings = {
        name: adb("shell", "settings", "get", "system", name)
        for name in ("accelerometer_rotation", "user_rotation")
    }
    original_acceleration = adb("emu", "sensor", "get", "acceleration")
    acceleration_match = re.search(r"acceleration = ([^\r\n]+)", original_acceleration)
    report = {"activity": activity, "expect_flip": args.expect_flip, "samples": []}
    try:
        adb("shell", "am", "force-stop", package)
        adb("shell", "settings", "put", "system", "accelerometer_rotation", "0")
        adb("emu", "sensor", "set", "acceleration", "9.81:0:0")
        launch_args = ["shell", "am", "start", "-W", "-n", f"{package}/org.gbarecomp.GbaSetupActivity"]
        if args.activity == "game":
            launch_args += ["--ez", "org.gbarecomp.extra.AUTOSTART", "true"]
        launch = adb(*launch_args)
        if "Error" in launch or "Exception" in launch:
            raise RuntimeError(launch)
        time.sleep(8)
        if args.activity == "game":
            activities = adb("shell", "dumpsys", "activity", "activities")
            top = re.search(r"topResumedActivity=.*", activities)
            if top and "GbaSetupActivity" in top.group():
                # Older builds predate AUTOSTART. Press their real Play button.
                remote_xml = "/sdcard/warioware-orientation-ui.xml"
                adb("shell", "uiautomator", "dump", remote_xml)
                try:
                    hierarchy = adb("shell", "cat", remote_xml)
                finally:
                    adb("shell", "rm", remote_xml)
                play = next(node for node in ET.fromstring(hierarchy).iter("node") if node.get("text") == "PLAY")
                x1, y1, x2, y2 = map(int, re.findall(r"\d+", play.get("bounds")))
                adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
                time.sleep(8)
        cases = (
            (0, "landscape", "9.81:0:0"),
            (0, "reverse-landscape", "-9.81:0:0"),
            (0, "portrait", "0:9.81:0"),
            (0, "upside-down", "0:-9.81:0"),
            (1, "reverse-landscape", "-9.81:0:0"),
            (1, "portrait", "0:9.81:0"),
            (1, "landscape", "9.81:0:0"),
        )
        for auto_rotate, pose, acceleration in cases:
            adb("shell", "settings", "put", "system", "accelerometer_rotation", str(auto_rotate))
            adb("emu", "sensor", "set", "acceleration", acceleration)
            time.sleep(3)
            activities = adb("shell", "dumpsys", "activity", "activities")
            displays = adb("shell", "dumpsys", "window", "displays")
            top = re.search(r"topResumedActivity=.*", activities)
            requested = re.search(r"requestedOrientation=(\S+)", activities)
            rotation = re.search(r"\bmRotation=(\d)\b", displays)
            if not top or f"{package}/org.gbarecomp.{activity}" not in top.group():
                raise AssertionError(f"Expected {activity} in foreground: {top}")
            if not requested or not rotation:
                raise AssertionError("Missing requested orientation/display rotation")
            sample = {
                "auto_rotate": auto_rotate,
                "pose": pose,
                "requested": requested.group(1),
                "rotation": int(rotation.group(1)),
                "pid": adb("shell", "pidof", package),
            }
            report["samples"].append(sample)
            name = f"auto-{auto_rotate}-{pose}"
            (args.output / f"{name}-activities.txt").write_text(activities, encoding="utf-8")
            (args.output / f"{name}-display.txt").write_text(displays, encoding="utf-8")
            (args.output / f"{name}.png").write_bytes(adb("exec-out", "screencap", "-p", binary=True))
            print(json.dumps(sample), flush=True)
        if args.expect_flip:
            off_rotations = {s["rotation"] for s in report["samples"] if s["auto_rotate"] == 0}
            assert len(off_rotations) > 1, "Negative control did not reproduce the rotation-lock bug"
        else:
            assert all(s["requested"] == "SCREEN_ORIENTATION_LANDSCAPE" for s in report["samples"])
            assert len({s["rotation"] for s in report["samples"]}) == 1, "Display flipped"
            assert len({s["pid"] for s in report["samples"]}) == 1, "Game restarted"
        report["passed"] = True
    finally:
        for name, value in original_settings.items():
            if value == "null":
                adb("shell", "settings", "delete", "system", name)
            else:
                adb("shell", "settings", "put", "system", name, value)
        if acceleration_match:
            adb("emu", "sensor", "set", "acceleration", acceleration_match.group(1))
        (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
