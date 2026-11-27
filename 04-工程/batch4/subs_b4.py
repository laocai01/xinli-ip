# -*- coding: utf-8 -*-
"""batch4 字幕生成（源 = 已校对字幕_N.json，时间轴 = ASR 逐句 cues）

铁律（董事长 2026-11-18）：
  · 字幕必须与口播一字不差，不许错字
  · 时间轴来自 ASR 逐句 cues，不许按字数均分
  · 断句只按标点切；超宽才按语义停顿拆
  · 中文按 字号×1.06 算宽，SAFE_W=880
  · 同屏最多 3 行，字顶 >= 1300
"""
import os
import io
import re

R4 = os.path.dirname(os.path.abspath(__file__))
OUTDIR = R4 + "/subs"
FONT_DIR = "E:/心理咨询IP/07-形象设计/fonts/fonts-main/DouyinSans"

FONTSIZE = 96
MARGIN_L = 58
BASELINE_Y = 1600
SAFE_W = 880
MIN_FS = 56
MAX_ROWS = 3

PUNC = "，。、；：？！“”‘’（）《》【】…—,.;:?!\"'()[]~· "
BREAK_PUNC = "，。！？、；："

ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Ref,DouyinSansBold,__FS__,&H0066E0FF,&H001A7AFF,&H002A1A08,&HCC000000,-1,0,0,0,100,100,2.2,0,1,9.5,8.5,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def tc(s):
    if s < 0:
        s = 0
    h = int(s // 3600)
    m = int(s % 3600 // 60)
    return "%d:%02d:%05.2f" % (h, m, s % 60)


def clean(t):
    t = t.strip()
    for p in PUNC:
        t = t.replace(p, "")
    return t


def text_px(t, size):
    """真实字宽：中文=字号，数字/英文=0.55 字号，加粗 ×1.06"""
    w = sum(size * 1.00 if ord(c) > 128 else size * 0.55 for c in t)
    return w * 1.06


def split_by_punct(t):
    """只按标点切，保留片段"""
    parts = re.split("([%s])" % BREAK_PUNC, t)
    out, cur = [], ""
    for x in parts:
        if x in BREAK_PUNC:
            cur += x
            out.append(cur)
            cur = ""
        else:
            cur += x
    if cur.strip():
        out.append(cur)
    return [x for x in out if x.strip()]


def wrap(t, size, max_w=SAFE_W):
    """超宽才按语义停顿词拆（最多 4 轮）"""
    t = clean(t)
    if not t:
        return []
    if text_px(t, size) <= max_w:
        return [t]
    # 语义停顿词优先
    for stop in ("然后", "但是", "因为", "所以", "其实", "不是", "就是", "这时候", "等我"):
        i = t.find(stop, 4)
        if 0 < i < len(t) - 3 and text_px(t[:i], size) <= max_w:
            return wrap(t[:i], size, max_w) + wrap(t[i:], size, max_w)
    # 按能放下的最大字数切
    k = len(t)
    while k > 2 and text_px(t[:k], size) > max_w:
        k -= 1
    return wrap(t[:k], size, max_w) + wrap(t[k:], size, max_w)


def pick_size(t):
    """按最长片段反推字号（>=MIN_FS）"""
    size = FONTSIZE
    longest = max((clean(x) for x in split_by_punct(t)), key=len, default="")
    while size > MIN_FS and text_px(longest, size) > SAFE_W:
        size -= 2
    return size


def build(n, cues, speed=1.0):
    os.makedirs(OUTDIR, exist_ok=True)
    # ① 先合并过短的 ASR 句（<1.2s），保证每句有时间做逐字淡入
    merged = []
    for c in cues:
        a, b = c["start"] / speed, c["end"] / speed
        t = c["text"]
        if merged and (b - a) < 1.2 and (merged[-1][1] - merged[-1][0]) < 2.6:
            pa, pb, pt = merged[-1]
            merged[-1] = (pa, b, pt + " " + t)
        else:
            merged.append((a, b, t))
    # 尾部过短的并入前句
    if len(merged) >= 2 and (merged[-1][1] - merged[-1][0]) < 1.0:
        pa, pb, pt = merged[-2]
        la, lb, lt = merged[-1]
        merged[-2] = (pa, lb, pt + " " + lt)
        merged.pop()

    lines = []
    for a, b, txt in merged:
        fs = pick_size(txt)
        segs = []
        for part in split_by_punct(txt):
            segs += wrap(part, fs)
        segs = [x for x in segs if x]
        if not segs:
            continue
        # 同一句内多行：按字数比例分时间
        tot = sum(len(x) for x in segs)
        cur = a
        for x in segs:
            d = (b - a) * len(x) / tot
            lines.append((cur, cur + d, x, fs))
            cur += d

    # ASS 写出
    head = ASS_HEAD.replace("__FS__", str(FONTSIZE)).replace(
        "__ML__", str(MARGIN_L)).replace("__MV__", str(1920 - BASELINE_Y))
    body = []
    for a, b, s, fs in lines:
        # ★ 动态（2026-11-18）：整句从下方 26px 升起 0.22s + 逐字淡入（每字 45ms）
        #   位置固定槽位（绝不滚动）；\an1 左下锚，从 pos 点向右展开
        chars = []
        for i, ch in enumerate(s):
            d = i * 45
            chars.append("{\\alpha&HFF&\\t(%d,%d,\\alpha&H00&)}%s" % (d, d + 110, ch))
        tag = ("{\\an1\\pos(%d,%d)\\fs%d\\fad(120,100)\\move(%d,%d,%d,%d,0,220)}"
               % (MARGIN_L, BASELINE_Y + 26, fs,
                  MARGIN_L, BASELINE_Y + 26, MARGIN_L, BASELINE_Y))
        body.append("Dialogue: 0,%s,%s,Ref,,0,0,0,,%s%s" % (tc(a), tc(b), tag, "".join(chars)))
    p = os.path.join(OUTDIR, "%d.ass" % n)
    io.open(p, "w", encoding="utf-8").write(head + "\n".join(body) + "\n")
    return p
