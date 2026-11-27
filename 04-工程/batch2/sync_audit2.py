# -*- coding: utf-8 -*-
"""真同步检测：把成片的人声轨和 ASS 字幕做"逐句对照"。
   方法（不用耳朵也能量）：
   ① 取成片音频，算出 20ms 能量包络
   ② 用自适应阈值切出「说话段」
   ③ 每条字幕区间 → 落在哪个说话段、覆盖多少
   ④ 反向：每个说话段 → 是否有字幕盖着
   输出：字幕落后/超前 的量化证据
"""
import io, os, subprocess, sys, glob
import numpy as np

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
ROOT = "E:/心理咨询IP"
WIN = 0.02


def envelope(p):
    cmd = [FF, "-v", "error", "-i", p, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    raw = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    hop = int(16000 * WIN)
    n = raw.size // hop
    e = np.empty(n, dtype=np.float32)
    for i in range(n):
        seg = raw[i * hop:(i + 1) * hop]
        e[i] = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)
    return e


def voiced_mask(e):
    """人声判定：BGM 是恒定底噪，人声是大幅度起伏。
       用滑动最大-最小差判定：局部动态范围大 = 有人在说。"""
    k = 25                      # 0.5s 窗
    out = np.zeros(len(e), dtype=bool)
    for i in range(len(e)):
        a = max(0, i - k)
        b = min(len(e), i + k)
        seg = e[a:b]
        if seg.max() - seg.min() > 9.0:      # 0.5s 内起伏 >9dB → 有语音
            out[i] = True
    # 平滑：去掉孤立点
    return out


def spans_from_mask(m, win=WIN, min_len=0.20, min_gap=0.18):
    idx = np.where(m)[0]
    if len(idx) == 0:
        return []
    spans = []
    s = prev = idx[0]
    for i in idx[1:]:
        if (i - prev) * win > min_gap:
            spans.append((s * win, (prev + 1) * win))
            s = i
        prev = i
    spans.append((s * win, (prev + 1) * win))
    return [(a, b) for a, b in spans if b - a >= min_len]


def parse_ass(p):
    cues = []
    for line in io.open(p, encoding="utf-8", errors="ignore"):
        if not line.startswith("Dialogue:"):
            continue
        f = line.split(",", 9)
        if len(f) < 10:
            continue
        def ts(s):
            h, m, sec = s.split(":")
            return int(h) * 3600 + int(m) * 60 + float(sec)
        cues.append(dict(start=ts(f[1]), end=ts(f[2]), text=f[9].strip()))
    return cues


def audit(n):
    vid = glob.glob(os.path.join(ROOT, "05-成片", "*", "第%d条_*_20261024.mp4" % (n + 22)))
    if not vid:
        print("EP%d 成片缺失" % n)
        return
    vid = vid[0]
    e = envelope(vid)
    m = voiced_mask(e)
    spans = spans_from_mask(m)
    cues = parse_ass(os.path.join(ROOT, "04-工程", "batch2", "subs", "%d.ass" % n))
    total = len(e) * WIN

    print("=" * 92)
    print("EP%d  %s" % (n, os.path.basename(vid)))
    print("  片长 %.1fs | 人声段 %d 段 | 字幕 %d 条 | 字幕末句 %.2fs"
          % (total, len(spans), len(cues), cues[-1]["end"]))
    if spans:
        print("  人声真实结束点 %.2fs（最后一段 %.2f→%.2f）" % (spans[-1][1], spans[-1][0], spans[-1][1]))
        print("  人声总长 %.1fs / 片长 %.1fs = %.0f%%" % (sum(b - a for a, b in spans), total,
                                                     100 * sum(b - a for a, b in spans) / total))

    # ① 每条字幕落在人声上的比例
    hits, misses = 0, []
    for c in cues:
        i0, i1 = int(c["start"] / WIN), int(min(c["end"] / WIN, len(m)))
        if i1 <= i0:
            continue
        cov = m[i0:i1].mean()
        if cov >= 0.55:
            hits += 1
        else:
            misses.append((c["start"], c["end"], cov, c["text"][:18]))
    print("  ★ 字幕与「有人在说」同时发生的条数: %d/%d (%.0f%%)" % (hits, len(cues), 100 * hits / len(cues)))
    if misses:
        print("  ★ 字幕显示但没人说（或错位）的 %d 条：" % len(misses))
        for a, b, v, t in misses[:6]:
            print("      %6.2f-%6.2f 覆盖%3.0f%%  「%s」" % (a, b, v * 100, t))

    # ② 每个说话段有没有字幕盖着
    naked = []
    for a, b in spans:
        if b - a < 0.35:
            continue
        covered = sum(max(0, min(b, c["end"]) - max(a, c["start"])) for c in cues)
        if covered / (b - a) < 0.5:
            naked.append((a, b, covered / (b - a)))
    print("  ★ 有人说话但没字幕的段数: %d / %d" % (len(naked), len(spans)))
    for a, b, v in naked[:6]:
        print("      %6.2f-%6.2f 仅覆盖%.0f%%" % (a, b, v * 100))


if __name__ == "__main__":
    for a in sys.argv[1:]:
        audit(int(a))
