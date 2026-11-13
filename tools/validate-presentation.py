"""Check actual Android gameplay presentation using the existing runtime log.

Run with an already configured, running debuggable QA APK at its default
fractional presentation. This does not launch
the game, import assets, clear logs, change settings or interact with a save.
The ordinary check fails on the old reserved-pad layout; --expect-reserved is
only a negative-control assertion. Captures retain the actual device surface.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--serial', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--runtime-log', type=Path,
                        help='Use an already exported log from this same running instance')
    parser.add_argument('--expect-reserved', action='store_true')
    args = parser.parse_args()
    package = 'com.mstan.wariowaretwisted'
    args.output.mkdir(parents=True, exist_ok=True)

    def adb(*command):
        return subprocess.check_output([args.adb, '-s', args.serial, *command])

    log = args.runtime_log.read_bytes() if args.runtime_log else adb(
        'exec-out', 'run-as', package, 'cat', 'files/android-runtime.log')
    (args.output/'android-runtime.log').write_bytes(log)
    (args.output/'device.png').write_bytes(adb('exec-out', 'screencap', '-p'))
    pattern = (rb'host_window: presentation drawable=(\d+)x(\d+) .*?'
               rb'logical=(\d+)x(\d+) layout=(-?\d+),(-?\d+) (\d+)x(\d+)')
    samples = [tuple(map(int,m)) for m in re.findall(pattern,log)]
    if not samples:
        raise RuntimeError('No completed gameplay presentation observation in runtime log')
    dw,dh,lw,lh,x,y,w,h = samples[-1]
    if min(dw,dh,lw,lh,w,h)<=0:
        raise AssertionError('Invalid presentation dimensions')
    report = dict(serial=args.serial, package=package, drawable=[dw,dh],
        logical=[lw,lh], layout=[x,y,w,h], expect_reserved=args.expect_reserved,
        package_details=adb('shell','dumpsys','package',package).decode(errors='replace'))
    # The production adaptive fitter rounds the contained dimension once.
    expected = (dw,max(1,(dw*lh+lw//2)//lw)) if dw*lh<=dh*lw else (max(1,(dh*lw+lh//2)//lh),dh)
    reserved_scale=max(1,min(int(dw*0.62/lw),int(dh*0.90/lh)))
    reserved=(lw*reserved_scale,lh*reserved_scale)
    target=reserved if args.expect_reserved else expected
    passed=(w,h)==target and (x,y)==((dw-w)//2,(dh-h)//2)
    report.update(expected_maximal=list(expected), expected_old_reserved=list(reserved),passed=passed)
    (args.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='package_details'}))
    if not passed: raise AssertionError('Gameplay does not use the expected contained presentation')


if __name__=='__main__': main()
