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

print("集成完成")
