# immortalwrt — HinLink 全设备线适配

HinLink（芯联）全系列路由器在 immortalwrt 上的设备树与板级配置。
**按硬件变体一机一档，不做运行时自适应探测** —— 每个 `compatible` 对应一份独立
DTS，`02_network` 里 `ethN` 映射写死。

- **18 个机型** · 19 份 DTS · 7 份 dtsi · 2 份内核 patch · 6 个工具脚本 · 3 份厂商 dtb
- 覆盖 RK3568（H66K / H68K / H69K）、RK3528（H28K / H29K / HT2）、RK3588（H88K / **H89K**）

> 本仓库是**支线仓库**，只提供补丁文件，不含完整 OpenWrt 源码。
> 应用方式见 [`docs/APPLY.md`](docs/APPLY.md)。
> **特殊硬件（屏 / 风扇 / WiFi / 5G 模组 IO）逐项清单见 [`docs/HARDWARE.md`](docs/HARDWARE.md)**。

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

# 4. 内核 patch
cp patches/*.patch <immortalwrt>/target/linux/rockchip/patches-6.18/

# 5. U-Boot：打入上游 openwrt 的 HINLINK 支持（★ 出固件必需，见 §七）
cp patches-uboot/upstream/*.patch <immortalwrt>/package/boot/uboot-rockchip/patches/
patch -p1 -d <immortalwrt>/package/boot/uboot-rockchip < patches-uboot/0001-*.patch

# 6. 编译
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
这类错误 DTS 语法检查查不出来 —— 本仓库自身就靠它抓出过 4 个真实缺陷（见 §八）。

---

## 二、机型矩阵

### RK3568 — H66K / H68K / H69K（10 个机型）

| 机型 | 年份/定位 | 口数 | 网络构成 | 板载 WiFi | 存储口 |
|---|---|---|---|---|---|
| **h66k** | 无板载网口 | 2 | **0×GMAC** + 2×RTL8125 | — | SATA |
| **h68k-a** | 2022 双千兆 | 2 | 2×GMAC | AP6256 | **SATA** |
| h68k-a-usb | 同上 | 2 | 2×GMAC | AP6256 | USB3.0 |
| **h68k-c** | 2022 四网口 | 4 | 2×GMAC + 2×RTL8125 | M.2 | **SATA** |
| **h68k-c-usb3** | 2022/2022.8 USB3.0 改型 | 4 | 2×GMAC + 2×RTL8125 | M.2 | USB3.0 |
| **h68k-d** | 2023.4 推荐版 | 4 | 2×GMAC + 2×RTL8125 | M.2 | **SATA** |
| h68k-d-usb | 同上 | 4 | 2×GMAC + 2×RTL8125 | M.2 | USB3.0 |
| **h68k-new** | 2023末~2024 | 4 | 2×GMAC + 2×RTL8125 | AIC8800 | USB3 + SATA |
| **h69k** | 装 USB 5G 模组 | **3** | 1×GMAC + 2×RTL8125 | AIC8800 | USB3 + SATA |
| **h69k-mini** | = **H68K max** | **4** | 2×GMAC + 2×RTL8125 | AIC8800 | USB3 + SATA |

**命名约定**（OpenWrt / lede / iStoreOS 互认）：**无后缀 = SATA，`-usb` = USB3.0**。

> ★ **已合并的重复机型**：`h68k-c-usb`（2022 C/D/F 的 USB3.0 变体）与
> `h68k-c-usb3`（2022.8 的 c-usb3 改型）—— 两者 DTS 硬件配置完全相同，
> 都是「C/D/F 基础上把 SATA 口改成 USB 3.0」，且 `02_network` 映射一致。
> 现合并为一份 `rk3568-hinlink-h68k-c-usb3.dts`，用两个 compatible 区分：
> `hinlink,opc-h68k-c-usb3` 与 `hinlink,opc-h68k-c-usb`。
>
> ★ **刻意不合并的重复**：`h68k-c` / `h68k-d`、`h68k-c-usb3` / `h68k-d-usb`
> 这两组的 DTS 硬件配置也完全相同，但 **WAN 口位置不同**：
>
> ```
> c 系（2022）  LAN eth0 eth2 eth3 / WAN eth1
> d 系（2023.4）LAN eth1 eth2 eth3 / WAN eth0
> ```
>
> 厂商确实当两个机型卖，WAN 插在不同的物理口上 —— 属实质硬件差异，
> 合并会导致其中一代机器的 WAN 接错口。**保持独立。**

### RK3528 — H28K / H29K / HT2（5 个机型）

| 机型 | 版本 | 屏 | 口 | 板载 WiFi |
|---|---|---|---|---|
| **h28k** | — | 无 | **2**：RGMII + PCIe | **无** | 8G eMMC + TF 卡 |
| **h29k-v1.3-1.14** | v1.3 主板 | 1.14" 135×240 rot270 | **1** | SDIO | — |
| **h29k-v5-1.14** | v5 主板 | 1.14" 135×240 rot90 | **1** | SDIO | — |
| **h29k-v5-1.49** | v5 主板 | 1.49" **172×320 GC9307 + 电容触控** | **1** | SDIO | — |
| **ht2** | — | 无 | **1** | SDIO SDR50 | — |

> ★ **H29K 全系与 HT2 是单网口** —— 只有板载 RGMII(gmac1)，DTS 里没有 PCIe 节点。
> HT2 有厂商 dtb 直接实证（`vendor-h28x.dtb` 里的 `hinlink,ht2` 同样只有一个 gmac）；
> H29K 则由厂商 DTS 与上游 unifreq `rk3528-hlink-h29k.dts` 两侧印证
> （`aliases` 都只含 `ethernet0 = &gmac1`）。
>
> ★ **H28K 是双网口**：板载 RTL8211F RGMII + PCIe RTL8111H，
> 依据 HinLink 官网产品页（详见 §4.8）。
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
**它的背光引脚有误**（见 §八）。仓库保留它仅作参考与映射兼容，
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
| h68k-c / c-usb / c-usb3 | `eth0 eth2 eth3` | `eth1` |
| h68k-d / -usb / new | `eth1 eth2 eth3` | `eth0` |
| h69k | `eth1 eth2` | `eth0` |
| h69k-mini | `eth1 eth2 eth3` | `eth0` |
| **h28k** | `eth0` | `eth1` |
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

### 4.8 H28K：PCIe 网卡不在 DT 里，是靠 PCI 枚举出来的

2024 厂商固件 `QWRT-R24.07.07-rockchip-rk35xx-hinlink_h28x-squashfs-combined.img.gz`
（1 GB，MBR + squashfs）boot 分区里有两个 dtb：

| dtb | 大小 | compatible | 对应机型 |
|---|---|---|---|
| `vendor-h28x-a.dtb` | 59319 B | `hlink,h28k` | **H28K** |
| `vendor-h28x-b.dtb` | 62736 B | `hinlink,ht2` | HT2 |

★ 该固件同时提供 H28K 与 HT2 两份 dtb，是 RK3528 这一代最直接的厂商证据。

**H28K 是双网口**（HinLink 官网产品页「我们的产品优势」）：

```
网口1   RTL8211F  RGMII 千兆
网口2   RTL8111H  PCIe 千兆
DDR     1GB / 2GB / 4GB
eMMC    8G 板载
TF 卡   接口 x1，最大支持 512GB
供电    Type-C 5V2A / 12V1A
```

**★ 一个重要的反直觉事实：DT 里找不到网卡，不代表板上没有网卡。**

厂商 dtb 里是这样：

```
/pcie@fe4f0000   status = "okay"
                 phys = <&phy@ffdc0000>   phy-names = "pcie-phy"
                 num-lanes = <1>   max-link-speed = <2>
                 子节点只有 legacy-interrupt-controller —— 没有网卡
/phy@ffdc0000    compatible = "rockchip,rk3528-naneng-combphy"
                 status = "okay"          ← combphy 作 PCIe PHY
全树 pci10ec 出现 0 次
/aliases         只有 ethernet0 = /ethernet@ffbe0000（gmac1）
```

**这三条「没有网卡」的证据全部成立，但结论是错的** —— H28K 确实有 PCIe 千兆口。

原因：**RTL8111H 是标准 PCI 设备**。PCIe 控制器一旦使能（`status="okay"`）
且 PHY 链路通（combphy 作 `pcie-phy`），内核 pcie 驱动枚举 bus 时就会自动
发现它、按 PCI ID `10ec:8168` 绑定 `r8169` 驱动。
**DT 里本来就不需要声明网卡节点**，写了反而多余。

所以正确做法与 RK3568 各机型一致：**不写 `pcie-eth`，靠 PCI 枚举**。
`kmod-r8169` 由此成为 H28K 的必需包。

> ⚠️ 本仓库曾在这一节得出「H28K 是单网口」的结论，是**推理错误**：
> 把「厂商 dtb 里没有网卡节点」当成了「板上没有网卡」。
> 校验器也曾据此把 H28K 判成 1 口。两者都已纠正。

**PHY 参数（厂商 dtb 原值，已全部采用）**：

| 项 | 厂商 dtb |
|---|---|
| `phy-mode` | **`rgmii-rxid`** |
| `tx_delay` | **59 (0x3b)** |
| PHY 复位 | **gmac1 的 `snps,reset-gpio`**（GPIO4_C2 低有效）+ `snps,reset-delays-us = <0 20000 100000>`；PHY 节点上**没有** reset-gpios |
| `rx_delay` | 厂商 dtb 无此属性，走内核 dtsi 默认 |
| gmac0 | `status = "disabled"`（不用） |

**存储（与官网「8G 板载 eMMC + TF 卡 x1」对应）**：

| 控制器 | 厂商 reg | 角色 | 关键属性 |
|---|---|---|---|
| `sdhci` | `mmc@ffbf0000` | 板载 8G eMMC | `bus-width=8`、`mmc-hs200-1_8v`、`non-removable`、`no-sd`、`no-sdio`、`max-frequency=200000000` |
| `sdmmc` | `mmc@ffc30000` | TF 卡槽 | `bus-width=4`、`cap-sd-highspeed`、`supports-sd`、`disable-wp`、`max-frequency=150000000`、`rockchip,use-v2-tuning` |

⚠️ **mmc 别名顺序已按厂商纠正**：厂商是 `mmc0 = sdmmc(TF卡)`、
`mmc1 = sdhci(eMMC)`；本仓库原写成 `mmc0 = sdhci / mmc1 = sdmmc`，与厂商相反。
固件安装脚本按 `mmc0` 找外置存储，顺序反了会导致「TF 卡插了不被识别」。

**WiFi**：厂商 dtb 里 `/mmc@ffbf0000` 带 `no-sdio` 属性 —— 明确禁用 SDIO。
RK3528 的 WiFi 走 sdio0，所以这是厂商自己声明「本机无 WiFi」，
与官网规格表（无 WiFi 项）及上游 `rk3528-hlink-h28k.dts` 无 sdio 节点三方一致。

**LED（厂商 dtb 原值，均为 gpio4 低有效）**：

| 节点 | 引脚 | label | 本仓库触发 |
|---|---|---|---|
| `led-work` | GPIO4_B7 | `green:work` | `heartbeat`（与厂商一致） |
| `led-yellow` | GPIO4_C1 | `yellow:led3` | 由 `01_leds` 按 netdev 接管 |
| `led-blue` | GPIO4_C0 | `blue:led4` | 同上 |

官网规格写「4 颗灯，包括电源指示灯」，但厂商 dtb 只有 3 颗 ——
第 4 颗电源灯应是常亮硬件，不经 GPIO 控制。

**HT2 是单网口**：`vendor-h28x-b.dtb`（`hinlink,ht2`）同样只有一个 gmac、
同样没有 PCIe 控制器，与本仓库的 ht2.dts 一致。官网未列 HT2 参数，
但厂商 dtb 已足够证明它与 H28K 不同。

### 4.9 ★「DT 里没有网卡节点」≠「板上没有网卡」

这是本项目最值得记住的一条判据（来源：H28K 的三次反转）。

| 场景 | DT 里写不写网卡节点 | 原因 |
|---|---|---|
| RK3568（H66K/H68K/H69K） | **不写** | RTL8125 是标准 PCI 设备，靠枚举 |
| RK3528 H28K | **不写** | 同上，RTL8111H 靠枚举 |
| RK3588 H88K/H89K | **写** `pcie-eth` | 沿用 iStoreOS 私有 dtsi 的写法 |

判断网口数量时，**只看「该机型有没有使能对应的 PCIe 控制器」**，
不要去数 DT 里有几个 `pci10ec` / `pcie-eth` 节点。

```sh
# 正确的查法：看控制器与 PHY 是否使能
grep -A5 "&pcie"  <dts>          # status 是否 okay
grep -A3 "combphy" <dts>         # PHY 链路是否通
# 交叉验证：官网/产品页的规格表最直接
```

⚠️ 反例（本仓库踩过）：RK3588 的 `pcie3x4` 在 dtsi 里是 `okay`，
但它是 PCIe x4 **插槽位**（H88K v1/v2）或 M.2 NVMe 位（H88K v3）——
这种「控制器使能但不是板载网口」的情况，才需要显式排除。

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

> ✅ v5 的电池电压读取**不需要 patch** —— Linux 6.18 上游已原生支持
> `rockchip,rk3528-saradc`（含4 通道 IIO），内核 `rk3528.dtsi` 里也已声明该
> compatible。本仓库早期的 `9527-...-iio-add-adc.patch` 已删除。

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
│   ├── rk3568-hinlink-h68k-c.dts             │ 10 份 RK3568 拆分机型
│   ├── rk3568-hinlink-h68k-c-usb3.dts        │ （c-usb 与 c-usb3 已合并）
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

patches/                                      2 份内核 patch（已验证干净应用）
patches-uboot/                                ★ U-Boot：上游 patch 存档 + Makefile 改动
├── upstream/106-...HINLINK-H66K-H68K.patch   openwrt/main 原文：H66K/H68K u-boot
├── upstream/107-...HINLINK-H28K.patch        openwrt/main 原文：H28K u-boot
├── 0001-...register-hinlink-devices.patch    给 uboot-rockchip/Makefile 登记 8 个变体
├── 108-...add-hinlink-h29k-ht2.patch         H29K / HT2 的板级 dts + overlay + defconfig
└── 109-...add-hinlink-rk3588-uboot.patch     H88K v2/v3、H89K 的板级 dts + overlay + defconfig
docs/APPLY.md                                 应用步骤（方案 A / B）
docs/HARDWARE.md                             ★ 特殊硬件清单（屏/风扇/WiFi/5G 模组 IO）
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

只有 **2 份** patch，都已验证 `patch -p1` 可干净应用到 Linux 6.18（无 fuzz、无 offset）。

| patch | 用途 | 必需性 |
|---|---|---|
| `9999-fbtft-read-display-offset-from-dt.patch` | fbtft 从 DT 读显示偏移（`x-offset` / `y-offset` / `x-offset-0` / `y-offset-0`），替代按机型硬编码的 switch | H29K 1.14" / H89K 必需 |
| `9528-linux-delfbcon-cursor.patch` | `fb_flashcursor()` / `fbcon_cursor()` 开头 `return`，禁framebuffer 硬件光标 | 建议（SPI 小屏上硬件光标会错位） |

**已删除的 patch**：

| ~~patch~~ | 原因 |
|---|---|
| ~~`9527-rockchip-rk3528-iio-add-adc.patch`~~ | **6.18 上游已原生支持** `rockchip,rk3528-saradc`（`rockchip_saradc.c` 里已有 `rockchip_rk3528_saradc_data` + of_match_table 条目，内核 `rk3528.dtsi` 里也已声明该compatible）。只需 `kmod-iio-adc-rk3528` 让用户态能读。 |
| ~~`9999-fbtft-...-h29k-1.14.patch`~~ | 被 `9999-fbtft-read-display-offset-from-dt.patch` 取代 —— 偏移量改为从 DT 读，同一份内核可同时支持 H29K（rotate 270）与 H89K（rotate 90），而硬编码 switch 无法区分。 |
| ~~`9999-fbtft-...-h29k-1.9.patch`~~ | 1.9 寸变体已随机型精简移除。 |

验证方法：

```sh
cd <kernel>
patch -p1 --dry-run < <仓库>/patches/9999-fbtft-read-display-offset-from-dt.patch
```

> ⚠️ `9528` 需注意：6.18 里 `fbcon_cursor()` 的第二个参数已从 `int mode`
> 改成 `bool enable`。旧版 patch 的上下文过时会导致 **fuzz 2** 应用，
> 本仓库的版本已按 6.18 实际原型重写。

---

## 七、U-Boot

### 全机型覆盖（8 个变体，均已实编译通过）

| 变体 | SoC | 覆盖机型 | 来源 |
|---|---|---|---|
| `hinlink-h28k-rk3528` | RK3528 | H28K | **上游** openwrt `patches/107` |
| `hinlink-h29k-rk3528` | RK3528 | H29K v1.3-1.14 / v5-1.14 / v5-1.49 | **本仓库自建** `patches-uboot/108` |
| `hinlink-ht2-rk3528` | RK3528 | OPC-HT2 | **本仓库自建** `patches-uboot/108` |
| `hinlink-h66k-rk3568` | RK3568 | OPC-H66K | **上游** `patches/106` |
| `hinlink-h68k-rk3568` | RK3568 | H68K a / a-usb / c / c-usb3 / d / d-usb / new<br>+ H69K + H69K-mini | **上游** `patches/106` |
| `hinlink-h88k-v2-rk3588` | RK3588 | OPC-H88K V2 | **本仓库自建** `patches-uboot/109` |
| `hinlink-h88k-v3-rk3588` | RK3588 | OPC-H88K V3 | **本仓库自建** `patches-uboot/109` |
| `hinlink-h89k-rk3588` | RK3588 | OPC-H89K | **本仓库自建** `patches-uboot/109` |

设备定义里统一写 `UBOOT_DEVICE_NAME := <上表的变体名>` —— **18 个机型全部覆盖**，
没有任何机型再留 `BOOT_FLOW :=` 空。

### 上游已有的部分（H28K / H66K / H68K）

上游 `openwrt/openwrt` 的 `package/boot/uboot-rockchip/` 里本来就有这三个：

```
define U-Boot/hinlink-h28k-rk3528   $(U-Boot/rk3528/Default)
define U-Boot/hinlink-h66k-rk3568   $(U-Boot/rk3568/Default)
define U-Boot/hinlink-h68k-rk3568   $(U-Boot/rk3568/Default)
```

对应 defconfig 与 u-boot dts 由 `patches/106`（H66K/H68K）与 `patches/107`（H28K）
提供，两个 patch 原样存档在 `patches-uboot/upstream/`：

```
106 →  arch/arm/dts/rk3568-hinlink-{h66k,h68k}-u-boot.dtsi   (overlay)
       configs/hinlink-{h66k,h68k}-rk3568_defconfig

107 →  arch/arm/dts/rk3528-hinlink-h28k-u-boot.dtsi
       configs/hinlink-h28k-rk3528_defconfig
       dts/upstream/src/arm64/rockchip/rk3528-hinlink-h28k.dts   ← 自带板级 dts
```

> H66K / H68K 的板级 dts 不用 patch 带 —— u-boot 2026.07 的
> `dts/upstream/src/arm64/rockchip/` 里已经有 `rk3568-hinlink-h66k.dts`、
> `rk3568-hinlink-h68k.dts`、`rk3568-hinlink-opc.dtsi`（实测确认）。
> H28K 是后加的，u-boot 里还没有，故 107 连板级 dts 一起带。

### 我们额外要做的（★ 三件事，缺一不可）

1. **补齐 `BUILD_DEVICES`** —— 上游只登记 `hinlink_h28k` / `hinlink_h66k` /
   `hinlink_h68k`，而本仓库是按变体拆开的（`hinlink_opc-h68k-c-usb3` 等），
   名字对不上。OpenWrt 的 u-boot 包靠 `BUILD_DEVICES` **反向关联**设备，
   不登记则 `make defconfig` 会丢掉 `CONFIG_PACKAGE_u-boot-xxx`。
2. **把变体名加进 `UBOOT_TARGETS`** —— ★ 最容易漏的一步。
   `include/u-boot.mk` 里包是这么注册的：

   ```make
   define BuildPackage/U-Boot
     $(foreach type,$(if $(DUMP),$(UBOOT_TARGETS),$(BUILD_VARIANT)), \
       $(call BuildPackage,u-boot-$(type)))
   endef
   ```

   **`UBOOT_TARGETS` 列表里没有的变体根本不会生成包**，光定义 `U-Boot/xxx` 没用。
   实测症状：只改 `BUILD_DEVICES` 时 `grep hinlink tmp/.packageinfo` 为空，
   `make defconfig` 把 `CONFIG_PACKAGE_u-boot-hinlink-h68k-rk3568` 丢掉了。
   ⚠️ 改完 `uboot-rockchip/Makefile` 后必须 `rm -f tmp/.packageinfo tmp/.targetinfo`
   再 `make defconfig`，否则用的是旧 metadata、看起来像改动没生效。
3. **换 u-boot 时撤掉旧条目** —— 早先为借用 sige3 曾把我们的设备名写进
   `U-Boot/sige3-rk3568` 的 `BUILD_DEVICES`，改回正规条目后忘了撤，
   结果 defconfig 又把 sige3 带回来。

以上三件事分别落在两个 patch 里：

| patch | 作用 |
|---|---|
| `patches-uboot/0001-...register-hinlink-devices.patch` | 给 `uboot-rockchip/Makefile` 加 8 个 `U-Boot/hinlink-*` 条目 + 8 行 `UBOOT_TARGETS` |
| `patches-uboot/108-...add-hinlink-h29k-ht2.patch` | H29K / HT2 的板级 dts + overlay + defconfig |
| `patches-uboot/109-...add-hinlink-rk3588-uboot.patch` | RK3588 三款的板级 dts + overlay + defconfig |

### 本仓库自建的两批

#### 108 —— H29K / HT2（RK3528）

u-boot 里只有 H28K 的板级 dts。逐项核对三款机型的内核 dts 后确认，
**U-Boot 关心的部分完全一致**，据此为 H29K / HT2 补了各自的板级 dts：

| 项 | H28K | H29K | HT2 |
|---|---|---|---|
| eMMC | bus-width 8 · vmmc=`vcc_3v3` · vqmmc=`vcc_1v8` · non-removable | 同 | 同 |
| SD 卡 | bus-width 4 · vmmc=`vcc3v3_sd`(gpio4 **PA1** 低有效) · vqmmc=`vccio_sd`(gpio4 **PB6** 高有效) | 同（引脚一致） | 同（引脚一致） |
| 调试串口 | `uart0` + `uart0m0_xfer`, 1500000n8 | 同 | 同 |
| vdd_arm / vdd_logic | pwm1 / pwm2 · 746~1201 mV / 705~1006 mV | 同 | 同 |
| 网口 | `gmac1` + RGMII PHY(`mdio1` reg 0x1) · reset gpio4 **PC2** 低有效 | 同 | 同 |

三份 dts 都是「只保留 U-Boot 需要的东西」（eMMC / SD / 串口 / 供电 / 网口），
屏幕、WiFi、红外、5G 模组一律不放 —— 那些 U-Boot 阶段用不到。

#### 109 —— OPC-H88K V2 / V3、OPC-H89K（RK3588）

u-boot 里既没有 hinlink 的 RK3588 板级 dts，也没有 rk806 dtsi，因此另写一份
**精简的 U-Boot 专用 dts**，只含 eMMC / TF 卡 / 调试串口。

★ 刻意**不含 rk806 PMIC 节点**：RK3588 的 PMIC 由 Rockchip TPL
（`rk3588_ddr_lp4_2112MHz_lp5_2400MHz_v1.19.bin`）在 SPL 之前就初始化好
（DDR 需要电压），U-Boot proper 不必再配一遍。少写这 34 路 regulator
反而更安全 —— 抄错电压会把板子拉坏。**代价**：U-Boot 下读不到 PMIC，
若日后需要（例如控制某路电源做掉电重启），再按原理图补 rk806 节点。

存储/串口依据（厂商 `vendor-h89k.dtb` 与 `rk3588-hinlink.dtsi` 两侧一致）：

```
sdhci  eMMC   bus-width 8, non-removable, mmc-hs200-1_8v
sdmmc  TF 卡  bus-width 4, cd-gpios gpio0 PA4 低有效, no-mmc
uart2  调试串口 uart2m0_xfer, 1500000n8
```

defconfig 基于 u-boot 自带的 `generic-rk3588_defconfig`，target 沿用
`CONFIG_TARGET_EVB_RK3588`（与上游 `generic-rk3588` 的做法一致 ——
RK3588 需要一个 `CONFIG_TARGET_*` 来提供板级支持代码）。

### ★ 自建 u-boot 时踩到的两个坑

**① `# CONFIG_OF_UPSTREAM is not set` 会让板级 dts 找不到**

照抄 `generic-rk3588_defconfig` 时带上了这一行，结果 u-boot 不再从
`dts/upstream/src/arm64/rockchip/` 取 dts，而是要求 dts 放在
`arch/arm/dts/` 并**列进 `arch/arm/dts/Makefile`**。报错是：

```
make[5]: *** No rule to make target
         'arch/arm/dts/rockchip/rk3588-hinlink-h88k-v2.dtb', needed by 'dtbs'.  Stop.
```

⇒ 删掉该行（保持 `OF_UPSTREAM` 默认 y）即可。h28k / sige7 等正常工作的
defconfig 都没有这行。

**② 手动往 `.config` 加 u-boot 包时，别忘了 `trusted-firmware-a-<soc>`**

只在 `.config` 里加 `CONFIG_PACKAGE_u-boot-hinlink-h28k-rk3528=y` 就直接编译，
会报：

```
binman: [Errno 2] No such file or directory:
  '.../staging_dir/target-aarch64_generic_musl/image/rk3528_ddr_1056MHz_v1.11.bin'
```

因为 TPL/ATF 由 `trusted-firmware-a-rk3528` 提供（`U-Boot/rk3528/Default` 里
`DEPENDS:=+PACKAGE_u-boot-$(1):trusted-firmware-a-rk3528`），而手动加包**不会触发
依赖解析**。要么补上 `CONFIG_PACKAGE_trusted-firmware-a-rk3528=y`，
要么跑一次 `make defconfig`（但后者会丢掉"当前没选中的设备"的 u-boot 包）。

### 实测验证（2026-10-09）

在真实 immortalwrt master + u-boot 2026.07 上编译**全部 8 个变体**：

```
make package/boot/uboot-rockchip/compile   →  EXIT 0

  9373184 B  hinlink-h28k-rk3528-u-boot-rockchip.bin
  9371648 B  hinlink-h29k-rk3528-u-boot-rockchip.bin
 9371648 B  hinlink-ht2-rk3528-u-boot-rockchip.bin
  9547776 B  hinlink-h66k-rk3568-u-boot-rockchip.bin
  9580032 B  hinlink-h68k-rk3568-u-boot-rockchip.bin
  9454080 B  hinlink-h88k-v2-rk3588-u-boot-rockchip.bin
  9454080 B  hinlink-h88k-v3-rk3588-u-boot-rockchip.bin
  9454080 B  hinlink-h89k-rk3588-u-boot-rockchip.bin
```

**固件内嵌的 u-boot 已确认是 HINLINK 专属那颗**（解包 h68k-c-usb3 的
sysupgrade.img.gz，在前 32 MB 里直接读到）：

```
U-Boot 2026.07-ImmortalWrt-r0-305089f (Oct 09 2026 - 02:50:14 +0000)
model: HINLINK H68K
compatible: hinlink,h68k
fdtfile=rockchip/rk3568-hinlink-h68k.dtb
```

> 验证方法（可复用）：
> ```sh
> gunzip -c <...-squashfs-sysupgrade.img.gz> > /tmp/fw.img
> head -c 33554432 /tmp/fw.img | strings -n 6 | grep -iE "U-Boot 20|HINLINK"
> ```
> ⚠️ **u-boot 包不进 rootfs**，所以不出现在 `.manifest` 里 ——
> 它由 `dd if=$(STAGING_DIR_IMAGE)/$(UBOOT_DEVICE_NAME)-u-boot-rockchip.bin`
> 写进 boot 区。想确认只能解包固件看字符串。

### ⚠️ 未实机验证的部分（RK3528 的 h29k/ht2 与 RK3588 三款）

上游提供的 h28k / h66k / h68k 是厂商与上游验证过的；本仓库自建的 5 个变体
（h29k / ht2 / h88k-v2 / h88k-v3 / h89k）**只做到「编译产出 bin」，没有上机启动验证**。

- RK3528 的 h29k / ht2：DDR/存储/供电三项都比对过内核 dts（见上表），
  风险主要在 DDR 颗粒与 U-Boot 的 TPL 是否匹配 —— TPL 是通用件，正常会自适应。
- RK3588 三款：dts 刻意不含 PMIC，靠 TPL 的默认设置。若无串口输出，
  优先用 SDK 的 `rkdeveloptool`/maskrom 模式恢复，**不要**直接 dd 覆盖 u-boot 区。

⇒ 建议：**先用 sysupgrade 升级**（不写 u-boot 区，最安全）；
确需整盘刷写时，先确认该机型的 u-boot 在实机上的串口输出正常。

---

## 八、验证状态

| 项目 | 状态 |
|---|---|
| DTS 语法结构（19 份） | ✅ 18/19 PASS（1 类失败为**既存**的版本错配，见下） |
| 口数与板级映射一致 | ✅ **19/19** 机型 OK（RK3568 + RK3528 + RK3588） |
| 重复机型清理 | ✅ 已合并 `h68k-c-usb` / `h68k-c-usb3`；`c` / `d` 系列经确认**不合并** |
| 设备定义 ↔ DTS 文件对齐 | ✅ 无孤儿、无缺失 |
| `compatible` 唯一性 | ✅全部唯一 |
| phandle 引用可解析 | ✅ **RK3568 / RK3588 全部 13份**；⚠️ RK3528 6 份受限于内核（见上） |
| 厂商 DTB ↔ 上游 DTS 交叉验证 | ✅ H89K 屏 7 项吻合；H28K / H66K / H68K 网络构成吻合 |
| dtc 完整编译（走 OpenWrt 真实链路） | ✅ **20/20 PASS**，产出 20 个 `image-*.dtb`（见下） |
| phandle 交叉引用 | ✅ 由 `tools/check_phandle.py` 覆盖（RK3568 + RK3588 全部通过） |
| u-boot 全机型覆盖 | ✅ **8 个变体全部编译通过**（RK3528×3 + RK3568×2 + RK3588×3），18 机型无遗漏（见 §七） |
| u-boot 实机启动 | ❌ 仅 h28k/h66k/h68k 为上游验证；自建 5 个变体未上机 |
| 整包编译出固件 | ✅ `BUILD_EXIT_0`，`sysupgrade.img.gz` ×2（h68k-c-usb3，含 LuCI + mt7921e） |
| 实机启动 | ❌ 未验证（无实机） |

> 语法校验用真实内核 6.18 的 include 树跑的：
> `python3 tools/dts_syntax_check.py <dts> <hinlink目录> <kernel>/include <kernel>/include/dt-bindings/input <kernel>/arch/arm64/boot/dts <kernel>/arch/arm64/boot/dts/rockchip`

### ★ 已在真实 immortalwrt master 树上完整编译验证（2026-10-09）

**验证方式**：在 Ubuntu 构建机克隆官方 `immortalwrt/immortalwrt` master
（commit 305089f，rockchip `KERNEL_PATCHVER=6.18`），打入本适配层后
用 **OpenWrt 自己的 cpp + dtc 命令**逐个编译全部 DTS。

**结果：20 份 DTS 全部 PASS，产出 20 个 `image-*.dtb`，0 失败。**

```
OK   rk3528-hinlink-h28k            35108 B      OK   rk3568-hinlink-h68k-new         65056 B
OK   rk3528-hinlink-h29k            36826 B      OK   rk3568-hinlink-h69k-3eth        65302 B
OK   rk3528-hinlink-h29k-v1.3-1.14  36559 B      OK   rk3568-hinlink-h69k-mini        66164 B
OK   rk3528-hinlink-h29k-v5-1.14    36829 B      OK   rk3588-hinlink-h88k-v2         133616 B
OK   rk3528-hinlink-h29k-v5-1.49    38580 B      OK   rk3588-hinlink-h88k-v3         133922 B
OK   rk3528-hinlink-ht2             35534 B      OK   rk3588-hinlink-h89k             94821 B
OK   rk3568-hinlink-h66k            61745 B      （另含 h68k-a / a-usb / c / c-usb3 /
OK   rk3568-hinlink-h68k            63628 B        d / d-usb 等共 20 份）
```

**这一轮真实编译共抓出 6 类静态工具查不到的问题**（全部已修）：

| # | 问题 | 影响 | 根因 |
|---|---|---|---|
| 1 | `RK_FUNC_3` 未定义 | 5 份 DTS `syntax error` | 6.18 的 `dt-bindings/pinctrl/rockchip.h` **只保留 `RK_FUNC_GPIO`**，`RK_FUNC_1..7` 已被内核删除；改用数字 `3` |
| 2 | `rk3588s-vpu/npu/gpu/crypto.dtsi` 缺失 | H88K/H89K 无法编译 | `rk3588s-ip.dtsi` 依赖这 4 个 iStoreOS 私有 dtsi，本仓库漏带；已从 iStoreOS 补齐 |
| 3 | `rk809_grf` phandle 不存在 | 5 份 DTS 编译失败 | 6.18 已无 rk809 节点；这 5 份还是从主线旧版继承的残留；已删除 |
| 4 | `sdmmc2m0_bus4/_cmd/_clk` 重复定义 | 5 份 DTS `duplicate_label` | 内核 `rk3568-pinctrl.dtsi` 已提供且内容逐项相同；删除本地重复定义 |
| 5 | `gmac0_miim` 等重复 + funct 值错误 | H89K `duplicate_label` | 我们写成 `RK_FUNC_GPIO`(0)，内核是 **1**（正确的 MDIO 功能）；删除本地定义改用内核的 |
| 6 | `backlight` 写成顶层裸节点 | 1.49" 屏 DTS `syntax error` | DTS 顶层只能是 `/ { }` 或 `&label { }`；改为挂在 `&{/}` 下 |

另修正 **`9528` fbcon patch**：其上下文按上游 6.18 写，但 immortalwrt 的
6.18.55 里 `struct fbcon_ops` 已改名 `struct fbcon_par`，导致 Hunk #1 FAILED。
已在真实内核树上重新生成，现可干净应用。

> ★ **教训**：`dts_syntax_check.py`（括号平衡）与 `check_phandle.py`（标签引用）
> 都查不出 **宏未定义**（`RK_FUNC_3`）与 **duplicate_label** 这类问题，
> 只有真实 dtc 编译能发现。适配层改完必须走一次真实编译。

### ⚠️ RK3528 的 USB / PCIe 控制器在内核 6.18 里缺失

`tools/check_phandle.py` 报出 6 份 RK3528 DTS 引用了无法解析的标签：

| 标签 | 用途 | 6.18 是否有定义 |
|---|---|---|
| `usb2phy` / `usb2phy_host` / `usb2phy_otg` | USB2 PHY | ❌ 无 |
| `pcie` | PCIe 控制器 | ❌ 无 |
| `usbdrd30` / `usbdrd_dwc3` | USB3 双角色控制器 | ❌ 无 |

**核查结论**：这是**内核 RK3528 支持不完整**，不是本仓库的问题。
6.18 的 `arch/arm64/boot/dts/rockchip/rk3528.dtsi`（31751 B，1178 行）里
只有 `gmac0` / `gmac1` / `combphy`（phy@ffdc0000）等节点，
**没有 pcie 与 usb2phy 控制器**；6.18 自带的 5 份 RK3528 官方板级 DTS
（`rk3528-nanopi-zero2.dts`、`rk3528-rock-2a.dts` 等）也**都没有**使能它们。

另查到 RK3528 是 Linux **6.14** 才引入的（6.10 / 6.12 的
`arch/arm64/boot/dts/rockchip/` 下没有该 SoC）。
immortalwrt `openwrt-24.10` 的 `KERNEL_PATCHVER` 是 **6.6** ——
也就是说 RK3528 要用 ≥6.14 的内核才有料。

**已处理**：把引用这些不存在节点的段落**注释保留**（不删原文，便于内核补齐后
恢复），保留说明文字。涉及 h29k 三份的 `&usb2phy0_host` / `&usb2phy0_otg` /
`&usb2phy` / `&sfc`。

⇒ 处理后 **20 份 DTS 在 6.18 上全部编译通过**（见上一节的实测结果）。

⚠️ 仍需要注意的是：**用 immortalwrt 24.10（`KERNEL_PATCHVER=6.6`）编不出
RK3528** —— 6.6/6.12 内核树里根本没有这个 SoC（RK3528 自 Linux 6.14 引入）。
RK3528 机型必须用 **≥ 6.14** 的内核（本仓库实测 6.18 可用）。

### ⚠️ 2 份 DTS 存在版本错配（H88K，非本轮引入）

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
| 6 | **误判 H28K 为单网口** —— 把「厂商 dtb 里没有网卡节点」当成「板上没有网卡」，实际 H28K 有 PCIe 千兆口（官网规格表 + 厂商 dtb 里 PCIe 链路完整使能） | H28K 少配一个 WAN 口 |
| 7 | **H89K 的 DTS 缺 rk806 PMIC / eMMC / TF 卡 / 调试串口** —— 厂商 dtb 里这四样全都有（详见下节） | 该 DTB **无法正常启动**（找不到根文件系统、无串口输出、CPU 供电不受内核控制） |

### ⚠️ 未修：H89K 的 DTS 严重不完整

做 RK3588 的 u-boot 时对比厂商 dtb（`vendor-h89k.dtb`）发现：本仓库的
`rk3588-hinlink-h89k.dts` 只有 8 个 `&label` 段（`gmac0` / `gmac1` / `mdio0` /
`pcie2x1l1` / `pcie2x1l2` / `pinctrl` / `pwm3` / `spi4`），
缺少下面这些**厂商 dtb 里确实存在**的内容：

| 缺什么 | 厂商 dtb 里的证据 |
|---|---|
| **rk806 PMIC 整棵树** | `/spi@feb20000/pmic@0` compatible = `rockchip,rk806`，含 dcdc-reg1~10 + pldo-reg1~6 + nldo-reg1~5 + pwrkey + 全部 pinctrl 状态 |
| **eMMC** | `/mmc@fe2e0000` bus-width 8 · non-removable · mmc-hs200-1_8v · status okay |
| **TF 卡** | `/mmc@fe2c0000` bus-width 4 · cd-gpios gpio0 PA4 低有效 · no-mmc · status okay |
| **调试串口** | `/serial@feb50000`（uart2）status okay |

成因：上一轮从厂商 dtb 逆推 H89K 时只挑了外设（网口/PCIe/屏），**漏了电源与存储**。

⇒ 影响：该 DTB 目前无法正常启动 —— 没有 eMMC 就找不到根文件系统，
没有 uart2 就没有串口日志，没有 rk806 则 CPU/DDR 供电不受内核管理。

**u-boot 侧不受影响**：`patches-uboot/109` 的 RK3588 板级 dts 是独立写的，
eMMC / TF 卡 / uart2 都按厂商 dtb 的值补上了。**但内核侧的 dts 需要单独修**
（补 rk806 的 34 路 regulator + 三个存储/串口节点，约 250 行）。
| 7 | H28K 的 mmc 别名顺序与厂商相反（`mmc0=sdhci` vs 厂商 `mmc0=sdmmc`） | TF 卡插上后固件不识别 |

同时修正了 `check_port_count.py` 自身的 4 个缺陷（否则上面这些根本查不出来）：
只取第一个 compatible、续行顶格时正则贪婪吞掉整个分支、
「节点存在但无 status」被误判为 okay、以及未区分「板载网口」与
「PCIe 插槽位 / 无网卡的控制器」（`pcie3x4` 与 H28K 的 `pcie`）。

### ★ 一条方法论教训

第 6 条缺陷的成因值得记下来：**我两次都把 DT 的「沉默」当成了硬件的「不存在」**。

| 轮次 | 错在哪 | 真相 |
|---|---|---|
| 第 2 轮 | 上游 DTS 挂了 `pcie-eth`，我据此判双口 | 那可能是给通用 M.2 扩展位预留的模板 |
| 第 3 轮 | 厂商 dtb 里没有 `pci10ec` 节点，我据此判单口 | RTL8111H 靠 PCI 枚举，DT 里本来就不写 |

⇒ **两条纪律**：

1. **DT 里「没有节点」不等于「硬件不存在」**。标准 PCI 设备（RTL8111H /
   RTL8125）永远不会被写进 DT，要靠枚举。判断网口只看
   「该机型有没有使能对应的 PCIe 控制器 + PHY 链路」。见 §4.9。
2. **厂商 dtb > 厂商 DTS > 上游开源 DTS > 官网规格表**。
   但官网规格表往往是**最直接**的证据 —— 这次就是官网一张图推翻了我的两次结论。
   优先级不是简单的排序，而是**互相印证**：当 DT 与规格表冲突时，
   要先怀疑自己的推理，而不是选一个信。

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
2. **H28K 的 PCIe 千兆口（eth1）能否枚举** —— 硬件与官网规格都确认有
   RTL8111H，DT 侧不写 `pcie-eth`、靠 PCI 枚举。刷机后请确认
   `ls /sys/class/net/` 出现 `eth1` 且 `ethtool -i eth1` 驱动是 `r8169`。
   若未出现，说明该批 RTL8111H 的 PCI ID 需要显式声明节点，补
   `pcie-eth@10,0 { compatible = "pci10ec,8168"; }` 即可。
3. **H28K 的 TF 卡是否识别** —— mmc 别名已按厂商纠正为
   `mmc0=TF卡 / mmc1=eMMC`，插卡后确认 `lsblk` 能看到。
4. **H29K 是否真的只有 1 个网口** —— HT2 与 H28K 都有厂商 dtb 实证，
   但 H29K 只有厂商 DTS 与上游 DTS 两侧印证（都只含 `ethernet0`），
   没有厂商 dtb。插上网线看 `ls /sys/class/net/` 即可确认。
5. **老机器 a-b 的 PHY 复位是否稳定** —— `pull_none` 依赖外部电路定电平。
6. **各机型 LED 颜色与闪烁规则** —— H28K 官网标「4 颗灯（含电源指示灯）」，
   而厂商 dtb 只有 3 颗 GPIO LED（第 4 颗疑为常亮硬件）。刷机后确认
   `led-yellow`(GPIO4_C1) 与 `led-blue`(GPIO4_C0) 分别跟哪个网口。
7. **1.49 寸屏用哪份 fbtft 偏移 patch** —— 厂商只给了 1.9 与 1.14 两份，1.49 未提供。
8. **H29K v5 的 5G 模组电源** —— 抄 iStoreOS 的 GPIO0_PC0 + 2s 启动延时。

取证命令：

```sh
ls /sys/class/net/                                  # 实际几个 ethN
for p in /sys/class/net/eth*; do ethtool -i $p | grep -E "driver|bus-info"; done
find /sys/bus/mdio_bus/devices/ -name phy_id -exec sh -c 'echo "$1 => $(cat "$1")"' _ {} \;
dmesg | grep -iE "gmac|ethernet|phy|combphy|saradc|pcie"
```

---

## 九、工具

| 脚本 | 用途 |
|---|---|
| `tools/check_port_count.py` | **口数自检**：交叉校验 DTS 网口构成与 `02_network` 映射 |
| `tools/dup_scan.py` | **去重扫描**：找出硬件配置完全相同的 DTS，并自动比对两者的 `02_network` 映射 |
| `tools/check_phandle.py` | **phandle 校验**：找出 `&label` 引用了不存在的标签（编译阻塞类问题） |
| `tools/dts_syntax_check.py` | 离线 DTS 结构校验（括号平衡、include 完整性） |
| `tools/fdtdump.py` | **DTB 反解析**：把厂商 dtb 的节点/属性 dump 成可读文本，查证硬件参数 |
| `tools/gen_hinlink.py` | RK3568 机型 DTS 生成器 |
| `tools/gen_hinlink_35xx.py` | RK3528 / RK3588 机型 DTS 生成器 |
| `tools/fix_uboot_devname.py` | **批量改设备定义的 u-boot 设置**（按 DEVICE_DTS 决定用哪个 `UBOOT_DEVICE_NAME`，见 §七） |
| `tools/add_hinlink_uboot_entries.py` | **往 uboot-rockchip/Makefile 登记我们的设备**（`U-Boot/xxx` 条目 + `UBOOT_TARGETS`，幂等） |

生成器是 DTS 的可读来源；直接改 DTS 也可以，但改完请跑校验脚本。

### 合并重复机型前必跑 dup_scan.py

同一块板子常被起多个名字（改型、批次年份、厂商内部命名），
仓库里容易出现多份 DTS 但硬件配置完全一样。`dup_scan.py` 会把 DTS 归一化
（去注释 + 归一 model/compatible + 压空白）后两两比对指纹：

```sh
python3 tools/dup_scan.py .
```

**关键**：DTS 指纹相同**只是候选**，能不能合并还要看 `02_network`。
工具会自动读取并打印两者的接口映射，给出结论：

```
=> ✅ **可合并**（02_network 映射一致）
=> ⚠️  需人工确认（02_network 映射不一致）
=> ⚠️  **已确认不合并**（映射不同，属实质硬件差异）
```

本仓库里 `h68k-c` / `h68k-d` 就是「DTS 相同但 WAN 口位置不同」的典型：
合并会让其中一代机器的 WAN 接错口。这类例外记在工具的 `KEEP_SEPARATE` 里。

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

## 十、数据来源

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

## 十一、授权

本仓库为补丁集合，遵循上游 OpenWrt / Linux 内核的 GPL-2.0。
厂商 DTS 的著作权归 HinLink（芯联）所有，此处仅作适配依据引用。
