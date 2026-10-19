# immortalwrt — HinLink 全设备线适配

HinLink（芯联）全系列路由器在 immortalwrt 上的设备树与板级配置。
**按硬件变体一机一档，不做运行时自适应探测** —— 每个 `compatible` 对应一份独立
DTS，`02_network` 里 `ethN` 映射写死。

- **16 个机型** · 17 份 DTS · 11 份 dtsi · 3 份内核 patch · 15 个工具脚本 · 3 份厂商 dtb
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

### RK3568 — H66K / H68K / H69K（8 个机型）

| 机型 | 年份/定位 | 口数 | 网络构成 | 板载 WiFi | 存储口 |
|---|---|---|---|---|---|
| **h66k** | 无板载网口 | 2 | **0×GMAC** + 2×RTL8125 | — | SATA |
| **h68k-a-b** | 2022 双千兆（A/B 板） | 2 | 2×GMAC | AP6256 | **SATA** |
| h68k-a-b-usb | 同上 | 2 | 2×GMAC | AP6256 | USB3.0 |
| **h68k-c-d-f** | 2022~2023.4 四网口（C/D/F 板） | 4 | 2×GMAC + 2×RTL8125 | M.2 | **SATA** |
| h68k-c-d-f-usb | 同上 | 4 | 2×GMAC + 2×RTL8125 | M.2 | USB3.0 |
| **h68k-new** | 2023末~2024 | 4 | 2×GMAC + 2×RTL8125 | AIC8800 | USB3 + SATA |
| **h69k** | 装 USB 5G 模组 | **3** | 1×GMAC(gmac1) + 2×RTL8125 | AIC8800 | USB3 + SATA |
| **h69k-mini** | = **H68K max** | **4** | 2×GMAC + 2×RTL8125 | AIC8800 | USB3 + SATA |

**命名约定**：**无后缀 = SATA，`-usb` = USB3.0**（OpenWrt / lede / iStoreOS 互认）。

**机型名 = 世代板本串**（2026-10-12 起）：`a-b` = A/B 板，`c-d-f` = C/D/F 板 ——
一眼能看出哪些板本是同一台机器。

> ★ **2026-10-12 合并 + 改名**（用户要求）：
>
> | 原机型（6 个） | 现机型（4 个） | 依据 |
> |---|---|---|
> | `h68k-a` / `h68k-a-usb` | `h68k-a-b` / `h68k-a-b-usb` | 仅改名（A/B 板） |
> | `h68k-c` + `h68k-d` | `h68k-c-d-f` | DTS 归一化后 **0 行差异**，映射也一致 |
> | `h68k-c-usb3` + `h68k-d-usb` | `h68k-c-d-f-usb` | 同上 |
>
> ★ **a 与 a-usb 不能合并**：两者只差 `&sata0 { status }` 一行，而 RK3568 上
>   sata0 与 USB3.0 争同一颗 `combphy0`，**硬件二选一**，故两个变体必须并存。
>
> ★ **旧 compatible 全部保留为次串**（`hinlink,opc-h68k-a` / `-c` / `-d` /
>   `-c-usb3` / `-d-usb` …），旧 DTB 与厂商写的 board.d 仍能匹配。
>
> ⚠️ **WAN 口判据（2026-10-12 实机更正）**：不是「几口」，而是 WAN 焊在哪颗 GMAC：
>
> ```
> 老一代（a-b / c-d-f 两组）  WAN = gmac0
>     h68k-a-b*（2 口）        LAN eth1            / WAN eth0
>     h68k-c-d-f*（4 口）      LAN eth1 eth2 eth3  / WAN eth0
> 新一代（h68k-new / h69k / h69k-mini）WAN = gmac1
>     h68k-new / h69k-mini     LAN eth0 eth2 eth3  / WAN eth1
>     h69k（gmac0 关掉）       LAN eth1 eth2       / WAN eth0  ← gmac1 独占 eth0
> ```

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
| **世代一（2022~2023）—— WAN 焊在 gmac0** | | |
| h66k | `eth1` | `eth0` |
| h68k-a-b / -a-b-usb | `eth1` | `eth0` |
| h68k-c-d-f / -c-d-f-usb | `eth1 eth2 eth3` | `eth0` |
| **世代二（2023末~）—— WAN 焊在 gmac1** | | |
| h68k-new | `eth0 eth2 eth3` | `eth1` |
| h69k（三网口） | `eth1 eth2` | `eth0` ⚠️ 名字是 eth0，**芯片是 gmac1**（gmac0 被 disabled） |
| h69k-mini | `eth0 eth2 eth3` | `eth1` |
| **其余** | | |
| h28k | `eth0` | `eth1` |
| h29k（全系） | `eth0` | —（单口） |
| ht2 | `eth0` | —（单口） |
| h88k-v2 | `eth1` | `eth0` |
| h88k-v3 | `eth1 eth2` | `eth0` |
| h89k | `eth0 eth1` | `eth2` |

> ⚠️ **别用「几口机型」去推 WAN**（2026-10-12 踩过）：`h69k` 与 `h69k-mini`
> 都是 H69K 但 `h69k-mini` 的 WAN 是 `eth1`、`h69k` 是 `eth0` —— 因为
> `h69k` 三网口版把 gmac0 disabled 了，**同一颗 gmac1 被枚举成了 eth0**。

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

### 4.10 ★ H88K 与 H89K 是同源改出来的（2026-10-10 核实）

用户指出「88K 的几个版本和 89k 都是互相修改出来的，并不是完全独立的」。
对比厂商 dtb（`vendor-h89k.dtb`）、armbian 的 `rk3588-hinlink-h88k.dts`
与 iStoreOS 的 `rk3588-hinlink.dtsi` 后**完全印证**：

**逐项一致的公共部分**（因此直接共享 `rk3588-hinlink.dtsi`）

| 项 | 说明 |
|---|---|
| rk806 系统电源 | 同一份 `rk3588-rk806-single.dtsi`；34 路 regulator 命名完全相同（`vdd_gpu_s0` / `vdd_cpu_lit_s0` / … / `vccio_sd_s0`）|
| rk8602 + rk8603 | `i2c0` 的 `vdd_cpu_big0_s0` / `vdd_cpu_big1_s0`、`i2c2` 的 `vdd_npu_s0`，相同 |
| hym8563 RTC | `i2c2` 下 `rtc@51`，相同 |
| es8388 音频 | `audio-codec@11`，相同 |
| eMMC / TF / uart2 | 引脚与供电相同（仅速率档位不同，见下表）|
| gmac0 + mdio0 | RTL8211F，reset 同为 **GPIO4_B3** |
| PCIe | `pcie2x1l1`(RTL8125, reset GPIO4_A2)、`pcie3x4`(NVMe, reset GPIO4_B6) 相同 |
| 模组 IO | `vcc3v3_modem`(**GPIO4_A3 高有效**) + `modem_enable`(**GPIO4_C6 高有效**, 2 s 延时) 相同；**2026-10-12 起 `modem_enable` 的 `vin-supply` 改挂 `vcc3v3_modem`**，由内核保证「先上电、后释放复位」 |
| LED | 4 个 GPIO **完全相同**（GPIO2_C3 / GPIO2_C5 / GPIO3_B7 / GPIO0_A0），只是标签用途不同 |
| 风扇 | 都是 **pwm14** + 50000 ns 周期 |

**H89K 相对 H88K 的全部差异**

| 项 | H88K | H89K |
|---|---|---|
| gmac0 | `rgmii-rxid`, tx_delay `0x44`, rx_delay `0` | `rgmii`, tx_delay `0x42`, rx_delay `0x34` |
| eMMC | hs400 + enhanced-strobe, 200 MHz | **hs200**, 150 MHz |
| TF 卡 | sd-uhs-sdr50 | **sd-uhs-sdr104** |
| 第 3 个 2.5G 口 | v2 无（`combphy0_ps` 给了 SATA0）| `pcie2x1l2` 挂 RTL8125 |
| 屏幕 | v3 走 spidev + 用户态 | **ST7789V 135×240 rot90 @spi4** + 3.0 V 独立供电 |
| 红外 | — | GPIO0_D4 |

⇒ **H89K 的 DTS 已重构为 `#include "rk3588-hinlink.dtsi"` + 只写差异**，
与 `h88k-v2` / `h88k-v3` 的做法完全一致（此前它是独立写的，见 §八 的历史缺陷记录）。

> ★ 方法论：这一节能成立靠的是**逐字段对比厂商 dtb 与两份 dts**，
> 而不是「看起来像就照抄」。用户给出的方向（同源）省掉了大量猜测。

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
| 2022-2023 老机器（`h68k-a-b` / `h68k-c-d-f` 两组，各含 SATA 与 `-usb` 两个变体） | ✅ 互斥，必须拆变体（无后缀 = SATA） |
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
| 背光 | GPIO 恒亮（gpio0_PA0） | **`pwm-backlight` 256 级（pwm6 / GPIO4_PC1）** |

**背光从 GPIO 改成 PWM 是最大架构差异** —— 1.49 寸能调亮度，其他屏不能。

触控：`irq = GPIO4_B2`、`reset = GPIO4_B3`、`inverted-x` + `inverted-y`（双轴反向）。
背光：`pwms = <&pwm6 0 25000 1>`、`brightness-levels = 0..255`、默认亮度 153。

> ★ **背光是 pwm6，不是 pwm3**（2026-10-19 从厂商 `vendor-h29k-v5-1.49.dtb` 逐项核对）：
> `pwmpanel/panel-pwm-pin = <4 0x11 1 0x60>` → **GPIO4_PC1, func 1 = PWM6**；
> `backlight.pwms = <0x68 0 0x61a8 1>`，`0x68 = pwm@ffa98020`。第 4 个 cell = 1
> 表示 `PWM_POLARITY_INVERTED`（**反相**：写大亮度值反而更暗）。
> 早期本仓库写成 `&pwm3 + pwm3m0_pins` 是错的，亮度调不动。

#### 屏幕的用户态程序（2026-10-19 起随固件发布）

三款 H29K 都带 `tft-display`（上游 [H29KorH69K-OPENWRT](https://github.com/ouyangzq/H29KorH69K-OPENWRT)）：
LVGL 系统信息页，写 `/dev/fb0`，开机自启，LuCI 里有配置页（Lua CBI，所以镜像带 `luci-compat`）。
1.49″ 触屏版另带 `kmod-input-touchscreen-axs5106`。

两个 DTS 上的坑（都已修）：

1. **背光节点必须挂在 `&pinctrl` 下、且不带 `reg`**。`pwm_bl.c` 用
   `backlight_device_register(dev_name(&pdev->dev), ...)` 注册，OF 对「无 reg 的子节点」
   用 `<父名>:<节点名>` 拼 platform device 名 ⇒ 设备名是 **`pinctrl:backlight`**，
   而 `tft-display` 的亮度页把这个路径写死了（`src/pages/brightness_page.c` 的
   `BACKLIGHT_DIR`）。挂到根节点下名字变成 `backlight`，亮度页立刻失效。
2. **GPIO 中断的 `interrupt-parent` 必须是 `&gpio4`**，`interrupts` 用 bank 内编号
   `RK_PB2`。写成 `<&gic> + RK_PB2` 是把 GPIO 编号喂给 GIC，规格不合法。
3. 三款的 LCD 背光使能脚 `GPIO0_A0` 用 **gpio-hog 常开**。不用 `led-gpios`：
   fbtft 只有解析到它才注册 backlight 设备，而且设备名取驱动名（`fb_st7789v` /
   `fb_gc9307`），同样与 `pinctrl:backlight` 对不上。

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
| 4G/5G 模组 | 供电 GPIO4_A3、复位 GPIO4_C6；**两路都是 3.3 V 高有效**（`enable-active-high`）。<br>⚠️ 旧文写「A3 5 V / C6 3.3 V，均低有效」是**错的**，见 `docs/HARDWARE.md` §4.2 / §4.3 |
| 红外 | dtb 有 `ir-int-pin`（GPIO0_D4）引脚定义，但无 `gpio-ir-receiver` 节点 |

**未配置项**（厂商 dtb 中同样未启用，未擅自添加）：SATA、RTC、红外接收。

> ⚠️ **上游 PR#19 的 h89k 有个明显 bug**：`compatible = "hlink,h88k"`、
> `model = "Hlink H88K"` —— 从 h88k-v3 复制粘贴忘了改，导致
> **H89K / H88K / H88K-v3 三者 compatible 完全相同、无法区分**。
> 本 DTS 使用独立 compatible `hinlink,opc-h89k`，勿沿用上游写法。

---

### 4.11 ★ 2026-10-10 全机型复验：board.d 合并 bug / LED 名字 / H69K GMAC

把上一轮用于 H88K/H89K 的标准（**全网检索 → 厂商 dtb 逐字段比对 → 真实编译**）
推广到其余全部机型后，查出 3 个「编得出但用不了」的真问题。

#### ❶ board.d 合并后，我们一半机型的分支被官方 `*)` 兜底吃掉（最严重）

`tools/integrate.py` 原来把我们的 case 体插在官方 `case ... esac` 的
**`esac` 之前**。但 OpenWrt 的 board.d 每个 case 块末尾都有

```sh
	*)
		;;
esac
```

⇒ 我们的分支落在 `*)` **之后**，`*)` 会先匹配到所有 HinLink 机型，
**我们的分支永远不会执行**。

实测（编出的固件里，`01_leds` / `02_network` 合并后）：

```
	hinlink,opc-h28k|\      ← 我们
	...
	*)
		;;
esac
	# ---- RK3528 机型 ----   ← 被丢掉（原文在这之后）
```

⇒ 后果：**H28K / H29K×3 / HT2 / H88K×2 / H89K 在固件里既没有网络配置
也没有 LED 配置**（落到官方兜底 = 不设任何东西）。

修法：
1. `tools/integrate.py` 的插入点改成 **官方 `*)` 之前**（新增 `insert_point()`），
   并顺手丢掉我方 body 里可能存在的 `*)` arm。
2. `01_leds` / `02_network` 重写为**结构合法**的脚本：01_leds 只含 **1** 个
   `case` 块、02_network **2** 个（接口 → MAC），**都不带 `*)` 兜底**，
   与官方块数一一对应。
3. 新增 `tools/verify_boardd.py` 校验「我们的条目是否都在 `*)` 之前」。

> 上一版文件还有个副作用：`01_leds` 里写了 `*) ;;` 又接着写 `esac` 后面的
> case 标签，**本身就是 shell 语法错误**（`sh -n` 不过）。

#### ❷ LED 名字与 DTS 不符 → 灯不亮

`rk3568-hinlink-opc.dtsi` 用的是 mainline 的 `color` / `function` 写法，
内核 gpio-leds 会拼出 LED 名字：

| DTS | 生成的 LED 名字 |
|---|---|
| `LED_COLOR_ID_BLUE` + `LED_FUNCTION_WAN` | **`blue:wan`** |
| `LED_COLOR_ID_AMBER` + `LED_FUNCTION_DISK` | **`amber:disk`** |
| `LED_COLOR_ID_GREEN` + `LED_FUNCTION_STATUS` | **`green:status`** |

而我们 `01_leds` 里写的是厂商 2022/2023 固件的**旧式 label**
`blue:net` / `yellow:disk` / `green:work` —— **一个都对不上**，
`/etc/init.d/led` 找不到设备，WAN / 盘位 / 状态灯全部不亮。

（厂商当年用的 DTS 是 `label = "opc-h68k-c:blue:net"`，名字带板名前缀；
本仓库换成 mainline 写法后名字变了，board.d 必须跟着改。）

⇒ 已按 DTS 实际名字改正。RK3588 那份不受影响 —— `rk3588-hinlink.dtsi`
用的仍是旧式 `label = "blue:net" / "yellow:disk" / "green:sys" / "red:work"`，
所以 h88k / h89k 的 `blue:net` 是对的。

#### ❸ H69K 用错了 GMAC（物理口接不上）

厂商 2024 QWRT-R24.07.07 固件里的 H69K 专用 dtb
`fw24/dtb/dtb_3245000.dtb`（`model = "HINLINK OPC-H69K Board"`）：

```
/ethernet@fe010000（gmac1）  status = "okay"
/ethernet@fe2a0000（gmac0）  status = "disabled"
aliases { ethernet0 = "/ethernet@fe010000" }
```

iStoreOS 官方 `rk3568-opc-h69k.dts` 完全一致（`ethernet0 = &gmac1`、
`&gmac0 { status = "disabled" }`）。

而本仓库早期写成 **gmac0 okay / gmac1 disabled** —— 板子 RGMII 走的是
gmac1 的引脚，用 gmac0 等于把信号绑到另一组复用，**网口根本起不来**。
已改为 gmac1（与 H68K 共底板，delay 值同 H68K 的 gmac1）。

#### ❹ 顺带查清：`tx_delay` / `rx_delay` 在 `rgmii-id` 下是死配置

`drivers/net/ethernet/stmicro/stmmac/dwmac-rk.c`：

```c
case PHY_INTERFACE_MODE_RGMII:     /* phy-mode = "rgmii" */
        bsp_priv->ops->set_to_rgmii(bsp_priv, tx_delay, rx_delay);
        break;
case PHY_INTERFACE_MODE_RGMII_ID:  /* phy-mode = "rgmii-id" */
        bsp_priv->ops->set_to_rgmii(bsp_priv, 0, 0);       /* ← 强制清零 */
        break;
```

⇒ 本仓库各机型的 `phy-mode = "rgmii-id"`（跟主线）时，
我们照厂商 dtb 抄的 `tx_delay` / `rx_delay` **完全被忽略**，
RGMII 延时全部由 PHY（RTL8211F）的内部延时提供 —— 这正是主线
`rk3568-hinlink-h68k.dts` 只写 `rgmii-id`、不写 delay 的原因。
两套做法都是「一份延时」，不会叠加；已在 DTS 里注明这层关系，
并保留厂商值（若将来改用 `phy-mode = "rgmii"` 就会生效）。

#### ❺ 补齐 LED 状态别名与 compatible

| 项 | 情况 |
|---|---|
| **LED 状态别名** | 上游有 `patches-6.18/121-arm64-dts-rockchip-add-led-aliases-for-HINLINK.patch`，给 h28k 与 opc.dtsi 加 `led-boot / led-failsafe / led-running / led-upgrade` → `&led_work`。本仓库以 `files/` 覆盖内核树，不便叠该 patch，**直接写进 DTS** —— 现在全部机型都有了（H88K/H89K 的 dtsi 原本就有） |
| **compatible 覆盖** | 补上上游/厂商用过的写法，使厂商固件的 board.d 也能匹配：`hinlink,h28k` + `linkstar,h28k`、`hinlink,h66k`、`hinlink,h68k` + `linkstar,h68k`、`hinlink,h69k`、`hinlink,ht2` + `hlink,ht2`、`hinlink,h89k`、`hinlink,h29k` |
| **H28K mmc 顺序** | 厂商 dtb 是 `mmc0=sdmmc(TF)`；**上游主线是 `mmc0=sdhci(eMMC)`**。我们改回上游 —— 因为 `02_network` 用 `macaddr_generate_from_mmc_cid mmcblk0` 生成稳定 MAC，`mmc0` 必须是 eMMC，否则换 TF 卡就换 MAC。（厂商固件用 `root=PARTUUID=`，与 mmc 编号无关，不受影响） |
| **RK3528 调压 ramp-delay** | 厂商 H28K dtb 有 `regulator-ramp-delay = <6001>`（`/vdd-cpu`），我们没有 → 内核打 `vdd_cpu: ramp_delay not set`。三款 RK3528（H28K / H29K×3 / HT2）是同一路 5kHz PWM 调压、电压范围逐值相同，统一补 `6001` |

#### 复验结果

```
DTS 编译（cpp + dtc，OpenWrt 同款命令）:  20/20 PASS   0 FAIL
DTB 反编译核查（verify_dtb.py）:
  H69K  gmac1=okay / gmac0=disabled / ethernet0→fe010000   ✅
  全部机型 LED aliases led-boot~led-upgrade 存在            ✅
  compatible 列表含上游/厂商写法                            ✅
board.d（verify_boardd.py）:
  01_leds   块1  兜底前 38 条 / 兜底后 0 条   ✅
  02_network 块1  兜底前 38 条 / 兜底后 0 条   ✅
             块2  兜底前 30 条 / 兜底后 0 条   ✅
u-boot: 8 个变体条目 + UBOOT_TARGETS 齐全；defconfig 自动选中
        CONFIG_PACKAGE_u-boot-hinlink-h68k-rk3568=y（证明登记生效）
```

---

### 4.12 ★ 2026-10-10 全 18 机型固件编译（LuCI + 全部无线网卡驱动 + 风扇）

> ⚠️ 本节是 2026-10-10 的**历史记录**，当时是 18 个机型。
> 2026-10-12 已把 h68k 老机器合并/改名为 4 个（见 §4.14），现在是 **16 个机型**。

用户要求：**编译全部机型固件，默认带上 LuCI、所有可能的无线网卡驱动、风扇驱动。**

#### 一、先修「从来没编译通过过」的包名

上一轮只编了 `h68k-c-usb3` 一个机型，所以 `armv8.mk.hinlink` 里大量
**不存在的包名**一直没暴露。逐个用 `make prepare-tmpinfo` 产出的
`tmp/.config-package.in`（13340 个真实包名）核对后：

| 原写法 | 问题 | 现在 |
|---|---|---|
| `kmod-aic8800s` | 不存在（AIC8800 的实际包名是 `kmod-aic8800-sdio`） | `kmod-aic8800-sdio` |
| `kmod-firmware-brcm80211` | 不存在 | `cypress-firmware-43455-sdio` + `brcmfmac-nvram-43455-sdio`（AP6256=BCM43455） |
| `kmod-fb-tft-st7789v` | 不存在 | 改为**内核内建**（见下） |
| `kmod-fb-tft-gc9307` | 不存在，且主线**没有** gc9307 驱动 | 自建驱动 + 内建 |
| `kmod-spi-spidev` | 不存在（`CONFIG_SPI_SPIDEV=y` 已内建） | 删除 |
| `kmod-iio-adc-rk3528` | 不存在（`CONFIG_ROCKCHIP_SARADC=y` 已内建） | 删除 |
| `kmod-power-supply` | 不存在（`CONFIG_POWER_SUPPLY=y` 已内建） | 删除 |
| `kmod-hwmon-thermal` | 不存在（`CONFIG_THERMAL_HWMON=y` 已内建） | 删除 |
| `kmod-input/i2c-chipone-axs5106` | 不存在，主线无 AXS5106 触控驱动 | 删除（1.49 寸触控待补驱动） |

#### 二、通用包集 `Device/hinlink_common`

`target/linux/rockchip/image/armv8.mk.hinlink` 顶部新增该模板，当时的 18 个机型
**全部**在 `endef` 前挂 `$(Device/hinlink_common)`，共 59 个包：

* **LuCI**：`luci luci-ssl luci-app-package-manager luci-i18n-base-zh-cn
  luci-proto-ipv6 luci-proto-ppp luci-mod-{network,status,system}
  luci-theme-bootstrap wpad-basic-mbedtls`
* **无线网卡(M.2/PCIe)**：`mt7921e`(MT7921/7922) `mt7925e` `mt7915e` `mt7615e`
  `rtw88-{8821ce,8822be,8822ce}` `rtw89-{8851be,8852ae,8852be,8852ce,8922ae}`
* **无线网卡(SDIO)**：`mt7921s` `mt7663s` `rtw88-8822cs` `aic8800-sdio`
  `cypress-firmware-43455-sdio` `brcmfmac-nvram-43455/43456-sdio`
  `brcmfmac-firmware-43456-sdio`
* **无线网卡(USB)**：`mt7921u` `mt7663u` `mt76x0u` `mt76x2u` `mt7601u`
  `rtw88-{8821cu,8822bu,8822cu,8821au}` `rtw89-8852bu` `rtl8xxxu`
  `rt2800-usb` `rtl8188eu` `aic8800-{usb,pcie}`
* **5G/4G 模组**：`usb-net-qmi-wwan` `usb-net-cdc-mbim`
  `usb-serial-option` `usb-serial-qualcomm` `usb-modeswitch`
* **风扇**：`kmod-hwmon-core` `kmod-thermal` `kmod-hwmon-pwmfan`
  `kmod-hwmon-gpiofan` `fancontrol` `luci-app-fancontrol`
  `luci-i18n-fancontrol-zh-cn`

⇒ 一块固件插任何一代模块都能认（AP6256 / AIC8800 / M.2 任意 mt76·rtw88·rtw89），
风扇在 LuCI「系统 → 风扇控制」里直接可调。

#### 三、fbtft 小屏栈改为**内核内建**（rockchip 上 package 层拿不到）

实证：`package/kernel/linux/modules/video.mk` 把整条 FB 栈限制成

```
FBDEV_TARGETS := @(TARGET_bcm27xx||TARGET_sunxi||TARGET_x86_legacy||TARGET_x86_geode)
```

⇒ **rockchip 上 `kmod-fb` / `kmod-fb-sys-*` / `kmod-fb-tft` 根本不存在**，
所以 `kmod-fb-tft-st7789v` 这类包名永远编不出来。

改为在 target config 里内建（`target/linux/rockchip/hinlink-config.append`，
由 `integrate.py` 幂等追加到 `armv8/config-6.18`）：

```
CONFIG_FB=y / FB_DEVICE / FB_DEFERRED_IO / FB_BACKLIGHT / FB_SYS_* / FB_SYSMEM_FOPS
CONFIG_FB_TFT=y / FB_TFT_ST7789V=y / FB_TFT_GC9307=y
CONFIG_FRAMEBUFFER_CONSOLE=y / VT / VT_CONSOLE / FONTS / FONT_8x16
+ 13 个「因开 VT/FB 才首次可见」的符号（CONSOLE_TRANSLATIONS、FONT_* 等）
```

#### 四、★ 踩坑：新符号会让内核 `syncconfig` 交互提问 → 非交互构建失败

只写 `CONFIG_VT=y` / `CONFIG_FB=y` 是不够的。OpenWrt 的
`Kernel/Configure` **不会**跑 `oldconfig/olddefconfig`，它只是把
generic+target 配置合并成 `.config`；紧接着内核 `make modules` 触发
`syncconfig`，遇到配置里没有、但首次可见的符号就直接交互提问：

```
    Enable character translations in console (CONSOLE_TRANSLATIONS) [Y/n/?] (NEW)
make[7]: *** [scripts/kconfig/Makefile:85: syncconfig] Error 1
```

精确做法（本次采用的）：

```sh
cd build_dir/.../linux-6.18.55
cp .config.set /tmp/merged.config && cp /tmp/merged.config .config
make ARCH=arm64 listnewconfig        # ← 精确列出所有 (NEW) 符号，不提问
# 一共 13 个，全部写进 hinlink-config.append 即可
```

另外：**改了 target 内核 config 后，必须删掉内核构建目录**
（`rm -rf build_dir/target-*/linux-rockchip_armv8/linux-6.18.55`），
否则残留的 `include/config/auto.conf` 会让 syncconfig 走「Restart config」
分支，症状同上。

#### 五、多机型同时编译的正确开关

`CONFIG_TARGET_MULTI_PROFILE=y`（**必须写在 `.config` stub 里再 `make defconfig`**），
机型符号是多选用的 **`CONFIG_TARGET_DEVICE_<board>_<sub>_DEVICE_<机型>`**
（不是单选 choice 里的 `CONFIG_TARGET_<board>_<sub>_DEVICE_<机型>`，后者是
`choice` 成员，18 个一起选只有最后一个生效并报
`warning: override: ... changes choice state`）。

`CONFIG_TARGET_PER_DEVICE_ROOTFS` 选 **n**：所有机型共用一个 rootfs
（= 所有机型包并集），编译快、且 profile 包在 `.config` 里是 `=y` 而非 `=m`。
选 y 会变成 per-device rootfs（`=m`），18 份 rootfs 各编一遍，没必要。

⚠️ 修改 `armv8.mk.hinlink` 后必须清缓存再 `defconfig`，否则 profile 元数据
不会更新（`armv8.mk.hinlink` 不在 `prepare-tmpinfo` 的依赖里）：

```sh
rm -f tmp/.targetinfo tmp/.config-target.in tmp/.packageinfo tmp/.packagedeps \
      tmp/.config-package.in tmp/info/.targetinfo-*
make defconfig
```

上面的整套流程已脚本化：**`sh tools/build_all.sh`**（可 `sh tools/build_all.sh -j8`），
它会把机型列表写进 stub、清缓存、defconfig、download、编译一条龙跑完。

#### 六、编译结果（2026-10-10，beaver-11800h，内核 6.18.55）

```
make -j16           →  BUILD_EXIT=0
18 机型 × (squashfs + ext4) sysupgrade  =  36 个 .img.gz   （当时）
每机型 sha256 互不相同 ✅（18/18 唯一）
场地 sha256sums 复核                      38/38 OK
rootfs 内实测含 kmod-mt7921e/s /rtw88-*/rtw89-*/aic8800-* /fancontrol 等 ✅
vmlinux 实测含 fb_st7789v / fb_gc9307 / sitronix,gc9307 / sitronix,st7789v ✅
（rockchip_saradc 18 个符号；pwm-fan 是模块，在 rootfs 里）
```

固件清单见 `index.html`（含每机型 sizing 与 sha256）。

---

### 4.13 ★ 2026-10-12 实机更正：H68K 的 WAN 口是 eth0，只有 h68k-new 是 eth1

**实机反馈**：`h68k-c` 刷完 WAN 变成 `eth1`，但这台老机器的 WAN 应该是 `eth0`；
`h68k-new` 才是 `eth1` 为 WAN。

**原因**：`02_network` 当初按「厂商固件代次」分了两组 ——

```
c 系（照抄 2022 fw22）  LAN eth0 eth2 eth3 / WAN eth1   ← 错的
d 系（照抄 2023 fw23）  LAN eth1 eth2 eth3 / WAN eth0
```

实机证明 2022 固件那份记录不可信（或不是这台机器的固件版本）。**判据不是「几口」，
而是 WAN 焊在哪颗 GMAC 上** —— 老一代 WAN 在 **gmac0**，新一代在 **gmac1**：

```
老一代：a / a-usb / c / c-usb / c-usb3 / d / d-usb        WAN = gmac0
    a / a-usb （2 口）        LAN eth1           / WAN eth0
    c / c-usb3 / d / d-usb    LAN eth1 eth2 eth3 / WAN eth0

新一代：h68k-new / h69k / h69k-mini                        WAN = gmac1
    h68k-new  （两 GMAC 都开）  LAN eth0 eth2 eth3 / WAN eth1
    h69k-mini （两 GMAC 都开）  LAN eth0 eth2 eth3 / WAN eth1
    h69k      （gmac0 关掉）    LAN eth1 eth2     / WAN eth0   ← gmac1 独占 eth0
```

⇒ `h69k` 的 WAN 名字仍是 `eth0`，但那颗芯片是 **gmac1**：因为三网口版把 gmac0
disabled 了，gmac1 变成 `ethernet0`。**同一个逻辑、不同的 eth 名**。

厂商固件原文佐证：

```
fw23      hinlink,opc-h69k|linkstar,opc-h68k|opc-h68k-c|opc-h68k-d → WAN eth0
fw29new   hinlink,opc-h68k                       → LAN 'eth0 eth2 eth3' / WAN 'eth1'
          hinlink,opc-h69k                       → LAN 'eth1 eth2'      / WAN 'eth0'
```

同一处映射在 **两个** board.d 文件里都有，必须一起改，否则会出现
「网口对了但 WAN 灯跟着错的接口闪」：

| 文件 | 改什么 |
|---|---|
| `02_network` | `ucidef_set_interfaces_lan_wan` 的 LAN/WAN 列表 |
| `01_leds` | `ucidef_set_led_netdev "wan" ... "<netdev>"` 的 netdev 名 |

**顺带的影响**：改正后 `h68k-c` 与 `h68k-d`、`h68k-c-usb3` 与 `h68k-d-usb`
的 DTS 指纹**和** `02_network` 映射都一致了 ⇒ 内容上已是真重复。
仍保留独立 profile（保住型号名），但 `tools/dup_scan.py` 的
`KEEP_SEPARATE` 理由已从「WAN 口位置不同」改成「厂商按两个型号出货」。

**顺手记一条方法论**：`board_name` 取的是
`strings /proc/device-tree/compatible | head -1`（见
`package/base-files/files/lib/preinit/02_sysinfo`）——
即 compatible 的**第一个串**。所以 DTS 里把具体机型名放在最前、
通用名（`hinlink,h68k` / `linkstar,h68k`）放后面是对的；
`case` 里那两条通用名分支只对上游 `rk3568-hinlink-h68k.dts`
（compatible 只有 `hinlink,h68k`）这类镜像兜底，本仓库机型永远走不到。

---

### 4.14 ★ 2026-10-12 h68k 老机器合并 + 改名（18 → 16 机型）

用户要求：**合并重复机型，并把名字改成一眼能看出是同一台机器的写法
`h68k-a-b` 与 `h68k-c-d-f`。**

#### 一、合并/改名映射

| 原机型（6 个） | 现机型（4 个） | DTS | 依据 |
|---|---|---|---|
| `hinlink_opc-h68k-a` | `hinlink_opc-h68k-a-b` | `rk3568-hinlink-h68k-a-b.dts` | 仅改名（A/B 板） |
| `hinlink_opc-h68k-a-usb` | `hinlink_opc-h68k-a-b-usb` | `rk3568-hinlink-h68k-a-b-usb.dts` | 仅改名 |
| `hinlink_opc-h68k-c` + `-d` | `hinlink_opc-h68k-c-d-f` | `rk3568-hinlink-h68k-c-d-f.dts` | DTS 归一化后 **0 行差异** + 映射一致 |
| `hinlink_opc-h68k-c-usb3` + `-d-usb` | `hinlink_opc-h68k-c-d-f-usb` | `rk3568-hinlink-h68k-c-d-f-usb.dts` | 同上 |

**`a` 与 `a-usb` 不能合并**：两者只差 `&sata0 { status }` 一行，而 RK3568 上
`sata0` 与 USB3.0 争同一颗 `combphy0`，**硬件二选一**，两个变体必须并存。

#### 二、旧 compatible 全部保留为**次串**

```
hinlink,opc-h68k-a-b        , hinlink,opc-h68k-a         , hinlink,h68k, linkstar,h68k, rockchip,rk3568
hinlink,opc-h68k-a-b-usb    , hinlink,opc-h68k-a-usb     , …
hinlink,opc-h68k-c-d-f      , hinlink,opc-h68k-c, -d     , …
hinlink,opc-h68k-c-d-f-usb  , hinlink,opc-h68k-c-usb3, -c-usb, -d-usb, …
```

⇒ 旧 DTB、厂商写的 board.d、以及 `02_network` / `01_leds` 里原有的旧标签
**都还能匹配**（我们在两个 board.d 里把新旧标签并排列出）。
`board_name` 取第一个串，所以新机型名必须排最前。

#### 三、`02_network` 与 `01_leds` 两个文件都要动

新增 compatible 标签必须**同时**加进两个文件的 H68K 分支，否则网口对了但
WAN 灯会绑到不存在的 netdev 上。另外 `rockchip_setup_macs()` 那块的
HinLink 兼容串清单也要补 4 个新的（否则 MAC 生成规则失效）。

#### 四、改名带来的「清理项」

- `tools/check_port_count.py` 的 `EXPECT` 表（按 DTS 文件名索引）→ 改成 4 个新名
- `tools/build_all.sh` 的 `DEVICES` 列表 → 16 个
- `tools/dup_scan.py` → `KEEP_SEPARATE` 清空（c/d 已实际合并）
- `tools/gen_hinlink.py` → 是**历史生成器**，产物已改为手工维护；保留仅作参考

---

### 4.15 ★ 2026-10-12 5G 模组启动上电/复位流程重做（修掉三个真 bug）

用户要求「为 h29k / 69k / 88k / 89k 设计 **iStoreOS 同款的启动 5G pin 复位
流程**」。逐字段对照厂商 dtb 后，发现此前实现有**三个会让模组完全不工作**的错误：

| # | 机型 | 原状 | 后果 |
|---|---|---|---|
| 1 | H69K / H69K-mini | `modem_enable` 多写了 `enable-active-high` | 极性反转，内核开机把 GPIO0_C0 拉**高** ⇒ **模组从没被上电过** |
| 2 | H29K v5（1.14 / 1.49） | `&gpio4 { modem_reset_en { gpio-hog; output-high; } }` | 与 `rfkill-modem` 抢同一个脚 GPIO4_B4；语义与厂商相反；写法本身也错（`gpios = <4 RK_PB4 ...>` 的 `4` 被当 phandle） |
| 3 | H29K 全系 | 只有 `rfkill-gpio`（`reset-gpios` + `power-gpios`） | 6.18 主线的 `rfkill-gpio.c` **只 request `reset`/`shutdown`，没有 `power`** ⇒ 供电脚 GPIO4_B5 **从来没人驱动** |

**核心知识点（值得单独记住）**：

`regulator-fixed` / `reg-fixed-voltage` / `regulator-gpio` 这三类 compatible 的
`gpio` / `gpios` 属性，**DT 里写的 phandle flag（`GPIO_ACTIVE_LOW` 等）被内核
主动忽略**，极性只由有没有 `enable-active-high` 决定 ——
见 6.18 `drivers/gpio/gpiolib-of.c` 的极性映射表及其注释。H69K 就是"照抄了
`GPIO_ACTIVE_LOW`"却又带着 `enable-active-high`，于是极性反转。

**改动**：

| 文件 | 改什么 |
|---|---|
| `rk3568-hinlink-h69k-{3eth,mini}.dts` | 删掉 `modem_enable` 的 `enable-active-high`（恢复低有效） |
| `rk3528-hinlink-h29k-{v1.3-1.14,v5-1.14,v5-1.49}.dts` | `rfkill-gpio` → 两级 `regulator-fixed`（供电 GPIO4_B5 + 复位 GPIO4_B4，均低有效，靠 `vin-supply` 串时序）；删掉 v5 的 `gpio-hog` 与从未被引用的 `modem_reset: <4 RK_PC1>` 死 pinctrl |
| `rk3588-hinlink.dtsi`（H88K v2/v3 + H89K 共用） | `modem_enable` 的 `vin-supply` 从 `vcc_3v3_s3` 改挂 `vcc3v3_modem`，补上「供电 → 复位」依赖链 |

**验证**：8 份相关 DTB 用内核 `cpp + dtc` 重新编译通过，并反编译逐字段核对 ——
节点存在性 / `enable-active-high` 有无 / gpio 的 bank-pin-flag / `vin-supply`
phandle 确实指向供电级 / 无 `rfkill-gpio` 残留 / 无 `gpio-hog` 残留。

**完整机理、逐机型表、内核执行时序图与实机验证命令**见
[`docs/HARDWARE.md` §四](docs/HARDWARE.md)（该节已按本次结论整体重写）。

**代价**：四个机型族都不再有 `rfkill-gpio`（`/dev/rfkill` 里没有 `wwan`）。
取舍理由与恢复方法见 `docs/HARDWARE.md` §4.4 末尾。

---

### 4.16 ★ 2026-10-12 补装 MT7915 / MT7916 固件包

用户反馈「69k 需要打包 mt7916 驱动」。查证结果：**驱动本来就在，固件不在**。

`kmod-mt7915e` 这**一个驱动同时支持 MT7915 与 MT7916 两种芯片**，
但 OpenWrt 把**固件拆成两个独立包**，而 **`kmod-mt7915e` 的 DEPENDS 里
不含任何固件包** —— 必须显式写进 `DEVICE_PACKAGES`。

| 包 | 内容 | 体积（未压缩） |
|---|---|---|
| `kmod-mt7915-firmware` | `mt7915_{wa,wm,rom_patch}.bin` | ≈ 1.5 MB |
| `kmod-mt7916-firmware` | `mt7916_{wa,wm,rom_patch}.bin` | ≈ 2.3 MB |

漏装的症状（插卡后）：

```
dmesg | grep -i "firmware load"
→ Direct firmware load for mediatek/mt7916_wm.bin failed
```

**对照**：`kmod-mt7921e` 的 DEPENDS 自带 `kmod-mt7921-firmware`，
所以 mt7921 / mt7922 那一路从来没出过问题 —— **mt7915e 就是漏在这一条上**。

**改动**：`Device/hinlink_common` 的 M.2/PCIe 段补上这两个包
（全系 16 机型共用；未压缩约 +3.8 MB，gz 后影响很小）。

**验证**：`BUILD_EXIT=0`；rootfs 实测 `/lib/firmware/mediatek/` 下 6 个文件
齐全（`mt7915_{rom_patch,wa,wm}.bin` + `mt7916_{rom_patch,wa,wm}.bin`）；
manifest 里 `kmod-mt7915e` / `kmod-mt7915-firmware` / `kmod-mt7916-firmware`
三个包都在。

---

### 4.17 ★ 2026-10-12 5G 软复位：复位脚改回 `rfkill-gpio`

紧接 §4.15/§4.16 之后，用户问「也就是说完全不可能实现软复位吗」——
**能**，但必须换归属：把复位脚从 `regulator-fixed` 改成 `rfkill-gpio`。

#### 为什么 regulator 做不到、rfkill-gpio 可以

两者都会**占用**复位脚（用户态 `export` 必 `EBUSY`），区别只在有没有
用户态接口：

| | `regulator-fixed` | `rfkill-gpio` |
|---|---|---|
| 用户态接口 | ❌ 无（`always-on` 还拒绝 disable） | ✅ `/sys/class/rfkill/rfkillN/state` = `DEVICE_ATTR_RW` |
| 开机作用 | 内核 `late_initcall_sync` 释放一次 | probe（`device_initcall`）时定电平 |
| **软复位** | ❌ | ✅ `echo 0` → 等 → `echo 1` |

6.18 `net/rfkill/core.c` 里就是 `static DEVICE_ATTR_RW(state)`：
`state_store()` → `rfkill_set_block()` → `rfkill_gpio_set_power()` →
`gpiod_set_value(reset_gpio, …)`。**不需要装 `rfkill` 命令**（纯 sysfs）。

另外两条上一轮没发现的 `rfkill-gpio` 规则：

1. 6.18 对 DT 节点读的是 **`label`** / **`radio-type`**（不是 `name` / `type`）——
   厂商 dtb 里的 `type = "wwan"` **会被忽略**，type 退化成 `RFKILL_TYPE_ALL`；
2. `power-gpios` 在 6.18 **无任何实现**（只 request `reset` / `shutdown`）。

#### 改动

| 文件 | 改什么 |
|---|---|
| `rk3528-hinlink-h29k-{v1.3-1.14,v5-1.14,v5-1.49}.dts` | `modem_enable`(regulator) → `rfkill-modem`(rfkill-gpio)；供电保留 `vcc3v3_modem`(regulator) |
| `rk3568-hinlink-h69k-{3eth,mini}.dts` | 唯一那路 `modem_enable`(regulator) → `rfkill-modem`(rfkill-gpio)，等效**断电重启** |
| `rk3588-hinlink.dtsi`（H88K v2/v3 + H89K） | `modem_enable`(regulator) → `rfkill-modem`(rfkill-gpio)；供电保留 `vcc3v3_modem` |
| **新增** `armv8/base-files/etc/init.d/hinlink-modem-hardreset` | `status` / `reset` / `power-off` / `power-on` |
| `tools/integrate.py` | 新增 `[6]`：同步 base-files 下 `init.d`/`hotplug.d`/`uci-defaults`（`board.d` 仍走合并），并强制 0755 |

#### 用法

```sh
/etc/init.d/hinlink-modem-hardreset reset      # 软复位（拉 300ms → 释放 → 等 2s）
/etc/init.d/hinlink-modem-hardreset status     # rfkill / regulator / USB 状态
/etc/init.d/hinlink-modem-hardreset power-off  # 只拉复位（保持）
```

时序可用环境变量覆盖：`HINLINK_MODEM_HOLD_MS`（默认 300）、
`HINLINK_MODEM_BOOT_WAIT`（默认 2）。
开机自动复位：在 `/etc/rc.local` 的 `exit 0` 前加 `/etc/init.d/hinlink-modem-hardreset reset`。

#### 取舍

放弃了「内核用 `vin-supply` 串死上电→复位顺序」的确定性：
复位脚现在在 `device_initcall`（rfkill probe）就定好工作态，
供电在更晚的 `late_initcall_sync` 才 enable。看似顺序反了，
但**模组上电时看到的已经是"不复位"，而且上电自身有 POR 复位** ⇒
开机路径依然正确。换来的是运行时软复位。

完整机理、三组极性表与实机验证命令见 `docs/HARDWARE.md` §四（§4.8 专讲软复位）。

---

### 4.18 ★ 2026-10-13 usbutils + LuCI「5G 模组」控制面板

用户要求：① 加 usbutils 让 `lsusb` 有内容；② 给 rfkill 写个 LuCI，
把「复位 5G pin」变成手动选项。

#### ① usbutils（还捎带一个 usbreset）

此前固件里**根本没有 `lsusb`** —— busybox 的 lsusb applet 未启用，
执行直接 `not found`，排查模组 / USB 网卡枚举很不方便。

加入 `usbutils`（自动带 `usbids` / `libusb-1.0` / `libudev-zero`）：

| 文件 | 说明 |
|---|---|
| `/usr/bin/lsusb` → `/usr/libexec/lsusb-usbutils` | 完整版 lsusb（`lsusb` / `-t` / `-v`） |
| `/usr/share/hwdata/usb.ids` | USB ID 库 —— 有它才显示厂商名（如 "Quectel"），注意实际路径是 `hwdata/` 不是 `share/` 根 |
| **`/usr/bin/usbreset`** | ★ usbutils 自带，对单个 USB 设备做 `USBDEVFS_RESET` —— **正好补上 pin 复位之外的 USB 层复位** |

#### ② LuCI 控制面板：网络 → 5G复位

全部落在 target base-files（与 hinlink-modem-hardreset 同一套，不做独立 ipk）：

| 路径 | 作用 |
|---|---|
| `/usr/libexec/hinlink-modem-hardreset` | **核心实现**（CLI 与 LuCI 共用）：`status` / `status-json` / `reset` / `power-off` / `power-on` / `usb-reset` |
| `/etc/init.d/hinlink-modem-hardreset` | rc.common 薄壳（可 `enable`；`start()` 读 UCI 决定是否自动复位） |
| `/usr/libexec/rpcd/hinlink-modem-hardreset` | **rpcd shell 插件**，把上面转成 ubus 方法 |
| `/etc/config/hinlink-modem-hardreset` | UCI：`enabled` / `auto_reset` / `hold_ms` / `boot_wait` |
| `/usr/share/luci/menu.d/luci-app-hinlink-modem-hardreset.json` | 菜单项（网络 → 5G复位，order 65） |
| `/usr/share/rpcd/acl.d/luci-app-hinlink-modem-hardreset.json` | ACL（`ubus hinlink-modem-hardreset` 的 read/write） |
| `/www/luci-static/resources/view/hinlink-modem-hardreset.js` | 前端视图 |
| `/etc/hotplug.d/usb/50-hinlink-modem-hardreset` | USB **设备级**插拔 → 日志（模组上线/下线） |
| `/etc/hotplug.d/tty/50-hinlink-modem-hardreset` | **串口级**（`/dev/ttyUSB*`）上下线 → 日志，逐口 |
| `/etc/hotplug.d/net/50-hinlink-modem-hardreset` | **网卡级**（`usb0`/`wwan0`）上下线 → 日志 |

页面三块：

1. **状态**（每 5 秒轮询）—— rfkill 设备与 `state`、供电 regulator、模组 USB
   （VID:PID）、`/dev/ttyUSB*`·`cdc-wdm*`·`ttyACM*`、当前时序参数
2. **手动动作** —— 软复位 / 断电（拉复位）/ 上电（释放复位）/ **仅 USB 重枚举**
3. **开机行为**（UCI 表单，走标准「保存并应用」）—— 启用服务、开机自动复位一次、
   复位保持时长、释放后等启动

#### 为什么用 rpcd shell 插件，而不是 ACL 里的 `file.exec`

`luci-app-h69k-fan` 用的是 `file` + `exec`（授权具体命令行）。
那种写法对「命令行匹配规则」有版本差异，容易踩坑；
rpcd 插件的 ACL 只要 `"ubus": { "hinlink-modem-hardreset": [ "reset", … ] }`，
与 LuCI 的 `rpc.declare` 天然对应，干净得多。

插件**没用 jshn**（少一层依赖），直接手拼 JSON —— 输出结构简单，
并已做转义（反斜杠 / 双引号 / 控制字符）。

#### 离线验证（不用实机就能验后端）

`status-json` 与 rpcd 插件的 `list` / `call status` / `call reset`
都在构建机上用 `sh` 跑过，输出经 `python3 -m json.tool` 校验为合法 JSON：

```json
{"rfkill_found":0,"hold_ms":300,"boot_wait":2,"regulator":"","usb_dev":"",...}
```

（构建机没有 wwan rfkill，所以 `rfkill_found:0`、`reset` 返回
`{"ok":false,"message":"…没有 type=wwan 的 rfkill 设备…"}` —— 符合预期。）

#### 一个 rc.common 的坑

`EXTRA_COMMANDS` 的条目会被 rc.common 当**函数名**调用，
而 shell 函数名**不能含 `-`** ⇒ init.d 下的命令名用下划线
（`power_off` / `power_on` / `usb_reset`）；
核心脚本 `/usr/libexec/hinlink-modem-hardreset` 同时接受连字符写法
（`hinlink-modem-hardreset power-off`），两种都不会踩空。

---

### 4.19 ★ 2026-10-14 出厂默认 LAN 网段改为 192.168.100.1

用户要求「默认 dhcp 改到 192.168.100.1」。**没有**用 uci-defaults 之类
「启动后再改」的脚本，而是让默认值**天生就是**目标网段。

#### 机理：config_generate 从 board.d 的 JSON 里读 ipaddr

`/bin/config_generate` 的 `generate_network()`：

```sh
	json_select network
		json_select "$1"
			json_get_vars device macaddr metric protocol ipaddr netmask vlan
	...
		case "$protocol" in
		static)
			case "$1" in
				lan) ipad=${ipaddr:-"192.168.1.1"} ;;          # ← 关键
				*) ipad=${ipaddr:-"192.168.$((addr_offset++)).1"} ;;
			esac
			netm=${netmask:-"255.255.255.0"}
```

⇒ board.d 的 JSON 里给了 `ipaddr` 就用它，没给才落到上游默认。
官方先例（同样写法）：

```
target/linux/qoriq/base-files/etc/board.d/02_network:14
	ucidef_set_interface "$device" device "$device" protocol static \
	                      ipaddr "10.0.${offset}.1" netmask 255.255.255.0
```

#### 为什么新开一个 board.d 脚本，而不是在 02_network 里加 12 行

`/bin/board_detect` 是按 `for a in $(ls /etc/board.d/*)` **逐个脚本**执行的：

```sh
	for a in $(ls /etc/board.d/*); do
		[ -s "$a" ] || continue
		(. "$a")
	done
```

每个脚本在**子 shell** 里跑，且都是
`board_config_update`（`json_load` 读入当前 CFG）→ 修改 → `board_config_flush`
（`json_dump -o` 写回）**同一个临时文件** ⇒ 这就是 OpenWrt board.d 的累加机制。

⇒ 新增 `03_hinlink-lan-ip`（字典序正好排在 `02_network` 之后），
只往它已经建好的 `network.lan` 对象里补两个字段，**02_network 的 12 个分支
一行都不用改**：

```sh
case "$(board_name)" in
	hinlink,*|hlink,*|linkstar,*)
		ucidef_set_interface "lan" ipaddr '192.168.100.1' netmask '255.255.255.0'
		;;
esac
```

**只匹配 HinLink 前缀** ⇒ 官方其它 rockchip 机型（radxa / friendlyarm…）
保持上游 192.168.1.1，不会被这批改动波及。

#### 离线验证（不用实机）

`board_detect` 的循环可以在构建机上用 host 版 jshn 复现
（`staging_dir/host/bin/jshn` + `share/libubox/jshn.sh`）：把脚本里的绝对
source 路径 sed 到临时树，再按 `01 → 02 → 03 → 05` 顺序跑一遍，读最终 JSON：

| board_name | `network.lan` |
|---|---|
| `hinlink,opc-h69k` | `ipaddr 192.168.100.1` / `netmask 255.255.255.0` ✅ |
| `hinlink,opc-h68k-c-d-f` | 同上 ✅ |
| `hinlink,h28k` / `hlink,ht2` / `hinlink,opc-h89k` | 同上 ✅ |
| **`radxa,rock-3a`（官方机型）** | **无 ipaddr** ⇒ 保持 192.168.1.1 ✅ |

（`wan` 对象没有被碰。）

#### 升级不会覆盖用户改过的 IP

`board_detect` 只在 `/etc/board-base.json` **不存在**时才遍历 board.d，
而它在 overlay 上 ⇒ sysupgrade 保留配置时本脚本不会重跑。
**反过来说**：已经跑过旧固件（LAN = 192.168.1.1）的机器，保留配置刷这版
**不会**自动变成 100.1 —— 想恢复出厂网段要「不保留配置」刷机。

DHCP 池不用改：`/etc/config/dhcp` 里 `dhcp.lan` 的 `start=100` / `limit=150`
是**主机位偏移**，会自动跟着网段走（⇒ 192.168.100.100 ~ 249）。

以后想换网段：只改 `03_hinlink-lan-ip` 里的 `hinlink_lan_ip` 一行。

---

### 4.20 ★ 2026-10-14 5G 模组日志（hotplug 自动记录 + LuCI 日志区）

用户要求「为其制作一个记录日志页面」。

#### 三处写入，一份文件

日志名 = 应用名 = `hinlink-modem-hardreset`
（2026-10-14 由 `hinlink-modem` 改名而来；旧文件在集成时**自动清理**，见 §4.22）。

| 来源 | 内容 |
|---|---|
| 手动操作（CLI / LuCI 按钮） | `reset` / `power-off` / `power-on` / `usb-reset` 的开始与结果 |
| 开机检查（`/etc/init.d/hinlink-modem-hardreset`） | rfkill 是否就绪、`auto_reset` 是否触发 |
| **USB 设备级**（`/etc/hotplug.d/usb/`） | **模组上线 / 下线**（含 `6-1`、vid:pid、总线设备号） |
| **串口级**（`/etc/hotplug.d/tty/`） | **串口上线 / 下线** —— **逐口**，如 `/dev/ttyUSB0 … ttyUSB3` |
| **网卡级**（`/etc/hotplug.d/net/`） | **网卡上线 / 下线**（`usb0` / `wwan0` 等 USB 网卡） |

⚠️ **三种事件是三件事，时间上也不同步，别混**：

```
USB 设备级   内核枚举完成                -> 模组上线 / 模组下线
串口级       usb-serial option 驱动绑定接口层后 /dev/ttyUSB* 出现
             （dmesg: "option 6-1:1.0: GSM modem (1-port) converter detected"）
网卡级       cdc_ether / qmi_wwan 注册 netdev -> usb0 / wwan0
```

**为什么必须分三层记录**：只看设备级，你只知道「USB 在线了」，**不知道
4 个串口是不是都回来了、网卡有没有起来** —— 而后者才是「模组能不能用」。
反过来，只看串口，你也看不到模组什么时候掉的。

> hotplug 脚本由 `/sbin/hotplug-call` **顺序**执行，自己 sleep 会拖住同子系统的
> 其它脚本（如 usb-modeswitch）⇒ 必须后台；用 `start-stop-daemon -b`
> （= setsid）确保脚本退出后不被带走。**实机验证过后台任务在 procd 路径下存活。**

#### tty / net 两个 hotplug 的过滤规则（★ 都踩过）

内核**确实**会为 tty 和 net 设备发 uevent（实测），但事件里混着很多噪音：

| 子系统 | 一次复位收到的原始事件 | 只有这条要 |
|---|---|---|
| `tty` | `remove DEVNAME=ttyUSB0`（tty 设备）+ `unbind DEVNAME=`（接口）+ `remove DEVNAME=`（接口）… | **DEVNAME 非空** |
| `net` | `remove/add INTERFACE=usb0`，以及 br-lan / eth0 / wlan0 的增删 | **接口名 `usb*`/`wwan*`/`cdc*` 且 DEVPATH 含 `usb`** |

⇒ **tty 的过滤器就一条**：`[ -n "$DEVNAME" ]`。接口级与 bind/unbind 事件的
`DEVNAME` 都是空的，只有真正的**字符设备节点**才带它。少了这个过滤，
一个串口会被记 3 遍。

⇒ **net 必须过滤**，否则 br-lan / eth0 / wlan0 的每次增删都会冲进 5G 日志。

#### 实测时间轴（H69K 实机，2026-10-14，改名后重测）

```
20:04:15 [INFO] reset: 开始（hold=300ms, boot_wait=2s）
20:04:15 [INFO] power-off: 已拉复位（模组进入复位 / 断电态）
20:04:15 [WARN] 串口下线：/dev/ttyUSB0        ← tty hotplug，逐口
20:04:15 [WARN] 串口下线：/dev/ttyUSB1
20:04:15 [WARN] 串口下线：/dev/ttyUSB2
20:04:15 [WARN] 串口下线：/dev/ttyUSB3
20:04:16 [WARN] 网卡下线：usb0                ← net hotplug
20:04:16 [INFO] power-on: 已释放复位（模组进入工作态）
20:04:16 [WARN] 模组下线：2cb7:105（掉线 / 正在被复位）   ← usb hotplug
20:04:18 [WARN] reset: 完成，耗时 3s，但 2s 内还没看到模组 USB
20:04:37 [OK]   模组上线：2cb7:105（6-1 总线 006 设备号 006）  ← 21 s 后
20:04:38 [OK]   串口上线：/dev/ttyUSB0
20:04:38 [OK]   串口上线：/dev/ttyUSB1
20:04:38 [OK]   串口上线：/dev/ttyUSB2
20:04:38 [OK]   串口上线：/dev/ttyUSB3
20:04:38 [OK]   网卡上线：usb0
```

⇒ **消失和恢复的全过程都在**，每个串口各自的时刻都能看到。
设备号 `005 → 006` 也证明是真重新枚举。

> `wait-tty` 现在带 `quiet` 调用：逐口的「串口上线」已由 tty hotplug 记录，
> 它只在**超时**（60 s 还没等到 `/dev/ttyUSB0`）时才出声告警，避免重复。
> ★ 注意 `${2:-}` 必须显式传 —— 早期版本漏传导致 quiet 失效、汇总行照旧出现。

#### 目的地两处

`logger -t hinlink-modem-hardreset`（syslog）+ `/etc/hinlink-modem-hardreset.log`
（持久文件，页面读它）。**为什么不只用 syslog** —— logd 是 64 KB 环形缓冲，
dnsmasq / netifd 刷得很快，「几分钟前模组掉过」这种记录往往已经滚没了。

文件超过 `log_max_lines`（默认 300）自动轮转（只留最近一半），避免吃满
overlay；同一份内容也进 syslog，方便远程收集。

#### ★ hotplug 脚本的坑：OpenWrt 没有 udev

`/etc/hotplug.d/usb/` 里**没有** `ID_VENDOR_ID` / `ID_MODEL` / `ID_VENDOR`
（那些是 udev 的 `usb_id` 工具补的）。环境里只有内核 uevent 给的：

```
PRODUCT=<vid>/<pid>/<rev>     # 均十六进制，如 2cb7/105/100
DEVTYPE=usb_device            # 整台设备；接口层是 usb_interface
ACTION=add|remove
BUSNUM / DEVNUM
```

所以需要用 VID 时要从 `PRODUCT` 里切（`cut -d/ -f1`），别照抄 udev 的写法。
另外**必须用 `DEVTYPE=usb_device` 过滤**，否则一次枚举会按接口写好几行重复。

★ 但**别拿 VID 当模组的身份判据**（2026-10-14 改）：VID 白名单换别家模组
就整条链路失灵 —— 现在按**接口结构**判，见下面「模组识别：结构判据」一节。

#### ★ 模组识别：结构判据（2026-10-14 起）

以前用一份 **VID 白名单**（`2c7c 2cb7 2dee …`）认模组。毛病是换别家模组
（移远 / 中移 / SIMCom / 美格 / 龙尚 …）时，「模组上线 / 下线」这条最关键
的日志会整条消失，`usb-reset` 也会直接报找不到 —— 而这正是排查时唯一想让
用户看到的东西。

现在改成问「这个 USB 设备**变成了什么**」，而不是「它是谁」：

| 判据 | 命中条件 | 覆盖 |
|---|---|---|
| ① 字符口 | 设备下出现 `ttyUSB*`（option）/ `ttyACM*`（cdc_acm）/ `cdc-wdm*`（qmi_wwan，在 `usbmisc/` 下） | 绝大多数 4G/5G 模组 |
| ② 网卡 + 0xff | 设备下有 USB 网卡，**且**至少一个接口 `bInterfaceClass=0xff` | 纯 ECM/MBIM/RNDIS 形态模组 |

两条都**不看 VID**，所以对任何厂家成立 —— 模组不管谁造的，都只能靠标准驱动
（option / qmi_wwan / cdc_mbim / cdc_ether / cdc_acm / rndis_host）工作，
内核生成的节点名是固定的。反过来不命中的：U 盘（只有 block）、键鼠（HID）、
HUB（类 0x09）、普通 USB 网卡（r8152 只有 net、没有 0xff 接口）。

**实测（H69K + FM160）**：

```
6-1  2cb7:0105   ttys=4  nets=1  ff=4      ← 命中①（option ×4 + cdc_ether ×2）
usb1..usb6  1d6b:*  ttys=0  nets=0  ff=0   ← root hub，不命中
```

**时序**：hotplug 的设备级 `add` 事件发出时接口目录已经存在，但 `ttyUSB*`
要等 option 驱动 probe 之后才出现 ⇒ **事件当下判定会漏**。所以 `add` 交给
`usb-probe` **轮询等待**（上限 `USB_PROBE_WAIT=10` s）再记日志，
日志里会带上「等了 Ns」。`remove` 时设备已消失、查不了结构，改用 `add` 时
写下的状态文件（`/tmp/hinlink-modem.usb`）比对，再兜一层已知 VID
（防轮询还没跑完就被拔）。

**想退回「全通配」**：UCI `hinlink-modem-hardreset.modem.usb_all=1`
（LuCI「开机行为 → 记录所有 USB 设备」），任何非 root-hub 的 USB 设备插拔
都记一条，完全不做识别。只在「明明插着模组却判不出来」时用来排查。

页面「状态」区因此多了一行 **识别依据**，直接写明是「结构判据 · 字符口 4 个」
还是「未命中」，不再只丢一句白名单结论。

#### LuCI「网络 → 5G复位」新增日志区

- 同一个页面第 ② 块：`<pre>` 倒序显示（最新在最上）+ 刷新 / 清空
- 数据来自 ubus `hinlink-modem-hardreset.log '{"lines":200}'`（rpcd 插件新增方法）
- **操作按钮点完自动刷新日志** —— 正好看到刚触发的那几步
- 状态区仍 5 秒轮询；日志**不**轮询（否则你正在看就被顶走了）

ACL 相应加 `log`（read）/ `log_clear`（write）。

#### 验证

- 构建机跑后端：`log` / `log-add` / `log-json` 输出经 `jsonfilter` 校验合法
- 实机 `ubus call hinlink-modem-hardreset log '{"lines":3}'` 返回正确 JSON（LuCI 真实链路）
- hotplug 过滤：手工喂 `DEVTYPE=usb_interface` **不写日志**；
  `PRODUCT=1d6b/2/600`（root hub，非模组）在 hotplug 层就被 `vid=1d6b` 挡掉，
  即使直接调 `usb-probe` 也只会记一条 INFO「未判为模组」
- 模组判定走**接口结构**：实测 FM160（`6-1 2cb7:0105`，ttys=4 nets=1 ff=4）
  判为「结构判据 · 字符口 4 个」；root hub（ttys=0 nets=0 ff=0）判为不是模组
- `curl http://<机>/luci-static/resources/view/hinlink-modem-hardreset.js` = HTTP 200 且与本地一致

#### ⚠️ 日志时间戳依赖系统时钟

实机实测系统时间是 `Oct 12`（实际 `Oct 14`）—— **RTC 走时本身偏了约 2 天，
且默认时区是 GMT**。日志时间戳直接取系统时钟，所以会跟着错。

2026-10-14 已在实机上把时区设成 `Asia/Shanghai`（`CST-8`）；NTP 客户端本来
就是 enabled（`system.ntp.server` = time.apple.com / time1.google.com /
time.cloudflare.com / pool.ntp.org），**一旦有外网就会自动校准绝对时间**。

⇒ 这台机器「没外网」的原因也一并查清了：`eth0`（WAN）没地址（没插网线 /
WAN 没起来），`usb0`（FM160 的 cdc_ether 网卡）也没有 IP（5G 尚未拨号）。
脚本自身不做时间纠正（那属于系统层）。

#### ★ 踩坑：LuCI `rpc.declare` 的 `expect` 不是类型校验，是「只取这个字段」

最初写的是 `expect: { entries: [] }`，以为意思是「entries 是个数组」。
结果页面直接报：

```
TypeError: (r.entries || []).slice is not a function
```

看 LuCI 的 `rpc.js` → `handleCallReply()`：

```js
if (req.expect) {
	for (const key in req.expect) {
		if (ret != null && key != '')
			ret = ret[key];          // ← 把**整个返回值**换成这个字段
		if (ret == null || type.call(ret) != type.call(req.expect[key]))
			ret = req.expect[key];   // ← 类型不符就替换成 expect 里的值
		break;                       // ← 只处理第一个 key
	}
}
```

⇒ 它的语义是 **「从返回值里取出这几个字段」**（`expect` 里写的是**默认值**），
**不是**类型校验。写 `{ entries: [] }` 的后果有两个：

1. `total` / `max_lines` / `file` **全部丢失**（页面上的行数统计永远是 0）；
2. 一旦类型判断把 `entries` 换成 `req.expect[key]`（一个非数组值），
   前端再调 `.slice()` 就整页 `TypeError`。

**修法**：**不写 `expect`**（拿完整对象），字段自己在前端兜底：

```js
var callLog = rpc.declare({
	object: 'hinlink-modem-hardreset',
	method: 'log',
	params: [ 'lines' ]          /* ← 不写 expect */
});
```

前端 `logEntries()` 对「数组 / 只剩数组 / 下标对象 / 字符串 / 数字 / null」
都做了兜底，11 种输入用 node 跑单测全不崩。

> 对照：`expect: {}`（**空对象**）是安全的 —— `for...in` 不产生任何 key，
> 什么都不会改。本项目其余方法（`status` / `reset`…）用的都是 `expect: {}`。

---

### 4.21 ★ 2026-10-14 应用整体改名：`hinlink-modem` → `hinlink-modem-hardreset`

用户要求「ipk 名称改成 `hinlink-modem-hardreset`」。

⚠️ **本项目没有独立 ipk** —— 整个应用都落在 target base-files（见 §4.18），
所以「包名」体现为**一组标识符**。本次把这一整套统一改名（共 124 处引用）：

| 旧 | 新 |
|---|---|
| `/etc/config/hinlink-modem` | `/etc/config/hinlink-modem-hardreset` |
| `/etc/init.d/hinlink-modem` | `/etc/init.d/hinlink-modem-hardreset` |
| `/usr/libexec/hinlink-modem` | `/usr/libexec/hinlink-modem-hardreset` |
| `/usr/libexec/rpcd/hinlink-modem`（= **ubus 对象名**） | `/usr/libexec/rpcd/hinlink-modem-hardreset` |
| `/etc/hotplug.d/usb/50-hinlink-modem` | `…/50-hinlink-modem-hardreset` |
| `luci-app-hinlink-modem`（menu.d / acl.d） | `luci-app-hinlink-modem-hardreset` |
| `www/…/view/hinlink-modem.js` | `www/…/view/hinlink-modem-hardreset.js` |
| **日志** `/etc/hinlink-modem.log` | `/etc/hinlink-modem-hardreset.log` |
| syslog tag `logger -t hinlink-modem` | `logger -t hinlink-modem-hardreset` |

**连带必须一起改的**（漏掉任何一处都会「改名改一半」）：

- `menu.d` 的 **`path`** 字段 —— 它必须等于 view 文件名，否则页面 404；
- `acl.d` 的 **`ubus` 对象名**与 **`uci` 段名** —— 与 rpcd 插件文件名、config 段名同源；
- 前端 JS 的 `object:` / `uci.load()` / `form.Map()` / `NamedSection`；
- init.d 的 `$MODEM` 路径与 `uci -q get <pkg>.modem.*`；
- DTS 注释、README / HARDWARE 文档里的命令示例。

**实机迁移**（老固件升级上来的机器）：
`/etc/config` 是 sysupgrade 保留项，所以旧配置不会自动消失 —— 部署脚本要
显式 `mv` 旧日志、按旧配置生成新配置，再 `rm` 旧名的 8 个文件 + 旧 `rc.d`
软链，最后 `/etc/init.d/rpcd restart`（**不重启 rpcd 新 ubus 对象不会出现**）。

实测确认：`ubus list` 只有 `hinlink-modem-hardreset`（旧对象消失）、
新页面 HTTP 200 / 旧页面 404、`ubus call hinlink-modem-hardreset log` 正常。

#### 附带：LuCI 显示名 `5G 模组` → `5G复位`

「应用名」和「显示名」是两件事：

| | 改哪里 | 值 |
|---|---|---|
| **应用标识**（文件 / ubus / uci） | 文件名 + 内部引用 | `hinlink-modem-hardreset` |
| **菜单显示名** | `menu.d` 的 **`title`** 字段 | **`5G复位`** |
| ACL 描述（`acl.d` 的 `description`） | 同上 | `HinLink 5G复位（模组硬复位 / 状态 / 日志）` |

⇒ 只改显示名**不需要**动目录路径（`admin/network/hinlink-modem-hardreset` 保持），
用户浏览器里唯一的变化就是菜单文字。改完要清 **LuCI 菜单缓存**
（`rm -f /tmp/luci-indexcache*`）或重启 uhttpd，否则还是旧字。

> 提醒：LuCI 菜单项的文字来自 `menu.d` 的 `title`，**不是** view 文件名、
> 也不是 ACL。三者互相独立，别混。

---

### 4.22 ★ 2026-10-14 修 `integrate.py` 的「只拷不删」缺陷

§4.21 改名时暴露出来的**真问题**：`tools/integrate.py` 的 `[6]` 只把
base-files 拷进内核树，**从不删除**已废弃的文件。于是改名后内核树里
**新旧两套并存**，会一起打进固件 —— 表现为「旧 LuCI 页面/旧 ubus 对象仍在」。

**修法**：`[6]` 增加一步清理 ——

1. 先收集源树里**应有**的相对路径集合；
2. 遍历目标树，凡是**文件名含 `hinlink` / `hlink`**（只认我方标记，绝不碰官方
   文件）而源树已没有的，删掉；
3. 顺手清掉空目录。

实测：一次运行清理掉 8 个旧文件，`phy-leds` / `reload-sdio-wifi` /
`40-net-smp-affinity` 等官方文件**一个都没动**。

> 教训：**集成脚本必须幂等**。只做「拷贝」的脚本，在源树删文件/改名时会
> 留下幽灵文件，而且症状很隐蔽（功能「还在」，只是是旧版本）。

---

### 4.23 ★ 2026-10-14 5G 复位插件包化 + 新增 `package/beaverfffan` + 完整发行仓库

**① 5G 复位从 base-files 裸文件改成正式 ipk 包**

`package/beaverfffan/luci-app-hinlink-modem-hardreset/`（Makefile + `files/`），
原先躺在 `target/.../base-files/` 下的 10 个文件**已全部移走**（base-files 现在
只剩 `etc/board.d/` 的三个映射文件）。

裸文件形式只能随固件内置 —— 不能单独装、不能卸、不能升级，也没法在
`menuconfig` 里勾选。包化之后它就是个正常 ipk，同时仍然是固件默认的一部分
（`configs/*.config` 里显式选中）。

Makefile **不走 `luci.mk`**：那是 `feeds/luci` 下的相对路径机制，本包在
`package/beaverfffan/` 里没有那个相对关系；手写 install 段反而更清楚，
顺便把文件权限一次钉死（脚本 0755 / 数据 0644 —— 权限错了 LuCI 会 404、
rpcd 不加载插件）。

**② 新增 `package/beaverfffan/`，四个插件**

| 包 | 说明 |
|---|---|
| `fancontrol` + `luci-app-fancontrol` | JiaY-shi 的通用 hwmon PWM 温控风扇。★ **默认配置改成 `enabled='1'`**（上游默认是关的），其余参数与上游一致 |
| `luci-app-hinlink-modem-hardreset` | 自研，见 ① |
| `luci-app-oled` | `jjm2473/luci-app-oled`（SSD1306 0.91″ I2C OLED） |
| `aic8800` | lede 的 AIC8800 驱动（PCIe / SDIO / USB 三形态） |

★ `luci-app-fancontrol` 上游用的是相对路径 `include ../../luci.mk`，搬进
`package/beaverfffan/` 后会指到不存在的 `package/luci.mk` ⇒ 已改成
`include $(TOPDIR)/feeds/luci/luci.mk`。

★★ **2026-10-15 发现的坑：`package/beaverfffan/` 下的包会被 feed 同名包覆盖** ★★

immortalwrt 官方 feeds 里**也有** `fancontrol`、`luci-app-fancontrol`、
`luci-app-oled` 三个同名包。`./scripts/feeds install -a` 会在 `package/feeds/`
下建出软链，而 OpenWrt 扫描 `package/` 时按**字母序**，`package/feeds/*`
晚于 `package/beaverfffan/*` ⇒ 同名的 `Package/xxx` 定义被 feed 那份
**静默覆盖** —— 编译不报错、包也照样进 manifest，只是**内容不是我们的**：

| 被覆盖的包 | 实际装进固件的 | 本应有的 |
|---|---|---|
| `fancontrol` | 上游配置（`option enabled '0'`） | 我们改的 `'1'`（**默认开温控**） |
| `luci-app-oled` | unifreq 血统版（`netsource=eth0`） | jjm2473 版（`netsource=wwan0`） |
| `luci-app-fancontrol` | feed 版（功能等同） | 我们的（只差 include 路径） |

**暴露经过**：2026-10-15 用户质疑「oled 怎么是 natelol 原版」，顺着查才发现
**三个包全被顶掉** —— 也就是说用户在 10-14 明确要求的「风扇插件默认打开温控」
**一直没生效**（固件里是上游的 `enabled='0'`）。

**修法（已落地，两处）**：
1. `tools/build_single.sh` 开头新增 `[0]` 步骤 —— 遍历 `package/beaverfffan/*/`，
   把 `package/feeds/*/<同名>` 一律 `rm -rf`（**只删软链**，feeds 源目录不动）。
2. 发行仓库 README 的编译步骤里加了
   `./scripts/feeds uninstall fancontrol luci-app-fancontrol luci-app-oled`
   —— 直接 `make defconfig && make` 的用户不走 `build_single.sh`，必须手工做。

**以后新增自维护包时必查**（有输出 = 存在同名 feed 包，会被顶掉）：
```sh
for d in package/beaverfffan/*/; do
  n=$(basename "$d"); find feeds -maxdepth 4 -type d -name "$n"
done
```
当前 `aic8800` 与 `luci-app-hinlink-modem-hardreset` 在 feeds 里无同名包，安全。

**③ 新增完整发行仓库 `Beaverfffan/immortalwrt-hinlink-full`**

一棵**完整的 immortalwrt 源码树**（base `305089f`，排除构建产物后 88 MB）
+ 本适配层固化进去 + `configs/`（16 机型 defconfig）+ `docs/devices/`
（每机型一份说明）+ `package/beaverfffan/`。clone 下来直接

```sh
cp configs/<机型>.config .config && make defconfig && make -j$(nproc)
```

**不再需要跑 `integrate.py`**（本仓库仍然保留，用于往已有的内核树里注入改动）。

config 由 `tools/gen_configs.py` 生成：拿一份已编过固件的**全机型** `.config`
当底稿 → 收敛成单机型 → 交给 `make defconfig` 校验一遍 → 再逐份检查追加的
包有没有被静默丢弃（包名写错 / 依赖不满足时 `defconfig` 会悄悄删掉那一行，
这是最容易漏的坑）。

**④ 风扇与 5G 复位面板是「两个独立判据」**（2026-10-15 用户更正）

```
有风扇        -> 编风扇插件（fancontrol + luci-app-fancontrol）
有 5G 复位脚  -> 编 5G 复位面板（luci-app-hinlink-modem-hardreset）
```

| 机型 | 风扇 | 5G 复位脚 | 编风扇插件 | 编 5G 面板 |
|---|---|---|---|---|
| h69k / h69k-mini | ✅ pwm-fan（PWM0 绑 cpu_thermal） | ✅ `GPIO0_C0` | ✅ | ✅ |
| h88k-v2 / h88k-v3 / h89k | ✅ pwm14（定义在 `rk3588-hinlink.dtsi`） | ✅ `GPIO4_C6` | ✅ | ✅ |
| h29k-v1.3-1.14 / v5-1.14 / v5-1.49 | ❌ 无风扇 | ✅ `GPIO4_B4` | ❌ | **✅** |
| h28k / ht2 / h66k / h68k 全系 ×5 | ❌ | ❌ | ❌ | ❌ |

> ⚠️ **别取交集**。我先前误把「有风扇 **且** 有 5G 复位脚」当成一个条件，结果
> 5G 面板只编了 5 个机型，「有复位脚但无风扇」的 **H29K 全系被漏掉**。两者互不
> 相干：**有风扇就编风扇，有复位脚就编面板**。代码在 `tools/gen_configs.py` 的
> `HAS_FAN` / `HAS_MODEM` 两组常量 + `FAN_ON|FAN_OFF` / `MODEM_ON|MODEM_OFF`。
>
> ⚠️ **判据要落到「真实节点」，不是裸关键词** —— 两个真实的误判源：
> ht2 的 dts 里有一行**注释**「无 4G/5G LED 与 rfkill（H29K 才有）」；
> h89k 的 dts 里有一行**注释**「风扇 = pwm14，5 档（由 dtsi 的 pwm-fan 提供）」。
> 判据应为 `compatible = "rfkill-gpio"` 与真实 `pwm-fan` 节点。
> 另：h88k-v2/v3、h89k 的节点都在 `rk3588-hinlink.dtsi`，只 grep 各自的 dts 会
> 得出「都没有」的错误结论；`rk3568-hinlink-opc.dtsi`（h66k / h68k 公共）里两者皆无。

**⑤ `integrate.py` 新增 `[7]`**：整目录同步 `package/beaverfffan` 进内核树
（`rmtree` + `copytree`，保证增删改名都被同步，不会留下旧包）。

### 4.24 ★ 2026-10-14 发行仓库改为「完整上游历史 + 逐机型提交」

第一版发行仓库图省事做成了**单提交快照**（一个 commit 装下全部适配），
用户纠正了两点，都记下来别再犯：

1. **不要一个巨提交** —— 要「一个机型一个提交」，这样才看得出哪个改动属于哪个机型；
2. **要保留完整的 immortalwrt 提交日志** —— 单提交快照等于把上游历史丢了。

**改法**

- `git fetch --unshallow` 取回完整历史：浅克隆 1 提交 → **76583 提交**，
  `.git` 19 MB → **466 MB**，只花 64 秒；
- 新增 `tools/rebuild_commits.py`：拿「最终态快照」重放出
  **基础设施 1 个 + 机型 16 个 = 17 个提交**，机型顺序 = `armv8.mk.hinlink`
  里 `define Device/` 的出现顺序；脚本**内置逐文件校验**（143 个文件字节一致
  才放行，不一致直接退出不推送）；
- 提交划分：
  - **基础设施**：U-Boot patch(106~109) / 内核 patch / 公共 dtsi /
    **board.d 两张映射表** / 5G 复位应用 / `package/beaverfffan` / 文档框架 /
    两个生成器工具；
  - **每个机型**：`DTS` + `configs/<机型>.config` + `docs/devices/<机型>.md`
    + `armv8.mk.hinlink` 里该机型的 Device 段。

**★ 为什么 board.d 不按机型拆**

`02_network` / `01_leds` 是**跨机型的共享映射表**，而且我方分支在文件里是
**夹在官方分支之间**的（多年多次插入的结果），既不在文件末尾、也不连续 ——
用「插在 `*)` 之前」或「按锚点插入」都复现不出原位置。硬拆只会把位置搞错，
所以整份放进基础设施提交，换来「最终树与快照逐字节一致」。

**release 仓库**：`Beaverfffan/immortalwrt-hinlink-full`
（旧库已删、同名重建；`default_branch` 已设为 `master`）。

---

### 4.25 ★ 2026-10-14 发行版编译：分区 128/1024 + 四件套（全机型）

**用户要求**：kernel 与 rootfs 分区改成 **128 MB / 1024 MB**；打包
`luci-app-passwall` / `luci-app-openclash` / `luci-app-ttyd` / `luci-app-upnp`；
**所有机型**编译；**发布进 release**。

**★ 随后追加的约定（重要）**：

> 「**不要更新 configs，这个只是编译发行版用的**」

⇒ 这组改动**只服务于这一次的发行版固件**，不写进仓库 configs：
- 标准 `configs/` 保持 **16/160、不带四件套**（git HEAD 不动、不提交）；
- 发行版配置**独立存放**：构建机 `~/iwrt-hinlink-full/configs-release/`。

**技术要点**

1. 分区两个值**只影响镜像生成**（分区表 + padding），不参与任何 C 编译
   ⇒ 改它不会引起重编。放大原因：passwall / openclash 的依赖
   （xray-core / sing-box / ruby）在 160 MB rootfs 里放不下。
2. 四个包都在官方 `feeds/luci/applications/` ⇒ **不需要额外 feed 源**。
   passwall 的 8 个 `INCLUDE_*` 子选项要**显式钉住**（默认值各版本不一，不写会
   得到不带 xray/sing-box 的残缺包）；openclash 的 kmod 依赖
   （`kmod-tun` / `kmod-inet-diag` / `kmod-nft-tproxy` / `kmod-nft-socket`）
   由 defconfig 自动 select。
3. `gen_configs.py`：机型行改为**显式重建**（不再遍历底稿重写）—— 底稿若是
   「某个单机型 config」，机型行已被 kconfig 规范化过，重写不可靠；
   同一处跳过 `CONFIG_PACKAGE_luci-app-hinlink-modem-hardreset`（由 `MODEM_APP` 决定）。

**★ 用单机型编译（`tools/build_single.sh`），不用 `build_all.sh` 的多机型模式**

多机型 `PER_DEVICE_ROOTFS=n` ⇒ 所有机型**共用一份 rootfs** ⇒ .config 里 =y 的
包会落到**每一个**机型，5G 复位面板会扩散到全部 16 个（用户要求它只在 5 个）。
单机型模式产物与 `configs/<机型>.config` 一一对应，代价是每机型重跑一次 make。

**★ 第一轮结果：11 个成功 / 5 个失败**，失败的**恰好**是带 5G 复位面板的
h69k / h69k-mini / h88k-v2 / h88k-v3 / h89k。

**根因**：构建树的 `target/linux/rockchip/armv8/base-files/` 里**还留着那 10 个
hinlink-modem-hardreset 文件** —— 上一轮「包化搬出」时只在**本地 repo2** 删了，
这棵构建树的 base-files 没同步删（它由原树 rsync 而来）。于是包与 base-files
**同名文件相撞**：

```
ERROR: luci-app-hinlink-modem-hardreset: trying to overwrite
       etc/config/hinlink-modem-hardreset owned by base-files-1950~b9bdaaa503
（10 个文件全报）→ package/install 失败 → 该机型不产镜像
```

**★ 第二个坑（隐蔽）：base-files 有编译缓存。** 只删文件不够，旧产物里仍带着
那 10 个文件，必须
`make package/base-files/clean && make package/base-files/compile`
再重编；验证方式是 `make -j1 V=s package/install` 看 `rc=0` 且
`trying to overwrite` 计数为 0。

**排查手法（可复用）**：`make -j16` 的错误被 `-s` 静音了（只打印
`make[3] -C xxx compile`），必须 `make -j1 V=s <目标>` 才看得到真正原因；
另外「**失败机型集合 = 装了某个包的机型集合**」是极强的线索 ——
直接用 `comm` 对比成功/失败机型的 config 差异即可锁定。

**新增工具**
- `tools/build_single.sh` —— 逐机型编译（单机型 config 模式，断点续跑）
- `tools/publish_release.py` —— 发布 GitHub release（建 release + 传 asset，
  带重试与断点续传，自动生成 `sha256sums.txt`）

**发行仓库补提交**：`2302fe11`（删除 base-files 里的残留文件）—— 否则用户
clone 后编译会撞同一个坑。

---

## 五、仓库结构

```
target/linux/rockchip/
├── files/arch/arm64/boot/dts/rockchip/
│   ├── rk3568-hinlink-h66k.dts               无板载网口（2×GMAC disabled）
│   ├── rk3568-hinlink-h68k-a-b.dts           ┐
│   ├── rk3568-hinlink-h68k-a-b-usb.dts       │
│   ├── rk3568-hinlink-h68k-c-d-f.dts         │ 8 份 RK3568 拆分机型
│   ├── rk3568-hinlink-h68k-c-d-f-usb.dts     │ ★ 2026-10-12 合并+改名：
│   ├── rk3568-hinlink-h68k-new.dts           │   a→a-b；c+d→c-d-f；
│   ├── rk3568-hinlink-h69k-3eth.dts          │   c-usb3+d-usb→c-d-f-usb
│   ├── rk3568-hinlink-h69k-mini.dts          ┘
│   ├── rk3568-hinlink-opc.dtsi               RK3568 公共设备树（来自主线）
│   ├── rk3528-hinlink-h28k.dts               双口（RTL8211F + PCIe RTL8111H，无 WiFi）
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
├── armv8/base-files/                         ★ 我方 base-files（integrate.py [6]）
│   ├── etc/board.d/02_network                网口映射（写死，不探测；合并进官方文件）
│   ├── etc/board.d/01_leds                   LED 定义（合并进官方文件）
│   ├── etc/board.d/03_hinlink-lan-ip         默认 LAN 网段 192.168.100.1（见 §4.19）
│   ├── etc/config/hinlink-modem-hardreset    UCI 配置
│   ├── etc/init.d/hinlink-modem-hardreset    rc.common 薄壳
│   ├── etc/hotplug.d/usb/50-hinlink-modem-hardreset   设备级 上线/下线
│   ├── etc/hotplug.d/tty/50-hinlink-modem-hardreset   串口级 逐口 上线/下线
│   ├── etc/hotplug.d/net/50-hinlink-modem-hardreset   网卡级 上线/下线
│   ├── usr/libexec/hinlink-modem-hardreset   核心实现（CLI + LuCI 共用）
│   ├── usr/libexec/rpcd/hinlink-modem-hardreset        rpcd shell 插件
│   ├── usr/share/luci/menu.d/luci-app-hinlink-modem-hardreset.json
│   ├── usr/share/rpcd/acl.d/luci-app-hinlink-modem-hardreset.json
│   └── www/luci-static/resources/view/hinlink-modem-hardreset.js
│
├── hinlink-config.append                     ★ 追加到 armv8/config-6.18：FB/fbtft 内建段
│                                             + 13 个 (NEW) 符号（见 §4.12）
└── image/armv8.mk.hinlink                    设备定义片段（追加到 armv8.mk）
                                             含 Device/hinlink_common 通用包集

patches/                                      3 份内核 patch（已验证干净应用）
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

只有 **3 份** patch，都已验证 `patch -p1` 可干净应用到 Linux 6.18（无 fuzz、无 offset）。

| patch | 用途 | 必需性 |
|---|---|---|
| `9999-fbtft-read-display-offset-from-dt.patch` | fbtft 从 DT 读显示偏移（`x-offset` / `y-offset` / `x-offset-0` / `y-offset-0`），替代按机型硬编码的 switch | H29K 1.14" / H89K 必需 |
| `9530-fbtft-add-gc9307-driver.patch` | **新增 GC9307 fbtft 驱动**（由 `fb_st7789v.c` 派生，compatible 用 `sitronix,gc9307`）+ Kconfig/Makefile 条目 | H29K v5 1.49" 必需（主线无此驱动） |
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

设备定义里统一写 `UBOOT_DEVICE_NAME := <上表的变体名>` —— **全部机型覆盖**，
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
   `hinlink_h68k`，而本仓库是按变体拆开的（`hinlink_opc-h68k-c-d-f-usb` 等），
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
**精简的 U-Boot 专用 dts**。

**2026-10-10 补全网口与 NVMe**：按 leux 的《RK3588设备H88K适配主线U-Boot》
笔记补上（此前只有 eMMC / TF / 调试串口，进 U-Boot 会看到 "No ethernet found"）：

```
板载千兆   &gmac0 (RTL8211F) + &mdio0，reset = GPIO4_B3
2.5G ×2    &pcie2x1l1 (reset GPIO4_A2) + &pcie2x1l2 (reset GPIO4_A5)
           + &combphy0_ps / &combphy1_ps / &combphy2_psu
NVMe       &pcie30phy + &pcie3x4 (reset GPIO4_B6)
defconfig  CONFIG_PCI / CMD_PCI / PCIE_DW_ROCKCHIP / RTL8169 /
           PHYLIB / PHY_REALTEK / DWC_ETH_QOS(_ROCKCHIP) / DM_MDIO /
           CMD_NVME / NVME_PCI，并**去掉 generic 的 CONFIG_NO_NET**
           （那是无网口通用板用的，留着网络驱动不会编译）
```

⚠️ H88K v2 的 `combphy0_ps` 给了 SATA 座 → 它的 u-boot dts **不使能 pcie2x1l2**
（只有 2 个网口）；v3 与 H89K 才使能第三个。
U-Boot 里查看 NVMe：`pci enum` → `nvme scan` → `nvme info`。

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
| H89K DTS 完整性 | ✅ **已修复**（2026-10-10 重构为继承 `rk3588-hinlink.dtsi`；eMMC/TF/uart2/PMIC/PCIe2x1l2 全部就位，真实编译 PASS 134257 B）|
| 重复机型清理 | ✅ **2026-10-12 完成**：h68k 老机器 6 个机型合并为 4 个（`a-b` / `a-b-usb` / `c-d-f` / `c-d-f-usb`），旧 compatible 全部保留 |
| 设备定义 ↔ DTS 文件对齐 | ✅ 无孤儿、无缺失 |
| `compatible` 唯一性 | ✅全部唯一 |
| phandle 引用可解析 | ✅ **RK3568 / RK3588 全部 13份**；⚠️ RK3528 6 份受限于内核（见上） |
| 厂商 DTB ↔ 上游 DTS 交叉验证 | ✅ H89K 屏 7 项吻合；H28K / H66K / H68K 网络构成吻合 |
| dtc 完整编译（走 OpenWrt 真实链路） | ✅ **20/20 PASS**，产出 20 个 `image-*.dtb`（见下） |
| phandle 交叉引用 | ✅ 由 `tools/check_phandle.py` 覆盖（RK3568 + RK3588 全部通过） |
| **5G 模组启动上电/复位流程** | ✅ **2026-10-12 重做**：h29k / 69k / 88k / 89k 四个机型族统一为「两级 `regulator-fixed` + `vin-supply` 依赖链」；极性经厂商 dtb 逐字段核对；8 份 DTB 反编译验证（节点 / `enable-active-high` / gpio pin+flag / 依赖链 phandle / 无 rfkill 与 hog 残留）。修掉三个真 bug（见 §4.15） |
| 5G 流程实机验证 | ❌ 未上机（无模组/无实机）；期望现象与验证命令见 `docs/HARDWARE.md` §4.5 |
| u-boot 全机型覆盖 | ✅ **8 个变体全部编译通过**（RK3528×3 + RK3568×2 + RK3588×3），全部机型无遗漏（见 §七） |
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

### ✅ 已修：H89K 的 DTS 曾严重不完整（2026-10-10 重构修复）

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

**已于 2026-10-10 修复**：把 `rk3588-hinlink-h89k.dts` 重构为
`#include "rk3588-hinlink.dtsi"` + 只写差异（因为 H88K 与 H89K 同源，
见 §4.10），顺带修掉另外几处错误：

| # | 旧写法（错） | 新写法（对） | 后果 |
|---|---|---|---|
| 1 | 无 rk806 / rk8602 / rk8603 | 由 dtsi 提供 | CPU/NPU 供电不受内核控制 |
| 2 | 无 `&sdhci` / `&sdmmc` / `&uart2` | 由 dtsi 提供 | **找不到根文件系统、无串口输出** |
| 3 | 无 `&pcie2x1l2` | 本文件补上 | 少一个 2.5G 网口 |
| 4 | `snps,reset-gpio = <&pinctrl RK_PB3 …>` | dtsi 里是 `<&gpio4 RK_PB3 …>` | PHY 复位脚指向错误对象 |
| 5 | 风扇写成 `&pwm3` | **pwm14**（厂商 `/pwm@febf0020`）| 风扇 PWM 通道错 |
| 6 | 模组 IO 写成 `ACTIVE_LOW` | **HIGH 有效**（厂商 dtb 实证）| 模组不上电 / 无法复位 |
| 7 | 有 LED pinctrl 但无 leds 节点 | 由 dtsi 提供（GPIO 相同）| LED 不亮 |

**验证**：真实 dtc 编译 **PASS**（134257 B）；反编译核查
`mmc@fe2e0000`(eMMC) / `mmc@fe2c0000`(TF) / `serial@feb50000`(uart2) /
`pcie@fe190000`(第 3 个 2.5G) 均为 **okay**，`ethernet@fe1c0000`(gmac1)
为 **disabled**（与厂商 dtb 一致），rk806 / rk8602 / rk8603 / hym8563 /
es8388 / pwm-fan / st7789v 全部就位。
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
8. ~~**H29K v5 的 5G 模组电源** —— 抄 iStoreOS 的 GPIO0_PC0 + 2s 启动延时。~~
   **2026-10-12 已闭环**：GPIO0_C0 是 **H69K** 的引脚，不是 H29K。H29K 由
   厂商 dtb `f3_318a000_40194.dtb` 实证为**供电 GPIO4_B5 + 复位 GPIO4_B4
   （均低有效）**，现已写成两级 regulator 并加 2 s 延时，见
   `docs/HARDWARE.md` §4.3。仍需实机确认模组能否正常枚举。

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

本仓库里 `h68k-c` / `h68k-d` 是「DTS 与映射都相同、但刻意保留两个型号名」的例子
（2026-10-12 之前记的理由是「WAN 口位置不同」，已被实机推翻 —— 见 §4.13）。
这类例外记在工具的 `KEEP_SEPARATE` 里。

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
