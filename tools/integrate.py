#!/usr/bin/env python3
"""把 HinLink 适配层集成进 immortalwrt 树。

board.d（01_leds / 02_network）官方已有内容 → **合并**，不覆盖，
否则会丢掉官方其他机型的配置。
其余（DTS / image mk / patch）直接放。
"""
import io
import os
import re
import glob
import shutil

SRC = os.path.expanduser("~/adapt")
DST = os.path.expanduser("~/iwrt-hinlink")
ROCK = os.path.join(DST, "target/linux/rockchip")


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, t):
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)


def blocks(text):
    """返回每个 case "$board" in ... esac 的 (body_start, esac_start)。"""
    out = []
    i = 0
    while True:
        m = re.search(r'^[ \t]*case\s+"?\$board"?\s+in\s*\n', text[i:], re.M)
        if not m:
            break
        bs = i + m.end()
        e = re.search(r'^[ \t]*esac\n', text[bs:], re.M)
        if not e:
            break
        out.append((bs, bs + e.start()))
        i = bs + e.end()
    return out


def insert_point(body):
    """★ 找插入点：**官方 `*)` 兜底之前**，而不是 esac 之前。

    OpenWrt 的 board.d 每个 case 块末尾都有一个 `*) ;;` 兜底。
    如果把我们的分支插在 esac 之前，就落在 `*)` **之后** ——
    `*)` 会先匹配到我们所有机型，我们的分支永远不会执行
    （这正是上一版 integrate.py 的实际 bug：
      built 固件里 H28K / H29K / HT2 / H88K / H89K 全都没有网络与 LED 配置）。
    """
    m = re.search(r'^[ \t]*\*\)[ \t]*\n', body, re.M)
    return m.start() if m else len(body)


HINLINK_RE = re.compile(r'hinlink,|hlink,|linkstar,')


def merge_boardd(name):
    base_p = os.path.join(ROCK, "armv8/base-files/etc/board.d", name)
    add_p = os.path.join(SRC, "target/linux/rockchip/armv8/base-files/etc/board.d", name)
    base = rd(base_p)
    add = rd(add_p)
    if HINLINK_RE.search(base):
        print("  %-12s 已含 hinlink 条目，跳过" % name)
        return
    bb = blocks(base)
    ab = blocks(add)
    if len(bb) != len(ab):
        print("  %-12s !! case 块数不同 base=%d add=%d -- 跳过" % (name, len(bb), len(ab)))
        return
    out = base
    for (bbs, bee), (abs_, aee) in reversed(list(zip(bb, ab))):
        body = add[abs_:aee]
        # 我方 body 里若有 `*)` 兜底就丢掉（避免吃掉官方机型）
        body = re.sub(r'^[ \t]*\*\)[ \t]*\n(?:[ \t]*[^\n]*\n)*?[ \t]*;;[ \t]*\n',
                      '', body, flags=re.M)
        # 官方用 tab 缩进，我方按 tab 缩进 -> 统一补一层，保持风格一致
        body = "".join(("\t" + ln) if ln.strip() else ln for ln in body.splitlines(True))
        pos = bbs + insert_point(base[bbs:bee])
        out = out[:pos] + body + out[pos:]
    wr(base_p, out)
    print("  %-12s 已合并 %d 个 case 块（插在官方 *) 之前）" % (name, len(bb)))


print("[1] 合并 board.d")
for n in ("01_leds", "02_network"):
    merge_boardd(n)

print("[2] 拷贝 DTS / dtsi（排除 vendor-*.dtb 参考文件）")
sd = os.path.join(SRC, "target/linux/rockchip/files/arch/arm64/boot/dts/rockchip")
dd = os.path.join(ROCK, "files/arch/arm64/boot/dts/rockchip")
os.makedirs(dd, exist_ok=True)
cnt = 0
for f in sorted(os.listdir(sd)):
    if not os.path.isfile(os.path.join(sd, f)):
        continue          # 跳过遗留的目录
    if f.startswith("vendor-"):
        continue
    shutil.copy2(os.path.join(sd, f), os.path.join(dd, f))
    cnt += 1
print("  拷贝 %d 个文件" % cnt)

print("[3] image 定义")
shutil.copy2(os.path.join(SRC, "target/linux/rockchip/image/armv8.mk.hinlink"),
             os.path.join(ROCK, "image/armv8.mk.hinlink"))
amk = os.path.join(ROCK, "image/armv8.mk")
t = rd(amk)
if "armv8.mk.hinlink" not in t:
    t = t.rstrip("\n") + "\n\n# HinLink 机型（外部维护，便于同步）\ninclude ./armv8.mk.hinlink\n"
    wr(amk, t)
    print("  已拷贝 armv8.mk.hinlink 并在 armv8.mk 末尾加 include")
else:
    print("  armv8.mk 已有 include，仅更新 .mk.hinlink")

print("[4] 内核 patch")
pd = os.path.join(ROCK, "patches-6.18")
os.makedirs(pd, exist_ok=True)
for f in sorted(glob.glob(os.path.join(SRC, "patches/*.patch"))):
    b = os.path.basename(f)
    shutil.copy2(f, os.path.join(pd, b))
    print("  + %s" % b)

print("[5] 追加 target 内核 config（FB / fbtft 内建）")
app_p = os.path.join(SRC, "target/linux/rockchip/hinlink-config.append")
if not os.path.exists(app_p):
    print("  (无 hinlink-config.append，跳过)")
else:
    app = rd(app_p)
    # 先删掉上一次追加的块（幂等），再整体追加
    strip_re = re.compile(r'\n*# =+ HinLink begin =+\n.*?# =+ HinLink end =+\n',
                          re.S)
    done = []
    for f in sorted(glob.glob(os.path.join(ROCK, "armv8/config-*"))):
        t = rd(f)
        t = strip_re.sub("\n", t).rstrip("\n") + "\n\n" + app
        wr(f, t)
        done.append(os.path.basename(f))
    print("  追加到 %s" % (", ".join(done) if done else "(未找到 config-*)"))

print("[6] base-files 其它文件（board.d 新文件 / init.d / hotplug.d / uci-defaults / libexec）")
# 说明：board.d 下的 01_leds / 02_network 是"合并"进官方文件的（见 [1] [2]），
#       必须**逐个文件**跳过，否则会把官方机型的配置整段覆盖掉。
#       但 board.d 下**其它**文件（如我们新增的 03_hinlink-lan-ip）应当正常拷贝 ——
#       OpenWrt 的 /bin/board_detect 本来就按 `for a in $(ls /etc/board.d/*)`
#       逐个执行并累加结果，多一个脚本是官方支持的用法。
#       Windows 侧 git 不保留可执行位，所以这里对脚本目录统一 chmod 0755。
bf_src = os.path.join(SRC, "target/linux/rockchip/armv8/base-files")
bf_dst = os.path.join(ROCK, "armv8/base-files")
EXEC_DIRS = ("init.d", "hotplug.d", "uci-defaults", "libexec")
BOARD_D_MERGE = ("01_leds", "02_network")   # 这两个走合并，不做整文件拷贝

# 我方的文件名特征 —— 删除旧文件时只认这些，绝不碰官方文件。
MINE_MARKERS = ("hinlink", "hlink")

nfile = 0
if os.path.isdir(bf_src):
    # --- 先收集源树里应有的相对路径 ---
    want = set()
    for root, dirs, files in os.walk(bf_src):
        rel = os.path.relpath(root, bf_src)
        parts = [] if rel == "." else rel.split(os.sep)
        for f in files:
            if "board.d" in parts and f in BOARD_D_MERGE:
                continue
            want.add(os.path.normpath(os.path.join(rel, f)))

    # --- 清理：目标树里「名字像我方的、但源树已经没有了」的文件 ---
    # ★ 为什么必须做：本脚本只拷不删，一旦我方改名（如 hinlink-modem ->
    #   hinlink-modem-hardreset）或删掉某个文件，旧文件会永久残留在内核树里，
    #   最终被打进固件 —— 表现为「旧 LuCI 页面/旧 ubus 对象仍在」。
    removed = []
    for root, dirs, files in os.walk(bf_dst):
        rel = os.path.relpath(root, bf_dst)
        for f in files:
            if not any(m in f.lower() for m in MINE_MARKERS):
                continue
            rp = os.path.normpath(os.path.join(rel, f)) if rel != "." else f
            if rp not in want:
                os.remove(os.path.join(root, f))
                removed.append(rp)
    # 顺手清掉空目录（我方创建过、现在没文件的）
    for root, dirs, files in os.walk(bf_dst, topdown=False):
        if root == bf_dst:
            continue
        try:
            if not os.listdir(root):
                os.rmdir(root)
        except OSError:
            pass
    if removed:
        print("  清理 %d 个已废弃的我方文件：" % len(removed))
        for r in sorted(removed):
            print("    - %s" % r)

    for root, dirs, files in os.walk(bf_src):
        rel = os.path.relpath(root, bf_src)
        parts = [] if rel == "." else rel.split(os.sep)
        od = bf_dst if rel == "." else os.path.join(bf_dst, rel)
        os.makedirs(od, exist_ok=True)
        for f in sorted(files):
            if "board.d" in parts and f in BOARD_D_MERGE:
                continue
            dp = os.path.join(od, f)
            shutil.copy2(os.path.join(root, f), dp)
            if any(d in parts for d in EXEC_DIRS):
                os.chmod(dp, 0o755)
            nfile += 1
    print("  拷贝 %d 个文件（%s 下已置 0755；board.d 下 %s 走合并）"
          % (nfile, "/".join(EXEC_DIRS), " / ".join(BOARD_D_MERGE)))
else:
    print("  (无 base-files 目录，跳过)")

print("[7] package/beaverfffan（本地包：风扇 / 5G复位 / ssd1306 / aic8800）")
# 这些是**本地包**，不属于任何 feed，直接整目录同步进内核树的 package/ 下。
# 用 rmtree + copytree 而不是逐个拷贝：包目录里会有增删改名（比如给上游
# fancontrol 换默认配置），只拷不删会留下旧文件、甚至出现两个同名包。
pkg_src = os.path.join(SRC, "package/beaverfffan")
pkg_dst = os.path.join(DST, "package/beaverfffan")
if os.path.isdir(pkg_src):
    if os.path.isdir(pkg_dst):
        shutil.rmtree(pkg_dst)
    shutil.copytree(pkg_src, pkg_dst)
    n = sum(len(fs) for _, _, fs in os.walk(pkg_dst))
    for d in sorted(os.listdir(pkg_dst)):
        print("  %s" % d)
    print("  同步 %d 个文件 -> package/beaverfffan" % n)
else:
    print("  (无 package/beaverfffan，跳过)")

print("集成完成")
