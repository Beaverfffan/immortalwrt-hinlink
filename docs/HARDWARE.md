# 特殊硬件清单

本文档逐项列出 HinLink 全系机型的**非网口类**特殊硬件：屏幕、风扇、WiFi、
5G/4G 模组供电与复位 IO、SARADC、按键、LED。

数据来源优先级（见 README §七的方法论）：
**厂商 dtb > 厂商 DTS > iStoreOS DTS > 上游 unifreq DTS > 推断（需实机确认）**

---

## ★ 0. 默认固件的预置策略（2026-10-10 起）

从这一版起，**所有机型（现 16 个）共用同一套预置包**（`Device/hinlink_common`），
不再按机型裁剪无线驱动：

* **无线网卡驱动全带上**（M.2/PCIe + SDIO + USB 三条总线穷举）
  ⇒ 一块固件，插 AP6256 / AIC8800 / 任意 mt76·rtw88·rtw89 模组都能认，
  不必先知道机器是哪一代。
* ★ **驱动 ≠ 固件：固件包必须单独装**（2026-10-12 补）
  `kmod-mt7915e` 这**一个驱动同时支持 MT7915 与 MT7916**，但它
  **DEPENDS 里不含任何固件包**，必须显式加：
  `kmod-mt7915-firmware`（`mt7915_{wa,wm,rom_patch}.bin`）+ 
  `kmod-mt7916-firmware`（`mt7916_{wa,wm,rom_patch}.bin`）。
  漏了就会出现「驱动加载了但没有固件可用」：
  ```
  dmesg | grep -i "firmware load"
  → Direct firmware load for mediatek/mt7916_wm.bin failed
  ```
  H69K / H88K / H89K 的 M.2 / PCIe 位插 MT7916 就靠这两个。
  （对照：`kmod-mt7921e` 的 DEPENDS 自带 `kmod-mt7921-firmware`，
  所以那一路不用手写 —— mt7915e 就是漏在这一条上。）
* **风扇驱动全带上**：`kmod-hwmon-pwmfan` + `kmod-hwmon-gpiofan` +
  `kmod-thermal` + `fancontrol` + `luci-app-fancontrol`（含简体中文）
  ⇒ LuCI「系统 → 风扇控制」直接可调。
* **fbtft 小屏栈改为内核内建**（`CONFIG_FB_TFT*` = y，含本仓库新增的
  GC9307 驱动）—— rockchip 上 package 层的 `kmod-fb*` 被
  `FBDEV_TARGETS` 限制成 bcm27xx/sunxi/x86 专用，拿不到。
* 5G/4G 模组的网络侧驱动也预置：`qmi-wwan` / `cdc-mbim` /
  `usb-serial-option` / `usb-serial-qualcomm` / `usb-modeswitch`。

详细包清单与踩坑见 `README.md §4.12`。

---

---

## 一、屏幕

### 驱动方式分两类

| 类型 | 机型 | 驱动 | 说明 |
|---|---|---|---|
| **fbtft**（内核**内建** =y） | H29K 全系（1.14" / 1.49"）、H89K | `fb_st7789v` / `fb_gc9307` | 屏节点写 `compatible = "sitronix,xxx"` + `width`/`height`/`rotate` |
| **spidev + 用户态** | H88K v3 | `CONFIG_SPI_SPIDEV=y`（内建）+ `kmsd`/`fb_ili9341` 类工具 | iStoreOS 的做法，DTS 里只有 `spidev@0`，**不带屏参数** |

⚠️ `fb_gc9307` 是**本仓库新增**的驱动（`patches/9530-fbtft-add-gc9307-driver.patch`）：
主线 6.18 的 `drivers/staging/fbtft/` 里 grep `gc9307` 零命中，只有 `fb_st7789v.c`。
H29K v5 1.49" 原厂用的就是 GC9307，所以此前这块屏**无驱动可用**。

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
| **H69K / H69K-mini** | **pwm0 → pwm-fan** | ✅✅ 4 档 | ✅ **已移植**（见下） |
| H89K | `pwm3`（febf0020）| — | ⚠️ 只有 PWM，无 pwm-fan 节点 |
| H88K v2/v3 | — | — | ✅ 无风扇（厂商无） |
| H66K / H68K 系列 | — | — | ✅ 无风扇（厂商无） |
| H28K / H29K / HT2 | pwm1/pwm2 作 **vdd_cpu/vdd_logic 调压** | — | ✅ 非风扇用途 |

### H69K / H69K-mini 的风扇配置（已移植）

参数来自 iStoreOS 官方 `rk3568-opc-h69k.dts`，并由「h69k-fan」LuCI 插件的
`DEVELOPMENT.md` 反向验证：

```dts
fan: pwm-fan {
    compatible = "pwm-fan";
    cooling-levels = <0 0x55 0x66 0x77 0x88 0x99 0xbb 0xcc 0xff>;
    #cooling-cells = <2>;
    fan-supply = <&vcc5v0_sys>;
    pwms = <&pwm0 0 50000 0>;
};
&pwm0 { status = "okay"; };
```

**9 档转速**（与插件的 `pct_to_state` 映射表**逐值一致**，改动会让插件档位错位）：

| 档 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| 占空比 | 0% | 33% | 40% | 47% | 53% | 60% | 73% | 80% | 100% |
| 值 | 0 | 0x55 | 0x66 | 0x77 | 0x88 | 0x99 | 0xbb | 0xcc | 0xff |

**温控曲线**（`&cpu_thermal` 的 cooling-maps 绑到 fan）：

| 温度 | 类型 | 风扇档位 |
|---|---|---|
| 20℃ | passive | 最低档常转（`THERMAL_NO_LIMIT`~2） |
| 65℃ | active | 2 ~ 4 |
| 85℃ | active | 4 ~ 6 |
| 95℃ | active | 6 ~ 满档 |
| — | critical | 115℃（内核默认，本仓库未改） |

⚠️ 内核 `rk356x-base.dtsi` 原本的 `cpu_thermal` 只有 passive 的
`cpu_alert0(70℃)` / `cpu_alert1(75℃)` + `critical(95℃)`，且 cooling-map0
绑的是 **CPU**（CPU_FREQ_INCREASE）不是风扇。本仓库覆盖为风扇曲线 ——
**这意味着放弃了内核的 CPU 降频策略**。若要两者兼得，需把两组
cooling-maps 合并（CPU 降频 + 风扇调速）。

⚠️ **设备树无 tach 引脚** → 没有 RPM 反馈，界面只能显示占空比。

### 可选：iStoreOS「h69k-fan」LuCI 插件

用户提供的 `iStoreOS_H69K风扇插件编译 已冻结.zip` 是**纯用户态**方案
（`/usr/libexec/h69k-fan` 是 POSIX shell 脚本，23849 B），**不需要任何内核 patch**。

它的工作方式：

1. **接管**：把 `cpu_thermal` 的 `mode` 写成 `disabled`，
   并把绑定风扇的 trip 温度抬到 `min(105, critical-10)`，
   阻止内核 thermal governor 跟用户态守护争抢 PWM
2. **探测**：遍历 `/sys/class/hwmon/hwmon*/pwm1`（pwm-fan 驱动）
   或 `/sys/class/thermal/cooling_device*/cur_state`（内核 thermal 框架）
3. **调速**：5 档曲线（40/50/60/70/80℃ → 25/35/50/75/100%）+ 迟滞 2℃
   + 低温踢转（0% → 100% 持续 1 秒防停转）
4. **释放**：`release` 时先满速交接，再还原 mode 与 trips

本仓库的 DTS 提供了它所需的 `pwm-fan` 节点，
所以**装上这个插件即可用**，无需改动内核。

配置项在 `/etc/config/h69k-fan`：`enabled` / `mode`(auto|manual) /
`t1..t5` / `s1..s5` / `hysteresis` / `kickstart` / `interval` / `zone`。

⚠️ 插件默认 `enabled '0'`，需在 LuCI「系统 → 风扇控制」里启用并保存。

### H69K / H69K-mini 的风扇：已移植（2026-10-09 起）

上面的 `fan: pwm-fan` + `&cpu_thermal cooling-maps` 已经写进
`rk3568-hinlink-opc.dtsi`（H69K / H69K-mini 共用），**不再是缺口**。
参数取自 iStoreOS 官方 `rk3568-opc-h69k.dts`，并由用户提供的
「iStoreOS_H69K风扇插件编译 已冻结.zip」里 `DEVELOPMENT.md` 的
`pct_to_state` 映射表**逐值反验**（9 档 duty 完全一致）。

固件侧自 2026-10-10 起默认预置：

| 包 | 作用 |
|---|---|
| `kmod-hwmon-pwmfan` | 提供 `/sys/class/hwmon/hwmonX/pwm1`（用户态可读写） |
| `kmod-thermal` / `kmod-hwmon-core` | 内核 thermal 框架与 hwmon 基类 |
| `fancontrol` | 通用 PWM 风扇守护脚本 |
| `luci-app-fancontrol` + `luci-i18n-fancontrol-zh-cn` | LuCI「系统 → 风扇控制」界面 |

⚠️ 若改用 iStoreOS 的「h69k-fan」插件，它会**接管** `cpu_thermal`
（把 mode 写成 disabled、抬 trip 温度），与内核 thermal governor 互斥 ——
两者选一个即可。

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
| H29K v1.3 | AIC8800 | `sdio0` | ✅ | ✅ | ✅ | `kmod-aic8800-sdio` |
| H29K v5 (1.14") | AIC8800 | `sdio0` | ✅ | ✅ | ✅ | `kmod-aic8800-sdio` |
| H29K v5 (1.49") | AIC8800 | `sdio0` | ✅ | ✅ | ✅ | `kmod-aic8800-sdio` |
| HT2 | AIC8800 | `sdio0` | ✅ | ✅ | ✅ | `kmod-aic8800-sdio` |
| H68K a / a-usb | **AP6256** | `sdio0`? | ✅ | ✅ | — | 见下 |
| H68K new | **AIC8800** | `sdio0` | ✅ | ✅ | — | `kmod-aic8800-sdio` |
| H69K / H69K-mini | AIC8800 | `sdio0` | ✅ | ✅ | — | `kmod-aic8800-sdio` |
| **H68K c-d-f / c-d-f-usb** | M.2 位 | — | ❌ | ❌ | ❌ | 无 |
| H66K | — | — | ❌ | ❌ | ❌ | 无 |
| H88K v2/v3 | M.2 位 | — | ❌ | ❌ | ❌ | 无 |

> ⚠️ 表里「M.2 位 / 驱动包 = 无」指的是**板上没有焊死的 WiFi 芯片**
> （走 M.2 / PCIe 扩展位，由用户自行插卡）。**固件里的驱动是全的**（见 §0）：
> M.2/PCIe 位的 `mt7921e` / `mt7925e` / **`mt7915e`（一个驱动同时支持
> MT7915 与 MT7916）** / `mt7615e` / rtw88 / rtw89 全部带上，插卡即可用。
>
> ★ **MT7915 / MT7916 还要额外两个固件包**（`kmod-mt7915-firmware` +
> `kmod-mt7916-firmware`）—— 因为 `kmod-mt7915e` 的 DEPENDS 里**不含固件**。
> 2026-10-12 之前漏装这两个，插 MT7916 会报：
> ```
> Direct firmware load for mediatek/mt7916_wm.bin failed
> ```
> 现在固件里已含 `mt7915_{wa,wm,rom_patch}.bin` 与 `mt7916_{wa,wm,rom_patch}.bin`
> 六个文件（约 3.8 MB 未压缩）。**H69K / H88K / H89K 插 MT7916 就靠这一组。**

### ★ H28K 无WiFi 的厂商证据

厂商 2024 固件 dtb（`vendor-h28x.dtb`）里 `/mmc@ffbf0000` 带 **`no-sdio`** 属性 ——
明确禁用 SDIO。RK3528 的 WiFi 走 sdio0，所以这是厂商自己声明「本机无 WiFi」。
上游 unifreq `rk3528-hlink-h28k.dts` 同样无任何 sdio/wifi 节点，两侧一致。

### ★ H68K c/d 系列无 WiFi

这4 个变体（c / c-usb3 / d / d-usb）的 DTS 里**完全没有 sdio 节点**。
README 的机型表把它们记为「M.2」—— 意思是 WiFi 走 M.2 扩展位，需要用户
自行插模组。**2026-10-10 起改为全系预置**所有可能的无线网卡驱动（M.2/PCIe + SDIO + USB 一起带上），
（AP6256 用 `kmod-brcmfmac`，AIC8800 用 `kmod-aic8800-sdio`）。**2026-10-10 起这些驱动已全部预置在固件里，无需再补。**

### AP6256 vs AIC8800 的代际差异

| | 老机器（2022–2023） | 新机器（2023末–2024） |
|---|---|---|
| 模组 | **AP6256**（Broadcom） | **AIC8800** |
| 驱动 | `kmod-brcmfmac` + 43455 固件/nvram | `kmod-aic8800-sdio`（自带固件） |
| 型号 | a / a-usb | c 系列外的新板、new、h69k 系 |

⚠️ AP6256 用 brcmfmac 驱动，AIC8800 用 aic8800-sdio 驱动，**驱动不通用**。
但自 2026-10-10 起两种驱动（以及 mt76 / rtw88 / rtw89 全家）都预置在固件里，
所以**刷同一块固件即可**，不必先确认自己机器是哪一代。

---

## 四、5G / 4G 模组：启动上电 + 复位流程

本节是「iStoreOS 同款的启动 5G pin 复位流程」的完整实现说明。
**2026-10-12 重写**：此前有三处理解错误，导致 **H69K 的模组其实从来没有
被上电过**、**H29K 的供电脚从来没人驱动** —— 见 §4.4。

### 4.1 机制：两级 `regulator-fixed`，用 `vin-supply` 串起时序

内核侧只有一种可靠做法（iStoreOS 与厂商固件本质也是这个）——
把「供电」和「复位」各做成一个 `regulator-fixed`，再用 `vin-supply`
把复位挂在供电**下面**：

```
        vcc5v0_sys / vcc_3v3_s3           板级常电
                │
                ▼
        vcc3v3_modem     第一级 = 模组供电    startup-delay-us = 5 ms
                │  (vin-supply)
                ▼
        modem_enable     第二级 = 复位释放    startup-delay-us = 2 s
```

★ **为什么必须用 `vin-supply` 串起来，而不是两个平级 regulator 都
`always-on`**：regulator core 的 `_regulator_enable()` 会**先递归 enable
上级电源**（`drivers/regulator/core.c`），所以顺序由内核保证 ——
**先上电、再释放复位**。两个平级的 regulator 则按注册顺序（≈ DTS 节点
书写顺序）enable，顺序不受控；一旦复位先释放，复位就等于没做。

厂商 H89K 的 dtb 就是平级的（`vcc3v3-modem` 与 `modem-enable` 都挂
`vcc_3v3_s3`），本仓库刻意改成串联。

### 4.2 ★★ 极性铁律：只看 `enable-active-high`，DT 里的 phandle flag 被忽略 ★★

**这是本节最重要的一条，也是 H69K bug 的根源，务必记住。**

6.18 的 `drivers/gpio/gpiolib-of.c` 里有一张极性映射表，注释原文：

```
The regulator GPIO handles are specified such that the presence
or absence of "enable-active-high" solely controls the polarity of
the GPIO line. Any phandle flags must be actively ignored.
```

⇒ 对 `regulator-fixed` 的 `gpio` / `gpios` 属性：

| 节点里有没有 `enable-active-high` | 实际极性 | 使能时物理电平 |
|---|---|---|
| **有** | 高电平使能 | 高（3.3 V） |
| **无** | 低电平使能 | 低（0 V） |

⚠️ **`gpios = <&gpio4 RK_PB4 GPIO_ACTIVE_LOW>` 里的 `GPIO_ACTIVE_LOW` 只是装饰**，
内核不读它。绝对不要"照抄 flag"就以为极性对了 —— 必须确认有没有
`enable-active-high`。

（对照：`rfkill-gpio` 走常规 gpiod 路径，flag **有效**；`gpio-hog` 也有效。
只有 `regulator-fixed` / `reg-fixed-voltage` / `regulator-gpio` 这三类
compatible 有这个"忽略 flag"的特殊规则。）

### 4.3 逐机型明细（全部以厂商 dtb 逐字段核对为准）

| 机型 | 供电脚 | 复位脚 | 极性 | 依赖链 | 权威来源 |
|---|---|---|---|---|---|
| **H29K v1.3 / v5（1.14 / 1.49）** | GPIO4_B5 | GPIO4_B4 | **低有效**（都无 EAH） | ✔ 复位挂供电下 | 厂商 dtb<br>`f3_318a000_40194.dtb` |
| **H69K / H69K-mini** | —（单路） | GPIO0_C0 | **低有效**（无 EAH） | vin = `vcc5v0_sys` | 厂商 dtb<br>`dtb_3245000.dtb` |
| **H88K v2 / v3 / H89K** | GPIO4_A3 | GPIO4_C6 | **高有效**（都有 EAH） | ✔ 复位挂供电下 | 厂商 dtb<br>`f3_24c8fc8_88036.dtb` |

（EAH = `enable-active-high`）

三组的极性**互不相同**：H29K / H69K 是**低有效**，H88K / H89K 是**高有效**。
任意两组抄错的结果都是**模组不上电**（H69K 就是这么错的）。

H69K 只有一路 —— 厂商与 iStoreOS 都只给了一个 `modem_enable`
（硬件上这**一个信号**同时担当「模组电源使能」和「复位释放」）。

> ⚠️ 旧版本本节把 H89K 记成「A3 低有效 **5 V**、C6 低有效 3.3 V」——
> **两个极性都写反了**（厂商 dtb 两路都是 `enable-active-high`），
> 电压也写错（两路 `regulator-min-microvolt` 都是 3300000）。已修正。

### 4.4 本次修正（2026-10-12）—— 三个真 bug

| # | 机型 | 原状 | 为什么是错的 | 现在 |
|---|---|---|---|---|
| 1 | **H69K / H69K-mini** | `modem_enable` 里写了 `enable-active-high` | 按 §4.2 变成**高电平使能**，而厂商是低有效 ⇒ 内核开机把 GPIO0_C0 拉**高**，模组从没被上电过 | 删掉该属性 = 低有效 |
| 2 | **H29K v5（1.14 / 1.49）** | `&gpio4 { modem_reset_en { gpio-hog; output-high; } }` | ① 与 `rfkill-modem` 抢**同一个脚** GPIO4_B4；② 语义与厂商相反（占成常高）；③ 写法本身也错（`gpios = <4 RK_PB4 ...>` 里那个 `4` 被当 phandle，内核解析失败） | 整块删除 |
| 3 | **H29K 全系** | 只有 `rfkill-gpio`（`reset-gpios` + `power-gpios`） | 6.18 主线的 `rfkill-gpio.c` **只 request `reset` / `shutdown`，没有 `power`** ⇒ `power-gpios` 被完全忽略，**供电脚 GPIO4_B5 从来没人驱动** | 改成两级 regulator（同 H88K 结构） |

顺带：H88K / H89K 的 `modem_enable` 的 `vin-supply` 从 `vcc_3v3_s3` 改挂
`vcc3v3_modem`，把「供电 → 复位」依赖链补上（厂商是平级的，靠运气）。

#### 为什么 `rfkill-gpio` 那条路走不通（值得记住）

```c
/* net/rfkill/rfkill-gpio.c（6.18 主线） */
rfkill->reset_gpio    = devm_gpiod_get_optional(dev, "reset",    GPIOD_ASIS);
rfkill->shutdown_gpio = devm_gpiod_get_optional(dev, "shutdown", GPIOD_ASIS);
/* ★ 没有 "power" —— power-gpios 属性是空转的 */

ret = gpiod_direction_output(rfkill->reset_gpio, true);  /* probe 时直接拉到"工作态" */
```

两个问题：

1. **`power-gpios` 无实现**（上面那段就是全部）；
2. **时序错**：`rfkill-gpio` 是 platform driver，在 `device_initcall` 阶段
   probe 时就把复位脚拉到工作态；而 `regulator-always-on` 的 enable 发生在
   更晚的 `late_initcall_sync`（`regulator_late_init`）⇒ **复位动作早于供电**，
   等于没复位。

⇒ 在「保留 `/dev/rfkill` 软开关」和「可靠复位时序」之间二选一时，
本仓库选**可靠时序**。要软开关就把 DTS 里的 regulator 段换回 rfkill 段
（各 DTS 的注释里保留了原文），但必须接受上面两点。

### 4.5 内核侧执行时序（可对照 dmesg / 万用表验证）

```
内核启动
  ├─ device_initcall     各 platform driver probe（此时 5G 相关 GPIO 还没人动）
  ├─ ...
  └─ late_initcall_sync  regulator_late_init()
         └─ 对每个 always-on / boot-on 的 regulator 调 _regulator_enable()
              ├─ 先递归 enable 上一级（vin-supply）      ← vcc3v3_modem
              │     gpiod_set_value(ena_gpiod, 1)，等 startup-delay-us(5ms)
              └─ 再 enable 自己                          ← modem_enable
                    gpiod_set_value(ena_gpiod, 1)，等 startup-delay-us(2s)
```

以 H29K 为例（两级都低有效），最终电平：

```
              复位保持        正常工作
供电 GPIO4_B5   高   ──上电──►  低 ┐
                                   │ 5 ms 电源稳定
复位 GPIO4_B4   高   ──释放──►  低 ┘ 然后等 2 s 模组启动
                                   ▲
                        顺序由 vin-supply 保证：B5 先变低，之后 B4 才变低
```

**实机验证命令**（H29K 上电后）：

```sh
# 1. 看两级 regulator 是否都存在且已使能
cat /sys/kernel/debug/regulator/regulator_summary | grep -i modem
#    期望看到 vcc3v3_modem 与 modem_enable，enable_count > 0

# 2. 看引脚当前电平（sysfs gpio 已内建 =y）
for n in 140 141; do echo "gpio$n = $(cat /sys/class/gpio/gpio$n/value 2>/dev/null || echo 未导出)"; done
#    RK3528 gpio4 base = 128 → B4=140, B5=141；工作态应为 0（低）

# 3. 看模组是否枚举出来
lsusb | grep -iE "quectel|fibocom|2cb7|2dee|0e8d"
ls /dev/ttyUSB* /dev/cdc-wdm* 2>/dev/null

# 4. 内核日志里 regulator / gpio 相关
dmesg | grep -iE "regulator|modem|ena_gpio"
```

### 4.6 5G 模组 UART

H29K v5 有 `&uart2`（5G 串口），v1.3 没有。这是 v1.3/v5 的重要区别之一，
详见 README §4.6。

### 4.7 启动延时为什么是 2 秒

三个机型的「复位释放」级都带 `startup-delay-us = <2000000>`（**2 秒**）——
模组上电后需要时间稳定，过早发 AT 命令会失败。这个值来自 iStoreOS / 厂商
dtb，**不要随意调小**。H29K 的「供电」级另有 5 ms 的小延时（等电源轨稳定，
本身也是厂商没有、本仓库补的）。

⚠️ 换用其他模组或调整延时后需实测。

### 4.8 rfkill 现状

改成两级 regulator 后，**四个机型族都没有 `rfkill-gpio` 节点**
（`/dev/rfkill` 里不会有 `wwan`）。厂商 dtb 里 H69K / H89K 本来也没有；
H29K 是本次为「时序可靠」主动去掉的。
需要软关机时见 §4.4 末尾的取舍说明。

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
| `9530-fbtft-add-gc9307-driver.patch` | **新增 GC9307 fbtft 驱动**（主线没有）+ Kconfig/Makefile 条目 | H29K v5 1.49" 必需 |

---

## 七、汇总：待确认清单

| # | 项目 | 机型 | 说明 |
|---|---|---|---|
| 1 | **风扇配置** | H89K | pwm3 已使能但无 `pwm-fan` 节点，风扇不会自动调速 |
| 2 | **1.49" 屏偏移** | H29K v5 1.49" | 原厂未提供偏移 patch，172×320 的偏移量未知 |
| 3 | **H89K 屏偏移** | H89K | 40/52 是从 H29K 1.14" 推断的，需实机确认画面完整 |
| 4 | **H89K 背光** | H89K | 厂商 dtb 里无背光节点（屏可能常亮），未配置 |
| 5 | **rfkill** | H69K / H89K | 无软关机节点，是否需要待定 |
| 6 | ~~**WiFi 代际**~~ | ~~H68K a 系列~~ | ✅ **已解决**：2026-10-10 起固件全系预置 brcmfmac + aic8800 + mt76/rtw88/rtw89 所有驱动 |
| 7 | ~~**M.2 WiFi**~~ | ~~H68K c/d / H88K~~ | ✅ **已解决**：同上，M.2/PCIe 侧 mt7921e/mt7925e/mt7915e/mt7615e/rtw88/rtw89 全部预置 |
| 8 | **CPU 降频** | H69K / H69K-mini | 风扇 cooling-maps 覆盖了内核原有的 CPU_FREQ 映射，需合并才能兼得 |
| 9 | **风扇实测** | H69K / H69K-mini | 9 档 duty 与 4 档温度曲线均取自 iStoreOS，未上机验证转速与噪音 |
| 10 | **AXS5106 触控** | H29K v5 1.49" | 主线无 `chipone,axs5106` 驱动（连 fbtft 的 gc9307 都是本仓库新加的），触控暂不可用 |
| 11 | **GC9307 初始化** | H29K v5 1.49" | `fb_gc9307` 由 `fb_st7789v.c` 派生、init 序列沿用 ST7789V，172×320 实际显示需实机确认 |
