#!/usr/bin/env python3
"""机型口数自检：交叉校验 DTS 的网口构成 与 02_network 的接口映射。

背景
----
RK3568 板上有两类网口控制器：
  - GMAC（SoC 内部，枚举顺序固定）-> gmac0=eth0、gmac1=eth1
  - PCIe 2.5G（PCI 设备，枚举顺序随硬件变）-> rtl8125_1=eth2、rtl8125_2=eth3

机器的口数 = okay 的 GMAC 数 + okay 的 PCIe 控制器数。
02_network 里的 LAN+WAN 接口数必须与口数一致，否则少一个口的机器会配错。

★ 关键：DTS 通常不显式覆写 pcie3x1/pcie3x2，继承 rk3568-hinlink-opc.dtsi
  （dtsi 里两者都是 status="okay"）。所以必须把 dtsi 作为基线合并计算，
  只扫 DTS 会把四网口机误判成两网口。

用法：python3 tools/check_port_count.py <仓库根目录>
退出码：不一致时 1，一致时 0
"""
import re
import sys
import os
import glob
import io

root = sys.argv[1] if len(sys.argv) > 1 else '.'
DTS = os.path.join(root, 'target/linux/rockchip/files/arch/arm64/boot/dts/rockchip')
NET = os.path.join(root, 'target/linux/rockchip/armv8/base-files/etc/board.d/02_network')
DTSI = os.path.join(DTS, 'rk3568-hinlink-opc.dtsi')

# 期望口数（人工确认的硬件事实）。改 DTS 时必须同步改这里。
EXPECT = {
    'rk3568-hinlink-h66k':        2,  # 无板载 GMAC，2xRTL8125（PCIe 枚举）
    'rk3568-hinlink-h68k-a':      2,  # 2022 双千兆，2xGMAC，无 PCIe
    'rk3568-hinlink-h68k-a-usb':  2,
    'rk3568-hinlink-h68k-c':      4,  # 2xGMAC + 2xRTL8125
    'rk3568-hinlink-h68k-c-usb':  4,
    'rk3568-hinlink-h68k-c-usb3': 4,
    'rk3568-hinlink-h68k-d':      4,
    'rk3568-hinlink-h68k-d-usb':  4,
    'rk3568-hinlink-h68k-new':    4,
    'rk3568-hinlink-h69k-3eth':   3,  # 屏蔽 gmac1 -> 1xGMAC + 2xRTL8125
    'rk3568-hinlink-h69k-mini':   4,  # = H68K max，2xGMAC + 2xRTL8125
}

# 只读这些节点
PORTS = ('gmac0', 'gmac1', 'pcie3x1', 'pcie3x2')


def node_status(text, node):
    """返回 DTS/DTSI 中某节点的 status；节点不存在返回 None。"""
    m = re.search(r'(?:^|\n)&?' + re.escape(node) + r' \{(.*?)\n\t\};',
                  text, re.S)
    if not m:
        return None
    s = re.search(r'status = "(\w+)"', m.group(1))
    return s.group(1) if s else 'okay'      # 未显式写 status 视为 okay


def dts_ports(dts, dtsi):
    """口数 = okay 的 GMAC + okay 的 PCIe 控制器。DTS 覆盖 dtsi。"""
    n = 0
    for node in PORTS:
        st = node_status(dts, node)
        if st is None:
            st = node_status(dtsi, node)
        if st == 'okay':
            n += 1
    return n


def parse_net(path):
    """解析 board.d/02_network 的 case 标签 -> (LAN, WAN)。

    case 标签有两种形态：
      A) 标签在行首，含反斜杠续行：
           hinlink,opc-h68k-a|\\
           <TAB>hinlink,opc-h68k-a-sata|\\
           <TAB>linkstar,opc-h68k-a)
      B) 单行无续行：
           hinlink,opc-h69k)
    两种都要匹配上，且续行里的 compatible 不能漏。
    """
    text = io.open(path, encoding='utf-8').read()
    cases = {}
    # 反斜杠续行：'|' 后紧跟 '\' + 换行 + 缩进 + 下一个标签
    cont = r'(?:\|\\\r?\n[\t ]*[a-z0-9][a-z0-9,\-]*)*'
    pat = re.compile(
        r'((?:^|\n)[a-z0-9][a-z0-9,\-]*' + cont + r'\))'
        r'[\t ]*\r?\n[\t ]*ucidef_set_interfaces_lan_wan \'([^\']*)\' \'([^\']*)\'',
        re.M)
    for m in pat.finditer(text):
        # 首项会带上匹配起始的换行符，续行会带上续行的反斜杠，统一清洗
        labels = [x.strip().strip('\\').strip() for x in m.group(1)[:-1].split('|')]
        lan = [x for x in m.group(2).split() if x]
        wan = [x for x in m.group(3).split() if x]
        for cp in labels:
            if cp:
                cases[cp] = (lan, wan)
    return cases


def main():
    dtsi = io.open(DTSI, encoding='utf-8').read()
    net = parse_net(NET)

    print('%-40s %7s %6s %8s  %s' % ('DTS', 'DTS口', '期望', '映射数', 'LAN / WAN'))
    print('-' * 100)

    bad = 0
    files = sorted(glob.glob(os.path.join(DTS, 'rk3568-hinlink-h6*.dts')))
    if not files:
        print('未找到 DTS 文件，检查路径：%s' % DTS)
        return 1

    for fn in files:
        base = os.path.basename(fn)[:-4]
        text = io.open(fn, encoding='utf-8').read()
        cp = re.search(r'compatible = "([^"]+)"', text)
        cp = cp.group(1) if cp else '?'

        n = dts_ports(text, dtsi)
        exp = EXPECT.get(base, '?')

        if cp in net:
            lan, wan = net[cp]
            m = len(lan) + len(wan)
            mapping = '%s / %s' % (' '.join(lan), ' '.join(wan))
        else:
            m = None
            mapping = '(02_network 无此 compatible)'

        ok = True
        if exp != '?':
            if n != exp:
                ok = False
            if m is not None and m != exp:
                ok = False
        if m is None and exp != '?':
            ok = False

        if not ok:
            bad += 1
        print('%-40s %7d %6s %8s  %-34s %s' % (
            base, n, exp, m if m is not None else '-', mapping,
            'OK' if ok else '<<< 不一致'))

    print()
    print('DTS 机型数: %d    不一致: %d' % (len(files), bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
