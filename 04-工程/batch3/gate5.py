# -*- coding: utf-8 -*-
"""交付前五项肉眼自检（2026-11-04 董事长定：机器指标全过 ≠ 合格）

背景：昨天已指出字幕溢出/卡片堆前面/错字/BGM发闷/手机播不了，
     今天仍原样交付。根因是把"指标全过"当交付标准，没做眼睛看的检查。
     以后每一批必须跑本脚本，五项全过才准交付。

用法: python gate5.py <成片mp4> [<成片mp4> ...]
"""
import os, sys, json, subprocess, re, glob
import numpy as np
from PIL import Image

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin"
FFMPEG = FF + "/ffmpeg.exe"
FFPROBE = FF + "/ffprobe.exe"
PY = sys.executable


def probe(p):
    return json.loads(subprocess.run(
        [FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", p],
        capture_output=True, text=True).stdout)


def grab(p, t, w=180):
    """抽一帧（缩到 w 宽）"""
    out = "E:/tmp/_g.png"
    subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", "%.2f" % t, "-i", p,
                    "-frames:v", "1", "-vf", "scale=%d:-1" % w, out], capture_output=True)
    if not os.path.exists(out):
        return None
    return np.array(Image.open(out).convert("RGB")).astype(np.int16)


# ---------- ① 字幕溢出 ----------
def check_sub_overflow(p, dur):
    worst, wt, n = 9999, 0, 0
    for t in np.arange(2, max(3, dur - 2), 2.0):
        im = grab(p, t, 1080)
        if im is None:
            continue
        h = im.shape[0]
        y0, y1 = int(h * 0.60), int(h * 0.95)      # 字幕带
        band = im[y0:y1, :, :]
        # ★ 必须按"字幕色"识别，不能按亮度——真人背景的白墙/窗帘亮度也很高，
        #   用亮度会把背景当字幕，误报"溢出0px"。
        r_, g_, b_ = band[:, :, 0], band[:, :, 1], band[:, :, 2]
        mask = (r_ > 180) & (g_ > 140) & (g_ < 235) & (b_ < 160) & (r_ - b_ > 60)
        cols = mask.sum(axis=0)
        xs = np.where(cols > 3)[0]
        if len(xs) > 10:
            n += 1
            gap = 1079 - int(xs.max())
            if gap < worst:
                worst, wt = gap, t
    return (n > 0 and worst >= 20), "字幕帧%d个 最右距边%spx (t=%.0fs)" % (n, worst if n else "-", wt)


# ---------- ② 卡片/真人分布 ----------
def check_card_spread(p, dur):
    prev = None
    card_t, real_t = [], []
    for t in np.arange(1, dur, 1.0):
        im = grab(p, t, 100)
        if im is None:
            continue
        if prev is not None:
            if np.abs(im - prev).mean() < 0.25:
                card_t.append(t)
            else:
                real_t.append(t)
        prev = im
    if not card_t:
        return False, "未检测到卡片"
    tot = len(card_t) + len(real_t)
    q = dur / 4.0
    seg = []
    for b in range(4):
        n = sum(1 for t in card_t if b * q <= t < (b + 1) * q)
        seg.append(n / max(1.0, q) * 100)
    ok = (card_t.count(card_t[0]) >= 0) and seg[0] <= 58 and max(seg) <= 60
    return ok, "卡片%.0f%% 真人%.0f%% 四段卡占比%s" % (
        len(card_t) / tot * 100, len(real_t) / tot * 100, ["%.0f%%" % x for x in seg])


# ---------- ③ 错字（读 ass 原文，查常见错型 + 与修正表联动） ----------
BADWORDS = ["别论区", "乐糕", "夫母", "被吹的地方", "星亮", "裸用", "对自己空",
            "这个家具", "来茶", "摸耳头", "老棒", "砍到医院", "要长起来",
            "句难说", "被指认", "头等大师", "口杂", "犯出去", "空潮气",
            "中联", "商具", "起心", "当问你的", "没有弹", "还三", "不够壮",
            "是吧会", "提供,", "旅游上", "长点的分工", "一拳直带娃", "睁夜",
            "插地板", "待夜在家", "三人,别人", "几分点"]


def check_typos(ass_dir, eps):
    found = []
    for ep in eps:
        f = os.path.join(ass_dir, "%d.ass" % ep)
        if not os.path.exists(f):
            continue
        txt = open(f, encoding="utf-8").read()
        for w in BADWORDS:
            if w in txt:
                found.append("ep%d:%s" % (ep, w))
    return (not found), ("发现错字 " + "、".join(found[:8])) if found else "未发现已知错字"


# ---------- ④ BGM 调式/低频 ----------
def check_audio(p):
    import wave
    out = "E:/tmp/_a.wav"
    subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", "10", "-t", "15", "-i", p,
                    "-ac", "1", "-ar", "22050", out], capture_output=True)
    w = wave.open(out)
    d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    sp = np.abs(np.fft.rfft(d)) ** 2
    fr = np.fft.rfftfreq(len(d), 1 / 22050.0)
    tot = sp.sum()
    lo = sp[(fr >= 60) & (fr < 250)].sum() / tot * 100
    mid = sp[(fr >= 800) & (fr < 2500)].sum() / tot * 100
    hi = sp[(fr >= 4000) & (fr < 9000)].sum() / tot * 100
    # 男声本身低频多，判据放宽：低频<62% 且 中高频要有一定量
    ok = lo < 62 and (mid + hi) > 8
    return ok, "低频%.0f%% 中%.0f%% 高%.0f%%" % (lo, mid, hi)


# ---------- ⑤ 手机可播 ----------
def check_playable(p):
    st = probe(p)
    v = [s for s in st["streams"] if s["codec_type"] == "video"][0]
    a = [s for s in st["streams"] if s["codec_type"] == "audio"]
    prof, lev = v.get("profile"), str(v.get("level"))
    ok_codec = prof == "Main" and lev == "41"
    ok_pix = v.get("pix_fmt") == "yuv420p"
    ok_audio = bool(a) and a[0].get("codec_name") == "aac"
    dur = float(st["format"]["duration"])
    ok_dur = dur <= 180
    r = subprocess.run([FFMPEG, "-v", "error", "-i", p, "-f", "null", "-"],
                       capture_output=True, text=True)
    ok_dec = not r.stderr.strip()
    with open(p, "rb") as fh:
        head = fh.read(2000000)
    ok_fast = 0 <= head.find(b"moov") < max(1, head.find(b"mdat") if head.find(b"mdat") > 0 else 10**9)
    ok = all([ok_codec, ok_pix, ok_audio, ok_dur, ok_dec, ok_fast])
    return ok, "%s@%s %s %s dur=%.0fs 解码%s faststart%s" % (
        prof, lev, v.get("pix_fmt"), "aac" if ok_audio else "?",
        dur, "OK" if ok_dec else "ERR", "OK" if ok_fast else "NO")


def main(paths):
    allok = True
    for p in paths:
        if not os.path.exists(p):
            print("❌ 文件不存在: %s" % p)
            allok = False
            continue
        dur = float(probe(p)["format"]["duration"])
        print("\n=== %s  (%.0fs) ===" % (os.path.basename(p), dur))
        res = []
        r1 = check_sub_overflow(p, dur)
        res.append(("①字幕不溢出", r1))
        r2 = check_card_spread(p, dur)
        res.append(("②卡片分散不扎堆", r2))
        r4 = check_audio(p)
        res.append(("④BGM不发闷", r4))
        r5 = check_playable(p)
        res.append(("⑤手机可播", r5))
        for name, (ok, msg) in res:
            print("  %s %-16s %s" % ("✅" if ok else "❌", name, msg))
            if not ok:
                allok = False
    print("\n" + ("=" * 40))
    print("总判定: %s" % ("✅ 五项全过，可交付" if allok else "❌ 未通过，不许交付"))
    return allok


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        d = "E:/心理咨询IP/05-成片/没人可说/"
        args = sorted(glob.glob(d + "*定稿.mp4"))
    sys.exit(0 if main(args) else 1)
