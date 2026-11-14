# UniXNU-turbo4（骨架，进行中）

Xiaomi Redmi Turbo 4（天玑 8400-Ultra）的 UniXNU 移植工作区。
蓝本：woaphone/UniXNU-rothko + woaphone/UniXNU-mt6989-common（天玑 9300，社区走得最远的 MTK port）。

## 当前状态
仅骨架。所有 `TODO` 项必须用**有出处的实测值**填掉后，`example = false` 才有效。

## 下一步
1. 按 `docs/hardware-inventory.md` 从 stock 固件收集硬件事实
2. 在有构建机的环境 clone 主仓库后验证解析：
   ./unixnu defconfig turbo4_defconfig -D ../UniXNU-turbo4 && ./unixnu fetch && ./unixnu status --json
3. 参考 [Port a device](https://unixnu.com/porting/steps) 与 [rothko 移植记录](https://unixnu.com/devices/rothko)

## 安全提示（本项目硬性规则）
- **永不刷写 lk / preloader / vbmeta 分区** —— 本设备靠解锁版 lk 维持解锁状态，刷原版 lk 会回锁
- 解析固件只针对 /sdcard 上的 ROM 包文件副本（只读），不对设备做任何写入
- 真机调试一律用 `fastboot boot`（一次性，不写分区），稳定后才考虑写 boot_a
- 写 boot 分区前全分区备份（尤其 boot/vbmeta/preloader/lk/modem）
- 参考记录里 rothko 曾因 UFS 参考时钟设置错误发生事故
