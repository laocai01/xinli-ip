"""★ 成片合成器 v3（2026-10-08 董事长定稿架构）
用法: python make_episode.py <配置名...>

★ 核心架构（修正 v2 的错误）：
  真人视频是「主轴」，全程连续播放不中断；
  卡片「盖」在真人画面上播完，播完自动露出真人 —— 卡片不占时间轴，不切碎讲话。

  时间轴：封面8s → [真人主轴（连续）………………] → 闭环8s
                  ↑ 卡片在口播关键句时刻盖上，盖完自动露出真人（声音全程不断）

★ 规格（董事长定）：
  · 封面停留 8 秒、穿插卡片停留 6 秒、闭环页停留 8 秒
  · 卡片张数＝按脚本定（停/退/看/做就是四张），不为凑占比增删
  · 卡片左上角不叠 LOGO（中间品牌条已有）；真人段叠 LOGO(44,70)
  · AI声明(672,1818) 全程叠
  · BGM 温柔轻音乐 -23dB，不压口播
  · 原声一秒不剪，只 atempo 变速（不变调）
  · 1080x1920 / 30fps / CRF17 / yuv420p / AAC192k
"""
import os, sys, subprocess, glob, json, io

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
ANIM = r"E:/心理咨询IP/07-形象设计/卡片v2/动画"
LOGO = r"E:/心理咨询IP/04-工程/overlay_new/logo_corner.png"
NOTICE = r"E:/心理咨询IP/04-工程/overlay_new/ai_notice.png"
MUSDIR = r"E:/心理咨询IP/06-音乐/温柔轻音乐_新"
OUTDIR = r"E:/心理咨询IP/05-成片"

COVER_ANIM = 6.0       # ★ 封面动画素材时长（渲染器渲 6.0s）
COVER_HOLD = 3.0       # ★ 封面动画播完后再停 3 秒
COVER_DUR = COVER_ANIM + COVER_HOLD   # = 9.0s（画面占位总时长，音频延迟跟随）
                       #   （封面动画素材已渲到 6.0s）
                       #   须完整看清封面内容再切真人
CARD_ANIM_DUR = 4.0    # ★ 卡片动画必须 4.0s：JS 动画表里辅助句1.6s、重点字<em>2.7s才出；
                       #   原来 1.4s → 重点字永远不出（成片"文字欠缺"根因）
CARD_HOLD = 3.0        # ★ 2026-10-09 董事长定：所有卡片「动画播完后再停留3秒」才切真人
                       #   → 内文卡窗口 = 动画4.0 + 停留3.0 = 7.0s
                       #   原6.0秒（动画4.0+停留2.0）→ 改 5.0 秒
                       #   封面/闭环另外：封面 3.0s、闭环 6.0s（END_ANIM5+END_HOLD1）
CARD_GAP = 1.0         # ★ 卡片之间至少露真人 1 秒（避免连成一片）
END_ANIM_DUR = 5.0     # 闭环页动画
END_HOLD = 3.0         # ★ 2026-10-09：闭环页同样「动画播完再停3秒」
BGM_DB = -32.0         # （旧）固定值，已不用
BGM_BELOW_VOICE = 6.0  # ★ 2026-10-09 董事长反馈「听不到BGM」→ 由10dB改6dB（严格10dB在手机外放等于没有；6dB仍不盖人声）
BGM_NORM_DB = -20.0    # （保留）
VOICE_TARGET_DB = -18.0  # ★ 人声目标响度（素材提升后约在此）
VOICE_DB = 10.0        # ★ 2026-10-09 人声提升 6→10dB（素材电平偏低，提升后更清晰响亮）

# 每讲配置：素材/总长/倍率/封面/BGM/卡表(卡名, 卡点原片秒)/输出名
# 卡点=该卡片应出现的口播关键句（原片秒）；闭环卡卡点填 0（固定放片尾）
EPISODES = {
    "A2": dict(src=r"E:/心理咨询IP/素材/A线/A2_raw.mp4", total=121.21, speed=1.00,
               cover="封面_新_第1讲_动画.mp4", bgm="BGM01_Saying_Goodbye.mp3",
               cards=[("A2n_01钩子_动画.mp4", 26.2), ("A2n_02痛点_动画.mp4", 44.5),
                      ("A2n_03机制_动画.mp4", 50.1), ("A2n_04转折_动画.mp4", 70.3),
                      ("A2n_05方法_动画.mp4", 77.3), ("A2n_06收束_动画.mp4", 95.3),
                      ("闭环_第1讲_动画.mp4", 0)],
               out="第03条_A线第1讲_想开点.mp4"),
    "A3": dict(src=r"E:/心理咨询IP/素材/A线/A3.mp4", total=96.40, speed=1.00,
               cover="封面_新_第2讲_动画.mp4", bgm="BGM02_Galaxys_Endless_Expanse.mp3",
               cards=[("A3n_01钩子_动画.mp4", 3.0),  ("A3n_02总览_动画.mp4", 19.0),
                      ("A3n_03停_动画.mp4", 30.0),  ("A3n_04退_动画.mp4", 41.0),
                      ("A3n_05看_动画.mp4", 52.0),  ("A3n_06做_动画.mp4", 63.0),
                      ("A3n_07收束_动画.mp4", 78.0),("闭环_第2讲_动画.mp4", 0)],
               out="第04条_A线第2讲_情绪四步.mp4"),
    "B1": dict(src=r"E:/心理咨询IP/素材/B线/B1.mp4", total=165.80, speed=1.15,
               cover="B1封面_第1讲_动画.mp4", bgm="BGM03_Broken_Inside.mp3",
               cards=[("B1n_01钩子_动画.mp4", 81.6), ("B1n_02场景_动画.mp4", 89.6),
                      ("B1n_03机制_动画.mp4", 103.6),("B1n_04点破_动画.mp4", 116.6),
                      ("B1n_05转折_动画.mp4", 123.6),("B1n_06方法_动画.mp4", 129.6),
                      ("B1n_07收束_动画.mp4", 140.0),("闭环_第3讲_动画.mp4", 0)],
               out="第05条_B线第1讲_追与躲.mp4"),
    "B2": dict(src=r"E:/心理咨询IP/素材/B线/B2.mp4", total=82.90, speed=1.00,
               cover="B2封面_第2讲_动画.mp4", bgm="BGM04_Upon_Reflection.mp3",
               cards=[("B2n_01钩子_动画.mp4", 1.1),  ("B2n_02痛点_动画.mp4", 8.1),
                      ("B2n_03机制_动画.mp4", 23.1), ("B2n_04对比_动画.mp4", 35.5),
                      ("B2n_05方法_动画.mp4", 48.1), ("B2n_06收束_动画.mp4", 58.1),
                      ("闭环_第4讲_动画.mp4", 0)],
               out="第06条_B线第2讲_你总是.mp4"),
    # ★★ 2026-10-08 新四条（A4/A5/B3/B4）—— 卡点按口播逐句对齐，闭环页放片尾
    "A4": dict(src=r"E:/心理咨询IP/素材/A线/A4.mp4", total=110.30, speed=1.00, voice_end=97.0,
               cover="封面A4_动画.mp4", bgm="BGM01_Saying_Goodbye.mp3",
               cards=[("A4n_01钩子_动画.mp4", 1.1), ("A4n_02反常识_动画.mp4", 9.1),
                      ("A4n_03方法_动画.mp4", 34.1), ("A4n_04金句_动画.mp4", 71.6),
                      ("闭环A4_动画.mp4", 0)],
               out="第07条_A线第3讲_越想开越堵_20261008.mp4"),
    "A5": dict(src=r"E:/心理咨询IP/素材/A线/A5.mp4", total=117.60, speed=1.00, voice_end=99.0,
               cover="封面A5_动画.mp4", bgm="BGM02_Galaxys_Endless_Expanse.mp3",
               cards=[("A5n_01钩子_动画.mp4", 1.9), ("A5n_02具象_动画.mp4", 18.4),
                      ("A5n_03核心_动画.mp4", 34.0), ("A5n_04方法_动画.mp4", 59.9),
                      ("闭环A5_动画.mp4", 0)],
               out="第08条_A线第4讲_一点就炸_20261008.mp4"),
    # ★ 正片止于 92.5s（之后是冗余签名段"大家好我是老蔡"，新算法禁止，截掉）
    "B3": dict(src=r"E:/心理咨询IP/素材/B线/B3.mp4", total=106.70, speed=1.00, voice_end=90.5,
               cover="封面B3_动画.mp4", bgm="BGM03_Broken_Inside.mp3",
               cards=[("B3n_01钩子_动画.mp4", 0.9), ("B3n_02痛点_动画.mp4", 16.0),
                      ("B3n_03方法_动画.mp4", 32.2), ("B3n_04关键_动画.mp4", 43.3),
                      ("B3n_05具象_动画.mp4", 60.5), ("闭环B3_动画.mp4", 0)],
               out="第09条_B线第3讲_躲的人说什么_20261008.mp4"),
    # ★ 正片止于 93.0s（之后是冗余签名段，截掉）
    "B4": dict(src=r"E:/心理咨询IP/素材/B线/B4.mp4", total=107.30, speed=1.00, voice_end=92.0,
               cover="封面B4_动画.mp4", bgm="BGM04_Upon_Reflection.mp3",
               cards=[("B4n_01钩子_动画.mp4", 0.7), ("B4n_02反常识_动画.mp4", 18.1),
                      ("B4n_03具象_动画.mp4", 28.8), ("B4n_04方法_动画.mp4", 50.9),
                      ("B4n_05金句_动画.mp4", 71.3), ("闭环B4_动画.mp4", 0)],
               out="第10条_B线第4讲_大脑断线_20261008.mp4"),
}


def _rms_db(path, ss=20.0, dur=6.0):
    """测音频片段的 RMS 响度(dB)，用于 BGM 自动归一化"""
    import subprocess as _sp, wave as _wv, numpy as _np, os as _os, tempfile as _tf
    tmp = _os.path.join(_tf.gettempdir(), "_hermes_rms.wav")
    _sp.run([FF, "-y", "-v", "error", "-ss", str(ss), "-i", path, "-t", str(dur),
             "-ac", "1", "-ar", "16000", tmp], capture_output=True, timeout=60)
    if not _os.path.exists(tmp) or _os.path.getsize(tmp) < 1000:
        return -30.0
    with _wv.open(tmp, "rb") as f:
        d = _np.frombuffer(f.readframes(f.getnframes()), dtype=_np.int16).astype(float)
    r = _np.sqrt((d ** 2).mean()) if len(d) else 0
    return 20 * _np.log10(r / 32768) if r > 0 else -60.0


def _detect_voice_start(src, max_sec=8.0):
    """★ 检测素材里「人声真正开口」的时刻（秒）。
    做法：取前 max_sec 秒音频 → 逐 50ms 算 RMS → 以开头 0.5s 中位数为底噪，
    第一个连续 2 帧超过 底噪*3 且 >300 的位置即开口点。
    """
    import numpy as _np
    r = subprocess.run([FF, "-v", "error", "-t", f"{max_sec}", "-i", src,
                        "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                       capture_output=True, timeout=120)
    if not r.stdout or len(r.stdout) < 16000:
        return 0.0
    a = _np.frombuffer(r.stdout, dtype=_np.int16).astype(_np.float32)
    win = int(0.05 * 16000)
    rms = [float(_np.sqrt((a[i:i + win] ** 2).mean()))
           for i in range(0, len(a) - win, win)]
    if not rms:
        return 0.0
    base = float(_np.median(rms[:10])) if len(rms) >= 10 else float(_np.median(rms))
    thr = max(base * 3.0, 300.0)
    for i in range(len(rms) - 1):
        if rms[i] > thr and rms[i + 1] > thr:
            return round(i * 0.05, 3)
    return 0.0


def build(key):
    cfg = EPISODES[key]
    SRC, TOTAL_RAW, SPEED = cfg["src"], cfg["total"], cfg["speed"]
    # ★ 2026-10-09：成片直接写「按线分文件夹」（A线_情绪自救 / B线_关系修复 / _未分线）
    #   避免「重跑写根目录、分线文件夹留旧版」的对不上（实测踩坑）。
    _out_name = cfg["out"]
    _sub = "A线_情绪自救" if key in ("A2", "A3", "A4", "A5") else \
           ("B线_关系修复" if key in ("B1", "B2", "B3", "B4") else "_未分线")
    _outdir = os.path.join(OUTDIR, _sub)
    os.makedirs(_outdir, exist_ok=True)
    OUT = os.path.join(_outdir, _out_name)
    TOTAL = TOTAL_RAW / SPEED          # 素材变速后时长（真人主轴长度）
    WIN = CARD_ANIM_DUR + CARD_HOLD    # 每张卡的覆盖窗口
    END_WIN = END_ANIM_DUR + END_HOLD

    # ============ 时间轴：真人主轴连续，卡片只是"盖"上去 ============
    # ★ 卡片时刻从 cue/cards_cue.json 读（已按口播逐句对齐 + 不重叠）
    CUE = json.load(io.open(r"E:/心理咨询IP/04-工程/cue/cards_cue.json", encoding="utf-8"))
    overlay_cards, closing = [], None
    for cf, t_raw in cfg["cards"]:
        if "闭环" in cf:
            closing = cf
        else:
            cue = CUE.get(cf.replace("_动画.mp4",""))
            t = cue["at"] if cue else t_raw
            overlay_cards.append((cf, t))
    overlay_cards.sort(key=lambda x: x[1])       # 按时刻排序
    # 卡片盖上时刻须留出完整窗口（不让它越过主轴末尾）
    last_start = TOTAL - WIN - 1.5

    # ★ 真人主轴只播到"人声真正结束"（cfg["voice_end"]），避免片尾空转/冷场
    _ve = cfg.get("voice_end")
    if _ve and _ve < TOTAL:
        print(f"  ★ 人声结束 {_ve:.2f}s < 素材 {TOTAL:.2f}s → 主轴截断，丢弃尾部 {TOTAL-_ve:.2f}s")
        TOTAL_RAW = _ve * SPEED      # 视频/音轨只取到这里
        TOTAL = _ve
        # ★★★★★ 2026-10-09 董事长最终口径：真人从 t=0 起（封面/卡片全部 overlay 压上去，不占时长）
    total_dur = COVER_DUR + TOTAL + (END_WIN if closing else 0)
    main_start, main_end = COVER_DUR, COVER_DUR + TOTAL

    print(f"=== {key} 时间轴（真人主轴连续，卡片覆盖不切碎讲话）===")
    print(f"  封面      0.00 - {COVER_DUR:7.2f} ({COVER_DUR:5.2f}s)   画面=封面，口播继续")
    # ★ 卡片窗口不重叠：后一张开始时刻 = max(脚本卡点, 前一张结束 + 间隔)
    placed, prev_end = [], None
    for cf, t_raw in overlay_cards:
        t = main_start + min(t_raw / SPEED, last_start)   # main_start=COVER_DUR → 成品时刻含封面偏移
        if prev_end is not None and t < prev_end + CARD_GAP:
            t = prev_end + CARD_GAP          # 顺延，保证卡片之间露出真人
        t = min(t, main_end - WIN)           # 不越过主轴末尾
        placed.append((cf, t))
        prev_end = t + WIN
    for cf, t in placed:
        print(f"  卡(盖)  {t:7.2f} - {t + WIN:7.2f} ({WIN:5.2f}s)  {os.path.basename(cf)}")
    print(f"  真人主轴  {main_start:7.2f} - {main_end:7.2f} ({TOTAL:5.2f}s)  ← 全程连续，声音不断")
    if closing:
        print(f"  闭环    {main_end:7.2f} - {total_dur:7.2f} ({END_WIN:5.2f}s)")
    cover_s = sum(min(WIN, max(0, (placed[i+1][1] if i+1 < len(placed) else main_end) - t))
                  for i, (cf, t) in enumerate(placed))
    print(f"总时长 {total_dur:.2f}s  真人画面 {main_end - main_start - cover_s:.1f}s"
          f"({(main_end - main_start - cover_s)/total_dur*100:.0f}%)  "
          f"卡片 {len(cfg['cards'])} 张（按脚本）")

    # ============ 输入 ============
    inputs = ["-i", SRC]
    ci = {}
    for cf, _ in cfg["cards"]:
        if cf not in ci:
            ci[cf] = len(inputs) // 2
            inputs += ["-i", os.path.join(ANIM, cf)]
    cover_i = len(inputs) // 2
    inputs += ["-i", os.path.join(ANIM, cfg["cover"])]
    inputs += ["-i", LOGO, "-i", NOTICE]
    LI = len(inputs) // 2 - 2; NI = LI + 1
    bgm_path = os.path.join(MUSDIR, cfg["bgm"])
    has_bgm = os.path.exists(bgm_path)
    if has_bgm:
        BI = len(inputs) // 2
        inputs += ["-stream_loop", "-1", "-i", bgm_path]
    print(f"BGM: {cfg['bgm']} {'✅' if has_bgm else '❌ 缺文件'}  {BGM_DB}dB")

    parts = []

    # ---- ① 真人主轴（整条连续，段内叠 LOGO）----
    parts.append(f"[0:v]trim=start=0:end={TOTAL_RAW},setpts=(PTS-STARTPTS)/{SPEED},"
                 f"fps=30,scale=1080:1920:force_original_aspect_ratio=increase,"
                 f"crop=1080:1920,setsar=1[hv];[hv][{LI}:v]overlay=44:70[base]")

    # ---- ② 卡片盖到真人上（enable 限窗口；卡片本身不叠 LOGO）----
    cur = "base"
    for n, (cf, t) in enumerate(placed):          # ★ 用排布后的时刻，与时间轴打印一致
        i = ci[cf]
        # ★★★ 2026-10-08 夜 铁证修复：卡片定位只靠"PTS 绝对偏移"，绝不用 enable
        #   原因（实测复现）：`overlay=...:enable='between(t,a,b)'` 串行叠加时，
        #     第 2 张卡之后的所有卡全部失效（实测 4 张卡只出第 1 张）。
        #     逐帧像素扫描证明成片里只有 t=5-7s 的钩子卡，其余三张完全没渲染。
        #   改为：卡片流 setpts 把首帧时间戳直接推到绝对时刻 t（+N/(30*TB) 保持帧数），
        #     再 overlay（无 enable）—— 卡片按自身时间戳落到正确位置，实测 2.6s/74.6s 全对。
        #   注意：偏移用「帧号/30」而非 PTS-STARTPTS+大偏移，避免时基溢出。
        # ★★★ 2026-10-08 夜 铁证修复（方案D/F）：卡片 = "tpad 前置黑帧 + enable 窗口"
        #   三个错误方案（已实测排除）：
        #     ① enable + eof_action=pass → 第2张卡之后全部失效（只出第1张）
        #     ② concat 输出 setpts=PTS-STARTPTS+t/TB → 卡内 1.5-3s 出现全黑帧（dark=0）
        #     ③ 流内 setpts 加偏移再 concat → 时基错乱、后续全黑
        #   正解：卡片流先 concat（无偏移）→ tpad 前置 t 秒黑帧 → overlay
        #         用 enable 限窗口（不用 eof_action、不用 shortest）
        def _card(idx, tag, t):
            return (f"[{idx}:v]trim=start=0:end={CARD_ANIM_DUR},setpts=N/(30*TB),fps=30,"
                    f"scale=1080:1920,setsar=1[{tag}i];"
                    f"[{idx}:v]trim=start={CARD_ANIM_DUR-0.05:.2f}:end={CARD_ANIM_DUR},"
                    f"setpts=N/(30*TB),fps=30,scale=1080:1920,setsar=1,"
                    f"tpad=stop_mode=clone:stop_duration={CARD_HOLD:.2f}[{tag}t];"
                    f"[{tag}i][{tag}t]concat=n=2:v=1:a=0,setpts=PTS-STARTPTS[{tag}c];"
                    f"[{tag}c]tpad=start_duration={t:.3f}:start_mode=add:color=black[{tag}]")
        # ★★★ 2026-10-09 铁证修复（卡片晚 1.5s 出现 = 封面偏移没扣）：
        #   卡片叠在 [cur]（起点=真人 base，t=0 在「封面之前」），
        #   而 t 是「含封面偏移」的成品时间轴时刻（t = COVER_DUR + …）。
        #   第③步封面 concat 会把整条链再后移 COVER_DUR → 卡片最终落在 t+COVER_DUR（晚 1.5s）。
        #   实测铁证：A5 卡3 窗口写 44.20，橙块跳变实际发生在 45.80（= 44.20+1.5）。
        #   修法：叠到 base 上的偏移用「base 坐标系」= t - COVER_DUR（封面 concat 时自动补回）。
        # ★ 卡片叠在 base（真人）上，而 base 会被第③步 concat 整体后移 COVER_DUR
        #   → 卡片偏移用 base 坐标系 = t - COVER_DUR（实测铁证：不扣会整体晚 COVER_DUR 秒）
        t_base = max(0.0, t - COVER_DUR)
        parts.append(_card(i, f"k{n}", t_base))
        parts.append(f"[{cur}][k{n}]overlay=0:0:enable='between(t,{t_base:.3f},{t_base+WIN:.3f})'[o{n}]")
        cur = f"o{n}"

    # ---- ③ ★ 封面：concat 在真人**前面**（2026-10-09 董事长定案）----
    #   封面段(0→COVER_DUR)：画面=封面、声音=只有BGM；封面撤掉后真人视频才从素材 0s 开始，
    #   人声也同时从素材 0s 起 → 音画天然同步，卡片也不会被封面吃掉。
    #   封面素材短于 COVER_DUR 时用末帧 clone 补足。
    parts.append(f"[{cover_i}:v]fps=30,scale=1080:1920,setsar=1,"
                 f"tpad=stop_mode=clone:stop_duration={COVER_DUR:.2f},"
                 f"trim=start=0:end={COVER_DUR},setpts=PTS-STARTPTS[coverv];"
                 f"[coverv][{cur}]concat=n=2:v=1:a=0[vcover]")

    # ---- ④ 闭环页追加在最末（★ 用 overlay+延长，不用 concat，避免时长不匹配静默丢段）----
    if closing:
        k = ci[closing]
        # a) 闭环动画 0→END_ANIM_DUR，PTS 平移到主轴末尾之后
        parts.append(f"[{k}:v]trim=start=0:end={END_ANIM_DUR},setpts=PTS-STARTPTS+{main_end:.3f}/TB,"
                     f"fps=30,scale=1080:1920,setsar=1[enda];"
                     # b) 末帧克隆补足 END_HOLD
                     f"[{k}:v]trim=start={END_ANIM_DUR-0.05:.2f}:end={END_ANIM_DUR},"
                     f"setpts=PTS-STARTPTS+{main_end+END_ANIM_DUR-0.05:.3f}/TB,"
                     f"fps=30,scale=1080:1920,setsar=1,"
                     f"tpad=stop_mode=clone:stop_duration={END_HOLD:.2f}[endb];"
                     f"[enda][endb]concat=n=2:v=1:a=0[endv];"
                     # c) 主轴先 tpad 补足 13s 黑底，再 overlay 闭环（闭环本身是全屏不透明）
                     f"[vcover]tpad=stop_mode=add:color=black:stop_duration={END_WIN:.2f}[vcpad];"
                     f"[vcpad][endv]overlay=0:0:eof_action=repeat[vpo];"
                     f"[vpo]trim=start=0:end={total_dur:.3f},setpts=PTS-STARTPTS[vc]")
    else:
        parts.append("[vcover]null[vc]")

    # ---- ⑤ AI 声明（全程）----
    parts.append(f"[vc][{NI}:v]overlay=672:1818[vout]")

    # ============ 音轨（★ PTS 归零 + 人声不被 amix 衰减）============
    # 人声提到 -20dB（清晰主体），BGM -23dB（衬底），amix=normalize=0 不做 1/N 衰减
    # ★★★★★ 2026-10-09 董事长第3次反馈后——最终正解（音画同源整体平移）：
    #   董事长原话：「素材里口型和声音本来是齐的，卡片只是穿插进去，切回真人时应该还是齐的」
    #   → 完全正确。素材的【画面】与【声音】是一体锁死的，**只能整体平移、绝不能单独推声音**。
    #   之前全错在：单独给音频加 adelay(COVER_DUR - voice_start) → 音频被额外推后，
    #     而视频仍从素材 0s 播 → 真人画面与声音差 voice_start 秒，永远对不上。
    #   正解：**音画使用同一个偏移（都等于封面时长 COVER_DUR）**——
    #     封面期间画面是封面、声音照常（董事长接受"声音和封面一起出来"）；
    #     切到真人时，画面与声音同处素材同一时刻 → 口型天然对齐。
    # ★★★★★ 2026-10-09 董事长第4次定（最终口径）：
    #   「全部按我的真人演讲视频开始，卡片压上去就可以，不要等封面动画结束再起声音，直接就起」
    #   → 真人主轴从 t=0 开始（画面+声音同时），封面/卡片/闭环全部 overlay 压在上面。
    #   → **音频延迟 = 0**，音画天然同步，永不出现"对不上"。
    # ★★★★★ 2026-10-09 董事长最终定案（第5次，最干净）：
    #   「封面出现和停留的时候只有 BGM，等封面差不多要撤掉，这时候我的视频再开始」
    #   → 封面段(0→COVER_DUR)：画面=封面、声音=只有 BGM（人声不响）
    #   → 封面撤掉后真人视频才从素材 0s 开始（画面+声音同时起 → 音画天然同步）
    #   → 卡片按口播时刻压上，不会被封面吃掉。
    _delay_ms = int(round(COVER_DUR * 1000))   # 人声延迟到封面结束
    print(f"  ★ 音画：封面段只有BGM；人声延迟到 {COVER_DUR:.1f}s 起（与真人画面同起）")
    # ★★★ 坑：adelay 之后**不能**再接 asetpts=PTS-STARTPTS —— 它会把 PTS 归零、抹掉延迟！
    #   实测：adelay=1550 后接 asetpts 归零 → 人声仍在素材原位 1.5s（delay 完全没生效）。
    #   正解：asetpts 归零 + atrim 都做完，**adelay 放最后**。
    # ★★★ 2026-10-09 最终正解（实测确认）：
    #   voice 上 **不能有 apad**（apad 让 voice 变无限长，amix 便按"都从0开始"对齐，延迟被吃）；
    #   adelay 必须加在 voice 上（amix 之前），且用 :all=1。
    #   实测：voice 内 adelay=1550（无apad）→ 人声 3.3s 起（期望3.0）✅；
    #         改用 amix 后 adelay / 或 voice 带 apad → 仍是 1.7s ❌。
    # ★★★★ 2026-10-09 终极正解（实测，前 5 次全错在这个顺序）：
    #   `atempo` 会重建音频时间轴，**吃掉它前面的 `adelay` 静音**。
    #   实测同一输入：
    #     atempo 在 adelay 前 → 人声 1.7s ❌ ；adelay 在 atempo 后 → 3.3s ✅
    #   SPEED=1.0 时 atempo 纯属有害 → 直接省略；需要变速时才在 adelay 之后加。
    #   另：全程禁用 apad（apad 会让 amix 吃掉延迟）。
    _at_tail = f",atempo={SPEED}" if abs(SPEED - 1.0) > 1e-6 else ""
    parts.append(f"[0:a]atrim=start=0:end={TOTAL_RAW},asetpts=PTS-STARTPTS,"
                 f"volume={VOICE_DB}dB,aresample=48000,"
                 f"adelay={_delay_ms}:all=1{_at_tail}[voice]")
    if has_bgm:
        # ★ BGM 响度自动归一化（2026-10-09 修正）：
        #   旧做法用「假设人声 = VOICE_TARGET_DB(-18dB)」→ 但董事长素材录得比这响（实测成品全片 -15~-16dB），
        #   BGM 被多压了 3dB，手机外放听不见。
        #   正解：**实测素材提升后的真实人声响度**，BGM 再严格比它低 BGM_BELOW_VOICE dB。
        _vd = _rms_db(SRC, 5.0) + VOICE_DB          # 人声提升后的实际响度（dB）
        bdb = _rms_db(bgm_path, 20.0)
        bgm_gain = (_vd - BGM_BELOW_VOICE) - bdb    # BGM = 人声实测 -10dB
        print(f"    ★ 实测人声 {_vd:.1f}dB（素材{_vd-VOICE_DB:.1f}+{VOICE_DB}dB）"
              f" | BGM原 {bdb:.1f}dB → 增益 {bgm_gain:+.1f}dB（严格低 {BGM_BELOW_VOICE:.0f}dB）")
        parts.append(f"[{BI}:a]atrim=start=20:end={20+total_dur:.3f},asetpts=PTS-STARTPTS,"
                     f"volume={bgm_gain:.1f}dB,aresample=48000[bgm];"
                     f"[voice][bgm]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
                     f"atrim=start=0:end={total_dur:.3f},asetpts=PTS-STARTPTS,"
                     f"alimiter=limit=0.95[aout]")
    else:
        parts.append(f"[voice]atrim=start=0:end={total_dur:.3f},alimiter=limit=0.95[aout]")

    cmd = [FF, "-y"] + inputs + ["-filter_complex", ";".join(parts),
        "-map", "[vout]", "-map", "[aout]", "-t", f"{total_dur:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-maxrate", "14M", "-bufsize", "28M",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT]

    if os.environ.get("DUMP_FILTER"):
        io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             f"_filter_{key}.txt"), "w", encoding="utf-8").write(
            "\n".join(parts))
        print(f"  [dump] filter 已写 _filter_{key}.txt")

    print(f"\n=== 合成 {key} ===")
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        print("exit:", r.returncode); print(r.stderr[-3000:]); return False
    print("OK ->", OUT, os.path.getsize(OUT) // 1024 // 1024, "MB")

    # 清理同讲旧版（★ 只清当前输出目录，避免误删别线/别版）
    for f in glob.glob(os.path.join(_outdir, "*.mp4")):
        b = os.path.basename(f)
        if b == cfg["out"]: continue
        if b[:4] == cfg["out"][:4] and b[:4].startswith("第"):
            try: os.remove(f); print("  🗑 已清理旧版:", b)
            except Exception: pass
    return True


if __name__ == "__main__":
    keys = sys.argv[1:] if len(sys.argv) > 1 else list(EPISODES)
    for k in keys:
        build(k)
