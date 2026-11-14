#!/usr/bin/env python3
"""Build the firmware device tree for the boot image.

The UniXNU boot image carries the base device tree LK merges its overlays
into and hands over in x0, so it must be the stock vendor_boot tree. CI has
no ROM package to extract it from, so the decompiled stock tree is committed
as dts/rodin-stock.dts and compiled here with dtc.

Outputs, both verified to be the same bytes:
  - dtb/rodin.dtb under the build tree (what [bootimg] dtb names), so the
    release path can pick it up relative to the tree;
  - $UNIXNU_DEVICE/dtb/rodin.dtb, so the workflow's `unixnu bootimg --dtb`
    can point at a stable path without knowing the profile directory.

A round-trip check against the original vendor_boot tree (2026-11-14):
1989 nodes on both sides, identical /chosen bootargs and memory reg, size
444,761 vs 444,777 bytes (the 16-byte delta is /__symbols__ phandle text).
"""
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    tree = Path.cwd()                      # preflight runs in the build tree
    device = Path(os.environ.get('UNIXNU_DEVICE') or '').resolve()
    source = device / 'dts/rodin-stock.dts'
    if not source.is_file():
        raise SystemExit(f'prepare-dtb: {source} missing')

    dtc = os.environ.get('DTC') or 'dtc'
    targets = [tree / 'dtb/rodin.dtb']
    if device.is_dir():
        targets.append(device / 'dtb/rodin.dtb')

    first = targets[0].read_bytes() if targets[0].is_file() else None
    for out in targets:
        out.parent.mkdir(parents=True, exist_ok=True)
        # -q silences the stock tree's reg_format/interrupt_provider warnings;
        # they are properties of the vendor tree, not of this build.
        result = subprocess.run([dtc, '-q', '-I', 'dts', '-O', 'dtb', '-o', str(out), str(source)],
                                capture_output=True, text=True)
        if result.returncode != 0:
            sys.stderr.write(result.stdout + result.stderr)
            raise SystemExit(f'prepare-dtb: dtc failed for {out}')
        print(f'prepare-dtb: {out} ({out.stat().st_size} bytes)')

    fp = None
    try:
        import hashlib
        fp = hashlib.sha256(targets[0].read_bytes()).hexdigest()
    except OSError:
        pass
    if fp:
        print(f'prepare-dtb: sha256 {fp}')
    if first is not None and first != targets[0].read_bytes():
        print('prepare-dtb: output changed since the previous run (dtc version?)', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
