# -*- coding: utf-8 -*-
"""第二批（11-16）合成器 —— 沿用 rebuild_20261013 架构（COVER_DUR=0）
   · 真人主轴连续，卡片 overlay 盖上（不占时长）
   · 字幕烧在真人上；LOGO 只真人段；AI 声明全程
   · 影视级调色：轻降噪 → 曲线压高光（吃掉屏幕反光）→ 对比/饱和 → 锐化 → 轻暗角
用法: python compose_batch2.py <n> [<n> ...]
"""
import os, sys, json, io, subprocess, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subs_and_anchors as SA
ILLUST_PLAN = {}  # C方案：不做插画插播（董事长否掉：遮挡真人+看不懂）

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
FFP = FF.replace("ffmpeg.exe", "ffprobe.exe")
ROOT = "E:/心理咨询IP"
R = ROOT + "/04-工程/batch2"
ANIM = R + "/cards_mp4_v2"   # 2026-10-26：15张卡方案；无则自动退回 cards_mp4
SUBD = R + "/subs"
LOGO = ROOT + "/04-工程/overlay_new/logo_corner.png"
NOTICE = ROOT + "/04-工程/overlay_new/ai_notice.png"
MUS_FOLK = ROOT + "/06-音乐/国际民谣_免版税"
MUS_AMB = ROOT + "/06-音乐/温柔轻音乐_新"
MUS_WAV = ROOT + "/06-音乐/_试听"

CARD_ANIM = 4.0
CARD_GAP = 1.0
READ_CPS = 5.0      # 卡片文字阅读速度（字/秒）
MIN_HOLD = 2.6     # 卡片最短停留（保证看清）
MAX_HOLD = 5.5     # 卡片最长停留（控制总占比，真人要露脸）
OPEN_MIN = 3.0
END_KEEP = 15.0
VOICE_DB = 10.0
BGM_BELOW = 15.0
GRADE = True
KEEP_LEN = 177.0      # 成片上限 177s（3分钟=180s，留3s余量；给口播+留白留出边界）
SW, SH = 810, 1440   # 中间底片尺寸：够 1080 输出，省一半 CPU


def dur(p):
    r = subprocess.run([FFP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def rms_db(path, ss=20.0, dur_s=6.0):
    import wave, numpy as np
    tmp = os.path.join(R, "_tmp", "_rms.wav")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(ss), "-i", path, "-t", str(dur_s),
                    "-ac", "1", "-ar", "16000", tmp], capture_output=True, timeout=120)
    if not os.path.exists(tmp) or os.path.getsize(tmp) < 1000:
        return -30.0
    with wave.open(tmp, "rb") as f:
        d = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(float)
    r = np.sqrt((d ** 2).mean()) if len(d) else 0
    return 20 * np.log10(r / 32768) if r > 0 else -60.0


EYE_W = 420            # 眼部小窗宽（1080 画幅下）
EYE_X = 1080 - EYE_W - 60
EYE_Y = 1230           # 竖屏中下，避开顶部品牌区、字幕和底部 LOGO
EYE_N = 3              # 每条插 3 处
EYE_DUR = 6.0          # 每处 6 秒


def eye_windows(total):
    """避开前 20 秒（观众先看人）与最后 20 秒（收尾），均分插 3 段"""
    a, b = 20.0, max(30.0, total - 20.0 - EYE_DUR)
    if b <= a:
        return []
    step = (b - a) / EYE_N if EYE_N > 1 else 0
    return [(a + step * i, EYE_DUR) for i in range(EYE_N)]


def card_chars(n, key):
    """卡片字数（决定停留时长）：优先从 cards_v2 直接算，退回 card_texts.json"""
    try:
        from cards_v2 import CARDS_V2
        for name, kind, kw, a in CARDS_V2.get(n, []):
            if name != key:
                continue
            if kind == "main":
                ups = [a["l1"], a["l2"], a["sub"]]
            elif kind == "three":
                ups = [a["lead"]] + list(a["items"]) + ([a["tail"]] if a.get("tail") else [])
            elif kind == "quote":
                ups = [a["lead"], a["big"]]
            else:
                ups = [a["lead"]] + list(a["items"])
            return sum(len(str(t).replace(" ", "")) for t in ups)
    except Exception:
        pass
    txts = json.load(io.open(R + "/card_texts.json", encoding="utf-8"))
    d, f = key.split("/") if "/" in key else (str(n), key)
    ups = txts.get("%s|%s.html" % (d, f)) or txts.get("%d|%s.html" % (n, f))
    if ups is None:
        raise KeyError(key)
    return sum(len(t.replace(" ", "")) for t in ups)


def plan(n):
    cfg = SA.EPS[n]
    clean = os.path.join(ROOT, "素材_clean2", "%d.mp4" % n)   # 2026-10-25：改用带音轨+去反光的新素材
    src = clean if os.path.exists(clean) else os.path.join(ROOT, "素材", "%d.mp4" % n)
    eye = os.path.join(ROOT, "素材_clean2", "eye_%d.mp4" % n)
    eye = eye if os.path.exists(eye) else None
    raw = dur(src)
    sp = cfg["speed"]
    # 只保留口播部分（剪掉片尾预告/多余空白），再按倍速压到 176s（抖音3分钟留余量）
    d = json.load(io.open(os.path.join(R, "final_%d.json" % n), encoding="utf-8"))
    speech_end = d["cues"][-1]["end"]
    # ★ 2026-10-26 修：final_N.json 可能是 ASR 转写不全（EP6 只到163.5s，实际口播到227.7s）。
    #   用 draft_N.json（ASR 细段）的末段做兜底，谁大用谁；再把片尾下集预告剪掉。
    _dp = os.path.join(R, "draft_%d.json" % n)
    if os.path.exists(_dp):
        _dd = json.load(io.open(_dp, encoding="utf-8"))
        _cues = _dd["cues"]
        _last = _cues[-1]["end"]
        # 找片尾预告起点（"下一讲"/"下集"），剪到它之前
        for _c in _cues:
            if ("下一讲" in _c["text"] or "下集" in _c["text"] or "下一期" in _c["text"]):
                _last = _c["start"]
                break
        speech_end = max(speech_end, _last)
    keep = min(raw, speech_end + 0.6)
    # ★ 2026-10-25 修：原版 total = KEEP_LEN(176) 写死，导致「内容不足176s时强行拉伸、
    #   超额时直接剪掉」（EP2 曾丢 45s、EP6 丢 22s 收尾）。改为按真实口播长度算。
    #   规则：口播结束落点 + 1.2s 收尾留白；不超过 176s 上限（抖音3分钟留余量）。
    _speech_total = keep / sp
    # 口播落点 + 1.2s 留白；但绝不允许小于口播落点（否则视频比音频短）
    total = min(KEEP_LEN, max(round(_speech_total + 1.2, 2), round(_speech_total, 2)))
    cards, prev_end, rows = [], None, []
    anch = sorted([(c, t) for c, t, _f in SA.anchors(n)], key=lambda x: x[1])
    # ★ 2026-10-26 修：原逻辑「t = min(t, total - win - tail)」会把靠后的卡片硬往前挤，
    #   导致后一张卡排到前一张卡之前（EP2 评论卡 153s 挤到接力卡 155s 前面，顺序乱）。
    #   改为：先算每张卡的理想时长，若尾部空间不够，就**统一压缩 hold**（最短 1.6s），
    #   而不是移动位置；实在放不下才丢弃末尾卡。顺序永远严格递增。
    _wins = []
    for i, (key, a) in enumerate(anch):
        cn = card_chars(n, key)
        hold = min(MAX_HOLD, max(MIN_HOLD, cn / READ_CPS))
        _wins.append([CARD_ANIM + hold, hold])
    _avail_end = total - END_KEEP
    # 尾部超出时只压"末尾放不下的那几张"，前面的卡保持正常停留时长。
    # （绝不对整片所有卡统一压缩，否则 15 张卡会被一起压到下限，内容看不清。）
    for _try in range(80):
        over = [(i, _wins[i][0]) for i in range(len(_wins))
                if anch[i][1] / sp + _wins[i][0] > _avail_end]
        if not over:
            break
        changed = False
        for i, _ in over:
            if _wins[i][1] > 2.2:
                _wins[i][1] = round(max(2.2, _wins[i][1] - 0.3), 2)
                _wins[i][0] = CARD_ANIM + _wins[i][1]
                changed = True
        if not changed:
            break

    # 全局占比封顶：卡片总时长不超过片长 55%，保证真人是画面的主体
    _cap = total * 0.55
    _guard = 0
    while sum(w[0] for w in _wins) > _cap and _guard < 200:
        _guard += 1
        shr = max(range(len(_wins)), key=lambda i: _wins[i][1])
        if _wins[shr][1] <= 2.6:
            break
        _wins[shr][1] = round(_wins[shr][1] - 0.2, 2)
        _wins[shr][0] = CARD_ANIM + _wins[shr][1]

    for i, (key, a) in enumerate(anch):
        win, hold = _wins[i]
        t = a / sp
        pushed = 0.0
        if i == 0 and t < OPEN_MIN:
            pushed = OPEN_MIN - t
            t = OPEN_MIN
        if prev_end is not None and t < prev_end + CARD_GAP:
            pushed += prev_end + CARD_GAP - t
            t = prev_end + CARD_GAP
        tail = END_KEEP if i == len(anch) - 1 else 0.3
        if t + win + tail > total:      # 严格保序：放不下就缩短本卡，绝不前移
            win = max(CARD_ANIM + 1.6, total - tail - t)
            hold = max(1.6, win - CARD_ANIM)
        if t + win > total:             # 实在放不下：丢掉这张，不留错序
            continue
        cards.append((key, t, win, hold))
        rows.append(dict(card=key, chars=cn, hold=round(hold, 1), win=round(win, 1),
                         t=round(t, 2), end=round(t + win, 2), pushed=round(pushed, 2)))
        prev_end = t + win
    return dict(src=src, eye=eye, raw=raw, keep=keep, total=total, cards=cards, rows=rows, cfg=cfg, speed=sp,
                card_pct=round(sum(r["win"] for r in rows) / total * 100))


def build(n):
    P = plan(n)
    cfg, total, rows, sp = P["cfg"], P["total"], P["rows"], P["speed"]
    print("=" * 100)
    print("【%d】%s | 素材 %.1fs ÷%.2f → 成片 %.1fs (%d:%04.1f) | BGM %s" %
          (n, cfg["name"], P["raw"], sp, total, int(total // 60), total % 60, os.path.basename(cfg["bgm"])))
    print("  卡片 %d 张，占片长 %d%%" % (len(rows), P["card_pct"]))
    print("  %-28s %4s %5s %6s %8s %8s" % ("卡", "字数", "停留", "窗口", "上屏", "下屏"))
    for r in rows:
        print("  %-28s %4d %5.1f %6.1f %8.2f %8.2f" % (r["card"], r["chars"], r["hold"], r["win"], r["t"], r["end"]))
    if not os.path.exists(cfg["bgm"]):
        print("  ❌ BGM 缺文件:", cfg["bgm"]); return False

    ins = ["-i", P["src"]]
    ci = {}
    for key, t, win, hold in P["cards"]:
        p = os.path.join(ANIM, str(n), key + ".mp4")
        if not os.path.exists(p):
            p = os.path.join(R, "cards_mp4", str(n), key + ".mp4")   # 老 4 张方案兜底
        if not os.path.exists(p):
            print("  ❌ 卡片动画缺:", p); return False
        ci[key] = len(ins) // 2
        ins += ["-i", p]
    EI = None
    # 2026-10-25 董事长要求：每个视频都去掉单独弹出的小窗口 → 不再加载眼窗素材
    # if P.get("eye"):
    #     EI = len(ins) // 2
    #     ins += ["-i", P["eye"]]
    LI = len(ins) // 2; ins += ["-i", LOGO]
    NI = len(ins) // 2; ins += ["-i", NOTICE]
    BI = len(ins) // 2; ins += ["-stream_loop", "-1", "-i", cfg["bgm"]]
    assert BI == LI + 2 and (EI is None or EI < LI)

    p = []
    # ① 真人主轴：先降尺寸（省 CPU）→ 变速 → 30fps → 1080x1920 → 影视调色
    # ★ 2026-10-25 修：视频只截到 keep，但 total 比它多 1.2s 留白 → 视频比音频短 1.18s
    #   （EP2/EP6 因此被判"音视频时长不等"）。修法：末尾定格补满到 total，两者严格对齐。
    _pad = max(0.0, float(total) - float(P["keep"]) / sp)
    # ★ C方案「画面呼吸」：真人全程在主画面不切走，靠缓慢推拉让画面不死板。
    #   做法：先按 1.10 倍尺寸裁切，再用 zoompan 在片子时间轴上做 1.00→1.06 的极缓推近，
    #   推近速度跟片长挂钩（长片更慢），肉眼几乎察觉不到切换，只觉得画面"活"。
    _breath = 0.055                      # 总推近幅度 5.5%（超过 8% 会显得假）
    _frames = max(2, int(round(total * 30)))
    chain = ("[0:v]trim=start=0:end=%.3f,setpts=PTS-STARTPTS[rawv];"
             "[rawv]scale=%d:%d:flags=bicubic,setsar=1,setpts=(PTS-STARTPTS)/%.4f,"
             "fps=30,tpad=stop_mode=clone:stop_duration=%.3f,"
             "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
             "crop=1080:1920,setsar=1" % (P["keep"], SW, SH, sp, _pad))
    # 呼吸推近（对已定尺寸的画面做轻微 zoompan，中心锁定人像）
    chain += (",zoompan=z='1+%.4f*on/%d':x='iw/2-(iw/zoom/2)':y='ih*0.42-(ih/zoom*0.42)':"
              "d=1:s=1080x1920:fps=30" % (_breath, _frames))
    if GRADE:
        # 电影级调色链 v3（2026-10-25 04:0x 定档：董事长反馈"太暗"，回抬一档）
        # 三版实测对照：
        #   原片        均值198 标准差39   （太亮太平，像手机录像）
        #   上一版      均值103 标准差55   （太暗，被否）
        #   ★本版 K1    均值136 标准差52 暗角+59 人脸亮度182  （脸不暗、有层次、有电影感）
        # 参数来源：单帧跑 10 组实测，选"人脸亮度≥180"里结构最好的一组，不靠感觉。
        chain += (
            # ① 轻度降噪
            ",hqdn3d=1.2:1.0:2.5:2.5"
            # ② 温和 S 曲线：留黑位层次但不压死，高光收一点
            ",curves=all='0/0 0.20/0.10 0.45/0.35 0.70/0.66 0.88/0.86 1/0.96'"
            # ③ 轻对比 + 轻压（关键：brightness 只 -0.04，不再 -0.16）
            ",eq=contrast=1.20:brightness=-0.04:saturation=1.04"
            # ④ 暗角：聚焦但不压脸
            ",vignette=angle=PI/4.8"
            # ⑤ 局部锐化
            ",cas=strength=0.20"
            # ⑥ 极轻颗粒
            ",noise=alls=5:allf=t+u")
    # 统一成 TV range 的 yuv420p（yuvj420p 会被平台判为非法像素格式）
    chain += ",scale=in_range=full:out_range=tv,format=yuv420p,setparams=range=tv:colorspace=bt709[hv]"
    p.append(chain)
    p.append("[hv]ass=%d.ass[hvsub]" % n)
    p.append("[hvsub][%d:v]overlay=44:70[base]" % LI)
    cur = "base"
    if EI is not None:
        # 眼部特写画中画：右下角，圆角边框，开口 20s 后插 3 处（避开首卡与末段）
        p.append("[%d:v]scale=%d:%d:flags=lanczos,setsar=1,setpts=(PTS-STARTPTS)/%.4f,fps=30"
                 "[ey0]" % (EI, EYE_W, int(EYE_W * 9 / 16), sp))
        p.append("[ey0]drawbox=x=0:y=0:w=iw:h=ih:color=white@0.85:t=6,format=yuva420p[ey1]")
        cur_eye = cur
        for j, (t0_, dur_) in enumerate(eye_windows(total)):
            p.append("[%s][ey1]overlay=%d:%d:enable='between(t,%.2f,%.2f)'[e%d]" %
                     (cur_eye, EYE_X, EYE_Y, t0_, t0_ + dur_, j))
            cur_eye = "e%d" % j
        cur = cur_eye
    for k, (key, t, win, hold) in enumerate(P["cards"]):
        i = ci[key]
        # ===== 卡片图层（总长严格 = win）=====
        # 动画段与停留段都从同一路输入裁出，拼合后再 trim 到窗口精确长度，
        # 保证 overlay 时窗与流时长完全对齐，15 张卡才能逐张叠上。
        # 停留段优先（董事长要"能看清楚再过"）：先按最短 2.6s 保住停留，
        # 剩下的给动画段；窗口够大时动画段保持完整 CARD_ANIM。
        hold_len = min(hold, max(2.6, win - CARD_ANIM)) if win > 3.2 else max(0.2, win - 0.4)
        anim_len = max(0.4, win - hold_len)
        # ★ 卡片必须 100% 原样呈现（2026-10-27 董事长纠正：不许裁剪、不许只放一部分）。
        #   卡片源本身就是 1080x1920 全屏画布，动画是完整分层入场；
        #   合成时原尺寸 overlay=0:0，卡片期间完整盖住画面（这是原有设计，不是缺陷）。
        #   曾错误地裁成 720x960 放底部，导致卡片内容和动画都被切掉 —— 禁止再改。
        p.append("[%d:v]trim=start=0:end=%.3f,setpts=PTS-STARTPTS,fps=30,"
                 "scale=1080:1920:flags=lanczos,setsar=1[ki%d]" % (i, anim_len, k))
        p.append("[%d:v]trim=start=%.3f:end=%.3f,setpts=PTS-STARTPTS,fps=30,"
                 "scale=1080:1920:flags=lanczos,setsar=1,tpad=stop_mode=clone:stop_duration=%.3f[kt%d]" %
                 (i, max(0.0, CARD_ANIM - 0.05), CARD_ANIM, hold_len, k))
        p.append("[ki%d][kt%d]concat=n=2:v=1:a=0,setpts=PTS-STARTPTS,"
                 "trim=start=0:end=%.3f[cc%d]" % (k, k, win, k))
        # 补到上屏时刻的填充必须是「全透明」，否则黑底会把整段时间遮住，
        # 表现为只有第一张卡能看见、后面的卡全被黑帧盖掉。
        p.append("[cc%d]format=yuva420p,tpad=start_duration=%.3f:start_mode=add:"
                 "color=0x000000@0.0,fade=t=in:st=%.3f:d=0.28:alpha=1,"
                 "fade=t=out:st=%.3f:d=0.22:alpha=1[kf%d]" %
                 (k, t, t, max(0.0, t + win - 0.24), k))
        p.append("[%s][kf%d]overlay=0:0:enable='between(t,%.3f,%.3f)'[o%d]" % (cur, k, t, t + win, k))
        cur = "o%d" % k
    # LOGO 只贴真人段：卡片本身已自带品牌区（左上老蔡说 + 右下AI声明），
    # 再叠一层就会出现两个老蔡说重影。用 enable 把人像段之外的时间排除。
    segs = []
    prev = 0.0
    for (_k, _t, _w, _h) in P["cards"]:
        if _t > prev + 0.01:
            segs.append((prev, _t))
        prev = max(prev, _t + _w)
    if total > prev + 0.01:
        segs.append((prev, total))
    en = "+".join("between(t,%.3f,%.3f)" % (a, b) for a, b in segs) or "1"
    p.append("[%s][%d:v]overlay=44:70:enable='%s'[lg0]" % (cur, LI, en))
    p.append("[lg0][%d:v]overlay=672:1818:enable='%s'[vout]" % (NI, en))
    # ② 音频：人声 +10dB → atempo → 混 BGM（严格低 6dB），禁 apad
    p.append("[0:a]atrim=start=0:end=%.3f,asetpts=PTS-STARTPTS,volume=%.1fdB,aresample=48000,"
             "atempo=%.4f[voice]" % (P["keep"], VOICE_DB, sp))
    vd = rms_db(P["src"], 5.0) + VOICE_DB
    bd = rms_db(cfg["bgm"], 20.0)
    gain = (vd - BGM_BELOW) - bd
    print("  ★ 人声 %.1fdB | BGM %.1fdB → 增益 %+.1f（严格低 %ddB）" % (vd, bd, gain, BGM_BELOW))
    p.append("[%d:a]atrim=start=20:end=%.3f,asetpts=PTS-STARTPTS,volume=%.1fdB,aresample=48000[bgm]" %
             (BI, 20 + total + 2, gain))
    p.append("[voice][bgm]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
             "atrim=start=0:end=%.3f,asetpts=PTS-STARTPTS,alimiter=limit=0.95[aout]" % total)

    graph = ";\n".join(p)
    io.open(os.path.join(R, "_filter_%d.txt" % n), "w", encoding="utf-8").write(graph)
    outdir = os.path.join(ROOT, "05-成片", cfg["line"])
    os.makedirs(outdir, exist_ok=True)
    OUT = os.path.join(outdir, cfg["name"])
    cmd = [FF, "-y", "-v", "warning", "-stats"] + ins + \
          ["-filter_complex", graph, "-map", "[vout]", "-map", "[aout]", "-t", "%.3f" % total,
           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-maxrate", "14M", "-bufsize", "28M",
           "-threads", "4", "-x264-params", "threads=4:lookahead_threads=1",
           "-pix_fmt", "yuv420p", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709",
           "-color_trc", "bt709", "-r", "30", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", OUT + ".tmp.mp4"]
    print("  → 合成中 ... (%d 段滤镜)" % len(p), flush=True)
    t0 = time.time()
    with open(os.path.join(R, "_ff_%d.log" % n), "w", encoding="utf-8") as lf:
        r = subprocess.run(cmd, cwd=SUBD, stdout=lf, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        print("  ❌ ffmpeg 失败，看 _ff_%d.log" % n)
        print(io.open(os.path.join(R, "_ff_%d.log" % n), encoding="utf-8", errors="ignore").read()[-1200:])
        try:
            os.remove(OUT + ".tmp.mp4")
        except OSError:
            pass
        return False
    chk = subprocess.run([FFP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          OUT + ".tmp.mp4"], capture_output=True, text=True)
    if not chk.stdout.strip():
        print("  ❌ 成品校验失败（moov 缺失）")
        return False
    _tmp_out = OUT + ".tmp.mp4"
    # ★ 2026-10-26：不再在脚本里改名/另存。成品就留成 .tmp.mp4，
    #   由外部（老马）确认 ffmpeg 全部退出后统一改名——脚本内改名容易与并发进程打架，
    #   历史上有两次成品被改名逻辑弄丢（FileNotFoundError + 时间戳文件名消失）。
    print("  ✅ 合成完成（成品）: %s  %.1fMB  用时 %.1f 分钟"
          % (_tmp_out, os.path.getsize(_tmp_out) / 1e6, (time.time() - t0) / 60), flush=True)
    return True


if __name__ == "__main__":
    for n in [int(x) for x in (sys.argv[1:] or ["1"])]:
        build(n)
