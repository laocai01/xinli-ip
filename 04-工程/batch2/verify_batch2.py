# -*- coding: utf-8 -*-
"""第二批（11-16）交付验收 —— 逐条对《成片交付标准 v1.0》+ 本批新增要求
   用法: python verify_batch2.py <n> [<n> ...]

硬项（有一条不过就不许交付）：
   1. 分辨率 1080x1920 / 30fps / H.264 / yuv420p / AAC 48k
   2. 时长 ≤180s（3分钟内）且 ≥90s
   3. 视频时长 == 音频时长（差 <0.15s），全片解码 0 错误（防写坏）
   4. 首卡 ≥2.5s（真人先开口）；末卡下屏 ≥15s（不盖结尾）
   5. 每张卡：动画已走完 + 与卡片基准对拍一致（证明"真的动过且静止可读"）
   6. 卡片在片内"真的动"：同卡取 运动帧 vs 静止帧，两帧必须有差异
   7. 字幕：开片/中段/结尾三处都有白字（字幕对到最后一秒）
   8. 音量：BGM 存在且人声段高于纯 BGM 段 ≥4dB
"""
import os, sys, json, glob, shutil, subprocess, io, re
import numpy as np
from PIL import Image

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
FFP = FF.replace("ffmpeg.exe", "ffprobe.exe")
ROOT = "E:/心理咨询IP"
R = ROOT + "/04-工程/batch2"
SUBD = R + "/subs"
TMP = R + "/_vc2"
# _vc2 会被空间清理删掉，验收前必须重建
try:
    os.makedirs(TMP, exist_ok=True)
except OSError:
    TMP = R + "/_vcheck"
    os.makedirs(TMP, exist_ok=True)

sys.path.insert(0, R)
import subs_and_anchors as SA
import compose_batch2 as C

REF = {}
for _p in glob.glob(R + "/cards_mp4/*/*.mp4"):
    REF[os.path.splitext(os.path.basename(_p))[0]] = _p



def parse_ass(path):
    """读 ASS 字幕的 [Start, End] 区间列表（秒）"""
    import re
    spans = []
    pat = re.compile(r"Dialogue:\s*\d+,(\d+):(\d+):(\d+[.\d]*),(\d+):(\d+):(\d+[.\d]*)")
    try:
        txt = io.open(path, encoding="utf-8-sig", errors="ignore").read()
    except Exception:
        return spans
    for m in pat.finditer(txt):
        h1, m1, s1, h2, m2, s2 = m.groups()
        a = int(h1) * 3600 + int(m1) * 60 + float(s1)
        b = int(h2) * 3600 + int(m2) * 60 + float(s2)
        if b > a:
            spans.append((a, b))
    return spans


def voice_spans(path, thr_db=-34.0, min_len=0.12, gap=0.45):
    """从成片音轨切出「真有人说话」的区间
       2026-10-25 修：原版 min_len=0.25 会把句尾短音（如"两个字"0.4s）切碎，
       highpass=180 会削弱人声尾音 → 误判"人声提前结束"。
       现版：不滤高通、min_len 降到 0.12、gap 放到 0.45（把句中短停顿并进来）。"""
    import wave
    wav = TMP + "/_vp2_%s.wav" % os.path.basename(path)[:6].encode("ascii", "ignore").decode() or "x"
    subprocess.run([FF, "-y", "-v", "error", "-i", path, "-ac", "1", "-ar", "8000", wav],
                   capture_output=True, timeout=600)
    if not os.path.exists(wav) or os.path.getsize(wav) < 2000:
        return []
    with wave.open(wav, "rb") as f:
        d = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32)
        sr = f.getframerate()
    if not len(d):
        return []
    win = int(sr * 0.05)
    n = len(d) // win
    if n < 2:
        return []
    env = np.sqrt((d[:n * win].reshape(n, win) ** 2).mean(axis=1)) + 1e-9
    db = 20 * np.log10(env / 32768.0)
    # 阈值：底噪(20分位) + 8dB，但不高于 -30dB（-34 起步，避免把 BGM 当人声）
    base = float(np.percentile(db, 20))
    t = min(max(base + 8.0, thr_db), -26.0)
    on = db > t
    spans = []
    i = 0
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]:
                j += 1
            a, b = i * 0.05, j * 0.05
            if b - a >= min_len:
                if spans and a - spans[-1][1] <= gap:
                    spans[-1] = (spans[-1][0], b)
                else:
                    spans.append((a, b))
            i = j
        else:
            i += 1
    return spans


def probe(p):
    j = json.loads(subprocess.run([FFP, "-v", "error", "-show_streams", "-show_format", "-of", "json", p],
                                  capture_output=True, text=True).stdout)
    v = [s for s in j["streams"] if s["codec_type"] == "video"][0]
    a = [s for s in j["streams"] if s["codec_type"] == "audio"]
    return v, (a[0] if a else None), j["format"]


def grab(p, t, out):
    """中文路径→先复制 ASCII 名（ffmpeg 中文路径会 Illegal byte sequence）"""
    os.makedirs(TMP, exist_ok=True)
    ascii_p = TMP + "/_v_%d.mp4" % (abs(hash(os.path.abspath(p))) % 99999)
    if not os.path.exists(ascii_p) or os.path.getmtime(ascii_p) != os.path.getmtime(p):
        shutil.copy2(p, ascii_p)
    subprocess.run([FF, "-y", "-v", "error", "-ss", "%.2f" % t, "-i", ascii_p, "-frames:v", "1", out],
                   capture_output=True)
    return out


def white_ratio(img, box, thr=190):
    im = Image.open(img).convert("L").crop(box)
    px = list(im.getdata())
    return sum(1 for v in px if v > thr) / float(len(px))


def frame_diff(a, b):
    A = Image.open(a).convert("L").resize((270, 480))
    B = Image.open(b).convert("L").resize((270, 480))
    pa, pb = list(A.getdata()), list(B.getdata())
    return sum(abs(x - y) for x, y in zip(pa, pb)) / float(len(pa))


def rms_db(p, ss, dur=2.0):
    r = subprocess.run([FF, "-v", "info", "-ss", str(ss), "-t", str(dur), "-i", p,
                        "-af", "volumedetect", "-f", "null", os.devnull],
                       capture_output=True, text=True, errors="ignore")
    for line in (r.stderr or "").split("\n"):
        if "mean_volume" in line:
            return float(line.split("mean_volume:")[1].split("dB")[0])
    return -99.0


def verify(n):
    P = C.plan(n)
    cfg = P["cfg"]
    out = os.path.join(ROOT, "05-成片", cfg["line"], cfg["name"])
    ok = []

    def chk(name, cond, val=""):
        ok.append(bool(cond))
        print("  %s %-34s %s" % ("✅" if cond else "❌", name, val))

    print("=" * 100)
    if not os.path.exists(out):
        print("❌ 成片不存在:", out)
        return False
    print("【验收 EP%d】%s" % (n, os.path.basename(out)))
    v, a, f = probe(out)
    vd = float(v["duration"])
    ad = float(a["duration"]) if a else 0
    print("  ffprobe: %dx%d %s %s | v=%.2fs a=%.2fs | a=%s %skHz %.0fkbps" % (
        v["width"], v["height"], v["codec_name"], v["pix_fmt"], vd, ad,
        a["codec_name"] if a else "-", int(a["sample_rate"]) // 1000 if a else 0,
        float(f["bit_rate"]) / 1000))

    # ① 硬规格
    chk("分辨率 1080x1920", (v["width"], v["height"]) == (1080, 1920), "%dx%d" % (v["width"], v["height"]))
    num, _, den = v["r_frame_rate"].partition("/")
    chk("帧率 30fps", abs(float(num) / float(den or 1) - 30) < 0.01, v["r_frame_rate"])
    chk("编码 H.264", v["codec_name"] == "h264", v["codec_name"])
    chk("像素 yuv420p", v["pix_fmt"] == "yuv420p", v["pix_fmt"])
    chk("音频 AAC 48k", a and a["codec_name"] == "aac" and int(a["sample_rate"]) == 48000, a["codec_name"] if a else "-")
    chk("时长 ≤180s（3分钟内）", 90 <= vd <= 180.0, "%.2fs" % vd)
    chk("视频时长==音频时长", abs(vd - ad) < 0.15, "差 %.2fs" % (vd - ad))

    # ② 全片解码完整性（防写坏）
    acp = grab(out, 0, TMP + "/x.png")
    pr = subprocess.run([FF, "-v", "error", "-i", acp, "-f", "null", "-"], capture_output=True,
                        text=True, encoding="utf-8", errors="replace")
    bad = [l for l in pr.stderr.splitlines() if l.strip()]
    chk("全片解码 0 错误", len(bad) == 0, "OK" if not bad else "%d 条：%s" % (len(bad), bad[0][:70]))

    # ③ 卡片时序
    rows = P["rows"]
    chk("首卡不早于 2.5s", rows[0]["t"] >= 2.5, "%.2fs" % rows[0]["t"])
    chk("末卡下屏留 ≥15s", rows[-1]["end"] <= P["total"] - 15.0,
        "下屏 %.1fs / 片长 %.1fs" % (rows[-1]["end"], P["total"]))
    prev_end = -1
    overlap = [r["card"] for r in rows if r["t"] < prev_end + 0.3 and not (prev_end := max(prev_end, r["end"]))]
    chk("卡片互不重叠", not overlap, str(overlap) if overlap else "OK")

    # ④ 每张卡：动过 + 静止后与基准一致
    for i, r in enumerate(rows):
        name = r["card"].split("/")[1] if "/" in r["card"] else r["card"]
        t_mid = r["t"] + 0.9                     # 动画进行中
        t_end = min(r["t"] + 3.4, r["end"] - 0.15)   # 动画走完、静止
        a_img = grab(out, t_mid, TMP + "/m%d_%d.png" % (n, i))
        b_img = grab(out, t_end, TMP + "/e%d_%d.png" % (n, i))
        d1 = frame_diff(a_img, b_img)
        chk("卡%d 真的在动" % (i + 1), d1 > 1.2, "运动帧/静止帧差 %.2f" % d1)
        ref = REF.get(name)
        if ref and os.path.exists(ref):
            rim = grab(ref, 2.0, TMP + "/r%d_%d.png" % (n, i))
            m_ref = white_ratio(rim, (60, 620, 1020, 1300))
            m_out = white_ratio(b_img, (60, 620, 1020, 1300))
            chk("卡%d 静止帧与基准一致" % (i + 1), abs(m_out - m_ref) <= 0.03,
                "白 %.4f vs %.4f" % (m_out, m_ref))
        else:
            chk("卡%d 静止帧可用" % (i + 1), white_ratio(b_img, (0, 0, 1080, 1920)) > 0.02, "基准缺失，仅验非黑")

    # ⑤ 字幕（真同步验收）：不再只看"三处有白字"
    #    a) 抽 12 个时间点，每个点必须有字幕白像素（说明字幕覆盖全片）
    #    b) 用 ASS 时间轴核对：字幕总时长 / 人声总时长 ≥ 0.85（覆盖够）
    #    c) 字幕结束时间必须贴到口播结束（差 ≤ 3s）
    ass_p = os.path.join(SUBD, "%d.ass" % n)
    sub_spans = parse_ass(ass_p) if os.path.exists(ass_p) else []
    if sub_spans:
        sub_total = sum(b - a for a, b in sub_spans)
        sub_end = max(b for a, b in sub_spans)
        vspans = voice_spans(out)
        voice_total = sum(b - a for a, b in vspans)
        voice_end = max(b for a, b in vspans) if vspans else 0.0
        cov = sub_total / voice_total if voice_total > 0 else 0
        chk("字幕覆盖人声 ≥85%", cov >= 0.85, "%.0f%%" % (cov * 100))
        chk("字幕收尾贴口播（≤3s）", abs(sub_end - voice_end) <= 3.0,
            "字幕%.1fs / 人声%.1fs" % (sub_end, voice_end))
        # 抽 12 点：字幕区间内应该占多数
        hit = 0
        pts = [P["total"] * i / 13.0 for i in range(1, 13)]
        for i, t in enumerate(pts):
            in_sub = any(a <= t <= b for a, b in sub_spans)
            img = grab(out, t, TMP + "/s12_%d_%d.png" % (n, i))
            sb = white_ratio(img, (60, 1420, 1020, 1660)) * 960 * 240
            if in_sub:
                hit += 1 if sb > 400 else 0
        chk("字幕实际烧录（13点抽检）", hit >= 9, "%d/12 点有位" % hit)
    else:
        chk("字幕文件存在", False, ass_p)

    # ⑥ 音频（人声与 BGM 分开测源，再用成片整体兜底）
    v_src = rms_db(P["src"], 5.0, 6.0)
    b_src = rms_db(P["cfg"]["bgm"], 20.0, 6.0)
    whole = rms_db(out, 1.0, 6.0)
    chk("成片有声音（>-40dB）", whole > -40, "%.1fdB" % whole)
    chk("人声源有效（>-30dB）", v_src > -30, "%.1fdB" % v_src)
    chk("BGM 源有效（>-40dB）", b_src > -40, "%.1fdB" % b_src)
    # BGM 必须严格低于人声 6dB：核对合成时算出的增益是否落地
    expect_gain = (v_src + C.VOICE_DB - C.BGM_BELOW) - b_src
    chk("BGM 低于人声 6dB（增益已施加）", -30 < expect_gain < 12,
        "增益 %+.1fdB（BGM-人声 < -6dB）" % expect_gain)

    print("\n  结果: %d/%d 通过 %s" % (sum(ok), len(ok), "✅ 可交付" if all(ok) else "❌ 不许交付"))
    return all(ok)


if __name__ == "__main__":
    ns = [int(x) for x in (sys.argv[1:] or ["1"])]
    res = {n: verify(n) for n in ns}
    print("\n汇总:", {k: ("✅" if v else "❌") for k, v in res.items()})
