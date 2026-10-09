# immortalwrt — HinLink 全设备线适配

HinLink（芯联）全系列路由器在 immortalwrt 上的设备树与板级配置。
**按硬件变体一机一档，不做运行时自适应探测** —— 每个 `compatible` 对应一份独立
DTS，`02_network` 里 `ethN` 映射写死。

- **21 个机型** · 22 份 DTS · 7 份 dtsi · 4 份内核 patch · 4 个工具脚本
- 覆盖 RK3568（H66K / H68K / H69K）、RK3528（H28K / H29K / HT2）、RK3588（H88K）

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
这类错误 DTS 语法检查查不出来。

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

### RK3528 — H28K / H29K / HT2（9 个机型）

| 机型 | 版本 | 屏 | 口 | 板载 WiFi |
|---|---|---|---|---|
| **h28k** | — | 无 | RGMII + PCIe RTL8111HS | M.2 |
| **h29k-v1.3-1.14** | v1.3 主板 | 1.14" 135×240 rot270 | 2 | SDIO |
| **h29k-v1.3-1.9** | v1.3 主板 | 1.9" 170×320 rot270 | 2 | SDIO |
| **h29k-v5-1.14** | v5 主板 | 1.14" 135×240 rot90 | 2 | SDIO |
| **h29k-v5-1.49** | v5 主板 | 1.49" **172×320 GC9307 + 电容触控** | 2 | SDIO |
| **h29k-v5-1.9** | v5 主板 | 1.9" 170×320 rot270 | 2 | SDIO |
| **h29k-v5-2.8** | v5 主板 | 2.8" 240×320 rot270 | 2 | SDIO |
| **ht2** | — | 无 | RGMII + PCIe | SDIO SDR50 |

### RK3588 — H88K（2 个机型）

| 机型 | 存储 | 屏 | 口 | 网络 |
|---|---|---|---|---|
| **h88k-v2** | combphy0_ps + SATA | — | 4 | 1×RGMII + 2×PCIe |
| **h88k-v3** | combphy0_ps + PCIe RTL8125 | SPI ST7789V | 4 | 1×RGMII + 2×PCIe |

### 关于 lede 的 H29K DTS

`rk3528-hinlink-h29k.dts` 从 coolsnowwolf/lede 取，compatible 为 `hinlink,opc-h29k`，
**它的背光引脚有误**（见 §七）。仓库保留它仅作参考与映射兼容，
实际使用请选 6 份 `h29k-v*` 拆分版。

---

## 三、网口映射（写死，不探测）

### 枚举顺序

```
RK3568 板（GMAC 为 SoC 内部控制器，枚举固定；PCIe 按扫描顺序）
  gmac0     -> eth0    aliases ethernet0    板载 RGMII #1
  gmac1     -> eth1    aliases ethernet1    板载 RGMII #2
  rtl8125_1 -> eth2    PCIe bus 0x10
  rtl8125_2 -> eth3    PCIe bus 0x20
```

| 机型 | LAN | WAN |
|---|---|---|
| h66k | `eth1` | `eth0` |
| h68k-a / -usb | `eth1` | `eth0` |
| h68k-c / -usb / c-usb3 | `eth0 eth2 eth3` | `eth1` |
| h68k-d / -usb / new | `eth1 eth2 eth3` | `eth0` |
| h69k | `eth1 eth2` | `eth0` |
| h69k-mini | `eth1 eth2 eth3` | `eth0` |
| h28k | `eth0` | `eth1` |
| h29k（全系） | `eth1` | `eth0` |
| ht2 | `eth0` | `eth1` |
| h88k-v2 / v3 | `eth1 eth2 eth3` | `eth0` |

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

⚠️ **因此本方案不写 `pcie-eth` 子节点** —— 写了反而可能干扰枚举顺序。
各机型只按需 `status = "disabled"` 若干控制器来控制口数。

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
| 1.9" | `9999-...-h29k-1.9.patch` | `xs+=35, ys+=0` | `xs+=0, ys+=35` |
| 1.14" | `9999-...-h29k-1.14.patch` | `xs+=52, ys+=40` | `xs+=40, ys+=52` |
| 2.8" | **未提供** | 厂商注释标为「2.8 屏幕 new」 | ⚠️ 需实机确认 |
| 1.49" | **未提供** | GC9307 + PWM 背光，走 SPI | ⚠️ 需实机确认 |

### 4.5 H29K 1.49 寸触屏版是独立硬件

从厂商 2025-10 固件解出的 dtb 拿到：

| 项 | 其他 H29K | **1.49 寸触屏版** |
|---|---|---|
| 屏驱动 | `sitronix,st7789v` | **`sitronix,gc9307`** |
| 分辨率 | 135 / 170 / 240 宽 | **172×320** |
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
│   ├── rk3528-hinlink-h28k.dts               ┐
│   ├── rk3528-hinlink-ht2.dts                │
│   ├── rk3528-hinlink-h29k.dts               │ lede 版本（背光有误）
│   ├── rk3528-hinlink-h29k-v1.3-1.9.dts      │
│   ├── rk3528-hinlink-h29k-v1.3-1.14.dts     │ 6 份 H29K 真实变体
│   ├── rk3528-hinlink-h29k-v5-1.9.dts        │
│   ├── rk3528-hinlink-h29k-v5-1.14.dts       │
│   ├── rk3528-hinlink-h29k-v5-2.8.dts        │
│   ├── rk3528-hinlink-h29k-v5-1.49.dts       ┘ 触屏版
│   ├── rk3588-hinlink-h88k-v2.dts            ┐ 2 份 RK3588
│   ├── rk3588-hinlink-h88k-v3.dts            ┘
│   ├── rk3588-hinlink.dtsi  + 5 个私有 dtsi   ← iStoreOS 私有，须连带移植
│   └── vendor-h29k-v5-1.49.dtb               厂商原始 dtb（1.49 寸参数溯源）
│
├── armv8/base-files/etc/board.d/
│   ├── 02_network                            网口映射（写死，不探测）
│   └── 01_leds                               LED 定义
│
└── image/armv8.mk.hinlink                    设备定义片段（追加到 armv8.mk）

patches/                                      4 份内核 patch（H29K 必需）
docs/APPLY.md                                 应用步骤（方案 A / B）
tools/                                        生成器 + 校验器
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
| `9999-fbtft-...-h29k-1.9.patch` | 1.9 寸屏显示偏移补偿 | H29K 1.9" 必需 |
| `9999-fbtft-...-h29k-1.14.patch` | 1.14 寸屏显示偏移补偿 | H29K 1.14" 必需 |

---

## 七、验证状态

| 项目 | 状态 |
|---|---|
| DTS 语法结构（22 份） | ✅ 全部 PASS |
| 口数与板级映射一致 | ✅ 11/11 RK3568 机型 OK |
| 设备定义 ↔ DTS 文件对齐 | ✅ 无孤儿、无缺失 |
| `compatible` 唯一性 | ✅ 全部唯一 |
| dtc 完整编译 | ❌ **未验证** |
| phandle 交叉引用 | ❌ 未验证 |
| 实机启动 | ❌ 未验证（无实机） |

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
本方案 6 份 H29K DTS 全部采用厂商原值 `PA0 / ACTIVE_LOW`。

lede 那份还是**混合体**：有红外接收（v5 特征）但无电池 ADC（v1.3 特征），
且 panel 完全没有 width/height/rotate 配置 —— 更像厂商某个中间版本。
仓库保留该文件仅作参考，**不建议用于生产**。

### 需实机确认

1. **1.9 寸屏是「微雪原厂」还是「线序修正版」** ——
   厂商 DTS 注释里存在两段 1.9 配置，`spi-max-frequency` 差 16 倍
   （`10000000` vs `600000`），刷错会花屏。
2. **2.8 寸与 1.49 寸屏用哪份 fbtft 偏移 patch** —— 厂商只给了 1.9 与 1.14 两份。
3. **老机器 a-b 的 PHY 复位是否稳定** —— `pull_none` 依赖外部电路定电平。
4. **各机型 LED 颜色与闪烁规则**。
5. **H29K v5 的 5G 模组电源** —— 抄 iStoreOS 的 GPIO0_PC0 + 2s 启动延时。

取证命令：

```sh
ls /sys/class/net/                                  # 实际几个 ethN
for p in /sys/class/net/eth*; do ethtool -i $p | grep -E "driver|bus-info"; done
find /sys/bus/mdio_bus/devices/ -name phy_id -exec sh -c 'echo "$1 => $(cat "$1")"' _ {} \;
dmesg | grep -iE "gmac|ethernet|phy|combphy|saradc"
```

---

## 八、工具

| 脚本 | 用途 |
|---|---|
| `tools/check_port_count.py` | **口数自检**：交叉校验 DTS 网口构成与 `02_network` 映射 |
| `tools/dts_syntax_check.py` | 离线 DTS 结构校验（括号平衡、include 完整性） |
| `tools/gen_hinlink.py` | RK3568 机型 DTS 生成器 |
| `tools/gen_hinlink_35xx.py` | RK3528 / RK3588 机型 DTS 生成器 |

生成器是 DTS 的可读来源；直接改 DTS 也可以，但改完请跑校验脚本。

### 使用 check_port_count.py 时注意

它的口数计算**必须以 dtsi 作基线**：

```
pcie3x1 / pcie3x2 在 DTS 里通常没有显式节点，
继承 rk3568-hinlink-opc.dtsi（dtsi 里两者都 status="okay"）。
只扫 DTS 会把四网口机误判成两网口。
```

---

## 九、数据来源

所有硬件参数均来自厂商原始固件的 dtb（解包反编译，逐项核对）：

| 来源 | 提供的机型 |
|---|---|
| 2022 厂商固件 ×5（`R22.7.19` / `R22.8.22`） | h68k a-b / c / d-f / c-usb3 |
| 2023 厂商固件（`R23.4.20`） | h68k-d |
| 2024 厂商固件（`QWRT-R24.07.07`） | h68k / h69k 硬件定义 |
| 2025 厂商固件（`H29K-NEW-UI-20251029`） | **h29k v5 1.49 寸触屏版** |
| H29K 设备树 ×5 + patch ×4（用户提供） | h29k v1.3 / v5 各屏尺寸 |
| 上游 `coolsnowwolf/lede` | **h66k** / ht2 / h28k / h29k 参考 |
| 上游 `istoreos/istoreos` | h88k v2 / v3 |
| 上游 OpenWrt 主线 + Linux 内核 | `rk3568-hinlink-h68k.dts`、`rk3568-hinlink-opc.dtsi` 蓝本 |

> ⚠️ **compatible 前缀历史上有 5 种**：`ink`（厂商 22-24 年）、`hinlink`、
> `hlink`、`linkstar`、`rockchip`。本仓库统一用 `hinlink,`，
> 按单一前缀匹配会漏掉 lede 的 H28K（它用 `hlink,h28k`）。

---

## 十、授权

本仓库为补丁集合，遵循上游 OpenWrt / Linux 内核的 GPL-2.0。
厂商 DTS 的著作权归 HinLink（芯联）所有，此处仅作适配依据引用。
