# -*- coding: utf-8 -*-
"""成片抽帧验证（正确做法）

用法:
    python verify_shots.py 2                 # 第2条
    python verify_shots.py 3 4 5 6

原则:
  1. 抽帧时间点必须来自 plan() 里卡片的实际上屏时刻，不凭感觉选
  2. 每张卡片抽"上屏+1.5秒"（动画已走完、卡片最完整）
  3. 每帧单独出一张图，逐张独立看，不拼图
"""
import os
import sys
import json
import subprocess

R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, R)
import compose_batch2 as C

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
OUT_ROOT = os.path.join(R, "_shots")

FINAL = {
    1: "第23条_没人可说第4讲_怎么跟一个不说话的人把话说上_20261024.mp4",
    2: "第24条_没人可说第5讲_你一歇下来就发慌_20261024_025229.mp4",
}


def shots(n, mp4):
    P = C.plan(n)
    d = os.path.join(OUT_ROOT, str(n))
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        if f.endswith(".jpg"):
            os.remove(os.path.join(d, f))

    rows = []
    for key, t, win, hold in P["cards"]:
        ts = round(t + 1.5, 2)          # 上屏 1.5 秒后：动画走完、卡片最完整
        jp = os.path.join(d, "%.2fs_%s.jpg" % (ts, key))
        subprocess.run([FF, "-y", "-v", "error", "-ss", str(ts), "-i", mp4,
                        "-frames:v", "1", "-vf", "scale=420:-1", jp], check=False)
        rows.append((ts, key, jp))
    return rows


if __name__ == "__main__":
    for n in [int(x) for x in sys.argv[1:]] or [2]:
        mp4 = None
        if n in FINAL:
            for base in ("E:/心理咨询IP/05-成片/没人可说", "E:/心理咨询IP/05-成片/我是不是没用了"):
                p = os.path.join(base, FINAL[n])
                if os.path.exists(p):
                    mp4 = p
                    break
        if not mp4:
            print("EP%d: 找不到成片" % n)
            continue
        rows = shots(n, mp4)
        print("EP%d 共 %d 张卡片，逐张图已出到 %s" % (n, len(rows), os.path.join(OUT_ROOT, str(n))))
        for ts, key, jp in rows:
            print("  %6.2fs  %-24s  %s" % (ts, key, os.path.basename(jp)))
