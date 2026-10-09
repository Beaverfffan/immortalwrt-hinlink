# immortalwrt HinLink 全机型适配（拆分版）

针对 `immortalwrt/immortalwrt`（`master` 分支）的 HinLink 设备线完整适配。

**设计原则：拆分所有机型，不允许自适应。** 每个硬件变体一个独立 DTS + 一个独立  
compatible，`02_network` / `01_leds` 每机型独立分支，`ethN` 映射写死。

---

## 一、蓝本与依据

| 项      | 来源                                                               |
| ------ | ---------------------------------------------------------------- |
| DTS 蓝本 | OpenWrt 主线 `rk3568-hinlink-h68k.dts` + `rk3568-hinlink-opc.dtsi` |
| 设备定义范式 | OpenWrt 主线 `target/linux/rockchip/image/armv8.mk`                |
| 硬件事实   | 厂商 2022/2023/2024 固件 dtb（已解包反编译逐项核对）                             |
| 无线参数   | 用户提供的 H69K AIC8800 点亮脚本 + 2022 a-b dtb 交叉验证                      |

**immortalwrt 现状**：`immortalwrt/immortalwrt` 默认分支 `master`  
（最后推送 2026-10-09T03:20:38Z，11713 star），**当前完全没有 hinlink 适配**  
（code search 全仓仅 1 处命中，是 Graperain-G3568 的无关 patch）。

---

## 二、机型矩阵（7 个独立机型）

| # | 机型                       | DTS                              | compatible                | 网口数 | 网络构成                 | 板载 WiFi                            |
| - | ------------------------ | -------------------------------- | ------------------------- | --- | -------------------- | ---------------------------------- |
| 1 | **H68K A/B**（2022 双千兆）   | `rk3568-hinlink-h68k-a.dts`      | `hinlink,opc-h68k-a`      | 2   | 2× GMAC              | **AP6256**（Broadcom brcmfmac）+ RTC |
| 2 | **H68K C/D/F**（2022 四网口） | `rk3568-hinlink-h68k-c.dts`      | `hinlink,opc-h68k-c`      | 4   | 2× GMAC + 2× RTL8125 | 无                                  |
| 3 | **H68K C USB3**（2022.8）  | `rk3568-hinlink-h68k-c-usb3.dts` | `hinlink,opc-h68k-c-usb3` | 4   | 同上                   | 无                                  |
| 4 | **H68K D**（2023.4 推荐版）   | `rk3568-hinlink-h68k-d.dts`      | `hinlink,opc-h68k-d`      | 4   | 同上                   | 无                                  |
| 5 | **H68K new**（2023末~2024） | `rk3568-hinlink-h68k-new.dts`    | `hinlink,opc-h68k-new`    | 4   | 同上                   | **AIC8800**                        |
| 6 | **H69K**（真·装 5G 模组）      | `rk3568-hinlink-h69k.dts`        | `hinlink,opc-h69k`        | 3   | 1× GMAC + 2× RTL8125 | **AIC8800** + 5G                   |
| 7 | **H69K mini**（体积精简）      | `rk3568-hinlink-h69k-mini.dts`   | `hinlink,opc-h69k-mini`   | 2   | 1× GMAC + 1× RTL8125 | 无                                  |

### 网口映射（写死，不探测）

| 机型                | LAN              | WAN    |
| ----------------- | ---------------- | ------ |
| H68K A/B          | `eth1`           | `eth0` |
| H68K C/D/F、C USB3 | `eth0 eth2 eth3` | `eth1` |
| H68K D、new        | `eth1 eth2 eth3` | `eth0` |
| H69K              | `eth1 eth2`      | `eth0` |
| H69K mini         | `eth1`           | `eth0` |

**枚举前提**（immortalwrt 6.18 内核 dtc 顺序）：

```
gmac0   -> eth0    SoC 内部控制器，顺序固定
gmac1   -> eth1    SoC 内部控制器，顺序固定
pcie3x1 -> eth2    PCI 扫描
pcie3x2 -> eth3    PCI 扫描
```

---

## 三、★ 关键设计：2.5G 网卡的初始化责任

**这一节是本方案最重要的部分**，也是我中途判断错的地方。

主线 `rk3568-hinlink-opc.dtsi` 里已经把两路 2.5G 口的初始化**全部落实**：

```dts
&combphy0 { status = "okay"; };
&combphy1 { status = "okay"; };
&combphy2 { status = "okay"; };

&pcie30phy { data-lanes = <1 2>; status = "okay"; };

&pcie3x1 {
	num-lanes = <1>;
	reset-gpios = <&gpio3 RK_PA4 GPIO_ACTIVE_HIGH>;
	vpcie3v3-supply = <&vcc3v3_pi6c_05>;
	status = "okay";
};

&pcie3x2 {
	num-lanes = <1>;
	reset-gpios = <&gpio2 RK_PD0 GPIO_ACTIVE_HIGH>;
	vpcie3v3-supply = <&vcc3v3_pi6c_05>;
	status = "okay";
};
```

**2022 年厂商 dtb 里的 `pcie-eth@10,0` / `pcie-eth@20,0` 子节点不是必需的。**  
RTL8125B 是标准 PCI 设备，内核 pcie 驱动 + `kmod-r8169` 会在启动时自动枚举，  
自然产生 `eth2`/`eth3`。OpenWrt 主线从未写这两个节点，H68K 依然是四网口。  
写进去反而可能干扰枚举顺序。

⇒ **本方案不写 `pcie-eth` 子节点**，只按机型决定是否 disable PCIe 控制器：

| 机型        | PCIe 处理                                           | 效果                    |
| --------- | ------------------------------------------------- | --------------------- |
| 2 口变体     | `&combphy1/2`、`&pcie3x1/2` 全部 `status="disabled"` | 只剩 2 个 GMAC           |
| 4 口变体     | 不动（dtsi 已okay）                                    | 2 GMAC + 2 PCIe = 4 口 |
| H69K      | 屏蔽 `gmac1`                                        | 1 GMAC + 2 PCIe = 3 口 |
| H69K mini | 屏蔽 `gmac1` + `pcie3x2`                            | 1 GMAC + 1 PCIe = 2 口 |

---

## 四、硬件事实表（全部来自厂商 dtb，无推测）

### GMAC 时序（跨 2022/2023/2024 三代固件完全一致）

| 控制器            | PHY 复位             | tx_delay | rx_delay |
| -------------- | ------------------ | -------- | -------- |
| `gmac0` (eth0) | `gpio2 RK_PD3` 低有效 | `0x3c`   | `0x2f`   |
| `gmac1` (eth1) | `gpio1 RK_PB0` 低有效 | `0x4f`   | `0x26`   |

`phy-mode = "rgmii-id"`（PHY 自带 50MHz 时钟），复位时序 `snps,reset-delays-us = <0 20000 100000>`。

这组值在 iStoreOS 中被改成了 `0x26/0x2a` 与 `0x34/0x22`（自行调优），  
**本方案采用厂商原厂值**，与 OpenWrt 主线一致。

### SDIO WiFi（a/b 系=AP6256，new/69K=AIC8800）

引脚来自 2022 a-b dtb 与 H69K 点亮脚本交叉验证：

```
sdmmc2m0:  data = GPIO3_C6..C7 + D0..D1  (pin 0x16-0x19)
           cmd  = GPIO3_D2              (pin 0x1a)
           clk  = GPIO3_D3              (pin 0x1b)
           func = 3
WiFi 电源:  GPIO3_D5 (0x1d) 高有效
host-wake:  GPIO3_D4 (0x1c) 高电平触发
32.768kHz:  RK809 PMIC clkout2  =>  clocks = <&rk809 1>
```

> > ⚠️ H69K 点亮脚本用 **GPIO3_A0**，2022 a-b dtb 用 **GPIO3_D5**，二者位置不同。  
> > 本方案取 `GPIO3_D5`（来自厂商正式 dtb）。**H69K 实机引脚仍需确认。**

### 5G 模组电源（H69K）

来自 iStoreOS `rk3568-opc-h69k.dts`：

```dts
modem-enable: gpio0 RK_PC0 低有效, startup-delay-us = <2000000>  // 等模组启动 2 秒
```

---

## 五、文件清单

```
immortalwrt/
├── dts/7 个机型 DTS
│   ├── rk3568-hinlink-h68k-a.dts
│   ├── rk3568-hinlink-h68k-c.dts
│   ├── rk3568-hinlink-h68k-c-usb3.dts
│   ├── rk3568-hinlink-h68k-d.dts
│   ├── rk3568-hinlink-h68k-new.dts
│   ├── rk3568-hinlink-h69k.dts
│   └── rk3568-hinlink-h69k-mini.dts
├── files/
│   ├── 02_network_hinlink        # 每机型独立分支，写死映射
│   └── 01_leds_hinlink           # 每机型独立分支
├── armv8.mk.hinlink# 设备定义片段
├── gen_hinlink.py                # 生成器（改机型表后重跑即可）
└── dts_syntax_check.py           # 离线语法校验器
```

**依赖的上游文件**（immortalwrt 已有，无需新增）：

- `arch/arm64/boot/dts/rockchip/rk3568-hinlink-opc.dtsi`（主线内核 6.18 已有）
- `rk3528-hinlink-h28k.dts`（H28K 已支持）

---

## 六、落地步骤

### 1. DTS（若目标内核还没有 hinlink-opc.dtsi）

immortalwrt 用 6.18 内核，需确认 `rk3568-hinlink-opc.dtsi` 已在  
`arch/arm64/boot/dts/rockchip/` 下。若无，从 OpenWrt 主线  
`target/linux/rockchip/patches-6.18/` 取对应 patch。

把 `dts/*.dts` 放入内核 `arch/arm64/boot/dts/rockchip/`。

### 2. 设备定义

把 `armv8.mk.hinlink` 的内容追加到  
`target/linux/rockchip/image/armv8.mk`。

### 3. 板级配置

- `files/02_network_hinlink` 的内容并入  
  `target/linux/rockchip/armv8/base-files/etc/board.d/02_network`
- `files/01_leds_hinlink` 同理并入 `01_leds`

> immortalwrt 的 `02_network` 用的是 `rockchip_setup_interfaces()` 函数结构，  
> 与 OpenWrt 主线一致。若目标分支用的是旧式 `ucidef_set_interfaces_lan_wan`  
> 直接调用形式，按目标分支结构调整函数包装即可，**映射内容不变**。

### 4. U-Boot

`armv8.mk.hinlink` 里每机型指定了 `UBOOT_DEVICE_NAME`（如  
`hinlink-h68k-a-rk3568`）。需要在  
`package/boot/uboot-rockchip/Makefile` 加对应 defconfig，  
或统一改用现有的 `generic-rk3568`。

**建议**：先统一用 `generic-rk3568` 验证能启动，再考虑做专属 U-Boot port。

### 5. 编译

```sh
make menuconfig   # Rockchip platform → Target Devices → 勾选机型
make target/download V=s
make -j$(nproc)
```

---

## 七、验证状态

| 项目            | 状态     | 说明                                                                                                 |
| ------------- | ------ | -------------------------------------------------------------------------------------------------- |
| DTS 语法        | ✅ 已验证  | 7 个 DTS + 主线对照组全部 PASS（`dts_syntax_check.py`，该检查器已用主线原生 DTS 校准）                                    |
| dtc 完整编译      | ⚠️ 未完成 | Ubuntu 上 dtc 1.7.2 太老，连主线内核官方 `rk3568.dtsi` 都编译失败（对照组同样失败 ⇒ 环境问题，非代码问题）。需在 buildroot 环境或新版 dtc 下验证 |
| phandle 引用完整性 | ⚠️ 未验证 | 离线检查器不检查 phandle 交叉引用                                                                              |
| 实机启动          | ❌ 未验证  | 无实机                                                                                                |
| LED 颜色与GPIO   | ❌ 待确认  | `01_leds_hinlink` 中的 color/label 需按实机调整                                                            |

### 需要实机确认的项

1. **H69K 的 WiFi 复位引脚**：脚本写 GPIO3_A0，a-b dtb 是 GPIO3_D5，需确认
2. **H69K-mini 的实际屏蔽配置**：当前按「屏蔽 1 GMAC + 1 PCIe」处理，需确认
3. ~~H68K new 的 WiFi 型号~~ **已确认：AIC8800**（全新机器）
4. **各机型 LED 颜色/闪烁规则**
5. **H69K 5G 模组**：当前用 GPIO0_PC0 + 2s 延时（抄 iStoreOS），需确认

---

## 八、遗留的已知不确定项

### 8.1 WiFi 驱动分档（已按实机确认）

| 机型                              | WiFi 芯片              | 驱动包                                     |
| ------------------------------- | -------------------- | --------------------------------------- |
| h68k-a（老机器）                     | **AP6256**（Broadcom） | `kmod-brcmfmac kmod-firmware-brcm80211` |
| h68k-new / h69k（全新机器）           | **AIC8800**          | `kmod-aic8800s`                         |
| h68k-c / c-usb3 / d / h69k-mini | 无板载 WiFi（M.2 插槽）     | `kmod-mt7921e`                          |

`armv8.mk.hinlink` 中已按此分三档基类：

- `hinlink_h6xk_base` —— 有线公共包
- `hinlink_h6xk_m2_wifi` —— M.2 无线机型
- `hinlink_h6xk_sdio_ap6256` —— 老机器 AP6256
- `hinlink_h6xk_sdio_aic8800` —— 新机器 AIC8800

### 8.2 2023.4 版 H68K-D 的 delay 值

2023.4.20 的 `ink,opc-h68k-d` dtb 是完整大 dtb（160639 B），但我在其中  
只提取到 model/compatible 与网口配置，**未逐一核对 delay**。  
若 2023 底板换代后 PHY 变了，delay 可能需要调整。

### 8.3 H68K A/B 的 RTC

2022 a-b dtb 有 `hym8563@51`（i2c1，irq gpio1_C4）。  
本方案已包含。若某批次无此芯片，需删掉。
--------------------

## RK3528 / RK3588 机型（第二批）

### 机型矩阵

| #  | 机型                       | SoC    | DTS                          | compatible         | 网口                     | 板载无线                             |
| -- | ------------------------ | ------ | ---------------------------- | ------------------ | ---------------------- | -------------------------------- |
| 8  | **H28K**                 | RK3528 | `rk3528-hinlink-h28k.dts`    | `hinlink,h28k`     | RGMII + PCIe RTL8111HS | 无（主线已支持）                         |
| 9  | **H29K**                 | RK3528 | `rk3528-hinlink-h29k.dts`    | `hinlink,opc-h29k` | RGMII                  | SDIO（SDR104）                     |
| 10 | ~~**H29K 电池版**~~ **已删除** | —      | —                            | —                  | —                      | 该划分模型有误，见第三批；真实变体是 v1.3/v5 × 屏尺寸 |
| 11 | **HT2**                  | RK3528 | `rk3528-hinlink-ht2.dts`     | `hinlink,opc-ht2`  | RGMII                  | SDIO（SDR50）                      |
| 12 | **H88K V2**              | RK3588 | `rk3588-hinlink-h88k-v2.dts` | `hinlink,h88k-v2`  | 1×RGMII + 2×PCIe       | M.2                              |
| 13 | **H88K V3**              | RK3588 | `rk3588-hinlink-h88k-v3.dts` | `hinlink,h88k-v3`  | 1×RGMII + 2×PCIe       | M.2                              |

### 网口映射（写死）

| 机型             | LAN            | WAN  |
| -------------- | -------------- | ---- |
| H28K           | eth0           | eth1 |
| H29K（全部 5 个变体） | eth1           | eth0 |
| HT2            | eth0           | eth1 |
| H88K V2/V3     | eth1 eth2 eth3 | eth0 |

### 与第一批的关键差异

**第一批（RK3568）是我手写 DTS；第二批直接复用已验证源码。**

第一版我手写 RK3528 DTS，犯了两个错：

1. 引用了 `&gmac1_rstn_l`（PHY 复位 pinctrl）但**没定义**它
2. 缺 `&sdmmc` / `&sdhci` / `&uart` / `&usb` 等基础节点，还留了一堆死 label

**判据教训**：手写设备树时最容易漏的是「被引用但未定义」—— 语法检查器查不出这种  
交叉引用错误（它只查括号与 include）。**复用已验证的源码比手写可靠得多。**

因此第二批的来源：

- H28K → OpenWrt 主线 `rk3528-hinlink-h28k.dts` 原版
- ~~H29K / 电池版 / HT2 → coolsnowwolf/lede的 DTS，只改头部注释~~ **已修正**
  - **H29K**：改用厂商原始 5 份 DTS（`hinlink,h29k-*`），lede 那份是混合体且背光引脚有误，见第三批
  - **HT2**：仍基于 coolsnowwolf/lede 的 `rk3528-opc-ht2.dts`，只改头部注释
- H88K V2/V3 → istoreos 的 `rk3588-h88k-v2.dts` / `-v3.dts`，**只改头部注释**

### ★ H88K 必须连带移植 iStoreOS 私有 dtsi

H88K 依赖 `rk3588-hinlink.dtsi`（15970 B，iStoreOS 私有，immortalwrt 6.18 内核中没有），  
它又引用同目录下 5 个私有 dtsi：

```
rk3588-hinlink.dtsi          15970 B   ← 主dtsi
rk3588-rk806-single.dtsi      8333 B
rk3588s-ip.dtsi                592 B
rk3588s-ip-supply.dtsi         575 B
rk3588-hdmirx.dtsi             443 B
rk3588-ramoops.dtsi            290 B
```

这 6 个文件**已包含在本仓库**，来源：  
<https://github.com/istoreos/istoreos> `target/linux/rockchip/dts/rk3588/`

`rk3588.dtsi` 本身用内核自带版本即可（166 B，只 include rk3588-extra.dtsi + rk3588-opp.dtsi）。

### RK3528 硬件要点

**H29K 与 HT2 的差异**（同为主线/lede 同一批板）：

| 项         | H29K                                                  | HT2                                |
| --------- | ----------------------------------------------------- | ---------------------------------- |
| SDIO 最高速率 | SDR104                                                | SDR50                              |
| LED       | 4G(red, gpio4 PC0) + 5G(blue, PC3) + work(green, PB7) | LAN(amber, PC0) + work(green, PB7) |
| rfkill    | 有（gpio1 PB0，控制 4G/5G 模组）                              | 无                                  |
| SPI 屏     | 有（st7789v，spi1）                                       | 无                                  |
| I2C1      | 启用                                                    | 未启用                                |

**WiFi 引脚**（两机相同）：

```
SDIO复位 = GPIO1_A6 低有效
host-wake = GPIO1_A7 高电平触发
上电延时 = 100 ms，断电延时 = 5 s
```

**板载 RGMII**（两机相同）：`phy-mode = "rgmii-id"`，PHY 复位 gpio4 PC2，  
`snps,reset-delays-us = <0 20000 100000>`。

### H29K：真实变体与待确认项（第三批修订）

原「电池版本」一节已删除 —— 该机型划分模型有误。真实变体见第三批章节。

仍需实机确认：

1. **1.9 寸屏是「微雪原厂」还是「线序不对版本」** —— 两者 `spi-max-frequency`  
   差 16 倍（10MHz vs 600kHz），刷错屏会花屏
2. **2.8 寸屏用哪份 fbtft 偏移 patch** —— 厂商只给了 1.9 与 1.14 两份
3. **v5 的电池电压读取** —— 依赖 `9527-rockchip-rk3528-iio-add-adc.patch`，  
   无此 patch 时 `adc-battery@0` 读不出数据

### RK3588 硬件要点（H88K）

**v2 vs v3 的差异**：

| 项       | V2                          | V3                                                          |
| ------- | --------------------------- | ----------------------------------------------------------- |
| 存储      | `combphy0_ps` + `sata0`     | `combphy0_ps` + `pcie2x1l2`（RTL8125 2.5G）                   |
| 屏       | 无                           | `&spi4` + ST7789V                                           |
| 3.3V 供电 | `vcc3v3_m2_sata`（gpio4 PA4） | `vcc3v3_sd`（gpio4 PA4，同引脚不同用途）                              |
| 网口枚举顺序  | 默认                          | `eth_order = "0004:*1:00.0,0003:*1:00.0,fe1b0000.ethernet"` |


v3 的 `eth_order` 是作者为解决枚举顺序不稳定而显式加的，移植时不要删。

### 验证状态

| 项目           | 状态                                                                    |
| ------------ | --------------------------------------------------------------------- |
| DTS 语法结构     | ✅ 6/6 PASS                                                            |
| 对照组校准        | ✅ lede 原版 + iStoreOS 原版 + 主线 H28K 均 PASS                              |
| dtc 完整编译     | ❌ 未验证（同第一批，环境问题）                                                      |
| phandle 交叉引用 | ❌ 未验证 —— **这正是第一版手写时出问题的地方，建议在 buildroot 里 `make target/compile` 实测** |
| 实机启动         | ❌ 未验证                                                                 |

---

## H29K 真实情况修订（第三批）

用户提供厂商原始 DTS 共 5 份 + 4 份内核 patch。  
**此前「H29K 分电池版 / 非电池版」的假设被推翻。**

### 撤回上一版的错误

上一版我建了 `rk3528-hinlink-h29k-battery.dts`（占位段，一个 GPIO 都没填），  
并在 README 写「H29K 电池版 / 非电池版」。**这个划分模型是错的，已删除。**

真实的两个维度是：**主板版本（v1.3 / v5）× 屏幕尺寸（1.9 / 1.14 / 2.8）**。  
电池电压检测只是 v5 主板的附带属性，不是独立机型。

### 5 个真实变体

| 变体           | compatible             | 屏幕             | 电池电压 ADC     | 红外          | 模组 power-gpios | uart2 |
| ------------ | ---------------------- | -------------- | ------------ | ----------- | -------------- | ----- |
| v1.3 / 1.9"  | `hinlink,h29k-v13`     | 170×320 rot270 | ✗            | ✗           | ✓ gpio4_PB5    | ✗     |
| v1.3 / 1.14" | `hinlink,h29k-v13-114` | 135×240 rot270 | ✗            | ✗           | ✓ gpio4_PB5    | ✗     |
| v5 / 1.9"    | `hinlink,h29k-v5`      | 170×320 rot270 | ✓ saradc ch1 | ✓ gpio4_PC6 | ✗              | ✓     |
| v5 / 1.14"   | `hinlink,h29k-v5-114`  | 135×240 rot90  | ✓ saradc ch1 | ✓ gpio4_PC6 | ✗              | ✓     |
| v5 / 2.8"    | `hinlink,h29k-v5-28`   | 240×320 rot270 | ✓ saradc ch1 | ✓ gpio4_PC6 | ✗              | ✓     |

v1.3 → v5 的实质变化（260 行差异）：

- **新增**电池电压检测：`adc-battery@0` 走 `io-channels = <&saradc 1>`
- **新增**红外接收：`gpio-ir-receiver` on gpio4_PC6
- **新增** `&uart2`（5G 模组串口）
- **移除** `rfkill-modem` 的 `power-gpios = <&gpio4 RK_PB5>`（模组不再独立供电控制）
- **移除** `vcc5v0_usb` / `vcc_3v3_s3` / `vcc_1v8_s3` 三路供电轨
- 背光 pinctrl 上下拉：v1.3 `pull_up` → v5 `pull_none`

### 屏幕差异需要不同内核 patch（硬证据）

`9999-fbtft-adjust-display-offset-for-rotation-h29k-1.9.patch`：

```c
rotate 0/180: xs+=35, ys+=0
rotate 90/270: xs+=0, ys+=35
```

`9999-fbtft-adjust-display-offset-for-rotation-h29k-1.14.patch`：

```c
rotate 0/180: xs+=52, ys+=40
rotate 90/270: xs+=40, ys+=52
```

**偏移量完全不同 ⇒ 屏不可用同一份 DTS + 同一份 patch 覆盖。**  
2.8 寸没有对应 patch —— 厂商 DTS 注释标为「2.8 屏幕 new」，可能沿用 1.9 的 +35 偏移，  
**需实机确认**。

### v1.9 屏还有「线序」子变体

厂商 DTS 注释里出现两段1.9 屏配置：

```
/* 1.9 微雪 */          spi-max-frequency = <10000000>  170x320 rot270
/* 1.9 new 线序不对版本 */ spi-max-frequency = <600000>     170x320 rot270
```

**「微雪」= Waveshare（微雪电子）**，另一段注释为「new 线序不对版本」。  
⇒ 1.9 寸内部至少还分「微雪原厂」与「线序修正版」两种，  
差别在 `spi-max-frequency`（10MHz vs 600kHz）。**这条必须实机确认是哪一种。**

### 另外 2 份 patch

- `9527-rockchip-rk3528-iio-add-adc.patch` —— 给 `rockchip_saradc.c` 加  
  `rockchip,rk3528-saradc` 驱动与 4 通道 IIO 芯片定义。  
  **v5 系列的电池电压读取依赖此 patch，没有它 saradc 读不出数据。**
- `9528-linux-delfbcon-cursor.patch` —— 在 `fb_flashcursor()` / `fbcon_cursor()`  
  开头加 `return`，禁掉 framebuffer 硬件光标。

### ★ 发现 lede 的 H29K DTS 有背光引脚错误

| 来源                    | 背光 GPIO        | 极性                 |
| --------------------- | -------------- | ------------------ |
| 厂商 v1.3 全部 5 份        | `gpio0 RK_PA0` | `GPIO_ACTIVE_LOW`  |
| **coolsnowwolf/lede** | `gpio0 RK_PA1` | `GPIO_ACTIVE_HIGH` |

**引脚（PA0 vs PA1）与极性都不同。** 按厂商 DTS，`PA0` 才是背光。  
lede 那份会导致背光不亮或反向。**本方案 5 份 DTS 全部采用厂商原值 `PA0 / ACTIVE_LOW`。**

lede 那份还是**混合体**：有红外接收（v5 特征）但无电池 ADC（v1.3 特征），  
且完全没有屏幕 `panel` 的 width/height/rotate 配置 ——  
它更像厂商某个中间版本，而不是 v1.3 或 v5 的精确对应物。

### 已修复的厂商 DTS 缺陷

| 问题                      | 文件          | 处理                                              |
| ----------------------- | ----------- | ----------------------------------------------- |
| `&saradc` 重复定义两次        | v5-2.8      | 合并为一个                                           |
| 缺 `adc-battery@0` 节点    | v5-1.14     | 补上（另 4 份都有）                                     |
| SPI 时钟注释写 10MHz 实际 6MHz | v5 / v5-2.8 | 修正注释                                            |
| 5 份全用同一 compatible 无法区分 | 全部          | 改为 `hinlink,h29k-{v13,v13-114,v5,v5-114,v5-28}` |

> ⚠️ **注意**：原始文件的 compatible 全部是 `hinlink,h29k`（5 份完全相同）。  
> 本方案改成了带版本后缀的独立 compatible，**这是本方案做的唯一结构性改动**，  
> 否则 5 份 DTS 在固件里无法区分。若要保持与厂商固件一致，可改回`hinlink,h29k`。

### 验证

5 个变体 DTS 语法全部 PASS；对照组（lede 原版 + 主线 H68K）PASS。
---

## H68K / H69K 修正（第五批）

用户两条纠正：**① 没有双网口 mini，只有三网口 h69k + 四网口 h69k-mini(=h68k-max)；
② SATA/USB3 复用只涉及 2022-2023 老机器（68k 的 a-b/c/d-f），不涉及新机。**

### 撤回 1：双网口 h69k-mini 是臆造的

原`rk3568-hinlink-h69k-mini.dts` 我写的是「屏蔽 gmac1 + 屏蔽 1 路 PCIe = 2 口」。
**已删除并重做。**

正确的构成：**屏蔽的是 gmac1，两路 PCIe 始终保留**
```
H69K        = 1×GMAC(gmac0) + 2×RTL8125 2.5G = 三网口
H69K-mini   = 同上                                = 四网口（= H68K max）
```
两者网络构成相同、口数相同，差异在形态与 5G 模组而非网口数量。

⇒ **02_network 映射两机型相同：`LAN 'eth1 eth2' / WAN 'eth0'`**
（`aliases ethernet0 = &gmac0` ⇒ 板载口是 eth0，两路 PCIe 是 eth2/eth3；
原 h69k-mini 写 `LAN 'eth1'` 是错的，已改）。

### 撤回 2：SATA 复用不涉及新机

我一度给 h69k-mini 加了 `&sata0 disabled` 和 `-sata` 变体 —— **已全部删除**。
按用户确认，复用只在 2022-2023 老机器上。

### ★ SATA / USB3.0 二选一的硬件依据

`rk3568.dtsi` 实证：
```
sata0:  phys = <&combphy0 PHY_TYPE_SATA>     (phy@fe820000)
pcie3x1: phys = <&pcie30phy>                  (phy@fe8c0000)
pcie3x2: phys = <&pcie30phy>                  (同上一路)
combphy0/1/2: rk3568-naneng-combphy
```
`PHY_TYPE_SATA=1 / PHY_TYPE_PCIE=2 / PHY_TYPE_USB3=4`（`dt-bindings/phy/phy.h`）。
**combphy 同一时刻只能是一种 PHY_TYPE** ⇒ SATA 与 USB3.0 抢同一路，硬件互斥。

**网口数量不受影响** —— 2.5G 网卡走独立的 `pcie30phy`，与 combphy0 无关。

### 拆分结果（10 个 RK3568 机型）

| 机型 | compatible | sata0 | 网口 | LAN / WAN |
|---|---|---|---|---|
| h68k-a（2022 双千兆） | `hinlink,opc-h68k-a` | disabled | 2 | eth1 / eth0 |
| h68k-a-sata | `hinlink,opc-h68k-a-sata` | **okay** | 2 | eth1 / eth0 |
| h68k-c（2022 四网口） | `hinlink,opc-h68k-c` | disabled | 4 | eth0 eth2 eth3 / eth1 |
| h68k-c-sata | `hinlink,opc-h68k-c-sata` | **okay** | 4 | 同上 |
| h68k-c-usb3（2022.8） | `hinlink,opc-h68k-c-usb3` | disabled | 4 | 同上 |
| h68k-d（2023.4 推荐） | `hinlink,opc-h68k-d` | disabled | 4 | eth1 eth2 eth3 / eth0 |
| h68k-d-sata | `hinlink,opc-h68k-d-sata` | **okay** | 4 | 同上 |
| **h68k-new**（2023末~2024） | `hinlink,opc-h68k-new` | **继承主线okay** | 4 | eth1 eth2 eth3 / eth0 |
| **h69k**（三网口） | `hinlink,opc-h69k` | **继承主线 okay** | 3 | eth1 eth2 / eth0 |
| **h69k-mini**（四网口） | `hinlink,opc-h69k-mini` | **继承主线 okay** | 4 | eth1 eth2 / eth0 |

**c-usb3 不拆 SATA 变体** —— 它本身就是「在 C/D/F 基础上改USB 3.0」的改型，
名字已表明是 USB3 版。

### 顺带修的 bug

**h69k-mini 的 compatible 原与 h69k 完全相同**（都是 `hinlink,opc-h69k`），
固件里无法区分。已改为 `hinlink,opc-h69k-mini`。现在 10 个 compatible 全部唯一。

### 校验

10 个 DTS 语法全部 PASS；对照组（主线原生 h68k）PASS。
三方一致性校验通过：设备定义引用 10 个 DTS = 磁盘 10 个文件，无孤儿无缺失。
