# Bring-up log — rodin (2026-11-14)

First hardware session of the rodin port. All steps below ran from the
Debian-side sandbox with the Turbo 4 on USB; nothing was written to `lk`,
`preloader`, `vbmeta` or any slot `a` partition.

## 1. Firmware build (host)

The platform builds with EDK II CLANGPDB against mu_basecore:

```
WORKSPACE=<uefi> EDK_TOOLS_PATH=<mu_basecore>/BaseTools CLANG_BIN=<clang>/ \
PACKAGES_PATH=<uefi>:<uefi>/Platforms/Xiaomi:<uefi>/Common/Mu: \
  <uefi>/Common/Mu_OEM_Sample:<mu_basecore>:<uefi>/Silicon/MediaTek: \
  <uefi>/Silicon/Silicium:<tree>/package:<tree>/drivers/DarwinBoot \
python3 <mu_basecore>/BaseTools/Source/Python/build/build.py \
  -p Platforms/Xiaomi/rodinPkg/rodin.dsc -a AARCH64 -b DEBUG -t CLANGPDB \
  -D FD_BASE=0x40400000 -D FD_SIZE=0x200000 -D FD_BLOCKS=0x200 \
  -D ENABLE_SECUREBOOT=0 -D DEVICE_MODEL=0 -D MEMORY_PROTECTION=TRUE -D SHIP_MODE=FALSE
```

Result: `Build/rodinPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd`, 2,097,152 bytes,
sha256 `27e8a9d0baf5ac16121efacdd1e5207cdad4901b2b140c3602b00b41ade82979`.
FVMAIN_COMPACT 22 % full, FVMAIN 99 % full (72 bytes free, DEBUG build).

## 2. Smoke boot image

Built locally from the FD plus the stock `vendor_boot` DTB:

- BootShim compiled `--target=aarch64-none-elf` with `FD_BASE=0x40400000`,
  `FD_SIZE=0x200000`, `REQUIRES_KERNEL_HEADER=1`; the shim relocates the FD to
  `0x40400000` wherever LK put the image, so the load address is not a variable.
- `kernel = gzip(shim + FD) + stock vendor_boot DTB`, header v4, empty ramdisk.
- Output: `boot-smoke.img`, 897,024 bytes, sha256
  `4ad1daace0ecb2584d295541a824cb22ca221df8a04fdec3302b7fe787ed387b`.

## 3. Getting the image onto the device

`fastboot boot` is **not available** on this bootloader:

```
$ fastboot boot boot-smoke.img
Booting  FAILED (remote: 'unknown command')
```

The bootloader is MediaTek fastboot 0.5 (`getvar version: 0.5`), unlocked,
A/B (`slot-count: 2`, running `_a`, `slot-unbootable:b: yes`). The image was
therefore written to the **inactive** slot only:

```
adb push boot-smoke.img /data/local/tmp/
adb shell su -c 'dd if=/data/local/tmp/boot-smoke.img of=/dev/block/by-name/boot_b bs=4096 conv=fsync'
adb reboot bootloader
fastboot set_active b
fastboot reboot
```

Read-back confirmed `ANDROID!` at the start of `boot_b`.

## 4. Result on hardware

The panel showed:

1. the UEFI Boot Manager — `Please select boot device:`, entries `UniXNU`,
   `UniXNU`, `Power Off`, `Exit`, key hints;
2. after activating `UniXNU`, the UniXNU 0.1.0 screen with
   `Return to Firmware / Restart / Power off / Tools`, red
   `no boot entry found` (the smoke image has an empty ramdisk) and
   `drivers 0 loaded / 0 failed`.

Volume Up/Down moved the selection and the power key activated entries.

Verified by this run: LK handoff (`x0` DTB), SEC/PEI/DXE bring-up, the
`/proc/iomem`-derived memory map (no translation fault, no GCD assert), GICv3,
the 13 MHz generic timer, the DSC+VDO framebuffer GOP at `0xFCC20000`, the
framebuffer text console, and the Volume Up (PMIC GPIO 196) / Power
(MT6363 PWRKEY) key path.

## 5. Restoring the phone

The bootloader does not mark slot `b` successful, so after the next power
cycle it falls back to slot `a` on its own; Android came back untouched. If a
manual restore is ever needed:

```
fastboot set_active a
```

## 6. Open items for the next session

- Run the full pipeline image (payload + `kernel.macho`) from slot `b`.
- `fastboot boot` being unavailable means every test needs the slot-`b`
  write + `set_active` cycle; keep boot_a untouched.
- The ADT/payload path has not been exercised on hardware yet.
