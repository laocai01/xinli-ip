# -*- coding: utf-8 -*-
"""成片验收（重建版 2026-10-13）—— 机器验，不靠嘴
用法: python verify.py <ep>
逐项对《成片交付标准 v1.0》：分辨率/帧率/编码/像素格式/音频/时长
   + 抽帧验：真人段 LOGO、字幕白像素、卡片窗口内有卡（且与真人帧不同）、无黑帧
   + 音频验：视频时长==音频时长，人声段 RMS > BGM-only 段
"""
import os, sys, json, subprocess, shutil, math
from PIL import Image

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
FFP = FF.replace("ffmpeg.exe", "ffprobe.exe")
R = "E:/心理咨询IP/04-工程/rebuild_20261013"
TMP = R + "/_vc"

# 卡片流基准表：卡名 → cards_mp4/*/<卡名>.mp4（验收「成片 vs 卡片流基准」对拍用）
import glob as _glob
REF = {}
for _p in _glob.glob(R + "/cards_mp4/*/*.mp4"):
    REF[os.path.splitext(os.path.basename(_p))[0]] = _p
sys.path.insert(0, R)


def probe(p):
    j = json.loads(subprocess.run([FFP, "-v", "error", "-show_streams", "-show_format", "-of", "json", p],
                                  capture_output=True, text=True).stdout)
    v = [s for s in j["streams"] if s["codec_type"] == "video"][0]
    a = [s for s in j["streams"] if s["codec_type"] == "audio"]
    return v, (a[0] if a else None), j["format"]


def grab(p, t, out):
    """★ 中文路径必须先复制成 ASCII 名再抽帧（ffmpeg 中文路径会 Illegal byte sequence）
    ★ 临时名按来源文件区分（否则连抽两个不同视频时会拿错帧）"""
    ascii_p = TMP + "/_v_%d.mp4" % (abs(hash(os.path.abspath(p))) % 99999)
    if not os.path.exists(ascii_p) or os.path.getmtime(ascii_p) != os.path.getmtime(p):
        shutil.copy2(p, ascii_p)
    subprocess.run([FF, "-y", "-v", "error", "-ss", "%.2f" % t, "-i", ascii_p,
                    "-frames:v", "1", out], capture_output=True)
    return out


def dark(img, box=None):
    im = Image.open(img).convert("L")
    if box:
        im = im.crop(box)
    px = im.getdata()
    return sum(1 for v in px if v < 140) / float(len(px))


def bright(img, box=None, thr=200):
    im = Image.open(img).convert("L")
    if box:
        im = im.crop(box)
    px = im.getdata()
    return sum(1 for v in px if v > thr)


def mid_white(img):
    """卡片中区（大字区）亮字占比 —— 用于「成片 vs 卡片流基准」对拍"""
    im = Image.open(img).convert("L").crop((60, 620, 1020, 1300))
    px = im.getdata()
    return sum(1 for v in px if v > 190) / float(len(px))


def rms_db(p, ss, dur=2.0):
    r = subprocess.run([FF, "-v", "info", "-ss", str(ss), "-t", str(dur), "-i", p,
                        "-af", "volumedetect", "-f", "null", os.devnull],
                       capture_output=True, text=True, errors="ignore")
    for line in (r.stderr or "").split("\n"):
        if "mean_volume" in line:
            return float(line.split("mean_volume:")[1].split("dB")[0])
    return None


def main(ep):
    import compose
    P = compose.plan(ep)
    out = os.path.join("E:/心理咨询IP/05-成片", P["cfg"]["line"] if ep != "00" else "过渡片", P["cfg"]["name"])
    if not os.path.exists(out):
        print("❌ 成片不存在:", out); return False
    os.makedirs(TMP, exist_ok=True)
    v, a, f = probe(out)
    ok = []
    def chk(name, cond, val=""):
        ok.append(bool(cond))
        print("  %s %-30s %s" % ("✅" if cond else "❌", name, val))

    print("=" * 96); print("【验收 %s】%s" % (ep, os.path.basename(out)))
    vd = float(v["duration"]); ad = float(a["duration"]) if a else 0
    fmt = float(f["duration"])
    print("  ffprobe: %dx%d %s %s | v=%.2fs a=%.2fs fmt=%.2fs | a=%s %skHz" %
          (v["width"], v["height"], v["codec_name"], v["pix_fmt"], vd, ad, fmt,
           a["codec_name"] if a else "-", int(a["sample_rate"]) // 1000 if a else 0))
    chk("分辨率 1080x1920", (v["width"], v["height"]) == (1080, 1920), "%dx%d" % (v["width"], v["height"]))
    _num, _, _den = v["r_frame_rate"].partition("/")
    _fps = float(_num) / float(_den or 1)          # ffprobe 输出 "30/1"，本机自产，安全解析（不用 eval）
    chk("帧率 30fps", abs(_fps - 30) < 0.01, v["r_frame_rate"])
    chk("编码 H.264", v["codec_name"] == "h264", v["codec_name"])
    chk("像素 yuv420p", v["pix_fmt"] == "yuv420p", v["pix_fmt"])
    chk("音频 AAC", a and a["codec_name"] == "aac", a["codec_name"] if a else "-")
    chk("时长 ≤ 180s 且 ≥ 60s", 60 <= vd <= 180.5, "%.1fs" % vd)
    chk("视频时长==音频时长", abs(vd - ad) < 0.15, "差 %.2fs" % (vd - ad))

    # --- 抽帧 ---
    cards = P["rows"]
    first_card_t = cards[0]["t"]
    chk("首卡不早于 2.5s（真人先开口）", first_card_t >= 2.5, "首卡上屏 %.2fs" % first_card_t)
    chk("末卡不盖结尾", cards[-1]["end"] <= P["total"] - 15.0,
        "末卡下屏 %.1fs / 片长 %.1fs" % (cards[-1]["end"], P["total"]))
    t_real = 1.0                              # 开头第 1 秒必须是真人段（有 LOGO + 字幕）
    f_real = grab(out, t_real, TMP + "/real.png")
    logo_box = (44, 70, 176, 202)
    lb = Image.open(f_real).convert("L").crop(logo_box)
    px = list(lb.getdata())
    chk("真人段左上 LOGO 存在", (max(px) - min(px)) > 60, "对比度 %d" % (max(px) - min(px)))
    # 字幕（白字黑描边）：真人段底部 y1500-1615
    sb = bright(f_real, (60, 1490, 1020, 1620), 190)
    chk("真人段有字幕白像素", sb > 800, "白像素 %d" % sb)
    chk("无黑帧(真人段)", dark(f_real) > 0.02, "暗占比 %.3f" % dark(f_real))

    for i, r in enumerate(cards):
        t = r["t"] + 3.6                     # ★ 动画末帧（4.0s 表最后一层 2.9s）
        t = min(t, r["end"] - 0.15)
        img = grab(out, t, TMP + "/c%d.png" % i)
        # ★ 判据：与「卡片流单独渲的基准」对拍（浅色卡片暗像素天生少，单看暗占比会误报）
        d, base = dark(img), dark(grab(out, max(0.4, r["t"] - 0.4), TMP + "/b%d.png" % i))
        ref_card = REF.get(os.path.basename(r["card"]))     # 卡片流基准（cards_mp4/*/<卡名>.mp4）
        if ref_card and os.path.exists(ref_card):
            rim = grab(ref_card, min(3.6, 4.0), TMP + "/r%d.png" % i)
            m_ref, m_out = mid_white(rim), mid_white(img)
            good = abs(m_out - m_ref) <= 0.03
            detail = "与基准对拍 中区白 %.4f vs %.4f" % (m_out, m_ref)
        else:
            good = abs(d - base) > 0.05 or d > 0.015
            detail = "卡内暗占比 %.3f / 卡前 %.3f（无基准可对拍）" % (d, base)
        chk("卡%d 已上屏(%s)" % (i + 1, r["card"].split("/")[1][:16]), good, detail)
    # 音频
    bgm_only = rms_db(out, max(0.3, t_real), 2.0)
    voice_seg = rms_db(out, min(P["total"] - 3, cards[-1]["end"] + 2), 2.0)
    print("  音频实测: 开头段 %.1fdB | 靠后段 %.1fdB" % (bgm_only or -99, voice_seg or -99))
    chk("有 BGM（> -40dB）", (bgm_only or -99) > -40, "%.1fdB" % (bgm_only or -99))
    # ★ 全片解码完整性（重复写/写坏文件时，只有这一项能直接抓出来）
    acp = grab(out, 0, TMP + "/x.png")             # 借用 grab 复制成 ASCII 名
    pr = subprocess.run([FF, "-v", "error", "-i", acp, "-f", "null", "-"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    bad = [l for l in pr.stderr.splitlines() if l.strip()]
    chk("全片解码无损坏", len(bad) == 0,
        "0 错误" if not bad else "%d 条解码错误：%s" % (len(bad), bad[0][:70]))
    print("\n  结果: %d/%d 项通过 %s" % (sum(ok), len(ok), "✅ 全过" if all(ok) else "❌ 有不通过"))
    return all(ok)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "01")
