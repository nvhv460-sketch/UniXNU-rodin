#!/usr/bin/env python3
"""Generate the minimal rodin hardware Apple-format DT for the first boot.

Adapted from UniXNU-rothko's scripts/make-rothko-adt.py with Redmi Turbo 4
(MediaTek Dimensity 8400-Ultra / MT6899) values, all verified against the
device on 2026-11-14 (adb + root; see docs/hardware-inventory.md):

  - GICv3 distributor 0x0C400000/0x40000, redistributor 0x0C440000/0x200000
    (stock LK DT interrupt-controller@c400000; identical to rothko/MT6989,
    NOT 0x0C000000 as an earlier note claimed -- the live device tree wins)
  - CPU timebase 13000000 Hz (stock DT timer clock-frequency 0xc65d40)
  - DRAM base 0x40000000 (stock DT memory@40000000); size comes from the board
    file / --dram-size (12 GiB unit: 0x300000000, single contiguous bank)
  - 8 cores, MPIDR affinities 0x000..0x700 (stock DT cpu@0..cpu@7, PSCI,
    4+3+1 cluster layout; no A55/A76 labels -- runtime MIDR is authoritative)
  - chip id 0x6899 (efuse mtk-devinfo0 word at 0x044, and dmesg
    "get chipid 0x6899:0x8a00:0xca00:0x0")
  - UFS is not published by this minimal ADT (the real host controller is at
    0x112b0000/0x2a00; the firmware exposes it as a block device instead)

First-boot bring-up data: no MT6899 platform expert exists yet, so the kernel
is expected to reach the video console. No Apple device identity is claimed
beyond the iPad7,1 userspace identity (same 21H461 donor as rothko).

payload.py drives this tool with (contract, no --soc is ever passed, so the
default soc is rodin): --output --dram-size [--owned-memory-size
--root-match-volume-uuid --chip-id --cpu-regs --psci-method --unique-chip-id]
[--packed-data-ramdisk|--data-ramdisk] [--trust-cache] [--gpu-addon]
[--persistent-data] [--text-fixup TYPE,OFFSET,OLD,NEW ...]
"""
from pathlib import Path
import argparse
import hashlib
import os
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]

DRAM_BASE = 0x40000000
ARMIO_BASE = 0x0C400000           # GIC peripheral window (stock DT @c400000)
ARMIO_SIZE = 0x00600000           # covers redist at +0x40000/0x200000
GIC_DIST = 0x0C400000
GIC_DIST_SIZE = 0x00040000
GIC_REDIST = 0x0C440000
GIC_REDIST_SIZE = 0x00200000
TIMEBASE = 13000000


def node(name, properties=(), children=()):
    properties = [('name', name.encode() + b'\0'), *properties]
    result = struct.pack('<II', len(properties), len(children))
    for key, data in properties:
        result += struct.pack('<32sI', key.encode(), len(data))
        result += data + bytes(-len(data) % 4)
    return result + b''.join(children)


def empty_nvram_proxy():
    """A fresh volatile CHRP bank for upstream IODTNVRAM, with no controller."""
    def header(name, size):
        raw = bytearray(struct.pack('<BBH12s', 0x70, 0, size // 16, name))
        checksum = sum(raw)
        while checksum > 255:
            checksum = (checksum & 255) + (checksum >> 8)
        raw[1] = checksum
        return raw

    image = bytearray(8192)
    image[:16] = header(b'nvram', 32)
    image[32:48] = header(b'common', 16 + 2048)
    free_at = 32 + 16 + 2048
    image[free_at:free_at + 16] = header(b'free', len(image) - free_at)
    struct.pack_into('<I', image, 16, zlib.adler32(image[20:]))
    return [('nvram-bank-size', struct.pack('<I', len(image))),
            ('nvram-bank-count', struct.pack('<I', 1)),
            ('nvram-current-bank', struct.pack('<I', 0)),
            ('nvram-proxy-data', bytes(image))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--soc', choices=['rodin'], default='rodin',
                        help='rodin only; payload.py never passes this')
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'build/rodin/boot/kernel.macho.adt')
    parser.add_argument('--dram-size', type=lambda value: int(value, 0), required=True,
                        help='Actual DRAM size, e.g. 0x300000000 for the 12 GiB unit')
    parser.add_argument('--owned-memory-size', type=lambda value: int(value, 0), default=None,
                        help='Explicit DarwinBoot contiguous window request, 256 MiB..8 GiB in 2 MiB steps')
    parser.add_argument('--root-match-volume-uuid', default=None,
                        help='/chosen/root-matching: select the root by the UUID of an IOMedia')
    parser.add_argument('--unique-chip-id', type=lambda value: int(value, 16), default=None,
                        help='/chosen/unique-chip-id (8 bytes) and --chip-id (4 bytes) seed XNU IOPlatformUUID')
    parser.add_argument('--chip-id', type=lambda value: int(value, 16), default=None)
    parser.add_argument('--ipad-identity', action='store_true',
                        help='/product and /buttons describe an iPad-class device without a Home button')
    parser.add_argument('--ipad-compatible', action='store_true',
                        help='Lead the root compatible with J120AP/iPad7,1/AppleARM (real iPad7,1 DT order)')
    parser.add_argument('--target-type', default='J120',
                        help='/target-type written when --ipad-identity is set')
    parser.add_argument('--no-display-scale', action='store_true',
                        help='Omit /chosen/display-scale (the pre-act4 layout: tablet-shaped UI)')
    parser.add_argument('--cpu-regs', default='0',
                        help='Comma-separated CPU MPIDR affinity values (the /cpus reg of each core)')
    parser.add_argument('--psci-method', choices=['smc', 'hvc'], default='smc',
                        help='/psci method used by the secondary-CPU start (MT6899 uses smc)')
    parser.add_argument('--packed-data-ramdisk', action='store_true')
    parser.add_argument('--data-ramdisk', action='store_true')
    parser.add_argument('--trust-cache', action='store_true')
    parser.add_argument('--gpu-addon', action='store_true',
                        help='Accepted for payload.py contract; no GPU addon node yet')
    parser.add_argument('--persistent-data', action='store_true',
                        help='Accepted for payload.py contract; no persistent data node yet')
    parser.add_argument('--text-fixup', action='append', default=[],
                        help='Accepted for payload.py contract; consumed by the patched kernel, not the ADT')
    args = parser.parse_args()
    if (args.unique_chip_id is None) != (args.chip_id is None):
        parser.error('--unique-chip-id and --chip-id must be supplied together')
    if args.unique_chip_id is not None and not (0 < args.unique_chip_id < 1 << 64 and 0 < args.chip_id < 1 << 32):
        parser.error('--unique-chip-id must fit 8 bytes and --chip-id 4 bytes, both nonzero')
    if args.owned_memory_size is not None and (
            not 0x10000000 <= args.owned_memory_size <= 0x200000000
            or args.owned_memory_size % 0x200000):
        parser.error('Owned memory must be 256 MiB to 8 GiB, aligned to 2 MiB')

    try:
        cpu_regs = [int(value, 0) for value in args.cpu_regs.split(',')]
    except ValueError:
        parser.error('--cpu-regs must be integers')
    if (not cpu_regs or cpu_regs[0] != 0 or len(set(cpu_regs)) != len(cpu_regs) or len(cpu_regs) > 8
            or any(reg not in range(0, 0x800, 0x100) for reg in cpu_regs)):
        parser.error('--cpu-regs: distinct MT6899 physical affinities 0x000..0x700, boot CPU 0 first')

    def cpu_compatible(affinity):
        # Stock LK supplies MPIDR affinities. Do not label MT6899 CPUs with a
        # core identity; runtime MIDR is authoritative (rothko lesson).
        return b'arm,armv8\0'

    def cpu_interrupts(index):
        # AppleARMCPU::_validateConfiguration() requires interrupts[2] == interrupts[0] + 1
        # (Apple AIC numbering shape). Values are unused when no-aic-ipi-required is set.
        first = 0x140 + index * 2
        return struct.pack('<III', first, 0x53 + index * 3, first + 1)

    def cpu_reg_private(index):
        # Mirrors the Apple DT pattern: 0x0202000000 | ((1 + ordinal << 4) << 16).
        return 0x0000000202000000 | ((0x01 + (index << 4)) << 16)

    cpus = [node('cpu%d' % index, [('state', b'running\0' if index == 0 else b'waiting\0'),
                                   ('reg', struct.pack('<I', reg)),
                                   ('cpu-id', struct.pack('<I', index)),
                                   ('cluster-core-id', struct.pack('<I', reg >> 8)),
                                   ('die-cluster-id', struct.pack('<I', 0)),
                                   ('device_type', b'cpu\0'),
                                   ('compatible', cpu_compatible(reg)),
                                   ('timebase-frequency', struct.pack('<I', TIMEBASE)),
                                   # Non-Apple platform: AppleARMCPU must not require AIC IPI
                                   # dispatch functions in the device tree.
                                   ('no-aic-ipi-required', struct.pack('<I', 1))])
            for index, reg in enumerate(cpu_regs)]
    tree = node('device-tree', [
        ('model', b'iPad7,1\0' if args.ipad_identity else b'rodin-first-boot\0'),
        *([('target-type', (args.target_type + '\0').encode())] if args.ipad_identity else []),
        # sheng/tb128fu keep the board's own compatible strings here; the iPad
        # identity lives in model/target-type and /chosen, not in compatible.
        ('compatible', (b'J120AP\0iPad7,1\0AppleARM\0' if args.ipad_compatible else b'')
                       + b'xiaomi,rodin\0mediatek,mt6899\0'),
        ('#address-cells', struct.pack('<I', 2)),
        ('#size-cells', struct.pack('<I', 2)),
    ], [
        node('chosen', [('random-seed', os.urandom(64)),
                        *([('unique-chip-id', struct.pack('<Q', args.unique_chip_id)), ('chip-id', struct.pack('<I', args.chip_id))]
                          if args.unique_chip_id is not None else []),
                        ('osenvironment', b'main\0'),
                        *([('certificate-production-status', struct.pack('<I', 0)), ('effective-production-status-ap', struct.pack('<I', 0)),
                           ('certificate-security-mode', struct.pack('<I', 1)), ('effective-security-mode-sep', struct.pack('<I', 1))]
                          if args.ipad_identity else []),
                        *([('ephemeral-storage', struct.pack('<I', 1))] if (args.data_ramdisk or args.packed_data_ramdisk) else []),
                        *( [('darwinboot-memory-size', struct.pack('<Q', args.owned_memory_size))]
                           if args.owned_memory_size else [] ),
                        ('dram-base', struct.pack('<Q', DRAM_BASE)),
                        ('dram-size', struct.pack('<Q', args.dram_size)),
                        ('crypto-hash-method', b'sha2-384\0'),
                        # pandora/ios-sweet: 3x screen class; 0 leaves FBSDisplayMode at 0x0
                        *([('display-scale', struct.pack('<I', 3))] if not args.no_display_scale else []),
                        # /sbin/mount (mount-phase-1, pid 3) exits EX_NOINPUT
                        # without this: IOGetBootManifestHash() reads the
                        # property and mount aborts with "failed to get boot
                        # manifest hash - No such file or directory".  A real
                        # device gets it from iBoot; nothing here verifies it,
                        # and any value up to 48 bytes (CCSHA384_OUTPUT_SIZE)
                        # is accepted, so a fixed digest is enough to let the
                        # boot continue past mount-phase-1.
                        ('boot-manifest-hash', hashlib.sha384(b'rodin-boot-manifest').digest()),
                        *( [('root-matching', ('<dict><key>IOProviderClass</key><string>IOMedia</string>'
                                               '<key>IOPropertyMatch</key><dict><key>UUID</key><string>' +
                                               args.root_match_volume_uuid.upper() + '</string></dict></dict>\0').encode())]
                           if args.root_match_volume_uuid else [] ),
                        ('amfi-only-platform-code', struct.pack('<I', 1)),
                        *empty_nvram_proxy()],
             [node('memory-map', ([("PackedRAMDisk" if args.packed_data_ramdisk else "RAMDisk", bytes(16))] if (args.data_ramdisk or args.packed_data_ramdisk) else []) +
                                 ([('TrustCache', bytes(16))] if args.trust_cache else [])),
              node('manifest-properties')]),
        node('cpus', [('#address-cells', struct.pack('<I', 1)),
                      ('#size-cells', struct.pack('<I', 0)),
                      ('max_cpus', struct.pack('<I', len(cpus)))], children=cpus),
        *([node('psci', [('compatible', b'arm,psci-1.0\0'), ('method', args.psci_method.encode() + b'\0')])] if len(cpus) > 1 else []),
        node('defaults', [('sleep-disabled', struct.pack('<I', 1))]),
        node('options', []),
        *( [node('buttons', [('compatible', b'buttons\0'), ('device_type', b'buttons\0'),
                             ('button-names', b'hold\0voldown\0volup\0'),
                             ('home-button-type', struct.pack('<I', 2))])] if args.ipad_identity else [] ),
        node('product', [('product-name', b'iPad Pro (12.9-inch) (2nd generation)\0' if args.ipad_identity else b'Xiaomi Redmi Turbo 4\0'),
                         ('model', b'xiaomi,rodin\0'),
                         *( [('product-description', b'iPad Pro (12.9-inch) (2nd generation)\0'),
                             ('artwork-device-idiom', b'pad\0'),
                             ('artwork-device-subtype', struct.pack('<I', 2732)),
                             # fb183: SpringBoard reads this key to decide the display scale, and the
                             # value must match the panel.  It was 2 (the iPad Pro
                             # 12.9-inch value, whose panel is 2732x2048), while the
                             # Turbo 4 panel is 2712x1220 at 1:1.  A scale that
                             # disagrees with the real pixel size collapses to 0, and
                             # FBSDisplayMode's own validation rejects a zero scale.
                             ('artwork-scale-factor', struct.pack('<I', 2)),
                             ('artwork-display-gamut', b'P3\0'),
                             ('compatible-device-fallback', b'iPad6,7\0'),
                             ('thin-bezel', struct.pack('<I', 1))] if args.ipad_identity else [] )]),
        node('arm-io', [('device_type', b'arm-io\0'),
                        ('#address-cells', struct.pack('<I', 2)),
                        ('#size-cells', struct.pack('<I', 2)),
                        # The window must cover the redistributor at +0x40000/0x200000
                        # (ArmCpu::mapGic rejects a reg range that exceeds ranges).
                        ('ranges', struct.pack('<QQQ', 0, ARMIO_BASE, ARMIO_SIZE))],
             [node('intc', [('compatible', b'arm,gic-v3\0'),
                            ('reg', struct.pack('<4Q',
                                                GIC_DIST - ARMIO_BASE, GIC_DIST_SIZE,
                                                GIC_REDIST - ARMIO_BASE, GIC_REDIST_SIZE)),
                            # The MT6899 stock DT leaves stride to GICR_TYPER.VLPIS.
                            # ArmCpu already walks those hardware-sized frames when
                            # the override is absent; rothko omitted it for MT6989
                            # for the same reason.
                            ]),
              # fb170: IOMobileFramebuffer.framework finds displays by walking
              # IODeviceTree:/arm-io and counting children whose device_type is
              # "display-subsystem" or "ext-display-subsystem".  With no such
              # child backboardd starts headless and SpringBoard dies with
              # "failed to find the main CADisplay" (rothko fb170).
              node('disp0', [('device_type', b'display-subsystem\0'),
                             ('compatible', b'disp0,rodin\0')])]),
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(tree)
    print(f'rodin ADT: {len(tree)} bytes, dram {args.dram_size:#x}, timebase {TIMEBASE}')


if __name__ == '__main__':
    main()
