# -*- coding: utf-8 -*-
"""字幕生成器（重建版 2026-10-13）
   源：《已校对字幕文本》json（含 start/end/text，原始素材秒）
   映射：成片时间 = (原片秒 − 前面已剪掉的秒数) / SPEED
   输出：ass（libass 本机可用，字体走 fontsdir 指向抖音美好体）
   ★ 位置：底边 y=1600（MarginV=320，避开 y=1620 安全线以下）字号 64（≥60）
"""
import json, os, re, io, sys

SPEED = 1.35
CUTS = {"03": [(174.5, 202.2)], "04": [(165.8, 190.6)], "05": [(182.4, 235.9)], "06": [(169.7, 199.0)]}
FONTDIR = "E:/心理咨询IP/07-形象设计/fonts/fonts-main/DouyinSans"
SUBS = "E:/心理咨询IP/03-内容/字幕校对/已校对字幕文本_第一批10条_20261013.json"
OUT = "E:/心理咨询IP/04-工程/rebuild_20261013/subs"

ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,DouyinSans,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4,1,2,60,60,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def removed_before(t, cuts):
    return sum(max(0.0, min(t, b) - a) for a, b in cuts)


def t_final(t, cuts):
    return (t - removed_before(t, cuts)) / SPEED


def tc(s):
    s = max(0.0, s)
    h = int(s // 3600); m = int((s % 3600) // 60); sec = s % 60
    return "%d:%02d:%05.2f" % (h, m, sec)


def build(ep):
    cuts = CUTS.get(ep, [])
    lines = json.load(io.open(SUBS, encoding="utf-8"))[ep]["lines"]
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "%s.ass" % ep)
    n = 0
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(ASS_HEAD)
        for l in lines:
            a, b = l["start"], l["end"]
            if any(a >= x and b <= y for x, y in cuts):      # 整句在被删段内 → 丢
                continue
            for x, y in cuts:                                 # 跨切口 → 夹到边界
                if x < a < y: a = y
                if x < b < y: b = x
            if b - a < 0.25:
                continue
            f.write("Dialogue: 0,%s,%s,Sub,,0,0,0,,%s\n" % (tc(t_final(a, cuts)), tc(t_final(b, cuts)),
                                                            l["text"].replace("\n", " ")))
            n += 1
    return path, n, [t_final(l["start"], cuts) for l in lines][-1]


if __name__ == "__main__":
    eps = sys.argv[1:] or ["%02d" % i for i in range(10)]
    for ep in eps:
        p, n, last = build(ep)
        print("  %s -> %s  字幕 %d 条  末句 %.1fs" % (ep, os.path.basename(p), n, last))
