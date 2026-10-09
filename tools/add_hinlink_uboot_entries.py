#!/usr/bin/env python3
"""在 uboot-rockchip/Makefile 里加入 HINLINK 的 u-boot 条目（照上游 openwrt/main）。

上游 openwrt/main 的条目只登记了 hinlink_h28k / hinlink_h66k / hinlink_h68k
三个设备名；本仓库的机型是按变体拆分的（h68k-a / -c / -c-usb3 / ... / h69k），
所以 BUILD_DEVICES 要把这些名字都登记进去 —— OpenWrt 的 u-boot 包靠
BUILD_DEVICES 反向关联设备，不登记的话 `make defconfig` 会把
CONFIG_PACKAGE_u-boot-hinlink-h68k-rk3568 丢掉（实测过）。

用法：python3 add_hinlink_uboot_entries.py <path/to/uboot-rockchip>
"""
import io
import os
import sys

ENTRIES = """
define U-Boot/hinlink-h28k-rk3528
  $(U-Boot/rk3528/Default)
  NAME:=HINLINK H28K
  BUILD_DEVICES:= \\
    hinlink_h28k_rk3528
endef

define U-Boot/hinlink-h66k-rk3568
  $(U-Boot/rk3568/Default)
  NAME:=HINLINK H66K
  BUILD_DEVICES:= \\
    hinlink_opc-h66k
endef

define U-Boot/hinlink-h68k-rk3568
  $(U-Boot/rk3568/Default)
  NAME:=HINLINK H68K
  BUILD_DEVICES:= \\
    hinlink_opc-h68k-a \\
    hinlink_opc-h68k-a-usb \\
    hinlink_opc-h68k-c \\
    hinlink_opc-h68k-c-usb3 \\
    hinlink_opc-h68k-d \\
    hinlink_opc-h68k-d-usb \\
    hinlink_opc-h68k-new \\
    hinlink_opc-h69k \\
    hinlink_opc-h69k-mini
endef

"""

# 插到 rk3568 段落里（easepi-r1 之前），确保 U-Boot/rk3568/Default 已定义
ANCHOR = 'define U-Boot/easepi-r1-rk3568\n'

# ★ 只定义 U-Boot/xxx 还不够 —— 包由 BuildPackage/U-Boot 遍历 UBOOT_TARGETS
#   展开（include/u-boot.mk 第 144-151 行），列表里没有就不会生成包，
#   make defconfig 也会把 CONFIG_PACKAGE_u-boot-xxx 丢掉。
TARGET_ANCHOR_RK3528 = '  mangopi-m28c-rk3528 \\\n'
TARGET_INSERT_RK3528 = '  hinlink-h28k-rk3528 \\\n'
TARGET_ANCHOR_RK3568 = '  fastrhino-r68s-rk3568 \\\n'
TARGET_INSERT_RK3568 = '  hinlink-h66k-rk3568 \\\n  hinlink-h68k-rk3568 \\\n'


def main():
    pkg = sys.argv[1]
    path = os.path.join(pkg, 'Makefile')
    t = io.open(path, encoding='utf-8').read()
    changed = False

    # --- 1) U-Boot/xxx 条目定义 ---
    if 'U-Boot/hinlink-h68k-rk3568' in t:
        print('[跳过] U-Boot/hinlink-* 条目已存在')
    elif ANCHOR in t:
        t = t.replace(ANCHOR, ENTRIES.lstrip('\n') + ANCHOR, 1)
        changed = True
        print('[改] 已插入 3 个 U-Boot/hinlink-* 条目定义')
    else:
        print('!! 条目锚点未找到：%s' % ANCHOR.strip())
        sys.exit(1)

    # --- 2) UBOOT_TARGETS 变体列表 ---
    if TARGET_ANCHOR_RK3528 not in t:
        print('!! UBOOT_TARGETS 的 rk3528 锚点未找到')
    elif TARGET_INSERT_RK3528 in t:
        print('[跳过] UBOOT_TARGETS 里已有 hinlink-h28k-rk3528')
    else:
        t = t.replace(TARGET_ANCHOR_RK3528,
                      TARGET_INSERT_RK3528 + TARGET_ANCHOR_RK3528, 1)
        changed = True
        print('[改] UBOOT_TARGETS += hinlink-h28k-rk3528')

    if TARGET_ANCHOR_RK3568 not in t:
        print('!! UBOOT_TARGETS 的 rk3568 锚点未找到')
    elif TARGET_INSERT_RK3568 in t:
        print('[跳过] UBOOT_TARGETS 里已有 hinlink-h66k/h68k-rk3568')
    else:
        t = t.replace(TARGET_ANCHOR_RK3568,
                      TARGET_ANCHOR_RK3568 + TARGET_INSERT_RK3568, 1)
        changed = True
        print('[改] UBOOT_TARGETS += hinlink-h66k-rk3568 / hinlink-h68k-rk3568')

    if changed:
        io.open(path, 'w', encoding='utf-8', newline='\n').write(t)
        print('已写入 %s' % path)
    else:
        print('无需改动')


if __name__ == '__main__':
    main()
