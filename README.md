# immortalwrt — HinLink 全设备线适配

HinLink（芯联）全系列路由器在 immortalwrt 上的设备树与板级配置。
**按硬件变体一机一档，不做运行时自适应探测** —— 每个 `compatible` 对应一份独立
DTS，`02_network` 里 `ethN` 映射写死。

- **19 个机型** · 20 份 DTS · 7 份 dtsi · 4 份内核 patch · 5 个工具脚本 · 3 份厂商 dtb
- 覆盖 RK3568（H66K / H68K / H69K）、RK3528（H28K / H29K / HT2）、RK3588（H88K / **H89K**）

> 本仓库是**支线仓库**，只提供补丁文件，不含完整 OpenWrt 源码。
> 应用方式见 [`docs/APPLY.md`](docs/APPLY.md)。

---

## 一、怎么用

```sh
git clone https://github.com/Beaverfffan/immortalwrt-hinlink
cd immortalwrt-hinlink

# 1. 把 DTS 与 dtsi 复制到 immortalwrt 树
cp target/linux/rockchip/files/arch/arm64/boot/dts/rockchip/rk* \
   <immortalwrt>/target/linux/rockchip/files/arch/arm64/boot/dts/rockchip/

# 2. 合并板级配置（把 hinlink 的 case 段并入，不要整文件覆盖）
#    见 docs/APPLY.md 的「方案 B」

# 3. 追加设备定义
cat target/linux/rockchip/image/armv8.mk.hinlink \
    >> <immortalwrt>/target/linux/rockchip/image/armv8.mk

# 4. 内核 patch（H29K 需要）
cp patches/*.patch <immortalwrt>/target/linux/rockchip/patches-6.18/

# 5. 编译
cd <immortalwrt>
make menuconfig   # Target Devices → Rockchip platform → 勾选机型
make -j$(nproc)
```

### 改机型后必跑校验

```sh
python3 tools/check_port_count.py .        # 口数与板级映射是否一致
python3 tools/dts_syntax_check.py <dts> <include-dirs...>   # DTS 结构
```

`check_port_count.py` 交叉校验 **DTS 的网口构成** 与 **`02_network` 的接口映射**：
口数 = okay 的 GMAC 数 + okay 的 PCIe 控制器数，且 `LAN+WAN` 接口数必须等于口数。
这类错误 DTS 语法检查查不出来 —— 本仓库自身就靠它抓出过 4 个真实缺陷（见 §七）。

---

## 二、机型矩阵

### RK3568 — H66K / H68K / H69K（11 个机型）

| 机型 | 年份/定位 | 口数 | 网络构成 | 板载 WiFi | 存储口 |
|---|---|---|---|---|---|
| **h66k** | 无板载网口 | 2 | **0×GMAC** + 2×RTL8125 | — | SATA |
| **h68k-a** | 2022 双千兆 | 2 | 2×GMAC | AP6256 | **SATA** |
| h68k-a-usb | 同上 | 2 | 2×GMAC | AP6256 | USB3.0 |
| **h68k-c** | 2022 四网口 | 4 | 2×GMAC + 2×RTL8125 | M.2 | **SATA** |
| h68k-c-usb | 同上 | 4 | 2×GMAC + 2×RTL8125 | M.2 | USB3.0 |
| **h68k-c-usb3** | 2022.8 USB3.0 改型 | 4 | 2×GMAC + 2×RTL8125 | M.2 | USB3.0 |
| **h68k-d** | 2023.4 推荐版 | 4 | 2×GMAC + 2×RTL8125 | M.2 | **SATA** |
| h68k-d-usb | 同上 | 4 | 2×GMAC + 2×RTL8125 | M.2 | USB3.0 |
| **h68k-new** | 2023末~2024 | 4 | 2×GMAC + 2×RTL8125 | AIC8800 | USB3 + SATA |
| **h69k** | 装 USB 5G 模组 | **3** | 1×GMAC + 2×RTL8125 | AIC8800 | USB3 + SATA |
| **h69k-mini** | = **H68K max** | **4** | 2×GMAC + 2×RTL8125 | AIC8800 | USB3 + SATA |

**命名约定**（OpenWrt / lede / iStoreOS 互认）：**无后缀 = SATA，`-usb` = USB3.0**。

### RK3528 — H28K / H29K / HT2（5 个机型）

| 机型 | 版本 | 屏 | 口 | 板载 WiFi |
|---|---|---|---|---|
| **h28k** | — | 无 | **1**：RGMII | **无** |
| **h29k-v1.3-1.14** | v1.3 主板 | 1.14" 135×240 rot270 | **1** | SDIO |
| **h29k-v5-1.14** | v5 主板 | 1.14" 135×240 rot90 | **1** | SDIO |
| **h29k-v5-1.49** | v5 主板 | 1.49" **172×320 GC9307 + 电容触控** | **1** | SDIO |
| **ht2** | — | 无 | **1** | SDIO SDR50 |

> ★ **RK3528 三款机型全是单网口** —— 只有板载 RGMII(gmac1)。
>
> H28K 与 HT2 的单口结论**有厂商 dtb 直接实证**（见 §4.8）；
> H29K 则由厂商 DTS 与上游 unifreq `rk3528-hlink-h29k.dts` 两侧印证
> （`aliases` 都只含 `ethernet0 = &gmac1`）。
>
> ★ **H28K 无板载 WiFi** —— 厂商 dtb 里 `/mmc@ffbf0000` 带 `no-sdio` 属性，
> 明确禁用 SDIO（RK3528 的 WiFi 走 sdio0）。DTS 不声明 sdio 链路，
> target 也不带 `kmod-aic8800s`。

### RK3588 — H88K / H89K（3 个机型）

| 机型 | 存储 | 屏 | 口 | 网络 |
|---|---|---|---|---|
| **h88k-v2** | combphy0_ps + SATA | — | **2** | 1×RGMII + 1×RTL8125 |
| **h88k-v3** | M.2 NVMe (pcie3x4) | SPI ST7789V | **3** | 1×RGMII + 2×RTL8125 |
| **h89k** | 无 SATA | ST7789V 135×240 rot90 | **3** | 1×RGMII + 2×RTL8125 |

> ★ `pcie3x4` **不是板载网口**。上游 `rk3588-hlink.dtsi` 注释写得很明确：
> `/* H88K v1 & v2: pcie x4 slot */`、`/* H88K V3: m.2 nvme */`。
> v2 上它是 PCIe x4 插槽位（可插扩展网卡），v3 上改跑 M.2 NVMe。

### 关于 lede 的 H29K DTS

`rk3528-hinlink-h29k.dts` 从 coolsnowwolf/lede 取，compatible 为 `hinlink,opc-h29k`，
**它的背光引脚有误**（见 §七）。仓库保留它仅作参考与映射兼容，
实际使用请选 3 份 `h29k-v*` 拆分版。

> ★ H29K 的屏幕**只保留 1.14 寸与 1.49 寸两种**。厂商的 1.9"（170×320）与
> 2.8"（240×320）变体按需求移除，对应 DTS / target / 02_network 条目已一并删除。

---

## 三、网口映射（写死，不探测）

### 枚举顺序

```
RK3568 板（GMAC 为 SoC 内部控制器，枚举固定；PCIe 按扫描顺序）
  gmac0     -> eth0    aliases ethernet0    板载 RGMII #1
  gmac1     -> eth1    aliases ethernet1    板载 RGMII #2
  rtl8125_1 -> eth2    PCIe bus 0x10
  rtl8125_2 -> eth3    PCIe bus 0x20

RK3528（gmac0/gmac1 在内核 dtsi 里默认 disabled，PCIe 网卡需显式挂 pcie-eth）
  gmac1     -> eth0    板载 RGMII
  pcie-eth  -> eth1    PCIe RTL8111HS（仅 H28K 有）

RK3588
  gmac0     -> eth0    板载 RGMII
  pcie2x1l1 -> eth1    RTL8125
  pcie2x1l2 -> eth2    RTL8125（h88k-v3 / h89k）
```

| 机型 | LAN | WAN |
|---|---|---|
| h66k | `eth1` | `eth0` |
| h68k-a / -usb | `eth1` | `eth0` |
| h68k-c / -usb / c-usb3 | `eth0 eth2 eth3` | `eth1` |
| h68k-d / -usb / new | `eth1 eth2 eth3` | `eth0` |
| h69k | `eth1 eth2` | `eth0` |
| h69k-mini | `eth1 eth2 eth3` | `eth0` |
| **h28k** | `eth0` | —（单口） |
| **h29k（全系）** | `eth0` | —（单口） |
| **ht2** | `eth0` | —（单口） |
| **h88k-v2** | `eth1` | `eth0` |
| **h88k-v3** | `eth1 eth2` | `eth0` |
| **h89k** | `eth0 eth1` | `eth2` |

---

## 四、关键硬件机制

### 4.1 2.5G 网卡的初始化责任在公共 dtsi

`rk3568-hinlink-opc.dtsi` 里 combphy 与 PCIe 控制器**已经是 okay**：

```dts
&combphy0 { status = "okay"; };
&combphy1 { status = "okay"; };
&combphy2 { status = "okay"; };

&pcie3x1 { num-lanes = <1>;
            reset-gpios = <&gpio3 RK_PA4 GPIO_ACTIVE_HIGH>;
            vpcie3v3-supply = <&vcc3v3_pi6c_05>;
            status = "okay"; };
&pcie3x2 { num-lanes = <1>;
            reset-gpios = <&gpio2 RK_PD0 GPIO_ACTIVE_HIGH>;
            vpcie3v3-supply = <&vcc3v3_pi6c_05>;
            status = "okay"; };
```

RTL8125B 是标准 PCI 设备，内核 pcie 驱动 + `kmod-r8169` 启动时自动枚举成 eth2/eth3。

⚠️ **因此 RK3568 各机型不写 `pcie-eth` 子节点** —— 写了反而可能干扰枚举顺序。
各机型只按需 `status = "disabled"` 若干控制器来控制口数。

> ★ **但 RK3528 相反**：`rk3528.dtsi` 里 `gmac0`/`gmac1` 都是 `status = "disabled"`，
> 且 PCIe 控制器**不带任何网卡子节点**。
>
> ⇒ **「控制器 status=okay」≠「有网卡」**。RK3528 上有没有网口，
> 得看 PCIe 控制器下挂没挂 `pcie-eth`，而不是看控制器状态。
> H28K 就是活例子：控制器 okay，但板上是单口。

### 4.8 H28K：厂商 dtb 三重实证「单网口」

2024 厂商固件 `QWRT-R24.07.07-rockchip-rk35xx-hinlink_h28x-squashfs-combined.img.gz`
（1 GB，MBR + squashfs）boot 分区里有两个 dtb：

| dtb | 大小 | compatible | 对应机型 |
|---|---|---|---|
| `vendor-h28x-a.dtb` | 59319 B | `hlink,h28k` | **H28K** |
| `vendor-h28x-b.dtb` | 62736 B | `hinlink,ht2` | HT2 |

★ 该固件同时提供 H28K 与 HT2 两份 dtb，是 RK3528 这一代最直接的厂商证据。

**H28K 单网口的三重实证**（任意一条都足以否定双口说法）：

```
1. 全树 pci10ec 出现 0 次          ← 没有任何 realtek 网卡节点
2. /pcie@fe4f0000 下只有 legacy-interrupt-controller
   没有任何 pcie@0,0 / pcie-eth@0,0 子节点
3. /aliases 只有 ethernet0 = /ethernet@ffbe0000（= gmac1），无 ethernet1
```

同时 `/ethernet@ffbd0000`（gmac0）`status = "disabled"`，
`/ethernet@ffbe0000`（gmac1）`status = "okay"`。

**⚠️ 这一条推翻了本仓库上一轮的做法**：
上一轮依据上游 unifreq 的 `rk3528-hlink-h28k.dts`
（其中挂了 `pcie_eth: pcie-eth@10,0 { compatible = "pci10ec,8168"; }`）
给 H28K 补了 PCIe 网卡节点并判为双口 —— **厂商 dtb 证明那是错的**。
上游那份 DTS 的 pcie-eth 可能是作者为通用 M.2 扩展位预留的，
不代表 H28K 板上真的焊了 RTL8111HS。现已移除，`EXCLUDE` 表里也剔除了 `pcie`。

**PHY 复位脚的位置也与我原先写的不一样**：

| 项 | 我原先 | 厂商 dtb |
|---|---|---|
| `phy-mode` | `rgmii-id` | **`rgmii-rxid`** |
| `tx_delay` | 未设 | **59 (0x3b)** |
| PHY 复位 | PHY 节点的 `reset-gpios` + pinctrl `gmac1_rstn_l` | **gmac1 的 `snps,reset-gpio`**（GPIO4_C2 低有效），PHY 节点上没有 reset-gpios |
| `snps,reset-delays-us` | 靠 PHY 的 `reset-assert-us`/`reset-deassert-us` | `<0 20000 100000>` |

已全部改为厂商原值。`rx_delay` 厂商 dtb 里没有（走内核 dtsi 默认）。

**WiFi**：厂商 dtb 里 `/mmc@ffbf0000` 带 `no-sdio` 属性 —— 明确禁用 SDIO。
RK3528 的 WiFi 走 sdio0，所以这是厂商自己声明「本机无 WiFi」，
与上游 `rk3528-hlink-h28k.dts` 无任何 sdio/wifi 节点一致。

**HT2 同样印证单口**：`vendor-h28x-b.dtb`（`hinlink,ht2`）同样只有一个 gmac，
与本仓库的 ht2.dts 一致。

### 4.2 SATA 与 USB3.0 二选一（仅 2022-2023 老机器）

`rk3568.dtsi` 实证：

```
sata0    phys = <&combphy0 PHY_TYPE_SATA>   (phy@fe820000)
USB3.0   同样需要 combphy0 作 PHY_TYPE_USB3
```

`PHY_TYPE_SATA=1 / PCIE=2 / USB3=4`（`dt-bindings/phy/phy.h`）。
**combphy 同一时刻只能是一种 PHY_TYPE** ⇒ 硬件互斥。

| 范围 | 是否涉及 |
|---|---|
| 2022-2023 老机器（h68k 的 a-b / c / d） | ✅ 互斥，拆 `-usb` 变体（无后缀 = SATA） |
| `h68k-c-usb3` | 本就是 USB3.0 改型，不拆 |
| 新机 `h68k-new` / `h69k` 系 | ❌ 不涉及，两者可同时使用 |

**网口数量不受影响** —— 2.5G 网卡走独立的 `pcie30phy`（`phy@fe8c0000`），与 combphy0 无关。

### 4.3 H68K GMAC 时序（跨三代固件一致）

```
gmac0(eth0): PHY 复位 gpio2_PD3 低有效,  tx_delay 0x3c, rx_delay 0x2f
gmac1(eth1): PHY 复位 gpio1_PB0 低有效,  tx_delay 0x4f, rx_delay 0x26
phy-mode = "rgmii-id"，snps,reset-delays-us = <0 20000 100000>
```

这组数值在厂商 **2022 / 2023 / 2024 三代固件 dtb 中完全一致**，且与 OpenWrt 主线相同。

> iStoreOS 用的 `0x26/0x2a` + `0x34/0x22` 是**未经厂商验证的自行调优**，本方案未采用。

复位脚采用 `&pcfg_pull_none`（与主线一致），靠外部 PHY 电路定电平，对新旧硬件都更宽容。

### 4.4 H29K 屏幕差异需要不同内核 patch

屏驱动用 `fbtft`，不同尺寸的显示偏移不同，**一份 patch 覆盖不了所有屏**：

| 屏 | patch | rotate 0/180 | rotate 90/270 |
|---|---|---|---|
| 1.14" | `9999-...-h29k-1.14.patch` | `xs+=52, ys+=40` | `xs+=40, ys+=52` |
| 1.49" | 未提供 | GC9307 + PWM 背光 | ⚠️ 需实机确认 |

> 厂商的 1.9" 偏移 patch（`9999-...-h29k-1.9.patch`）随 1.9" 变体一并移除。

### 4.5 H29K 1.49 寸触屏版是独立硬件

从厂商 2025-10 固件解出的 dtb 拿到：

| 项 | 其他 H29K | **1.49 寸触屏版** |
|---|---|---|
| 屏驱动 | `sitronix,st7789v` | **`sitronix,gc9307`** |
| 分辨率 | 135 宽 | **172×320** |
| 触控 | 无 | **`chipone,axs5106` @ I2C1(0x63)** |
| 背光 | GPIO 恒亮（gpio0_PA0） | **`pwm-backlight` 256 级（pwm3 / GPIO4_B6）** |

**背光从 GPIO 改成 PWM 是最大架构差异** —— 1.49 寸能调亮度，其他屏不能。

触控：`irq = GPIO4_B2`、`reset = GPIO4_B3`、`inverted-x` + `inverted-y`（双轴反向）。
背光：`pwms = <&pwm3 0 25000>`、`brightness-levels = 0..255`、默认亮度 153。

### 4.6 H29K v1.3 与 v5 的实质差异

260 行差异，核心是**功能增减**而非接口变化：

| | v1.3 | v5 |
|---|---|---|
| 电池电压检测 | ✗ | ✅ `adc-battery@0` 走 `saradc` 通道 1 |
| 红外接收 | ✗ | ✅ `gpio-ir-receiver` on GPIO4_PC6 |
| `&uart2`（5G 串口） | ✗ | ✅ |
| 模组 `power-gpios` | ✅ GPIO4_PB5 | ✗（不再独立控制供电） |
| 供电轨 | 含 `vcc5v0_usb` / `vcc_3v3_s3` / `vcc_1v8_s3` | 已移除 |
| 背光 pinctrl | `pull_up` | `pull_none` |

> ⚠️ v5 的电池电压读取**依赖 `9527-rockchip-rk3528-iio-add-adc.patch`**，没有它读不出数据。

### 4.7 H89K：厂商 dtb + 上游 PR 双重实证

H89K 在 2022-2025 年的多数 OpenWrt 衍生固件中**长期零适配**。
本方案从厂商 immortalwrt v1.2.2（2025-06-08）固件内解出的 dtb 重建，
并与上游 [unifreq/linux-6.1.y-rockchip PR#19](https://github.com/unifreq/linux-6.1.y-rockchip/pull/19)
提交的 `rk3588-hlink-h89k.dts` 做**逐项交叉验证**。

**网口构成**

| 项 | 值 |
|---|---|
| GMAC | `gmac0`（fe1b0000），RGMII，`tx_delay 0x42` / `rx_delay 0x34` |
| GMAC 复位 | `&pinctrl RK_PB3` 低有效，`snps,reset-delays-us = <0 20000 100000>` |
| GMAC PHY | `ethernet-phy@1`（MDIO 地址 1） |
| PCIe 网卡 ×2 | `pcie2x1l1`(fe180000) 与 `pcie2x1l2`(fe190000)，各挂一个 `pci10ec,8125` |
| PCIe 复位 | GPIO2_A0 与 GPIO5_A0，低有效 |
| PCIe 速率 | `max-link-speed = <2>`（Gen2 = 5 GT/s） |

GMAC 显式引脚（厂商 dtb 原值）：

```
gmac0_miim      GPIO4_C4 GPIO4_C5
gmac0_rgmii_bus GPIO2_A6 GPIO2_A7 GPIO2_B1 GPIO2_B2
gmac0_rgmii_clk GPIO2_B0 GPIO2_B3
gmac0_tx_bus2   GPIO2_B6 GPIO2_B7 GPIO2_C0
gmac0_rx_bus2   GPIO2_C1 GPIO2_C2 GPIO4_C2
```

**⚠️ 枚举顺序有个陷阱**：厂商 GMAC 节点带 `label = "eth2"`，
但 dtc 实际把它枚举成 `eth0`（GMAC 是 SoC 内部控制器，枚举固定）。
厂商 `02_network` 写的是 `LAN "eth0 eth1" / WAN "eth2"` ——
即**板载 RGMII 作 WAN**，两路 PCIe 作 LAN。本方案沿用厂商映射。

**屏参数：厂商 dtb ↔ 上游 PR 六项完全吻合**

| 项目 | 厂商 dtb | 上游 PR#19 | |
|---|---|---|---|
| compatible | `sitronix,st7789v` | `sitronix,st7789v` | ✓ |
| 分辨率 | 135 × 240（`0x87`×`0xf0`） | 135 × 240 | ✓ |
| rotate | `0x5a` = 90 | `<90>` | ✓ |
| buswidth | 8 | 8 | ✓ |
| spi-max-frequency | 1000000（1 MHz） | 1000000 | ✓ |
| dc-gpios | gpio1 pin4 = **GPIO1_A4** | `<&gpio1 RK_PA4 ACTIVE_HIGH>` | ✓ |
| CS | `spi4m2_cs0`（GPIO1_B3） | `&spi4m2_cs0` | ✓ |
| x/y-offset | ★ 厂商 dtb **无**此属性 | 40 / 52 | 见下 |

⇒ 屏驱动型号、分辨率、旋转、总线宽度、频率、DC 脚、CS **七项双方完全吻合**，
可确认「上游 PR#19 的 H89K 屏配置可信」。

关于 `x-offset=40 / y-offset=52`：这是**上游自己加的**，厂商 dtb 里没有。
它对应 fbtft 的 `set_addr_win` 偏移补偿 —— ST7789V 135×240 面板在 `rotate=90` 后
显存窗口需要平移才能对上实际可见区。本仓库的
`9999-fbtft-adjust-display-offset-for-rotation-h29k-1.14.patch` 正是同一机制
（1.14 寸也是 135×240，rot90 时同为 `xs+=40, ys+=52`），两边数值吻合，可交叉印证。

**其它硬件**

| 项 | 状态 |
|---|---|
| SATA | ★ **三路均 disabled** —— 厂商 dtb 里 `sata0/1/2` 与 combphy 全未使能，本机不接 SATA 座 |
| 屏 | ST7789V 135×240 rot90 @ `spi@fecb0000`，`dc-gpios` = GPIO1_A4，SPI 1 MHz，屏供电 `vcc3v0_lcd`(3.0V) |
| 风扇 | `pwm3`（febf0020） |
| 4G/5G 模组 | 供电 GPIO4_A3（5V）、复位 GPIO4_C6（3.3V） |
| 红外 | dtb 有 `ir-int-pin`（GPIO0_D4）引脚定义，但无 `gpio-ir-receiver` 节点 |

**未配置项**（厂商 dtb 中同样未启用，未擅自添加）：SATA、RTC、红外接收。

> ⚠️ **上游 PR#19 的 h89k 有个明显 bug**：`compatible = "hlink,h88k"`、
> `model = "Hlink H88K"` —— 从 h88k-v3 复制粘贴忘了改，导致
> **H89K / H88K / H88K-v3 三者 compatible 完全相同、无法区分**。
> 本 DTS 使用独立 compatible `hinlink,opc-h89k`，勿沿用上游写法。

---

## 五、仓库结构

```
target/linux/rockchip/
├── files/arch/arm64/boot/dts/rockchip/
│   ├── rk3568-hinlink-h66k.dts               无板载网口（2×GMAC disabled）
│   ├── rk3568-hinlink-h68k-a.dts             ┐
│   ├── rk3568-hinlink-h68k-a-usb.dts         │
│   ├── rk3568-hinlink-h68k-c.dts             │ 11 份 RK3568 拆分机型
│   ├── rk3568-hinlink-h68k-c-usb.dts         │
│   ├── rk3568-hinlink-h68k-c-usb3.dts        │
│   ├── rk3568-hinlink-h68k-d.dts             │
│   ├── rk3568-hinlink-h68k-d-usb.dts         │
│   ├── rk3568-hinlink-h68k-new.dts           │
│   ├── rk3568-hinlink-h69k-3eth.dts          │
│   ├── rk3568-hinlink-h69k-mini.dts          ┘
│   ├── rk3568-hinlink-opc.dtsi               RK3568 公共设备树（来自主线）
│   ├── rk3528-hinlink-h28k.dts               单口（厂商 dtb 实证，无 WiFi）
│   ├── rk3528-hinlink-ht2.dts                单口（厂商 dtb 实证）
│   ├── rk3528-hinlink-h29k.dts               lede 版本（背光有误，仅参考）
│   ├── rk3528-hinlink-h29k-v1.3-1.14.dts     ┐
│   ├── rk3528-hinlink-h29k-v5-1.14.dts       │ 3 份 H29K 真实变体
│   ├── rk3528-hinlink-h29k-v5-1.49.dts       ┘ 触屏版
│   ├── rk3588-hinlink-h88k-v2.dts            ┐
│   ├── rk3588-hinlink-h88k-v3.dts            │ 3 份 RK3588
│   ├── rk3588-hinlink-h89k.dts               ┘ 厂商 dtb + 上游 PR 双重实证
│   ├── rk3588-hinlink.dtsi  + 5 个私有 dtsi   ← iStoreOS 私有，须连带移植
│   ├── vendor-h28x.dtb                       厂商原始 dtb（H28K + HT2 溯源）
│   ├── vendor-h29k-v5-1.49.dtb               厂商原始 dtb（H29K 1.49 寸溯源）
│   └── vendor-h89k.dtb                       厂商原始 dtb（H89K 溯源）
│
├── armv8/base-files/etc/board.d/
│   ├── 02_network                            网口映射（写死，不探测）
│   └── 01_leds                               LED 定义
│
└── image/armv8.mk.hinlink                    设备定义片段（追加到 armv8.mk）

patches/                                      4 份内核 patch（H29K 必需）
docs/APPLY.md                                 应用步骤（方案 A / B）
tools/                                        生成器 + 校验器 + DTB 解析器
```

### 依赖的私有 dtsi

H88K 依赖 `rk3588-hinlink.dtsi`（immortalwrt 6.18 内核中没有），它又引用同目录 5 个：

| 文件 | 大小 |
|---|---|
| `rk3588-hinlink.dtsi` | 15970 B |
| `rk3588-rk806-single.dtsi` | 8333 B |
| `rk3588s-ip.dtsi` | 592 B |
| `rk3588s-ip-supply.dtsi` | 575 B |
| `rk3588-hdmirx.dtsi` | 443 B |
| `rk3588-ramoops.dtsi` | 290 B |

来源：[istoreos/istoreos](https://github.com/istoreos/istoreos)
`target/linux/rockchip/dts/rk3588/`。`rk3588.dtsi` 用内核自带版本即可（166 B，只 include extra + opp）。

---

## 六、内核 patch

| patch | 用途 | 必需性 |
|---|---|---|
| `9527-rockchip-rk3528-iio-add-adc.patch` | 给 `rockchip_saradc.c` 加 `rockchip,rk3528-saradc` 驱动 + 4 通道 IIO 芯片 | **H29K v5 必需**（电池电压） |
| `9528-linux-delfbcon-cursor.patch` | `fb_flashcursor()` / `fbcon_cursor()` 开头 `return`，禁 framebuffer 硬件光标 | 建议 |
| `9999-fbtft-...-h29k-1.14.patch` | 1.14 寸屏显示偏移补偿（H29K + H89K 都用它） | H29K 1.14" / H89K 必需 |

---

## 七、验证状态

| 项目 | 状态 |
|---|---|
| DTS 语法结构（20 份） | ✅ 17/20 PASS（3 份失败均为**既存**的版本错配，见下） |
| 口数与板级映射一致 | ✅ **20/20** 机型 OK（RK3568 + RK3528 + RK3588） |
| 设备定义 ↔ DTS 文件对齐 | ✅ 无孤儿、无缺失 |
| `compatible` 唯一性 | ✅ 全部唯一 |
| 厂商 DTB ↔ 上游 DTS 交叉验证 | ✅ H89K 屏 7 项吻合；H28K / H66K / H68K 网络构成吻合 |
| dtc 完整编译 | ❌ **未验证** |
| phandle 交叉引用 | ❌ 未验证 |
| 实机启动 | ❌ 未验证（无实机） |

> 语法校验用真实内核 6.18 的 include 树跑的：
> `python3 tools/dts_syntax_check.py <dts> <hinlink目录> <kernel>/include <kernel>/include/dt-bindings/input <kernel>/arch/arm64/boot/dts <kernel>/arch/arm64/boot/dts/rockchip`

### ⚠️ 3 份 DTS 存在版本错配（H88K，非本轮引入）

`rk3588s-ip.dtsi`（来源 jjm2473 / unifreq）末尾 include 了 4 个文件：

```dts
#include "rk3588s-vpu.dtsi"
#include "rk3588s-gpu.dtsi"
#include "rk3588s-npu.dtsi"
#include "rk3588s-crypto.dtsi"
```

但 **Linux 6.18 已把这 4 个文件合并进 `rk3588-extra.dtsi`**（内含
`rk3588-base.dtsi` + `rk3588-extra-pinctrl.dtsi`），旧的 `rk3588s-*.dtsi`
在 torvalds/linux 与 immortalwrt 树里都已 404。

⇒ **H88K v2 / v3 在 6.18 上会因找不到这 4 个文件而编译失败**。
H89K 不受影响（直接 include `rk3588.dtsi`，不经过 `rk3588s-ip.dtsi`）。

这是移植 iStoreOS 私有 dtsi 时带进来的既存问题，本轮未擅自改动 ——
删掉 include 需确认 VPU/GPU/NPU/crypto 节点是否已有替代来源（应由
`rk3588-extra.dtsi` 提供），建议在 buildroot 里实测一轮后决定：
- 若 `rk3588-extra.dtsi` 已覆盖这些节点 ⇒ 直接删掉 4 行 include；
- 若不能覆盖 ⇒ 需要把 unifreq 版的 `rk3588s-ip.dtsi` 里
  rockchip_system_monitor / otp 节点拆出来单独成文件。

### 本轮交叉验证抓出的真实缺陷

`check_port_count.py` 与上游 DTS 逐项比对，发现并修复了 5 个会导致用户配置错乱的 bug：

| # | 缺陷 | 后果 |
|---|---|---|
| 1 | `02_network` 里 H89K 出现在**两个** case 分支 | 命中的是 H88K 的四口映射，H89K 三口机被配成四口，WAN 指向不存在的 `eth3` |
| 2 | H29K / HT2 映射了 `eth0 eth1`，但 DTS 只有 `gmac1` | `eth1` 不存在，WAN 可能配到空接口 |
| 3 | H88K v2/v3 映射四口，但 `pcie3x4` 是 PCIe x4 插槽位 / M.2 NVMe | 多配 1~2 个不存在的口 |
| 4 | H28K DTS 只使能了 `&pcie` 控制器，**没挂 `pcie-eth` 子节点** | RK3528 的 PCIe 控制器不带网卡节点，不会枚举出 eth1，实际只有 1 个口 |
| 5 | `h29k-v5-1.49` 的 compatible 在 02_network 写成 `h29k-v5-5-1.49`（DTS 里是 `hinlink,h29k-v5-149`） | 1.49 寸版匹配不到网口映射 |
| 6 | **上一轮据上游 DTS 给 H28K 补的 `pcie-eth`（RTL8111HS）是错的** —— 厂商 2024 固件 dtb 三重实证无此网卡 | H28K 被误判为双口，`eth1` 永远不存在 |

同时修正了 `check_port_count.py` 自身的 4 个缺陷（否则上面这些根本查不出来）：
只取第一个 compatible、续行顶格时正则贪婪吞掉整个分支、
「节点存在但无 status」被误判为 okay、以及未区分「板载网口」与
「PCIe 插槽位 / 无网卡的控制器」（`pcie3x4` 与 H28K 的 `pcie`）。

### ★ 一条方法论教训

第 6 条缺陷的成因值得记下来：**上一轮把上游开源 DTS 当成了硬件事实，
而厂商固件 dtb 才是事实**。上游 `rk3528-hlink-h28k.dts` 里那条
`pcie-eth@10,0 { compatible = "pci10ec,8168"; }` 很可能是作者为
**通用 M.2 扩展位**预留的模板，并不对应 H28K 板上真实焊的器件。

⇒ 本仓库的纪律应当是：**厂商 dtb > 厂商 DTS > 上游开源 DTS**。
只有在拿不到厂商 dtb 时才用上游 DTS，且必须在 README 里标注这是二手推断。

### 为什么 dtc 完整编译未验证

测试环境的 dtc 1.7.2（2020 年）**连主线官方 `rk3568.dtsi` 都编译失败** ——
用主线原生 DTS 做对照组，同样失败，所以是环境问题而非代码问题。
改用自写预处理器校验语法，并**先用主线 DTS 校准检查器**。

⚠️ 语法检查器**不覆盖 phandle 交叉引用**。建议在 buildroot 里
`make target/compile` 实测一轮。

### ⚠️ 发现上游 DTS 的错误

**coolsnowwolf/lede 的 `rk3528-opc-h29k.dts` 背光引脚有误**：

| 来源 | 背光 GPIO | 极性 |
|---|---|---|
| 厂商 5 份 DTS 全部 | `gpio0 RK_PA0` | `GPIO_ACTIVE_LOW` |
| coolsnowwolf/lede | `gpio0 RK_PA1` | `GPIO_ACTIVE_HIGH` |

引脚与极性都不同，lede 那份会导致**背光不亮或反向**。
本方案 3 份 H29K DTS 全部采用厂商原值 `PA0 / ACTIVE_LOW`。

lede 那份还是**混合体**：有红外接收（v5 特征）但无电池 ADC（v1.3 特征），
且 panel 完全没有 width/height/rotate 配置 —— 更像厂商某个中间版本。
仓库保留该文件仅作参考，**不建议用于生产**。

### 需实机确认

1. **H89K 屏显示是否偏移** —— 上游用 `x-offset=40 / y-offset=52`，
   需确认本仓库的 fbtft 1.14 寸 patch 在 H89K 上是否同样生效。
2. **H28K 的 M.2 扩展位** —— 厂商 dtb 里 PCIe 控制器 okay 但无网卡。
   若你的 H28K 插了 M.2 网卡（RTL8111/8125），插上后 `ls /sys/class/net/`
   应出现 eth1，此时需给 H28K 补一条 02_network 分支。
3. **H29K 是否真的只有 1 个网口** —— H28K 已有厂商 dtb 实证，
   但 H29K 只有厂商 DTS 与上游 DTS 两侧印证（都只含 `ethernet0`），
   没有厂商 dtb。插上网线看 `ls /sys/class/net/` 即可确认。
4. **老机器 a-b 的 PHY 复位是否稳定** —— `pull_none` 依赖外部电路定电平。
5. **各机型 LED 颜色与闪烁规则**。
6. **1.49 寸屏用哪份 fbtft 偏移 patch** —— 厂商只给了 1.9 与 1.14 两份，1.49 未提供。
7. **H29K v5 的 5G 模组电源** —— 抄 iStoreOS 的 GPIO0_PC0 + 2s 启动延时。

取证命令：

```sh
ls /sys/class/net/                                  # 实际几个 ethN
for p in /sys/class/net/eth*; do ethtool -i $p | grep -E "driver|bus-info"; done
find /sys/bus/mdio_bus/devices/ -name phy_id -exec sh -c 'echo "$1 => $(cat "$1")"' _ {} \;
dmesg | grep -iE "gmac|ethernet|phy|combphy|saradc|pcie"
```

---

## 八、工具

| 脚本 | 用途 |
|---|---|
| `tools/check_port_count.py` | **口数自检**：交叉校验 DTS 网口构成与 `02_network` 映射 |
| `tools/dts_syntax_check.py` | 离线 DTS 结构校验（括号平衡、include 完整性） |
| `tools/fdtdump.py` | **DTB 反解析**：把厂商 dtb 的节点/属性 dump 成可读文本，查证硬件参数 |
| `tools/gen_hinlink.py` | RK3568 机型 DTS 生成器 |
| `tools/gen_hinlink_35xx.py` | RK3528 / RK3588 机型 DTS 生成器 |

生成器是 DTS 的可读来源；直接改 DTS 也可以，但改完请跑校验脚本。

### 使用 fdtdump.py 查证硬件参数

厂商 dtb 是本方案唯一的参数来源。`fdtdump.py` 无需 dtc，纯 Python 解析 FDT：

```sh
python3 tools/fdtdump.py vendor-h89k.dtb spi@fecb0000   # 按路径过滤
```

典型用途：确认某个 GPIO 到底是哪一 bank's 哪一位、某个 regulator 挂在哪路电源上。
本轮用它纠正了 README 里 `dc-gpios` 从 `GPIO1_D4` 误记为 **`GPIO1_A4`** 的错误；
在 H28K 上更直接地证明了「上游 DTS 的 pcie-eth 是错的」。

### 从厂商 img 固件里挖 dtb

厂商固件是 combined img（MBR + squashfs），dtb 在 boot 分区里。流程：

```sh
gunzip -kf firmware.img.gz                 # 1 GB 镜像，trailing garbage 可忽略
# 读 MBR 找 boot 分区（本例：part1 start=65536 sector = 32 MB）
# 在该分区内搜 FDT magic d00dfeed，本例命中 0x1211000 与 0x1220000
# 读 header 的 totalsize 字段截出完整 dtb
python3 tools/fdtdump.py vendor-h28x.dtb "/aliases"     # 确认是哪个机型
```

2024 那份 `hinlink_h28x` 固件一个镜像里就带了两份 dtb（H28K + HT2），
是 RK3528 这一代最省事的证据来源。

### 使用 check_port_count.py 时注意

它的口数计算**必须以 dtsi 作基线**：

```
pcie3x1 / pcie3x2 在 DTS 里通常没有显式节点，
继承 rk3568-hinlink-opc.dtsi（dtsi 里两者都 status="okay"）。
只扫 DTS 会把四网口机误判成两网口。
```

但**插槽位要显式剔除**：`pcie3x4` 在 `rk3588-hinlink.dtsi` 里是 okay 的，
可它在 H88K 上是 PCIe x4 插槽位 / M.2 NVMe 位，不是板载网口 ——
所以 `EXCLUDE` 表里按机型剔除了它。这正是它能抓出 H88K 四口映射错误的原因。

---

## 九、数据来源

所有硬件参数均来自厂商原始固件的 dtb（解包反编译，逐项核对），
并与上游开源 DTS 双向交叉验证：

| 来源 | 提供的机型 / 信息 |
|---|---|
| 2022 厂商固件 ×5（`R22.7.19` / `R22.8.22`） | h68k a-b / c / d-f / c-usb3 |
| 2023 厂商固件（`R23.4.20`） | h68k-d |
| 2024 厂商固件（`QWRT-R24.07.07`） | h68k / h69k 硬件定义 |
| **2024 厂商固件（`QWRT-R24.07.07-...-hinlink_h28x`，1 GB）** | **h28k + ht2**（boot 分区含两份 dtb，已归档 `vendor-h28x.dtb`） |
| 2025 厂商固件（`H29K-NEW-UI-20251029`） | **h29k v5 1.49 寸触屏版** |
| 2025 厂商固件（`immortalwrt-v1.2.2-20250608-...h89k`） | **h89k** |
| H29K 设备树 ×5 + patch ×4（用户提供） | h29k v1.3 / v5 各屏尺寸 |
| 上游 `coolsnowwolf/lede` | **h66k** / ht2 / h28k / h29k 参考 |
| 上游 `istoreos/istoreos` | h88k v2 / v3 |
| 上游 `unifreq/linux-6.1.y-rockchip` | **h89k 屏参数交叉验证**、h28k 的 `pcie-eth` 写法、h66k / h68k / h69k 网络构成 |
| 上游 OpenWrt 主线 + Linux 内核 | `rk3568-hinlink-h68k.dts`、`rk3568-hinlink-opc.dtsi`、`rk3528.dtsi` 蓝本 |

> ⚠️ **compatible 前缀历史上有 5 种**：`ink`（厂商 22-24 年）、`hinlink`、
> `hlink`、`linkstar`、`rockchip`。本仓库统一用 `hinlink,`，
> 但 `02_network` 里**同时保留**了 `hlink,` / `linkstar,` 别名分支 ——
> 因为上游 unifreq 与 lede 的 H28K 用的是 `hlink,h28k`，
> 刷那些固件时不会被本仓库的映射漏掉。

### 上游还有几个 HinLink 机型未纳入

`unifreq/linux-6.1.y-rockchip` 里还有这些 HinLink 相关 DTS，本轮**只作参考、未适配**，
因为缺少厂商 dtb 交叉验证（不满足本仓库「参数必须可溯源」的纪律）：

| 文件 | 机型 | 状态 |
|---|---|---|
| `rk3568-hlink-ht3.dts` | HT3（NAS，4 盘位 + RTC + 风扇） | 未适配 |
| `rk3568-hinlink-hnas.dts` | HNAS（同 HT3 硬件，`compatible = "hinlink,hnas"`） | 未适配 |
| `rk3588-hlink-ac88.dts` | AC88 | 未适配 |
| `rk3588-hlink-th88.dts` | TH88 | 未适配 |
| `rk3588-hinlink-h88k-v31.dts` | H88K **V3.1**（`compatible = "hlink,h88k-v31"`） | 未适配 |
| `rk3566-hlink-netfusion.dts` | 非 RK3568，非本方案范围 | 不适用 |

> `rk3588-hlink-h88k-v31.dts` 值得注意：它是 H88K V3.1，`compatible` 三段式
> `hlink,h88k-v31` / `hlink,h88k-v3` / `rockchip,rk3588`，与本仓库的
> `hinlink,h88k-v3` 是不同硬件。若你有 V3.1 的机器，需要单独适配。

---

## 十、授权

本仓库为补丁集合，遵循上游 OpenWrt / Linux 内核的 GPL-2.0。
厂商 DTS 的著作权归 HinLink（芯联）所有，此处仅作适配依据引用。
