# -*- coding: utf-8 -*-
"""调色参数实测筛选：单帧快跑，用数据选最优，不拿整条片子试错。"""
import subprocess
from PIL import Image
import numpy as np

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
SRC = "E:/心理咨询IP/素材_clean2/2.mp4"
OUT = "E:/心理咨询IP/04-工程/batch2/_qc"

TV = ",scale=in_range=full:out_range=tv,format=yuv420p,setparams=range=tv:colorspace=bt709"

# 候选调色链（目标：均值 105~125、标准差 58~70、暗角为正）
CANDS = {
    "F": ",curves=all='0/0 0.20/0.06 0.45/0.30 0.70/0.66 0.90/0.88 1/0.95'"
         ",eq=contrast=1.26:brightness=-0.10:saturation=1.06"
         ",vignette=angle=PI/5.4",
    "G": ",curves=all='0/0 0.20/0.03 0.45/0.26 0.70/0.63 0.90/0.87 1/0.94'"
         ",eq=contrast=1.30:brightness=-0.12:saturation=1.06"
         ",vignette=angle=PI/5.6",
    "H": ",curves=all='0/0 0.18/0.02 0.42/0.22 0.68/0.60 0.88/0.85 1/0.93'"
         ",eq=contrast=1.34:brightness=-0.14:saturation=1.05"
         ",vignette=angle=PI/5.6",
    "I_带色调": ",curves=all='0/0 0.20/0.04 0.45/0.27 0.70/0.64 0.90/0.88 1/0.95'"
              ",eq=contrast=1.30:brightness=-0.11:saturation=1.04"
              ",colorbalance=rs=-0.04:bs=0.05:rh=0.03:bh=-0.035"
              ",vignette=angle=PI/5.6",
}}


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
        if not __import__("os").path.exists(out):
            print("%-12s ❌ 失败 %s" % (name, r.stderr.decode("utf-8", "ignore")[:80]))
            continue
        m, s, v = stat(out)
        print("%-12s 均值=%3.0f 标准差=%2.0f 暗角=%+3.0f" % (name, m, s, v))
    print("\n基准（原始素材）: 均值=198 标准差=39")
    print("目标区间: 均值 105~125 / 标准差 58~70 / 暗角 +30 以上")
