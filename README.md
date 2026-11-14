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

## 安全提示
- 任何真机操作前全分区备份
- 用 `fastboot boot` 一次性启动，不用 `fastboot flash`
- 参考记录里 rothko 曾因 UFS 参考时钟设置错误发生事故
