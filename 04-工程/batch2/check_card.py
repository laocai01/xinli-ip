# -*- coding: utf-8 -*-
"""短片段验证：只合成第 2 条 12–25 秒（含第 1 张卡），确认卡片缩小后真人可见。"""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose_batch2 as C

n = 2
P = C.plan(n)
src = P["src"]
card0 = os.path.join(C.ANIM, str(n), P["cards"][0][0] + ".mp4")
print("卡片:", card0, os.path.exists(card0))
print("卡片窗口:", P["cards"][0])

FF = C.FF
out = os.path.join(C.R, "_cmp", "cardcheck.mp4")
os.makedirs(os.path.dirname(out), exist_ok=True)

# 12s 起截 10 秒，卡片起点 3.0s 在窗口内 → 换到卡点附近
t0 = max(0.0, P["cards"][0][1] - 1.0)
cmd = [FF, "-y", "-v", "error",
       "-ss", "%.2f" % t0, "-t", "8", "-i", src,
       "-i", card0,
       "-filter_complex",
       "[0:v]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
       "crop=1080:1920,setsar=1,fps=30[bg];"
       "[1:v]trim=start=0:end=4,setpts=PTS-STARTPTS,fps=30,"
       "crop=1080:1440:0:0,scale=720:-1:flags=lanczos,setsar=1,format=yuva420p[cd];"
       "[bg][cd]overlay=180:960:enable='between(t,1.0,5.0)'[v]",
       "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-an", out]
r = subprocess.run(cmd, capture_output=True, text=True)
print("rc", r.returncode, r.stderr[-400:] if r.returncode else "")
print("out", out, os.path.getsize(out) // 1048576 if os.path.exists(out) else 0, "MB")
