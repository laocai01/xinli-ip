# -*- coding: utf-8 -*-
"""用互相关精准测「成片 vs 源素材变速后」的时间偏移
   逻辑：成片的人声轨 = 源素材人声 × atempo(sp)。
   如果字幕按「ASR原始时间 / sp」铺，那它天然就该对齐。
   所以真错位若存在，只能来自：①删除段落 ②空档重排 ③setpts 与 atempo 不一致。
   本脚本逐段测偏移，输出毫秒级证据。
"""
import subprocess, sys
import numpy as np

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
SR = 8000


def pcm(p, ss=None, t=None, af=None):
    cmd = [FF, "-v", "error"]
    if ss is not None:
        cmd += ["-ss", "%.3f" % ss]
    cmd += ["-i", p]
    if t is not None:
        cmd += ["-t", "%.3f" % t]
    if af:
        cmd += ["-af", af]
    cmd += ["-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def best_offset(a, b, max_lag_s=2.0):
    """找 b 相对 a 的偏移（b 需要左移多少秒才与 a 对齐）"""
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    if n < SR:
        return None
    max_lag = int(max_lag_s * SR)
    best, best_v = 0, -1e18
    for lag in range(-max_lag, max_lag + 1, 8):
        if lag >= 0:
            x, y = a[lag:], b[:len(b) - lag] if lag else b
        else:
            x, y = a[:lag], b[-lag:]
        m = min(len(x), len(y))
        if m < SR // 2:
            continue
        x, y = x[:m], y[:m]
        x = x - x.mean()
        y = y - y.mean()
        d = (np.linalg.norm(x) * np.linalg.norm(y))
        if d <= 0:
            continue
        v = float(np.dot(x, y) / d)
        if v > best_v:
            best_v, best = v, lag
    return best / SR, best_v


if __name__ == "__main__":
    video = sys.argv[1]
    src = sys.argv[2]
    sp = float(sys.argv[3])
    # 分 5 个窗口测偏移
    for t in [5, 30, 60, 100, 150]:
        a = pcm(video, t, 6.0)
        b = pcm(src, t * sp, 6.0, af="atempo=%.4f" % sp)
        r = best_offset(a, b, 2.0)
        if r:
            print("t=%3ds  偏移 %+6.0f ms  相关 %.3f" % (t, r[0] * 1000, r[1]))
