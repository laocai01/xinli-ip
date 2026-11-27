# -*- coding: utf-8 -*-
"""逐句核对：字幕显示区间 vs 真实人声，找出错位证据
   方法：人声轨做能量包络，字幕区间覆盖率；再对比"字幕说A句"时人声是否在说A句
   简化可信指标：①字幕区间内人声占比 ②字幕空白处人声占比 ③末尾同步
"""
import json, io, os, subprocess, sys
import numpy as np

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
ROOT = "E:/心理咨询IP"


def env(p, win=0.02):
    cmd = [FF, "-v", "error", "-i", p, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    raw = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    hop = int(16000 * win)
    n = raw.size // hop
    out = np.empty(n, dtype=np.float32)
    for i in range(n):
        seg = raw[i * hop:(i + 1) * hop]
        out[i] = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)
    return out, win


def parse_ass(p):
    cues = []
    for line in io.open(p, encoding="utf-8", errors="ignore"):
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        if len(parts) < 10:
            continue
        def ts(s):
            h, m, sec = s.split(":")
            return int(h) * 3600 + int(m) * 60 + float(sec)
        cues.append(dict(start=ts(parts[1]), end=ts(parts[2]), text=parts[9].strip()))
    return cues


def analyze(n):
    ass = os.path.join(ROOT, "04-工程", "batch2", "subs", "%d.ass" % n)
    cues = parse_ass(ass)
    # 成片路径
    import glob
    vids = glob.glob(os.path.join(ROOT, "05-成片", "*", "第%d条_*_20261024.mp4" % (n + 22)))
    if not vids:
        print("EP%d 找不到成片" % n); return
    fn = vids[0]
    e, win = env(fn)
    # 人声判定：只取"高于自身低分位 8dB"的窗；BGM 恒定，起伏来源就是人声
    base = np.percentile(e, 20)
    thr = base + 5.0
    voiced = e > thr

    def cover(a, b):
        i0, i1 = int(a / win), int(min(b / win, len(voiced)))
        if i1 <= i0:
            return 0.0
        return float(voiced[i0:i1].mean())

    # ① 字幕区间内人声覆盖
    covs = [cover(c["start"], c["end"]) for c in cues]
    # ② 字幕之间的空档，人声是否还在说（= 漏字幕）
    gaps = []
    for i in range(len(cues) - 1):
        g0, g1 = cues[i]["end"], cues[i + 1]["start"]
        if g1 - g0 > 0.45:
            gaps.append((g0, g1, cover(g0, g1), cues[i]["text"][-14:], cues[i + 1]["text"][:14]))

    total = len(e) * win
    print("=" * 90)
    print("EP%d  %s" % (n, os.path.basename(fn)))
    print("  片长 %.1fs | 字幕 %d 条 | 字幕末句结束 %.2fs" % (total, len(cues), cues[-1]["end"]))
    print("  ★ 字幕区间内平均人声覆盖 %.1f%%（理想 >85%%）" % (100 * np.mean(covs)))
    low = [(c["start"], c["end"], v) for c, v in zip(cues, covs) if v < 0.6]
    print("  ★ 人声覆盖<60%% 的字幕条数: %d / %d" % (len(low), len(cues)))
    for a, b, v in low[:8]:
        print("      %.2f-%.2f 覆盖%.0f%%" % (a, b, v * 100))
    bad = [g for g in gaps if g[2] > 0.55]
    print("  ★ 字幕空档里人声还在说（=漏字幕/慢半拍）: %d 处 / %d 个空档" % (len(bad), len(gaps)))
    for g0, g1, v, t1, t2 in bad[:6]:
        print("      %.2f→%.2f 人声覆盖%.0f%%  「%s」→「%s」" % (g0, g1, v * 100, t1, t2))
    # 尾部
    tail_voiced = voiced[int((total - 8) / win):]
    print("  ★ 最后8秒人声占比 %.0f%%（字幕末句在 %.2fs，片长 %.2fs）"
          % (100 * tail_voiced.mean(), cues[-1]["end"], total))


if __name__ == "__main__":
    for a in sys.argv[1:]:
        analyze(int(a))
