# -*- coding: utf-8 -*-
"""开跑前自检 · 任何一项不过就拒绝启动

用法：
    python preflight.py 5          # 检查第5集能不能开跑
    python preflight.py all        # 检查全部 2-6 集

为什么要有它：
    这两天所有"重跑"都源于开跑前没查环境——旧批处理还在跑、卡片HTML跟文案不同步、
    锚点关键词对不上口播、片长算错导致尾部被剪。这些在开跑前 10 秒就能查出来，
    一旦开跑就是 16 分钟白烧。

七项检查（全过才允许开跑）：
    1. 并发     —— 不能有 ffmpeg / run_one_c 在跑（抢文件会写坏成品）
    2. 卡片HTML —— cards_v2_out/<n>/*.html 必须比 cards_v2.py 新
    3. 卡片mp4  —— cards_mp4_v2/<n>/*.mp4 必须存在且非空
    4. 锚点     —— 每张卡的锚点关键词必须逐字出现在 draft_<n>.json 口播里，命中 >= 9/10
    5. 片长     —— plan(n)['total'] 必须 == 177.0
    6. 字幕     —— subs/<n>.ass 必须存在、条数 > 100、末句时间接近片长
    7. 素材     —— 素材_clean2/<n>.mp4 存在且带音轨

退出码 0 = 可开跑；非 0 = 不许开跑。
"""
import json
import io
import os
import subprocess
import sys

R = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(R))
BIN = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin"
FFP = os.path.join(BIN, "ffprobe.exe")
TARGET_DUR = 177.0
MIN_ANCHOR_HIT = 9


def _ps(cmd):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, errors="ignore")
    return r.stdout.strip()


def check_concurrency():
    """1. 并发闸门 —— 最关键，抢文件会把成品写坏（历史事故根因）"""
    # ★ Count 在 0 个匹配时会输出空串，不是 "0" —— 必须把空串当 0，否则永远误报"有并发"
    def _cnt(cmd):
        t = _ps(cmd)
        t = t.strip()
        return 0 if t == "" else int(t)

    try:
        a = _cnt("(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'ffmpeg.exe'}).Count")
        b = _cnt("(Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*run_one_c*'}).Count")
    except ValueError as e:
        return False, "进程查询失败：%s" % e
    if a > 0 or b > 0:
        return False, "有 %d 个 ffmpeg / %d 个 run_one_c 在跑，必须先等它们结束" % (a, b)
    return True, "无并发"


def check_html(n):
    """2. 卡片 HTML 必须比文案源文件新（改了文案没重出HTML = 卡片内容过期）"""
    src = os.path.join(R, "cards_v2.py")
    d = os.path.join(R, "cards_v2_out", str(n))
    if not os.path.isdir(d):
        return False, "缺 cards_v2_out/%d/" % n
    htmls = [f for f in os.listdir(d) if f.endswith(".html")]
    if len(htmls) < MIN_ANCHOR_HIT:
        return False, "HTML 只有 %d 个" % len(htmls)
    oldest = min(os.path.getmtime(os.path.join(d, f)) for f in htmls)
    if oldest < os.path.getmtime(src):
        return False, "cards_v2.py 比 HTML 新（改了文案没重出卡片）"
    return True, "%d 个，且比文案新" % len(htmls)


def check_cards_mp4(n):
    """3. 卡片 mp4 必须已渲染且非空"""
    d = os.path.join(R, "cards_mp4_v2", str(n))
    if not os.path.isdir(d):
        return False, "缺 cards_mp4_v2/%d/" % n
    mp4 = [f for f in os.listdir(d) if f.endswith(".mp4")]
    if len(mp4) < MIN_ANCHOR_HIT:
        return False, "卡片 mp4 只有 %d 个" % len(mp4)
    empty = [f for f in mp4 if os.path.getsize(os.path.join(d, f)) < 10000]
    if empty:
        return False, "%d 个卡片 mp4 是空文件：%s" % (len(empty), empty[:2])
    return True, "%d 个" % len(mp4)


def check_anchors(n):
    """4. 锚点关键词必须逐字出现在本集口播里（对不上=卡片会挤到片尾）"""
    sys.path.insert(0, R)
    import cards_v2 as V
    dp = os.path.join(R, "draft_%d.json" % n)
    if not os.path.exists(dp):
        return False, "缺 draft_%d.json" % n
    d = json.load(io.open(dp, encoding="utf-8"))
    txt = "".join(c["text"] for c in d["cues"])
    cards = V.CARDS_V2.get(n, [])
    miss = [cd[2] for cd in cards if cd[2] not in txt]
    hit = len(cards) - len(miss)
    if hit < MIN_ANCHOR_HIT:
        return False, "锚点只命中 %d/%d，缺：%s" % (hit, len(cards), miss[:3])
    return True, "命中 %d/%d" % (hit, len(cards))


def check_total(n):
    """5. 片长必须 == 177.0（片长算错会把整段口播剪掉，ep6 曾丢 64 秒）"""
    sys.path.insert(0, R)
    import compose_batch2 as C
    p = C.plan(n)
    total = p["total"]
    ncards = len(p["cards"])
    if abs(total - TARGET_DUR) > 0.35:
        return False, "片长 %.1fs（应 %.1f）" % (total, TARGET_DUR)
    if ncards < MIN_ANCHOR_HIT:
        return False, "实际卡片只有 %d 张" % ncards
    ts = [c[1] for c in p["cards"]]
    gap = max(ts[i + 1] - ts[i] for i in range(len(ts) - 1)) if len(ts) > 1 else 999
    if gap > 45:
        return False, "卡片最大间隔 %.0fs（应 <45s，中段空了）" % gap
    return True, "%.1fs / %d 张 / 最大间隔 %.0fs" % (total, ncards, gap)


def check_subs(n):
    """6. 字幕必须存在、够多、末句接近片长（字幕只到163s=转写不全）"""
    import re
    p = os.path.join(R, "subs", "%d.ass" % n)
    if not os.path.exists(p):
        return False, "缺 subs/%d.ass" % n
    txt = io.open(p, encoding="utf-8", errors="ignore").read()
    ev = re.findall(r"Dialogue:\s*\d+,(\d+):(\d+):([\d.]+),(\d+):(\d+):([\d.]+)", txt)
    if len(ev) < 100:
        return False, "字幕只有 %d 条" % len(ev)

    def sec(a, b, c):
        return int(a) * 3600 + int(b) * 60 + float(c)

    end = max(sec(*e[3:]) for e in ev)
    if end < TARGET_DUR - 12:
        return False, "字幕只到 %.0fs（片长 %.0fs，转写可能不全）" % (end, TARGET_DUR)
    return True, "%d 条 / 到 %.0fs" % (len(ev), end)


def check_source(n):
    """7. 素材必须存在且带音轨（缺音轨=成片静音）"""
    src = os.path.join(ROOT, "素材_clean2", "%d.mp4" % n)
    if not os.path.exists(src):
        alt = os.path.join(ROOT, "素材", "%d.mp4" % n)
        if not os.path.exists(alt):
            return False, "缺素材"
        src = alt
    r = subprocess.run([FFP, "-v", "error", "-show_entries", "stream=codec_type",
                        "-of", "csv=p=0", src], capture_output=True, text=True, errors="ignore")
    types = r.stdout
    if "video" not in types:
        return False, "素材无视频流"
    if "audio" not in types:
        return False, "素材无音轨（成片会静音）"
    return True, "视频+音轨齐"


def main():
    if len(sys.argv) < 2:
        print("用法: python preflight.py <集号>|all")
        return 2
    eps = [2, 3, 4, 5, 6] if sys.argv[1] == "all" else [int(sys.argv[1])]

    # 并发是全局的，先查一次
    ok, msg = check_concurrency()
    print(("  ✅" if ok else "  ❌") + " 1 并发: " + msg, flush=True)
    if not ok:
        print("\n❌ 拒绝开跑：等并发结束再来", flush=True)
        return 1

    failed = False
    for n in eps:
        print("\n=== EP%d ===" % n, flush=True)
        for label, fn in [
            ("2 卡片HTML", lambda: check_html(n)),
            ("3 卡片mp4 ", lambda: check_cards_mp4(n)),
            ("4 锚点    ", lambda: check_anchors(n)),
            ("5 片长    ", lambda: check_total(n)),
            ("6 字幕    ", lambda: check_subs(n)),
            ("7 素材    ", lambda: check_source(n)),
        ]:
            ok, msg = fn()
            print(("  ✅" if ok else "  ❌") + " %s: %s" % (label, msg), flush=True)
            if not ok:
                failed = True

    print()
    if failed:
        print("❌ 有检查项未通过，不许开跑。先修好再跑，别浪费 16 分钟。", flush=True)
        return 1
    print("✅ 全部可开跑", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
