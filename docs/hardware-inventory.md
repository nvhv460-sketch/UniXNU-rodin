# Redmi Turbo 4（rodin）硬件清单核对表

> 用途：移植第一步（Collect the device inputs）。每项都要标注信息来源
> （stock DTS 节点路径 / LK 日志行 / adb 实测 / 拆机报告），没有来源的值不许写入 board.toml。
>
> 固件包：/sdcard/澎湃os305/rodin_images_OS3.0.305.0.WOJCNXM_16.0/（正式包，无 preloader/lk）
> 工厂包：/sdcard/1工厂包turbo4/（含 preloader_rodin.bin、lk.img）
> 参考仓库：/sdcard/{UniXNU-ref, UniXNU-mt6989-common, UniXNU-rothko, Silicium-Rothko}

## 0. 设备身份
- [x] 官方代号：**rodin**（来源：工厂包 preloader_rodin.bin、scatter project 字段、相机 sensor 名 rodin*）
- [x] SoC：**MT6899 / 天玑 8400-Ultra**（来源：scatter platform 字段）
- [ ] 内存量版本（12 GiB / 16 GiB），DRAM 类型（dram_para 分区 / lk mblock）
- [x] fastboot 包结构齐全；bootloader 解锁状态与 fastboot boot 待实测（**先备份全部分区**）

## 1. CPU / 中断
- [x] CPU 拓扑：8 核，三簇 4+3+1，capacity 0x400/0x3bb/0x3cb，MPIDR 0x0..0x700，PSCI（来源：vendor_boot DTB /cpus）
- [x] 中断控制器：GIC500 @0xc000000（0x400000），CPU interface @0xc400000（来源：vendor_boot DTB）
- [x] 计时器：arm,armv8-timer，13 MHz（0x00c65d40），4 PPI（来源：/timer 节点）
- [x] PSCI：enable-method=psci，idle-state 参数链已提取（来源：/cpus/idle-states）
- [ ] FDVFS / 频率投票接口（stock DTS 的 CPU vote 表 —— 待从 super.img vendor 提取）

## 2. 内存 / DMA
- [x] 内存基址 0x40000000（stock DT 占位；真实映射待 lk mblock）
- [ ] 保留内存区（DTB /reserved-memory 有 mkp、ccci-dpmaif、ssmr-cma 等，需完整提取）
- [x] IOMMU 家族：m4/m6/m7 iommu-apb、m4-smmu-apb@10500000(2MB)、disp@1e816000、mdp@1e81b000、apu@19010000/19015000（来源：vendor_boot DTB）

## 3. 存储
- [x] UFS host：0x112b0000 / 0x2a00，mt8183-ufshci；freq-table-hz 已在 DTB；PHY 0x112a0000 mt8183-ufsphy mphy-ver 1（与 rothko host 地址相同）
- [ ] 参考时钟设置（rothko 在这里出过事故 —— **双重核对**；lk.img 待解）
- [x] GPT 完整导出（PGPT_UFS，92 分区，4K LBA）：super 524288..3407871、lk_a 264960..、boot_a 269056..、pstore 129792..163839
- [ ] LU 布局确认：user LUN 块大小（预期 4096，需 lk 或真机 sg 实测）；unixnu 窗口规划（userdata 起点 4K LBA 0xD50C0）
- [x] UFS 厂商固件三件套在工厂包 MI_FFU（KIOXIA 512G / Micron 256G / SS V8 512G——你的机器是哪个待确认）

## 4. 显示
- [x] 面板候选：o10_42_02_0a_dsc_vdo 与 o10_36_02_0b_dsc_vdo（dtbo overlay，两款批次）；DSI0@0x1420a000；ESD irq GPIO 已记录
- [x] 背光：mediatek,disp-leds，max 0x3fff（14 bit），default 15%
- [ ] 分辨率与初始化序列（预期 1220x2712，待 super.img vendor 面板驱动确认）
- [ ] DSC 压缩 + VDO 模式与 rothko CMD 模式的差异评估

## 5. 触控 / 按键
- [x] 触控：xiaomi-touch 框架，xiaomi,touch-spi，SPI 15 MHz，interrupt 0x9（dtbo）；面板双供应商 phandle 关联
- [ ] 具体 IC 型号（Goodix/Novatek?）与 SPI 总线号
- [ ] 三颗实体按键路由（PMIC MT6363 pwrkey/homekey?）

## 6. 无线 / USB / 音频 / 电源（后期）
- [x] Wi-Fi/BT/GNSS 固件三件：connsys_wifi/bt/gnss.img（两个包都有）
- [ ] PMIC：MT6685 (SPMI@0x1cc04000) + MT6363（来源 vendor_boot DTB）
- [x] 电量计 TI bq28z610 @0x55、充电 sc858x@0x6F + bq25985@0x6E、120W（dtbo）
- [x] 音频：aw882xx 智能功放 ×2 @0x34/0x35（dtbo）
- [x] NFC：NXP nq-nci；指纹：xiaomi-fp SPI；振动：aw8697/sih6887（dtbo）
- [ ] USB 控制器与 PHY（日志通道依赖它）
- [ ] 基带：建议排除并记录 not-applicable（modem.img 200 MiB x2 存在于分区表）

## 7. 固件输入
- [x] 官方正式包（HyperOS 3.0.305.0 WOJCNXM）本地已有；工厂包本地已有
- [x] UEFI fork 蓝本：ChallengeThePeak/Silicium-Rothko（已克隆 /sdcard/Silicium-Rothko）
- [ ] 逐项填写 proprietary-files.txt（dtbo/connsys/logo 已在包内，直接可引用）

## 8. 调试通道
- [ ] UART 焊点/测试点（如有）；否则确认 USB 串口方案
- [ ] pmsg/ramoops：已有独立 pstore 分区（133 MiB）+ oops 分区 16 MiB
- [ ] UEFI 日志导出（QR/log ring）已在固件里集成
