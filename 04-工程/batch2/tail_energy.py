# -*- coding: utf-8 -*-
"""看成片最后 X 秒的能量曲线：判断"人声到底说没说完、字幕盖在哪" """
import subprocess, sys
import numpy as np

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"


def env(p, win=0.5):
    cmd = [FF, "-v", "error", "-i", p, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    raw = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    hop = int(16000 * win)
    n = raw.size // hop
    out = []
    for i in range(n):
        seg = raw[i * hop:(i + 1) * hop]
        out.append((i * win, 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)))
    return out


p = sys.argv[1]
tail = float(sys.argv[2]) if len(sys.argv) > 2 else 45.0
e = env(p)
total = e[-1][0] if e else 0
print("片长 %.1fs，%d 个 0.5s 窗" % (total, len(e)))
sel = [x for x in e if x[0] >= total - tail]
vals = np.array([v for _, v in sel])
print("末 %.0fs 能量: min %.1f / 中位 %.1f / max %.1f" % (tail, vals.min(), np.median(vals), vals.max()))
print("时间      dB    波形")
for t, v in sel:
    bar = "#" * max(0, int((v + 55) / 1.5))
    print("%6.1fs %6.1f %s" % (t, v, bar))
