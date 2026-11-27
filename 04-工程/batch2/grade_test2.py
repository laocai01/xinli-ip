# -*- coding: utf-8 -*-
"""调色参数实测筛选 v2：单帧快跑，用数据选最优。"""
import os
import subprocess
from PIL import Image
import numpy as np

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
SRC = "E:/心理咨询IP/素材_clean2/2.mp4"
OUT = "E:/心理咨询IP/04-工程/batch2/_qc"

CANDS = {}
CANDS["F"] = (",curves=all='0/0 0.20/0.06 0.45/0.30 0.70/0.66 0.90/0.88 1/0.95'"
              ",eq=contrast=1.26:brightness=-0.10:saturation=1.06"
              ",vignette=angle=PI/5.4")
CANDS["G"] = (",curves=all='0/0 0.20/0.03 0.45/0.26 0.70/0.63 0.90/0.87 1/0.94'"
              ",eq=contrast=1.30:brightness=-0.12:saturation=1.06"
              ",vignette=angle=PI/5.6")
CANDS["H"] = (",curves=all='0/0 0.18/0.02 0.42/0.22 0.68/0.60 0.88/0.85 1/0.93'"
              ",eq=contrast=1.34:brightness=-0.14:saturation=1.05"
              ",vignette=angle=PI/5.6")
CANDS["I"] = (",curves=all='0/0 0.20/0.04 0.45/0.27 0.70/0.64 0.90/0.88 1/0.95'"
              ",eq=contrast=1.30:brightness=-0.11:saturation=1.04"
              ",colorbalance=rs=-0.04:bs=0.05:rh=0.03:bh=-0.035"
              ",vignette=angle=PI/5.6")
CANDS["J"] = (",curves=all='0/0 0.18/0.01 0.40/0.18 0.66/0.56 0.86/0.83 1/0.92'"
              ",eq=contrast=1.38:brightness=-0.16:saturation=1.04"
              ",vignette=angle=PI/5.6")


def stat(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    h, w = lum.shape
    c = lum[int(h * 0.35):int(h * 0.65), int(w * 0.35):int(w * 0.65)].mean()
    tl = lum[:int(h * 0.15), :int(w * 0.15)].mean()
    br = lum[int(h * 0.85):, int(w * 0.85):].mean()
    return lum.mean(), lum.std(), c - (tl + br) / 2


if __name__ == "__main__":
    for name, chain in CANDS.items():
        out = "%s/g_%s.jpg" % (OUT, name)
        cmd = [FF, "-y", "-v", "error", "-ss", "60", "-i", SRC, "-frames:v", "1",
               "-vf", chain.lstrip(",") + ",scale=432:-1", out]
        r = subprocess.run(cmd, capture_output=True, timeout=300)
        if not os.path.exists(out):
            print("%-4s FAIL %s" % (name, r.stderr.decode("utf-8", "ignore")[:70]))
            continue
        m, s, v = stat(out)
        print("%-4s 均值=%3.0f 标准差=%2.0f 暗角=%+3.0f" % (name, m, s, v))
    print("\n基准(原始=198/39)  目标: 均值105~125 标准差58~70 暗角+30以上")
