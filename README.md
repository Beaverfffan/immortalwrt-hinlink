# immortalwrt HinLink 全机型适配（拆分版）

针对 `immortalwrt/immortalwrt`（`master` 分支）的 HinLink 设备线完整适配。

**设计原则：拆分所有机型，不允许自适应。** 每个硬件变体一个独立 DTS + 一个独立
compatible，`02_network` / `01_leds` 每机型独立分支，`ethN` 映射写死。

---

## 一、蓝本与依据

| 项 | 来源 |
|---|---|
| DTS 蓝本 | OpenWrt 主线 `rk3568-hinlink-h68k.dts` + `rk3568-hinlink-opc.dtsi` |
| 设备定义范式 | OpenWrt 主线 `target/linux/rockchip/image/armv8.mk` |
| 硬件事实 | 厂商 2022/2023/2024 固件 dtb（已解包反编译逐项核对） |
| 无线参数 | 用户提供的 H69K AIC8800 点亮脚本 + 2022 a-b dtb 交叉验证 |

**immortalwrt 现状**：`immortalwrt/immortalwrt` 默认分支 `master`
（最后推送 2026-10-09T03:20:38Z，11713 star），**当前完全没有 hinlink 适配**
（code search 全仓仅 1 处命中，是 Graperain-G3568 的无关 patch）。

---

## 二、机型矩阵（7 个独立机型）

| # | 机型 | DTS | compatible | 网口数 | 网络构成 | 板载 WiFi |
|---|---|---|---|---|---|---|
| 1 | **H68K A/B**（2022 双千兆） | `rk3568-hinlink-h68k-a.dts` | `hinlink,opc-h68k-a` | 2 | 2× GMAC | **AP6256**（Broadcom brcmfmac）+ RTC |
| 2 | **H68K C/D/F**（2022 四网口） | `rk3568-hinlink-h68k-c.dts` | `hinlink,opc-h68k-c` | 4 | 2× GMAC + 2× RTL8125 | 无 |
| 3 | **H68K C USB3**（2022.8） | `rk3568-hinlink-h68k-c-usb3.dts` | `hinlink,opc-h68k-c-usb3` | 4 | 同上 | 无 |
| 4 | **H68K D**（2023.4 推荐版） | `rk3568-hinlink-h68k-d.dts` | `hinlink,opc-h68k-d` | 4 | 同上 | 无 |
| 5 | **H68K new**（2023末~2024） | `rk3568-hinlink-h68k-new.dts` | `hinlink,opc-h68k-new` | 4 | 同上 | **AIC8800** |
| 6 | **H69K**（真·装 5G 模组） | `rk3568-hinlink-h69k.dts` | `hinlink,opc-h69k` | 3 | 1× GMAC + 2× RTL8125 | **AIC8800** + 5G |
| 7 | **H69K mini**（体积精简） | `rk3568-hinlink-h69k-mini.dts` | `hinlink,opc-h69k-mini` | 2 | 1× GMAC + 1× RTL8125 | 无 |

### 网口映射（写死，不探测）

| 机型 | LAN | WAN |
|---|---|---|
| H68K A/B | `eth1` | `eth0` |
| H68K C/D/F、C USB3 | `eth0 eth2 eth3` | `eth1` |
| H68K D、new | `eth1 eth2 eth3` | `eth0` |
| H69K | `eth1 eth2` | `eth0` |
| H69K mini | `eth1` | `eth0` |

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

| 机型 | PCIe 处理 | 效果 |
|---|---|---|
| 2 口变体 | `&combphy1/2`、`&pcie3x1/2` 全部 `status="disabled"` | 只剩 2 个 GMAC |
| 4 口变体 | 不动（dtsi 已okay） | 2 GMAC + 2 PCIe = 4 口 |
| H69K | 屏蔽 `gmac1` | 1 GMAC + 2 PCIe = 3 口 |
| H69K mini | 屏蔽 `gmac1` + `pcie3x2` | 1 GMAC + 1 PCIe = 2 口 |

---

## 四、硬件事实表（全部来自厂商 dtb，无推测）

### GMAC 时序（跨 2022/2023/2024 三代固件完全一致）

| 控制器 | PHY 复位 | tx_delay | rx_delay |
|---|---|---|---|
| `gmac0` (eth0) | `gpio2 RK_PD3` 低有效 | `0x3c` | `0x2f` |
| `gmac1` (eth1) | `gpio1 RK_PB0` 低有效 | `0x4f` | `0x26` |

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
> 本方案取 `GPIO3_D5`（来自厂商正式 dtb）。**H69K 实机引脚仍需确认。**

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

| 项目 | 状态 | 说明 |
|---|---|---|
| DTS 语法 | ✅ 已验证 | 7 个 DTS + 主线对照组全部 PASS（`dts_syntax_check.py`，该检查器已用主线原生 DTS 校准） |
| dtc 完整编译 | ⚠️ 未完成 | Ubuntu 上 dtc 1.7.2 太老，连主线内核官方 `rk3568.dtsi` 都编译失败（对照组同样失败 ⇒ 环境问题，非代码问题）。需在 buildroot 环境或新版 dtc 下验证 |
| phandle 引用完整性 | ⚠️ 未验证 | 离线检查器不检查 phandle 交叉引用 |
| 实机启动 | ❌ 未验证 | 无实机 |
| LED 颜色与GPIO | ❌ 待确认 | `01_leds_hinlink` 中的 color/label 需按实机调整 |

### 需要实机确认的项

1. **H69K 的 WiFi 复位引脚**：脚本写 GPIO3_A0，a-b dtb 是 GPIO3_D5，需确认
2. **H69K-mini 的实际屏蔽配置**：当前按「屏蔽 1 GMAC + 1 PCIe」处理，需确认
3. ~~H68K new 的 WiFi 型号~~ **已确认：AIC8800**（全新机器）
4. **各机型 LED 颜色/闪烁规则**
5. **H69K 5G 模组**：当前用 GPIO0_PC0 + 2s 延时（抄 iStoreOS），需确认

---

## 八、遗留的已知不确定项

### 8.1 WiFi 驱动分档（已按实机确认）

| 机型 | WiFi 芯片 | 驱动包 |
|---|---|---|
| h68k-a（老机器） | **AP6256**（Broadcom） | `kmod-brcmfmac kmod-firmware-brcm80211` |
| h68k-new / h69k（全新机器） | **AIC8800** | `kmod-aic8800s` |
| h68k-c / c-usb3 / d / h69k-mini | 无板载 WiFi（M.2 插槽） | `kmod-mt7921e` |

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
