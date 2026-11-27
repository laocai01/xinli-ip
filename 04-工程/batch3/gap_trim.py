# -*- coding: utf-8 -*-
"""呼吸/废话压缩——剪掉不说话的空隙，内容一个字不减。

原理:
    人说话字与字之间有换气、尾音、口头禅前后的空隙。这些空隙不承载内容，
    剪掉后内容完整、语速不变（不是加速，是删空白），只是把"停顿"去掉。

判定:
    逐 5ms 算 RMS 电平，低于阈值且持续 >= minlen 的段判为"空隙"，
    每段两端各保留 keep/2 秒，避免切断字头字尾。

铁律:
    · 只删空隙，不删任何语音
    · 每段两端留余量，防止切字
    · 剪完必须校验：无能量突变、语音段 RMS 不下降
"""
import json
import io
import subprocess
import numpy as np

FF = (r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/"
      r"Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/"
      r"ffmpeg-9.0.1-full_build/bin")
ROOT = "E:/心理咨询IP"


def load_mono(path, sr=16000):
    r = subprocess.run([FF + "/ffmpeg.exe", "-v", "error", "-i", path,
                        "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                       capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def detect_gaps(path, thr=-31.0, minlen=0.18, keep=0.10):
    """返回要删掉的区间列表 [(a,b), ...]（已含两端保留余量）"""
    a = load_mono(path)
    sr = 16000
    w = int(sr * 0.005)          # 5ms 窗
    nb = len(a) // w
    rms = np.sqrt((a[:nb * w].reshape(nb, w) ** 2).mean(axis=1))
    db = 20 * np.log10(np.maximum(rms, 1e-6))
    silent = db < thr
    segs, s = [], None
    for i, v in enumerate(silent):
        if v and s is None:
            s = i
        elif not v and s is not None:
            segs.append((s * w / sr, i * w / sr))
            s = None
    if s is not None:
        segs.append((s * w / sr, nb * w / sr))
    cuts = []
    for x, y in segs:
        if y - x >= minlen:
            a0, b0 = x + keep / 2, y - keep / 2
            if b0 - a0 > 0.05:
                cuts.append((round(a0, 3), round(b0, 3)))
    return cuts, len(a) / sr


def keep_intervals(dur, cuts):
    pts = [0.0] + [v for c in cuts for v in c] + [dur]
    out = []
    for i in range(0, len(pts), 2):
        if i + 1 < len(pts) and pts[i + 1] - pts[i] > 0.01:
            out.append((pts[i], pts[i + 1]))
    return out


def remap(t, cuts):
    """把原始时间轴上的 t 映射到剪后时间轴"""
    shift = 0.0
    for a, b in cuts:
        if t <= a:
            break
        if t >= b:
            shift += b - a
        else:
            return a - shift          # t 落在被删段内 → 落到删除点
    return t - shift


def analyze(n, thr=-31.0):
    src = "%s/素材/%d.mp4" % (ROOT, n)
    cuts, dur = detect_gaps(src, thr=thr)
    keep = keep_intervals(dur, cuts)
    return dict(src=src, dur=dur, cuts=cuts, keep=keep,
                new_len=sum(b - a for a, b in keep))


def build_plan(n, thr=-31.0, out_json=None):
    d = analyze(n, thr)
    if out_json:
        json.dump(d, io.open(out_json, "w", encoding="utf-8"), indent=1)
    return d


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1])
    d = build_plan(n, out_json="%s/04-工程/batch3/gaps_%d.json" % (ROOT, n))
    print("第%d条 原%.1fs → 剪后%.1fs（删%.1fs，%d段），倍速后成片见 compose"
          % (n, d["dur"], d["new_len"], d["dur"] - d["new_len"], len(d["cuts"])))
