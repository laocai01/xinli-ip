# -*- coding: utf-8 -*-
"""《老蔡说》第一批10条 · 合成器（重建版 2026-10-13，本机 CPU 零成本）
架构（最新定案 COVER_DUR=0）：
  0 秒即真人开口；字幕烧在真人主轴；LOGO 只在真人段；卡片按卡点「盖」上去（不占时长）；
  卡片窗口 = 动画4.0s + 停留(按卡面字数算) ；卡片之间必露真人 ≥1.0s；AI声明全程。

用法: python compose.py <ep> [<ep> ...]      ep = 00..09
"""
import os, sys, json, io, re, subprocess, glob, shutil, pickle

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
FFP = FF.replace("ffmpeg.exe", "ffprobe.exe")
ROOT = "E:/心理咨询IP"
R = ROOT + "/04-工程/rebuild_20261013"
ANIM = R + "/cards_mp4"
SUBD = R + "/subs"
LOGO = ROOT + "/04-工程/overlay_new/logo_corner.png"
NOTICE = ROOT + "/04-工程/overlay_new/ai_notice.png"
MUS_FOLK = ROOT + "/06-音乐/国际民谣_免版税"
MUS_AMB = ROOT + "/06-音乐/温柔轻音乐_新"
SPEED = 1.35
CARD_ANIM = 4.0          # 卡片动画时长（JS 时间表最后一层 2.9s，留余量）
CARD_GAP = 1.0           # 卡片之间至少露真人 1.0s
READ_CPS = 5.0           # 舒适阅读速度 字/秒（董事长 2026-10-13：卡片不许一闪而过）
MIN_HOLD = 3.0           # 最短停留（交付标准 3.6）
MAX_HOLD = 8.0
OPEN_MIN = 3.0           # ★ 首卡不早于 3.0s：定案「第 0 秒就是真人开口」，开头必须先露真人
END_KEEP = 20.0          # ★ 末卡不盖结尾：结尾四段式（金句/转发/评论+关注/预告）必须露真人

ANCH = {
 "00": [("过渡片/01_我讲错了一件事",4.9),("过渡片/02_讲一点就炸",15.9),("过渡片/03_同一个人",29.7),
        ("过渡片/04_谁都可以累就是你",49.8),("过渡片/05_你都找不到人说",66.4),("过渡片/06_所以你就不说了",80.2),
        ("过渡片/07_我把话分成三块",96.3),("过渡片/08_第二块家里人",119.4),("过渡片/09_第三块孩子",138.7),
        ("过渡片/10_哪块说到心坎",171.7),("过渡片/11_下一条从头讲",192.9)],
 "01": [("01_睡不着/01_主_你不是睡不着",5.4),("01_睡不着/02_副_脑子不肯下班",37.0),
        ("01_睡不着/03_金句_发动机还在空转",86.9),("01_睡不着/04_方法_给脑子下班",101.1)],
 "02": [("02_脾气/01_主_你不是脾气变了",0.1),("02_脾气/03_金句_稻草不是原因",82.2),
        ("02_脾气/02_副_装的地方满了",91.4),("02_脾气/04_方法_问自己一句",108.2)],
 "03": [("03_沉默的人/01_主_他不是不想说",20.6),("03_沉默的人/03_金句_沉默里有东西",58.9),
        ("03_沉默的人/02_副_他在外面装了十小时",85.6),("03_沉默的人/04_方法_问一句轻的",130.3)],
 "04": [("04_没用了/01_主_退休那天起我就没用了",0.5),("04_没用了/02_副_手机一天不响",33.0),
        ("04_没用了/03_金句_没人需要你",86.0),("04_没用了/04_方法_找件小事",118.4)],
 "05": [("05_屋里安静/01_主_屋里安静得吓人",0.7),("05_屋里安静/02_副_电视不是陪伴",13.0),
        ("05_屋里安静/03_金句_一潭死水",118.5),("05_屋里安静/04_方法_去有人的地方",154.3)],
 "06": [("06_打电话/01_主_说不到两句就挂了",20.8),("06_打电话/02_副_想说的一句没说",58.3),
        ("06_打电话/03_金句_错位",88.8),("06_打电话/04_方法_说想他了",163.1)],
 "07": [("07_孩子不说话/01_主_不说话不代表没事",0.5),("07_孩子不说话/02_副_他不是不想说",62.0),
        ("07_孩子不说话/04_方法_问小的",100.0),("07_孩子不说话/03_金句_别急他没事",138.7)],
 "08": [("08_越问越不说/01_主_你第一句话把门关了",3.7),("08_越问越不说/02_副_查岗还是话筒",42.5),
        ("08_越问越不说/04_方法_三句话",79.4),("08_越问越不说/03_金句_后来呢",97.4)],
 "09": [("09_考砸那天/01_主_他怕的不是你骂他",5.4),("09_考砸那天/02_副_那个乖是害怕",35.9),
        ("09_考砸那天/03_金句_我不值钱了",72.9),("09_考砸那天/04_方法_你还是我的孩子",84.1)],
}
CUTS = {"03": [(174.5, 202.2)], "04": [(165.8, 190.6)], "05": [(182.4, 235.9)], "06": [(169.7, 199.0)]}
EPS = {
 "00": dict(src="00_过渡片_我讲了好几期今天说件事_原片.mp4", line="过渡片", bgm=MUS_FOLK + "/A_沉静反思_01_Through_Ups_and_Down.mp3",
            name="00_过渡片_我讲了好几期今天说件事.mp4"),
 "01": dict(src="01_没人可说_为什么你累得要死却睡不着_原片.mp4", line="没人可说", bgm=MUS_FOLK + "/C_夜静陪伴_03_Irenko.mp3",
            name="第14条_没人可说第1讲_为什么你累得要死却睡不着_20261013.mp4"),
 "02": dict(src="02_没人可说_你不是脾气变了_原片.mp4", line="没人可说", bgm=MUS_FOLK + "/A_沉静反思_02_Forever_in_My_Heart.mp3",
            name="第15条_没人可说第2讲_你不是脾气变了_20261013.mp4"),
 "03": dict(src="03_没人可说_家里那个最沉默的人_原片.mp4", line="没人可说", bgm=MUS_AMB + "/BGM05_Deep_Meditation.mp3",
            name="第16条_没人可说第3讲_家里那个最沉默的人_20261013.mp4"),
 "04": dict(src="04_我是不是没用了_退休那天起我就没用了_原片.mp4", line="我是不是没用了", bgm=MUS_FOLK + "/E_旧日微温_01_Old_Old_Love.mp3",
            name="第17条_我是不是没用了第1讲_退休那天起我就没用了_20261013.mp4"),
 "05": dict(src="05_我是不是没用了_屋里安静得吓人_原片.mp4", line="我是不是没用了", bgm=MUS_AMB + "/BGM01_Saying_Goodbye.mp3",
            name="第18条_我是不是没用了第2讲_屋里安静得吓人_20261013.mp4"),
 "06": dict(src="06_我是不是没用了_我给孩子打电话没说两句就挂了_原片.mp4", line="我是不是没用了",
            bgm=MUS_FOLK + "/E_旧日微温_03_Wedding_03.mp3", name="第19条_我是不是没用了第3讲_我给孩子打电话没说两句就挂了_20261013.mp4"),
 "07": dict(src="07_你根本不了解我_孩子不说话不代表没事_原片.mp4", line="你根本不了解我",
            bgm=MUS_AMB + "/BGM04_Upon_Reflection.mp3", name="第20条_你根本不了解我第1讲_孩子不说话不代表没事_20261013.mp4"),
 "08": dict(src="08_你根本不了解我_你越问他越不说_原片.mp4", line="你根本不了解我",
            bgm=MUS_AMB + "/BGM06_Anhedonia.mp3", name="第21条_你根本不了解我第2讲_你越问他越不说_20261013.mp4"),
 "09": dict(src="09_你根本不了解我_他考砸那天最怕的不是你骂他_原片.mp4", line="你根本不了解我",
            bgm=MUS_AMB + "/BGM03_Broken_Inside.mp3", name="第22条_你根本不了解我第3讲_他考砸那天最怕的不是你骂他_20261013.mp4"),
}


def dur(p):
    r = subprocess.run([FFP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def rms_db(path, ss=20.0, dur_s=6.0):
    import wave, numpy as np, tempfile
    tmp = os.path.join(R, "_tmp", "_rms_%d.wav" % (abs(hash(path)) % 99999))
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(ss), "-i", path, "-t", str(dur_s),
                    "-ac", "1", "-ar", "16000", tmp], capture_output=True, timeout=90)
    if not os.path.exists(tmp) or os.path.getsize(tmp) < 1000:
        return -30.0
    with wave.open(tmp, "rb") as f:
        d = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(float)
    os.remove(tmp)
    r = np.sqrt((d ** 2).mean()) if len(d) else 0
    return 20 * np.log10(r / 32768) if r > 0 else -60.0


def card_chars(key):
    """卡面正文字数（up 层：主标题+辅助句；不含品牌条/签名条）
    ★ 读本机自产的 card_texts.json（不用 pickle，避免反序列化风险）"""
    txts = json.load(io.open(R + "/card_texts.json", encoding="utf-8"))
    d, f = key.split("/")
    ups = txts.get("%s|%s.html" % (d, f))
    if ups is None:
        raise KeyError(key)
    return sum(len(t.replace(" ", "")) for t in ups), ups


def plan(ep):
    cfg = EPS[ep]
    src = os.path.join(ROOT, "素材", cfg["src"])
    raw = dur(src)
    cuts = CUTS.get(ep, [])
    cutlen = sum(b - a for a, b in cuts)
    total = (raw - cutlen) / SPEED

    def fin(t):
        return (t - sum(max(0.0, min(t, b) - a) for a, b in cuts)) / SPEED

    cards, prev_end, rows = [], None, []
    for i, (key, a) in enumerate(ANCH[ep]):
        n, ups = card_chars(key)
        hold = min(MAX_HOLD, max(MIN_HOLD, n / READ_CPS))
        win = CARD_ANIM + hold
        t = fin(a)
        pushed = 0.0
        if i == 0 and t < OPEN_MIN:          # ★ 首卡不早于 3.0s（定案：第 0 秒真人开口）
            pushed = OPEN_MIN - t
            t = OPEN_MIN
        if prev_end is not None and t < prev_end + CARD_GAP:
            pushed += prev_end + CARD_GAP - t
            t = prev_end + CARD_GAP
        # ★ 末卡不盖结尾（结尾四段式必须露真人），其余卡只要不超出片尾
        tail = END_KEEP if i == len(ANCH[ep]) - 1 else 0.2
        t = min(t, total - win - tail)
        cards.append((key, t, win, hold))
        rows.append(dict(card=key, chars=n, hold=round(hold, 1), win=round(win, 1),
                         t=round(t, 2), end=round(t + win, 2), pushed=round(pushed, 2)))
        prev_end = t + win
    cov = sum(r["win"] for r in rows)
    return dict(src=src, raw=raw, total=total, cards=cards, rows=rows,
                card_pct=round(cov / total * 100), cfg=cfg)


def build(ep):
    P = plan(ep)
    cfg, total, rows = P["cfg"], P["total"], P["rows"]
    print("=" * 96)
    print("【%s】%s  |  素材 %.1fs → 成片 %.1fs (%d:%04.1f)  |  BGM %s" %
          (ep, cfg["name"], P["raw"], total, int(total // 60), total % 60, os.path.basename(cfg["bgm"])))
    print("  卡片 %d 张，占片长 %d%%" % (len(rows), P["card_pct"]))
    print("  %-34s %4s %5s %6s %8s %8s %6s" % ("卡", "字数", "停留", "窗口", "上屏", "下屏", "顺延"))
    for r in rows:
        print("  %-34s %4d %5.1f %6.1f %8.2f %8.2f %6.1f" %
              (r["card"], r["chars"], r["hold"], r["win"], r["t"], r["end"], r["pushed"]))
    for r in rows:
        if r["pushed"] > 0.01:
            print("  ⚠ 卡点顺延 %.1fs：%s（前卡窗口挤到）" % (r["pushed"], r["card"]))
    if not os.path.exists(cfg["bgm"]):
        print("  ❌ BGM 缺文件:", cfg["bgm"]); return False

    cuts = CUTS.get(ep, [])
    ins = ["-i", P["src"]]
    ci = {}
    for key, t, win, hold in P["cards"]:
        p = os.path.join(ANIM, ep, key.split("/")[1] + ".mp4")
        if not os.path.exists(p):
            print("  ❌ 卡片动画缺:", p); return False
        ci[key] = len(ins) // 2; ins += ["-i", p]
    LI = len(ins) // 2; ins += ["-i", LOGO]
    NI = len(ins) // 2; ins += ["-i", NOTICE]
    BI = len(ins) // 2; ins += ["-stream_loop", "-1", "-i", cfg["bgm"]]
    assert BI == LI + 2

    p = []
    # ① 真人主轴（剪段 → 变速 → 30fps → 1080x1920）
    vq = ",cas=strength=0.35" if cfg.get("sharpen") else ""
    if cuts:
        for i, (a, b) in enumerate(cuts):
            p.append("[0:v]trim=start=0:end=%.3f,setpts=PTS-STARTPTS[vp0]" % a)
            p.append("[0:v]trim=start=%.3f:end=%.3f,setpts=PTS-STARTPTS[vp1]" % (b, P["raw"]))
            p.append("[vp0][vp1]concat=n=2:v=1:a=0[rawv]")
    else:
        p.append("[0:v]trim=start=0:end=%.3f,setpts=PTS-STARTPTS[rawv]" % P["raw"])
    p.append("[rawv]setpts=(PTS-STARTPTS)/%.4f,fps=30,scale=1080:1920:"
             "force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,setsar=1%s[hv]" % (SPEED, vq))
    # ② 字幕（烧在真人上，卡片会盖住它）
    p.append("[hv]ass=%s.ass:fontsdir=fonts[hvsub]" % ep)
    # ③ 真人段 LOGO
    p.append("[hvsub][%d:v]overlay=44:70[base]" % LI)
    # ④ 卡片盖上去（tpad 前置到窗口起点 + enable 限窗）
    cur = "base"
    for n, (key, t, win, hold) in enumerate(P["cards"]):
        i = ci[key]
        p.append("[%d:v]trim=start=0:end=%.2f,setpts=N/(30*TB),fps=30,scale=1080:1920,setsar=1[ki%d]" % (i, CARD_ANIM, n))
        p.append("[%d:v]trim=start=%.2f:end=%.2f,setpts=N/(30*TB),fps=30,scale=1080:1920,setsar=1,"
                 "tpad=stop_mode=clone:stop_duration=%.2f[kt%d]" % (i, CARD_ANIM - 0.05, CARD_ANIM, hold, n))
        p.append("[ki%d][kt%d]concat=n=2:v=1:a=0,setpts=PTS-STARTPTS[kc%d]" % (n, n, n))
        p.append("[kc%d]tpad=start_duration=%.3f:start_mode=add:color=black[k%d]" % (n, t, n))
        p.append("[%s][k%d]overlay=0:0:enable='between(t,%.3f,%.3f)'[o%d]" % (cur, n, t, t + win, n))
        cur = "o%d" % n
    # ⑤ AI 声明（全程）
    p.append("[%s][%d:v]overlay=672:1818[vout]" % (cur, NI))
    # ⑥ 音频：剪段 → 人声 +10dB → atempo（无 atempo 时省略；全程禁 apad）
    if cuts:
        p.append("[0:a]atrim=start=0:end=%.3f,asetpts=PTS-STARTPTS[ap0]" % cuts[0][0])
        p.append("[0:a]atrim=start=%.3f:end=%.3f,asetpts=PTS-STARTPTS[ap1]" % (cuts[0][1], P["raw"]))
        p.append("[ap0][ap1]concat=n=2:v=0:a=1[rawa]")
    else:
        p.append("[0:a]atrim=start=0:end=%.3f,asetpts=PTS-STARTPTS[rawa]" % P["raw"])
    p.append("[rawa]asetpts=PTS-STARTPTS,volume=10.0dB,aresample=48000,atempo=%.4f[voice]" % SPEED)
    vd = rms_db(P["src"], 5.0) + 10.0
    bd = rms_db(cfg["bgm"], 20.0)
    gain = (vd - 6.0) - bd
    print("  ★ 实测人声 %.1fdB（素材 %.1f+10）| BGM原 %.1f → 增益 %+.1f（严格低 6dB）" % (vd, vd - 10, bd, gain))
    p.append("[%d:a]atrim=start=20:end=%.3f,asetpts=PTS-STARTPTS,volume=%.1fdB,aresample=48000[bgm]" %
             (BI, 20 + total, gain))
    p.append("[voice][bgm]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
             "atrim=start=0:end=%.3f,asetpts=PTS-STARTPTS,alimiter=limit=0.95[aout]" % total)

    os.makedirs(SUBD, exist_ok=True)
    fpath = os.path.join(R, "_filter_%s.txt" % ep)
    graph = ";\n".join(p)
    io.open(fpath, "w", encoding="utf-8").write(graph)
    outdir = os.path.join(ROOT, "05-成片", cfg["line"] if ep != "00" else "过渡片")
    os.makedirs(outdir, exist_ok=True)
    OUT = os.path.join(outdir, cfg["name"])
    # ★ ffmpeg 9.0 已移除 -filter_complex_script → 直接传滤镜串（本链约 3-6K 字符，远低于 32K 上限）
    cmd = [FF, "-y", "-v", "warning", "-stats"] + ins + \
          ["-filter_complex", graph, "-map", "[vout]", "-map", "[aout]", "-t", "%.3f" % total,
           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-maxrate", "14M", "-bufsize", "28M",
           "-threads", "4", "-x264-params", "threads=4:lookahead_threads=1",
           "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", OUT]
    print("  → 合成中 ... (filter %d 段)" % len(p), flush=True)
    import time
    t0 = time.time()
    with open(os.path.join(R, "_ff_%s.log" % ep), "w", encoding="utf-8") as lf:
        r = subprocess.run(cmd, cwd=SUBD, stdout=lf, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        print("  ❌ ffmpeg 失败，看 _ff_%s.log" % ep)
        print(io.open(os.path.join(R, "_ff_%s.log" % ep), encoding="utf-8", errors="ignore").read()[-1500:])
        return False
    print("  ✅ %s  %.1fMB  用时 %.1f 分钟" % (OUT, os.path.getsize(OUT) / 1e6, (time.time() - t0) / 60))
    return True


if __name__ == "__main__":
    for ep in (sys.argv[1:] or ["01"]):
        build(ep)
