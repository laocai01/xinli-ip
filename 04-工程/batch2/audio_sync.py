# -*- coding: utf-8 -*-
"""真人声能量检测：每 50ms 一窗，判断"这段话有没有人在说"
   用来核对 字幕时间轴 vs 真实人声 是否同步——不靠眼看，靠能量
"""
import json, io, os, subprocess, sys
import numpy as np

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
SR = 16000
HOP = int(SR * 0.05)   # 50ms


def track(p, ss=0, dur=None):
    """返回 [(t, dbfs)]，每 50ms 一个点"""
    cmd = [FF, "-v", "error"]
    if ss:
        cmd += ["-ss", "%.2f" % ss]
    cmd += ["-i", p]
    if dur:
        cmd += ["-t", "%.2f" % dur]
    cmd += ["-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    raw = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    if raw.size == 0:
        return []
    n = raw.size // HOP
    out = []
    for i in range(n):
        seg = raw[i * HOP:(i + 1) * HOP]
        rms = float(np.sqrt(np.mean(seg ** 2)) + 1e-9)
        out.append((ss + i * 0.05, 20 * np.log10(rms)))
    return out


def speech_spans(p, ss=0, dur=None, thr=-32.0, min_gap=0.25, min_len=0.12):
    """能量阈值 → 合并成"有说话"的连续区间"""
    t = track(p, ss, dur)
    if not t:
        return []
    spans, cur = [], None
    for ts, db in t:
        if db > thr:
            if cur is None:
                cur = [ts, ts]
            else:
                cur[1] = ts
        else:
            if cur is not None and ts - cur[1] > min_gap:
                spans.append(cur); cur = None
    if cur is not None:
        spans.append(cur)
    # 丢弃极短的（气口/杂音）
    return [(a, b) for a, b in spans if b - a >= min_len]


if __name__ == "__main__":
    p = sys.argv[1]
    d = sys.argv[2] if len(sys.argv) > 2 else None
    sp = speech_spans(p, 0, float(d) if d else None)
    print("检测到 %d 段人声，总长 %.1fs" % (len(sp), sum(b - a for a, b in sp)))
    for a, b in sp[:20]:
        print("  %.2f → %.2f (%.2fs)" % (a, b, b - a))
