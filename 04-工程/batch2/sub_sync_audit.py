# -*- coding: utf-8 -*-
"""字幕 vs 真人声 逐句核对（可靠版）
   原理：BGM 是恒定底噪，人声有起伏。用"滑动窗口动态范围"判语音/静音，
   再检查：①字幕显示时是否有人在说 ②有人说话时是否有字幕
   输出到 stdout，供出片前卡关。
"""
import io, os, subprocess, sys, glob
import numpy as np

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
ROOT = "E:/心理咨询IP"
SR = 16000
HOP = 0.02


def envelope(p):
    r = subprocess.run([FF, "-v", "error", "-i", p, "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True)
    raw = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    n = int(SR * HOP)
    cnt = raw.size // n
    e = np.empty(cnt, dtype=np.float32)
    for i in range(cnt):
        seg = raw[i * n:(i + 1) * n]
        e[i] = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)
    return e


def voice_mask(e, win=0.25, dyn=7.0):
    """局部动态范围 > dyn dB 视为有语音（BGM 平稳，人声起伏大）"""
    k = max(1, int(win / HOP))
    m = np.zeros(len(e), dtype=bool)
    for i in range(len(e)):
        a, b = max(0, i - k), min(len(e), i + k + 1)
        seg = e[a:b]
        if seg.max() - seg.min() > dyn:
            m[i] = True
    # 膨胀 2 帧补齐
    d = m.copy()
    for s in (1, 2):
        d[s:] |= m[:-s]
        d[:-s] |= m[s:]
    return d


def spans(m, min_len=0.25, min_gap=0.20):
    idx = np.where(m)[0]
    if len(idx) == 0:
        return []
    out, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if (i - prev) * HOP > min_gap:
            out.append((s * HOP, (prev + 1) * HOP))
            s = i
        prev = i
    out.append((s * HOP, (prev + 1) * HOP))
    return [(a, b) for a, b in out if b - a >= min_len]


def parse_ass(p):
    cues = []
    for line in io.open(p, encoding="utf-8", errors="ignore"):
        if not line.startswith("Dialogue:"):
            continue
        f = line.split(",", 9)
        if len(f) < 10:
            continue
        def ts(s):
            h, m, sec = s.split(":")
            return int(h) * 3600 + int(m) * 60 + float(sec)
        cues.append(dict(s=ts(f[1]), e=ts(f[2]), t=f[9].strip()))
    return cues


def audit(video, ass):
    e = envelope(video)
    m = voice_mask(e)
    sp = spans(m)
    cues = parse_ass(ass)
    total = len(e) * HOP
    ok_sub = 0
    bad = []
    for c in cues:
        i0, i1 = int(c["s"] / HOP), int(min(c["e"] / HOP, len(m)))
        if i1 <= i0:
            continue
        cov = m[i0:i1].mean()
        if cov >= 0.5:
            ok_sub += 1
        else:
            bad.append((c["s"], c["e"], cov, c["t"]))
    naked = []
    for a, b in sp:
        if b - a < 0.35:
            continue
        cov = sum(max(0, min(b, c["e"]) - max(a, c["s"])) for c in cues) / (b - a)
        if cov < 0.4:
            naked.append((a, b, cov))
    voice_end = sp[-1][1] if sp else 0
    print("=" * 90)
    print("字幕条数 %d | 人声段 %d | 片长 %.1fs | 人声真实结束 %.2fs | 字幕末句 %.2fs"
          % (len(cues), len(sp), total, voice_end, cues[-1]["e"] if cues else 0))
    print("★ 字幕对齐率 %.0f%% (%d/%d)" % (100 * ok_sub / max(1, len(cues)), ok_sub, len(cues)))
    print("★ 有话音无字幕的段 %d / %d" % (len(naked), len(sp)))
    for a, b, v in naked[:5]:
        print("    %.2f-%.2f 覆盖%.0f%%" % (a, b, v * 100))
    for a, b, v, t in bad[:5]:
        print("    错位 %.2f-%.2f 覆盖%.0f%% 「%s」" % (a, b, v * 100, t[:16]))
    return dict(cues=len(cues), align=ok_sub / max(1, len(cues)), naked=len(naked),
                voice_end=voice_end, total=total)


if __name__ == "__main__":
    n = int(sys.argv[1])
    vid = glob.glob(os.path.join(ROOT, "05-成片", "*", "第%d条_*_20261024.mp4" % (n + 22)))
    if not vid:
        print("缺片 EP%d" % n); sys.exit(1)
    audit(vid[0], os.path.join(ROOT, "04-工程", "batch2", "subs", "%d.ass" % n))
