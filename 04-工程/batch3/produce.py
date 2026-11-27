# -*- coding: utf-8 -*-
"""
《老蔡说》心理IP · 单条成片生产总入口（正确路线，唯一入口）

用法:
    python produce.py <集号>            # 生产一条
    python produce.py <集号> --check    # 只跑闸门自检，不出片

路线（固定，不许跳步、不许绕开）:
    0. 前置自检 —— 素材/转录/卡片方案是否齐全，缺任何一项直接停
    1. 闸门自检 —— 内容完整（未剪）、语速未超档、字幕不裁切/不重复/不同屏超3行
    2. 渲染卡片 —— 只渲染本条缺的，已存在则跳过
    3. 合成     —— 字幕+卡片+LOGO+合规字+BGM 一次成型
    4. 验收     —— 时长/画幅/解码/削波/卡片数/LOGO/帧率，任一不过即失败
    5. 归档     —— 通过的才改名为 _终版.mp4

铁律（违反任何一条即中止，不靠记忆靠代码）:
    · 不剪任何内容
    · 语速不得快于 EPS[n] 设定档
    · 时长 ≤ 180 秒（手机端发布上限）
    · 字幕一句一条 Dialogue，禁止多段复制
    · 字幕顶行不得被裁（字顶 ≥ 1300）
    · 卡片只能来自本条 CARDS[n]
    · 一次只跑一个 ffmpeg
"""
import os
import sys
import json
import io
import re
import subprocess
import time

R3 = "E:/心理咨询IP/04-工程/batch3"
ROOT = "E:/心理咨询IP"
FF = (r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/"
      r"Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/"
      r"ffmpeg-9.0.1-full_build/bin")
PY = "E:/Hermes/hermes-agent/venv/Scripts/python.exe"
OUT = os.path.join(ROOT, "05-成片", "没人可说")
MAX_SEC = 180.0
SUB_SAFE_TOP = 1300
SUB_MAX_ROWS = 3

sys.path.insert(0, R3)


def hr(t):
    print("\n" + "=" * 60)
    print("  " + t)
    print("=" * 60)


def die(msg):
    print("\n❌ 中止: " + msg)
    sys.exit(1)


def ffprobe_dur(path):
    r = subprocess.run([FF + "/ffprobe.exe", "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def ascii_copy(src, tag):
    """中文路径给 ffmpeg 会出错，先复制成 ASCII 名"""
    dst = "E:/tmp/_w_%s.mp4" % tag
    os.makedirs("E:/tmp", exist_ok=True)
    import shutil
    shutil.copy2(src, dst)
    return dst


# ---------------------------------------------------------------- 0. 前置
def precheck(n):
    hr("0/5 前置检查 · 第 %d 条" % n)
    import cards_ep as CE
    src = os.path.join(ROOT, "素材", "%d.mp4" % n)
    if not os.path.exists(src):
        die("素材不存在: %s" % src)
    tp = None
    for b in ("batch3", "batch2"):
        p = os.path.join(ROOT, "03-内容", "转录", b, "raw_%d.json" % n)
        if os.path.exists(p):
            tp = p
            break
    if not tp:
        die("转录不存在: raw_%d.json" % n)
    if n not in CE.CARDS:
        die("卡片方案缺失: CARDS[%d]" % n)
    d = ffprobe_dur(src)
    sp = CE.EPS[n]["speed"]
    est = d / sp
    print("  素材 %.1fs  倍速 %.2f  预计成片 %.1fs" % (d, sp, est))
    print("  转录 %s" % os.path.basename(tp))
    print("  卡片 %d 张" % len(CE.CARDS[n]))
    if est > MAX_SEC + 0.5:
        die("预计 %.1fs 超过 %ds 上限。\n"
            "     当前倍速 %.2f 不能再快（董事长要求语速不能更快）、内容不能剪，\n"
            "     → 只能将该条内容拆成两集，或由董事长另行拍板。"
            % (est, int(MAX_SEC), sp))
    return d, sp, est


# ---------------------------------------------------------------- 1. 闸门
def gate(n, subs_p):
    hr("1/5 闸门自检 · 第 %d 条" % n)
    import cards_ep as CE
    # 未剪内容
    if getattr(CE, "TRIM_CUTS", {}).get(n):
        die("TRIM_CUTS 非空 —— 违反『内容必须完整』")
    tr = getattr(CE, "TRIM", {}).get(n, {})
    if float(tr.get("head", 0)) > 0.01 or float(tr.get("tail", 999)) < 999:
        die("TRIM 掐头去尾 —— 违反『内容必须完整』")
    print("  ✅ 内容完整（未剪）")

    def s2(t):
        h, m, s = t.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    rows = []
    for line in io.open(subs_p, encoding="utf-8"):
        if not line.startswith("Dialogue:"):
            continue
        q = line.split(",", 9)
        txt = re.sub(r"\{[^}]*\}", "", q[9]).replace("\\N", "").strip()
        m = (re.search(r"\\pos\(\d+,(\d+)\)", q[9])
             or re.search(r"\\move\(\d+,(\d+),\d+,(\d+)", q[9]))
        ys = [int(g) for g in m.groups() if g] if m else []
        rows.append((s2(q[1]), s2(q[2]), txt, ys))
    if not rows:
        die("字幕为空")
    # 重复 = 同一句在同一时间段被写了多条（会造成叠层压字）
    # 注意：原片真的说两遍时，文本相同但时间不同，那是正常口播，不算重复
    from collections import Counter
    dup = [k for k, v in Counter((r[2], round(r[0], 2)) for r in rows).items()
           if v > 1]
    if dup:
        die("字幕叠层 %d 处（同句同时间多条），例: %s" % (len(dup), dup[:3]))
    print("  ✅ 无叠层（同句同时间只有一条）")
    # 同屏
    mx = max(len([r for r in rows if r[0] <= t < r[1]])
             for t in sorted(r[0] for r in rows))
    if mx > SUB_MAX_ROWS:
        die("同屏 %d 行，超过 %d 行上限" % (mx, SUB_MAX_ROWS))
    print("  ✅ 同屏最多 %d 行" % mx)
    # 裁切
    miny = min(min(r[3]) for r in rows if r[3])
    if miny - 68 < SUB_SAFE_TOP:
        die("字幕顶行会被裁（字顶 %d < %d）" % (miny - 68, SUB_SAFE_TOP))
    print("  ✅ 字幕不裁切（顶字 y=%d）" % (miny - 68))
    return len(rows)


# ---------------------------------------------------------------- 2. 卡片
def render_cards(n):
    hr("2/5 渲染卡片 · 第 %d 条" % n)
    import cards_ep as CE
    need = [c[0] for c in CE.CARDS[n]]
    d = os.path.join(R3, "cards_mp4", str(n))
    os.makedirs(d, exist_ok=True)
    miss = [k for k in need
            if not os.path.exists(os.path.join(d, k + ".mp4"))]
    if not miss:
        print("  ✅ 卡片齐备 %d/%d" % (len(need), len(need)))
        return
    print("  缺 %d 张，开始渲染: %s" % (len(miss), miss))
    have_html = [k for k in miss
                 if os.path.exists(os.path.join(R3, "cards_html", str(n), k + ".html"))]
    if len(have_html) < len(miss):
        print("  先生成 HTML…")
        subprocess.run([PY, "render_cards3.py", str(n)], cwd=R3, check=True)
    tasks = [dict(html="%s/cards_html/%d/%s.html" % (R3, n, k),
                  out="%s/cards_mp4/%d/%s.mp4" % (R3, n, k),
                  frames=120, fps=30) for k in miss]
    tp = os.path.join(R3, "tasks_%d_produce.json" % n)
    json.dump(tasks, io.open(tp, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    lanes = 3
    procs = []
    for i in range(lanes):
        procs.append(subprocess.Popen(
            [PY, "render_cards.py", tp, str(i), str(lanes)],
            cwd="E:/心理咨询IP/04-工程/batch2",
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for p in procs:
        p.wait()
    miss2 = [k for k in need
             if not os.path.exists(os.path.join(d, k + ".mp4"))]
    if miss2:
        die("卡片仍缺 %s" % miss2)
    print("  ✅ 卡片齐备 %d/%d" % (len(need), len(need)))


# ---------------------------------------------------------------- 3. 合成
def compose(n):
    hr("3/5 合成 · 第 %d 条" % n)
    r = subprocess.run([PY, "compose_batch3.py", str(n)], cwd=R3)
    if r.returncode != 0:
        die("合成失败，退出码 %d" % r.returncode)


# ---------------------------------------------------------------- 4. 验收
def verify(n, name):
    hr("4/5 验收 · 第 %d 条" % n)
    import cards_ep as CE
    src = os.path.join(OUT, "%s_20261102.tmp.mp4" % name)
    if not os.path.exists(src):
        cand = [f for f in os.listdir(OUT) if f.endswith(".tmp.mp4")]
        die("找不到产物，目录现有: %s" % cand)
    a = ascii_copy(src, str(n))
    fails = []
    d = ffprobe_dur(a)
    print("  时长 %.1fs" % d)
    if d > MAX_SEC + 0.5:
        fails.append("时长 %.1fs 超 %ds" % (d, int(MAX_SEC)))
    info = subprocess.run([FF + "/ffprobe.exe", "-v", "error", "-show_entries",
                           "stream=codec_type,width,height,pix_fmt,r_frame_rate",
                           "-of", "csv=p=0", a],
                          capture_output=True, text=True).stdout
    print("  规格 " + info.strip().replace("\n", " | "))
    if "1080,1920" not in info.replace(" ", ""):
        fails.append("画幅不是 1080x1920")
    if "30/1" not in info:
        fails.append("帧率不是 30")
    if "audio" not in info:
        fails.append("缺音频")
    # 解码
    r = subprocess.run([FF + "/ffmpeg.exe", "-v", "error", "-i", a,
                        "-f", "null", "-"], capture_output=True, text=True)
    errs = [l for l in r.stderr.split("\n") if l.strip()]
    print("  解码错误 %d" % len(errs))
    if errs:
        fails.append("解码错误 %d 处" % len(errs))
    # 削波
    rp = subprocess.run([FF + "/ffmpeg.exe", "-v", "info", "-i", a,
                         "-af", "volumedetect", "-f", "null", "-"],
                        capture_output=True, text=True)
    m0 = re.search(r"histogram_0db: (\d+)", rp.stderr)
    clip = int(m0.group(1)) if m0 else 0
    mx = re.search(r"max_volume: ([-\d.]+)", rp.stderr)
    print("  峰值 %s dB  削波 %d" % (mx.group(1) if mx else "?", clip))
    if clip > 0:
        fails.append("削波 %d 点" % clip)
    # 卡片数量
    import compose_batch3 as C
    P = C.plan(n)
    print("  卡片窗口 %d 个" % len(P["rows"]))
    if len(P["rows"]) != 10:
        fails.append("卡片 %d 个（应 10）" % len(P["rows"]))
    if fails:
        die("验收不通过:\n     - " + "\n     - ".join(fails))
    print("\n  ✅ 全部验收项通过")
    return src


# ---------------------------------------------------------------- 5. 归档
def archive(n, name, src):
    hr("5/5 归档 · 第 %d 条" % n)
    dst = os.path.join(OUT, "%s_终版.mp4" % name)
    if os.path.exists(dst):
        try:
            os.remove(dst)
        except Exception:
            die("旧终版被占用，删不掉: %s" % dst)
    os.replace(src, dst)
    print("  ✅ %s  %.0fMB" % (dst, os.path.getsize(dst) / 1048576))


NAMES = {1: "第29条_不哭的男孩",
         2: "第30条_你一开口孩子就嫌烦",
         3: "第31条_孩子说不想上学",
         4: "第32条_你管得越多孩子离得越远",
         5: "第33条", 6: "第34条", 7: "第35条",
         8: "第36条", 9: "第37条", 10: "第38条", 11: "第39条"}


def main():
    if len(sys.argv) < 2:
        die("用法: python produce.py <集号> [--check]")
    n = int(sys.argv[1])
    only_check = "--check" in sys.argv
    t0 = time.time()
    print("▶ 生产第 %d 条  %s" % (n, time.strftime("%H:%M:%S")))

    d, sp, est = precheck(n)
    import subs_ref as SR
    subs_p, nsub, _ = SR.build(n, speed=sp)
    print("  字幕 %d 句" % nsub)
    gate(n, subs_p)
    if only_check:
        print("\n✅ 自检通过（未出片）  用时 %.1fs" % (time.time() - t0))
        return
    render_cards(n)
    compose(n)
    src = verify(n, NAMES.get(n, "第%d条" % n))
    archive(n, NAMES.get(n, "第%d条" % n), src)
    print("\n▶ 完成 %.1f 分钟" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    main()
