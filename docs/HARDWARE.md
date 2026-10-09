# 特殊硬件清单

本文档逐项列出 HinLink 全系机型的**非网口类**特殊硬件：屏幕、风扇、WiFi、
5G/4G 模组供电与复位 IO、SARADC、按键、LED。

数据来源优先级（见 README §七的方法论）：
**厂商 dtb > 厂商 DTS > iStoreOS DTS > 上游 unifreq DTS > 推断（需实机确认）**

---

## 一、屏幕

### 驱动方式分两类

| 类型 | 机型 | 驱动 | 说明 |
|---|---|---|---|
| **fbtft**（内核驱动） | H29K 全系（1.14" / 1.49"）、H89K | `kmod-fb-tft-st7789v` / `kmod-fb-tft-gc9307` | 屏节点写 `compatible = "sitronix,xxx"` + `width`/`height`/`rotate` |
| **spidev + 用户态** | H88K v3 | `kmod-spi-spidev` + `kmsd`/`fb_ili9341` 类工具 | iStoreOS 的做法，DTS 里只有 `spidev@0`，**不带屏参数** |

⚠️ **这个差异很重要**：H88K v3 的屏在 DTS 里**没有** `width`/`height`/`rotate`，
所以它**用不到** fbtft 的偏移 patch。刷 H88K v3 时不要装 fbtft 的包。

###逐机型明细

| 机型 | 屏驱动 | 分辨率 | rotate | SPI 频率 | DC 引脚 | 背光 | 偏移 patch |
|---|---|---|---|---|---|---|---|
| H29K v1.3 1.14" | st7789v | 135×240 | **270** | 6 MHz | GPIO1_B4 | GPIO0_A0 恒亮 | ✅ 40/52 |
| H29K v5 1.14" | st7789v | 135×240 | **90** | 6 MHz | GPIO1_B4 | GPIO0_A0 恒亮 | ✅ 40/52 |
| H29K v5 1.49" | **gc9307** | **172×320** | 270 | 6 MHz | GPIO1_B4 | **PWM3/GPIO4_B6** | ⚠️ **未提供** |
| H89K | st7789v | 135×240 | 90 | **1 MHz** | GPIO1_A4 | 未配置 | ✅ 40/52（推断） |
| H88K v3 | spidev | — | — | 50 MHz | GPIO1_A4 | — | 不适用 |
| 其余机型 | 无屏 | — | — | — | — | — | — |

**背光是架构级差异**：1.49 寸是唯一支持**亮度调节**的机型
（`pwm-backlight`，256 级，`pwms = <&pwm3 0 25000>`，默认亮度 153）；
其他屏是 GPIO 恒亮（`backlight-gpios`，低有效）。

**触控**：只有 1.49 寸有电容触控（`chipone,axs5106` @ I2C1 addr 0x63，
irq=GPIO4_B2，reset=GPIO4_B3，`inverted-x` + `inverted-y` 双轴反向）。

### 显示偏移 patch

```
patches/9999-fbtft-read-display-offset-from-dt.patch
```

ST7789V 135×240 在 rotate 后显存窗口需平移才能对上可见区。本patch
**从 DT 读偏移量**，不在内核里按机型硬编码：

```dts
x-offset    = <40>;   /* rotate 90/270 时 x += 40 */
y-offset    = <52>;   /* rotate 90/270 时 y += 52 */
x-offset-0  = <52>;   /* rotate 0/180  时 x += 52 */
y-offset-0  = <40>;   /* rotate 0/180  时 y += 40 */
```

> ★ 为什么改成读 DT：H29K 与 H89K 都是 135×240 但 rotate 不同，
> 硬编码 switch 无法区分。改成 DT 后一块屏改DTS 就能调偏移，
> 不必重编内核。数值来自原厂 1.14" 偏移 patch。

⚠️ **1.49 寸（172×320）没有偏移数据** —— 原厂只给了 1.9" 与 1.14" 两份。
若实机显示位置不对，在其 DTS 的 panel 节点加 `x-offset` / `y-offset` 即可。

---

## 二、风扇

### 覆盖情况

| 机型 | 风扇 PWM | 温控 cooling-maps | 状态 |
|---|---|---|---|
| **H69K / H69K-mini** | — | — | ⚠️ **缺**（iStoreOS 有） |
| H89K | `pwm3`（febf0020）| — | ⚠️ **只有 PWM，无 pwm-fan 节点** |
| H88K v2/v3 | — | — | ✅ 无风扇（厂商无） |
| H66K / H68K 系列 | — | — | ✅ 无风扇（厂商无） |
| H28K / H29K / HT2 | pwm1/pwm2 作 **vdd_cpu/vdd_logic 调压** | — | ✅ 非风扇用途 |

### ★ 已知缺口：H69K 缺风扇配置

iStoreOS `rk3568-opc-h69k.dts` 里有完整的风扇实现，本仓库**没有移植**：

```dts
fan: pwm-fan {
    compatible = "pwm-fan";
    cooling-levels = <0 0x55 0x66 0x77 0x88 0x99 0xbb 0xcc 0xff>;
    #cooling-cells = <2>;
    fan-supply = <&vcc5v0_sys>;
    pwms = <&pwm0 0 50000 0>;
};

&pwm0 { status = "okay"; };

&cpu_thermal {
    trips { cpu_warm(65℃) / cpu_hot(85℃) / cpu_hall(95℃) / cpu_idle(20℃) };
    cooling-maps {
        map2: idle  -> <&fan THERMAL_NO_LIMIT 2>;   /* 低温常转最低速 */
        map3: warm  -> <&fan 2 4>;
        map4: hot   -> <&fan 4 6>;
        map5: hall  -> <&fan 6 THERMAL_NO_LIMIT>;   /* 高温全速 */
    };
};
```

**未移植的原因**：H69K 的 PWM 编号与风扇存在与否，需要厂商 dtb 确认。
H69K 的厂商 dtb 尚未提取（本仓库只有 h68k / h28k / h29k / h89k 的厂商 dtb）。
**在拿到厂商 dtb 前不擅自添加** —— 猜错PWM 通道会导致 CPU 无风扇或风扇乱转。

⇒ 已列入README 的「需实机确认」。

### H89K 的 pwm3 只接了 PWM 未接风扇

厂商 dtb 里 `pwm@febf0020` 是 `okay`，本仓库照抄了，但**没有 `pwm-fan` 节点**，
所以风扇不会自动调速（需用户态控制）。厂商 dtb 里也没有 pwm-fan / cooling-maps，
说明厂商固件同样只把它当普通 PWM 用。

---

## 三、WiFi

### 覆盖情况

| 机型 | WiFi 模组 | 控制器 | pwrseq | enable | host-wake | 驱动包 |
|---|---|---|---|---|---|---|
| **H28K** | **无** | — | — | — | — | — |
| H29K v1.3 | AIC8800 | `sdio0` | ✅ | ✅ | ✅ | `kmod-aic8800s` |
| H29K v5 (1.14") | AIC8800 | `sdio0` | ✅ | ✅ | ✅ | `kmod-aic8800s` |
| H29K v5 (1.49") | AIC8800 | `sdio0` | ✅ | ✅ | ✅ | `kmod-aic8800s` |
| HT2 | AIC8800 | `sdio0` | ✅ | ✅ | ✅ | `kmod-aic8800s` |
| H68K a / a-usb | **AP6256** | `sdio0`? | ✅ | ✅ | — | 见下 |
| H68K new | **AIC8800** | `sdio0` | ✅ | ✅ | — | `kmod-aic8800s` |
| H69K / H69K-mini | AIC8800 | `sdio0` | ✅ | ✅ | — | `kmod-aic8800s` |
| **H68K c / c-usb3 / d / d-usb** | M.2 位 | — | ❌ | ❌ | ❌ | 无 |
| H66K | — | — | ❌ | ❌ | ❌ | 无 |
| H88K v2/v3 | M.2 位 | — | ❌ | ❌ | ❌ | 无 |

### ★ H28K 无WiFi 的厂商证据

厂商 2024 固件 dtb（`vendor-h28x.dtb`）里 `/mmc@ffbf0000` 带 **`no-sdio`** 属性 ——
明确禁用 SDIO。RK3528 的 WiFi 走 sdio0，所以这是厂商自己声明「本机无 WiFi」。
上游 unifreq `rk3528-hlink-h28k.dts` 同样无任何 sdio/wifi 节点，两侧一致。

### ★ H68K c/d 系列无 WiFi

这4 个变体（c / c-usb3 / d / d-usb）的 DTS 里**完全没有 sdio 节点**。
README 的机型表把它们记为「M.2」—— 意思是 WiFi 走 M.2 扩展位，需要用户
自行插模组。因此**不预置 WiFi 驱动**，插上模组后按实际芯片补包
（AP6256 用 `kmod-brcmfmac-ap6256`，AIC8800 用 `kmod-aic8800s`）。

### AP6256 vs AIC8800 的代际差异

| | 老机器（2022–2023） | 新机器（2023末–2024） |
|---|---|---|
| 模组 | **AP6256**（Broadcom） | **AIC8800** |
| 驱动 | `kmod-brcmfmac-ap6256` | `kmod-aic8800s`（需额外固件） |
| 型号 | a / a-usb | c 系列外的新板、new、h69k 系 |

⚠️ AP6256 用 brcmfmac 驱动，AIC8800 用 aic8800s 驱动，**不通用**。
刷机前必须确认自己机器是哪一代，否则 WiFi 不工作。

---

## 四、5G / 4G 模组供电与复位 IO

这是最容易配错的部分 —— 各机型的 IO 完全不同。

### 逐机型明细

| 机型 | 模组供电 | 模组复位/power-gpios | 启动延时 | RF kill |
|---|---|---|---|---|
| **H69K / H69K-mini** | `modem_enable`: GPIO0_C0 低有效，3.3V | — | **2 秒** | ❌ 未配 |
| H69K（iStoreOS 参考） | 同上 GPIO0_C0 | — | 2 秒 | ❌ |
| **H29K v1.3** | 模组有 `power-gpios` = **GPIO4_B5** | — | — | ✅ `rfkill-gpio` |
| **H29K v5** | 模组**不独立控制供电** | — | — | ✅ `rfkill-gpio` |
| H69K（上游 unifreq 参考） | `vcc5v0_sata` GPIO0_C5；`vcc3v8_lte_modem` GPIO0_A5（已注释） | `lte_modem_reset` GPIO0_C0 | — | ✅ `rfkill-gpio` modem |
| **H89K** | `modem_power` GPIO4_A3 低有效 **5V** + `modem_reset` GPIO4_C6 低有效 3.3V | 双路（供电 + 复位分开） | — | ❌ 未配 |
| H68K 系列 | 无（无5G 模组） | — | — | — |

### ⚠️ 关键差异：H89K 与 H29K 的模组 IO 完全相反

```
H29K v1.3:  模组 power-gpios = GPIO4_B5（单路，深处模组自己管）
H89K:       modem_power  = GPIO4_A3  5.0V  低有效   ← 供电
            modem_reset  = GPIO4_C6  3.3V  低有效   ← 复位
```

H89K 是**两路独立 IO**（5V 供电 + 3.3V 复位），H29K 是**一路**。
把H29K 的配置套到 H89K（或反之）都会导致**模组无法上电或无法复位**。

参数来源：H89K 来自厂商 2025 固件 dtb（`vendor-h89k.dtb`）逐项核对，
H29K 来自厂商 DTS。

### 5G 模组 UART

H29K v5 有 `&uart2`（5G 串口），v1.3 没有。这是 v1.3/v5 的重要区别之一，
详见 README §4.6。

### 启动延时的必要性

H69K 的 `modem_enable` regulator 带 `startup-delay-us = <2000000>`（**2 秒**）——
5G 模组上电后需要时间稳定，过早发AT 命令会失败。这个延时来自 iStoreOS，
本仓库已采用。

⚠️ 若换用其他模组或改延时，需实测调整。

### rfkill 缺失

H69K 与 H89K 都**没有** `rfkill-gpio` 节点。H29K 有。
厂商 dtb 里 H89K 也没有 rfkill —— 可能是设计上模组常电，无需 rfkill。
若需要软关机功能，得自己加节点。

---

## 五、SARADC（电池电压）

| 机型 | SARADC | 用途 | 依赖 |
|---|---|---|---|
| **H29K v5** | ch1 (`adc-battery@0`) | 电池电压检测 | ⚠️ **依赖 patch** |
| H29K v1.3 | 无 | — | — |
| 其他机型 | 见各 DTS | — | — |

✅ **不需要 patch** —— Linux 6.18 上游已原生支持 rk3528 SARADC：

```
# drivers/iio/adc/rockchip_saradc.c（6.18 原生）
static const struct iio_chan_spec rockchip_rk3528_saradc_iio_channels[] = {
	SARADC_CHANNEL(0, "adc0", 10), ... SARADC_CHANNEL(3, "adc3", 10),
};
static const struct rockchip_saradc_data rk3528_saradc_data = { ... };
/* of_match_table 里 */ { .compatible = "rockchip,rk3528-saradc", .data = &rk3528_saradc_data, },

# arch/arm64/boot/dts/rockchip/rk3528.dtsi（6.18 原生）
saradc: saradc@ff300000 { compatible = "rockchip,rk3528-saradc"; ... }
```

本仓库早期带的 `9527-rockchip-rk3528-iio-add-adc.patch` 已**删除**（上游已合入）。
只需装 `kmod-iio-adc-rk3528` 让用户态能读。

---

## 六、其他

### LED

各机型 LED 定义见 `target/linux/rockchip/armv8/base-files/etc/board.d/01_leds`。
DTS 里的 `leds` 节点给出引脚，`01_leds` 补netdev / heartbeat 触发规则。

### 按键

- H28K：`adc-keys` on SARADC ch0（KEY_SETUP = BOOT）
- H68K 系列：`gpio-keys` on GPIO0_A0（factory / KEY_RESTART）

### 内核 patch 清单

| patch | 用途 | 必需性 |
|---|---|---|
| `9999-fbtft-read-display-offset-from-dt.patch` | 从 DT 读显示偏移 | H29K 1.14" / H89K 必需 |
| ~~`9527-...-iio-add-adc.patch`~~ | ~~加 rk3528 SARADC 驱动~~ | ❌ **已删除** —— 6.18 上游已原生支持 |
| `9528-linux-delfbcon-cursor.patch` | 禁 framebuffer 硬件光标 | 建议（SPI 小屏上光标会显示异常） |

---

## 七、汇总：待确认清单

| # | 项目 | 机型 | 说明 |
|---|---|---|---|
| 1 | **风扇配置** | H69K / H69K-mini | iStoreOS 有完整 `pwm-fan` + 温控，本仓库未移植。需厂商 dtb 确认 PWM 通道后再加 |
| 2 | **风扇配置** | H89K | pwm3 已使能但无 `pwm-fan` 节点，风扇不会自动调速 |
| 3 | **1.49" 屏偏移** | H29K v5 1.49" | 原厂未提供偏移 patch，172×320 的偏移量未知 |
| 4 | **H89K 屏偏移** | H89K | 40/52 是从 H29K 1.14" 推断的，需实机确认画面完整 |
| 5 | **H89K 背光** | H89K | 厂商 dtb 里无背光节点（屏可能常亮），未配置 |
| 6 | **rfkill** | H69K / H89K | 无软关机节点，是否需要待定 |
| 7 | **WiFi 代际** | H68K a 系列 | AP6256（brcmfmac）vs AIC8800（aic8800s）驱动不通用 |
| 8 | **M.2 WiFi** | H68K c/d / H88K | 无预置驱动，插模组后需按实际芯片补包 |
