# -*- coding: utf-8 -*-
"""渲染一段短样并逐帧测字幕高度，用来定位"放大帧"真实存在于哪一时刻。

用法：python probe_zoom.py <n> <开始秒> <时长秒> <放大%> <光边宽>
"""
import os
import subprocess
import sys

import numpy as np

FF = "C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
R = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(R, "_cmp")
os.makedirs(OUT, exist_ok=True)
FONTDIR = "E:/心理咨询IP/07-形象设计/fonts/fonts-main/DouyinSans"


def run(n, t0, dur, scale, glow_w, tag):
    src = os.path.join(R, "subs", "%d.ass" % n)
    import io
    base = io.open(src, encoding="utf-8").read()
    out = base.replace("\\bord26", "\\bord%d" % glow_w)
    out = out.replace("\\t(0,9,\\fscx145\\fscy145",
                      "\\t(0,9,\\fscx%d\\fscy%d" % (scale, scale))
    tmp = os.path.join(OUT, "p_%s.ass" % tag)
    io.open(tmp, "w", encoding="utf-8").write(out)

    esc = tmp.replace("\\", "/").replace(":", "\\:")
    fdir = FONTDIR.replace("\\", "/").replace(":", "\\:")
    vf = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
          "subtitles=filename='%s':fontsdir='%s'" % (esc, fdir))
    raw = os.path.join(OUT, "p_%s.raw" % tag)
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(t0), "-t", str(dur),
                    "-i", "E:/心理咨询IP/素材_clean2/%d.mp4" % n,
                    "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", raw], check=True)

    W, H = 1080, 1920
    d = open(raw, "rb").read()
    nf = len(d) // (W * H * 3)
    print("帧数", nf)
    for f in range(nf):
        a = np.frombuffer(d[f * W * H * 3:(f + 1) * W * H * 3],
                          dtype=np.uint8).reshape(H, W, 3).astype(int)
        r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
        sat = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
        m = (sat > 80) & (r > 130)
        m[:900, :] = False
        ys, xs = np.nonzero(m)
        if len(xs) > 300:
            print("f%02d t=%.2fs 高%d宽%d 像素%d" %
                  (f, t0 + f / 30.0, ys.max() - ys.min(), xs.max() - xs.min(), len(xs)))


if __name__ == "__main__":
    a = sys.argv[1:]
    run(int(a[0]), float(a[1]), float(a[2]), int(a[3]), int(a[4]), a[5])
