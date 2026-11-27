# -*- coding: utf-8 -*-
"""成片时长锁 3 分钟以内（≤178s）：
   在"语速正常"的前提下，用【剪掉片尾下一讲预告 + 多余的尾巴】来省时间，
   不靠加速硬压。只动 tail_cut 指定的尾部秒数，正文一个不剪。
"""
import sys, io, json, subprocess
sys.path.insert(0, 'E:/心理咨询IP/04-工程/batch2')
import subs_and_anchors as SA

LIMIT = 178.0
FFP = 'C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffprobe.exe'

# 各集允许剪掉的尾部秒数（只剪"下一讲预告"这段钩子，以及口播结束后多余的空白）
TAIL_CUT = {1: 0, 2: 8.0, 3: 15.0, 4: 0, 5: 0, 6: 5.0}

print("集 | 素材 | 剪尾 | 有效 | 目标倍速 | 成片 | 语速字/分")
for n in range(1, 7):
    d = json.load(io.open('E:/心理咨询IP/04-工程/batch2/final_%d.json' % n, encoding='utf-8'))
    tot = sum(len(c['text']) for c in d['cues'])
    raw = float(subprocess.run([FFP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                                'E:/心理咨询IP/素材/%d.mp4' % n], capture_output=True, text=True).stdout.strip())
    cut = TAIL_CUT[n]
    eff = raw - cut
    need = eff / LIMIT
    sp = max(1.0, min(need, 1.20))          # 语速不超过 1.20（≈270字/分上限）
    out = eff / sp
    print("%2d | %5.1f | %4.1f | %5.1f | %.3fx | %5.1f | %3.0f  %s" %
          (n, raw, cut, eff, sp, out, tot / out * 60, "✅" if out <= LIMIT else "❌ 仍超"))
