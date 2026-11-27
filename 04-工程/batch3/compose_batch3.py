# -*- coding: utf-8 -*-
"""batch3 合成器 —— 2026-11-02 新建（4 条新素材）

沿用 batch2 已验证的架构：
  · 真人主轴连续，卡片 overlay 盖上去（全屏原样，不裁剪）
  · 字幕烧在真人上：新式字幕（单行固定、下方升起放大、立体金字）
  · LOGO 左上、AI 声明右下
  · 影视级调色：轻降噪 → 曲线压高光 → 对比/饱和 → 锐化 → 轻暗角

用法: python compose_batch3.py <n> [<n> ...]
"""
import os
import io, sys, json, io, subprocess, time

R3 = os.path.dirname(os.path.abspath(__file__))
ROOT = "E:/心理咨询IP"
BATCH = "batch3"
R2 = ROOT + "/04-工程/batch2"
sys.path.insert(0, R3)
sys.path.insert(0, R2)

import subs_ref as SR          # 新字幕
import cards_ep as CE          # batch3 卡片锚点

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
FFP = FF.replace("ffmpeg.exe", "ffprobe.exe")
ANIM = R3 + "/cards_mp4"
SUBD = R3 + "/subs_ref"
LOGO = ROOT + "/04-工程/overlay_new/logo_corner.png"
NOTICE = ROOT + "/04-工程/overlay_new/ai_notice.png"

CARD_ANIM = 4.0
CARD_GAP = 1.0
MIN_HOLD = 2.0        # ★ 董事长2026-11-04定：每张卡含动画共6-8s → 停留2.0s起
MAX_HOLD = 4.0        # ★ 含动画4s即上限8s
READ_CPS = 6.5        # ★ 阅读速度，长卡自动取上限4.0
OPEN_MIN = 3.0
END_KEEP = 8.0
VOICE_DB = 5.0
BGM_BELOW = 9.0     # ★ 2026-11-04 董事长：BGM 声音太小，抬一点点（原 15.0）
KEEP_LEN = 177.0
TEST_SEC = float(os.environ.get("TEST_SEC", "0"))   # >0 时只跑前 N 秒做链路验证
SW, SH = 1080, 1920   # ★ 2026-11-04：必须与 ASS(1080×1920) 一致，否则字幕/卡片被拉伸挤右


HARD_RULES = dict(
    NO_TRIM=True,          # 严禁剪任何内容，必须完整
    NO_SPEEDUP=True,       # 严禁把语速调快到超过设定档
    MAX_SECONDS=None,      # 时长不再硬性 180s（提速会牺牲语速，故放开）
    SUB_SAFE_TOP=1300,     # 字幕最高行字顶不得高于此值，否则被裁
    SUB_MAX_ROWS=3,        # 同屏最多 3 行
)

def _guard(n, total, subs_p):
    """合成前自检，任一不过直接中止"""
    import re as _re
    # 1) 未剪内容
    if getattr(CE, "TRIM_CUTS", {}).get(n):
        raise SystemExit("❌ 第%d条 TRIM_CUTS 非空，违反‘内容必须完整’" % n)
    tr = getattr(CE, "TRIM", {}).get(n, {})
    if float(tr.get("head", 0)) > 0.01 or float(tr.get("tail", 999)) < 999:
        raise SystemExit("❌ 第%d条 TRIM 掐头去尾，违反‘内容必须完整’" % n)
    # 2) 字幕不裁切
    import io as _io
    ys = []
    for l in _io.open(subs_p, encoding="utf-8"):
        if not l.startswith("Dialogue:"):
            continue
        m = _re.search(r"\\pos\(\d+,(\d+)\)", l) or _re.search(r"\\move\(\d+,(\d+),\d+,(\d+)", l)
        if m:
            ys += [int(g) for g in m.groups() if g]
    if ys and min(ys) - 68 < HARD_RULES["SUB_SAFE_TOP"]:
        raise SystemExit("❌ 第%d条 字幕顶行会被裁切（字顶=%d）" % (n, min(ys) - 68))
    print("   ✅ 闸门: 未剪内容 / 字幕不裁切 / 顶行y=%d" % min(ys))


def dur(p):
    r = subprocess.run([FFP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", p], capture_output=True, text=True)
    return float(r.stdout.strip())


def plan(n):
    cfg = CE.EPS[n]
    src = os.path.join(ROOT, "素材", "%d.mp4" % n)
    raw = dur(src)
    sp = cfg["speed"]
    # 片尾预告剪掉
    # ★ 转录源自动定位：先找本批次目录，找不到再回退 batch2
    #   卡片锚点 ANCH 的时间轴必须与所用转录同源，否则卡片会串组
    _cands = [ROOT + "/03-内容/转录/%s/raw_%d.json" % (BATCH, n),
              ROOT + "/03-内容/转录/batch3/raw_%d.json" % n,
              ROOT + "/03-内容/转录/batch2/raw_%d.json" % n]
    _tp = next(p for p in _cands if os.path.exists(p))
    d = json.load(io.open(_tp, encoding="utf-8"))
    print("   转录源:", os.path.basename(os.path.dirname(_tp)))
    cues = d["segs"] if isinstance(d, dict) else d
    speech_end = cues[-1]["end"]
    for c in cues:
        if "下一讲" in c["text"] or "下集" in c["text"] or "下一期" in c["text"]:
            speech_end = c["start"]
            break
    # ★ 掐头去尾（董事长要求：3分钟内 + 语速自然 → 必须删掉无用内容）
    tr = getattr(CE, "TRIM", {}).get(n, dict(head=0.0, tail=999))
    head = float(tr["head"])
    tail = min(float(tr["tail"]), raw)
    if tail >= raw:
        keep_end = min(raw, speech_end + 0.6)
    else:
        keep_end = tail
    keep_len = keep_end - head          # 实际使用的素材长度
    # ★ 气口剪除（只删不说话的空隙，语音一个字不减）
    gaps = None
    _gp = os.path.join(R3, "gaps_%d.json" % n)
    if os.path.exists(_gp):
        gaps = json.load(io.open(_gp, encoding="utf-8"))
        keep_len = gaps["new_len"]
        print("   气口剪除: 原%.1fs → %.1fs（删%.1fs空隙）"
              % (gaps["dur"], gaps["new_len"], gaps["dur"] - gaps["new_len"]))
    # 扣掉冗余段
    _cuts = getattr(CE, "TRIM_CUTS", {}).get(n, [])
    _cutlen = sum(min(b, keep_end) - max(a, head) for a, b in _cuts if b > head and a < keep_end)
    keep_len -= max(0, _cutlen)
    total = round(keep_len / sp, 2)

    # 卡片排期
    cards, rows = [], []
    # 候选卡按时间排序，先过滤掉超出片长的
    def _rm(t):
        if not gaps:
            return t
        sh = 0.0
        for a, b in gaps["cuts"]:
            if t <= a:
                break
            if t >= b:
                sh += b - a
            else:
                return a - sh
        return t - sh

    cand = sorted([(k, (_rm(t) - head) / sp) for k, _kw, t in CE.ANCH[n]
                   if _rm(t) >= head], key=lambda x: x[1])
    cand = [c for c in cand if c[1] < total - END_KEEP - CARD_ANIM]
    # ★★ 卡片排布铁律 v3（2026-11-04 董事长：卡片全堆在前边看不到真人）：
    #   ① 张数由「内容有几个可讲的节点」决定，不硬套 8/9/10
    #   ② 卡片必须铺满全片：任何 1/4 片长区间内，卡片占比不超过 40%
    #   ③ 卡与卡之间至少留 CARD_GAP_BIG 秒真人画面，不许连片
    CARD_GAP_BIG = 5.0        # 卡间至少 5 秒真人
    MAXCARD_RATIO = 0.40      # 任何 1/4 片段里卡片最多占 40%
    WORK_MIN = 4.5            # 工作区（去掉片头 END_KEEP 与片尾）卡片最多占 45%

    cand = [c for c in cand if c[1] < total - END_KEEP - CARD_ANIM]
    # —— ① 张数：内容节点数 = 候选卡数，上限仍按片长，但不低于内容需要
    if total >= 155:      MAXCARDS = 10
    elif total >= 135:    MAXCARDS = 9
    else:                 MAXCARDS = 8
    # 若内容节点本来就少（<MAXCARDS），就按实际节点数，不凑数
    NCARD = min(MAXCARDS, len(cand))
    if NCARD < 4:                 # 内容太少就少放，绝不硬加
        NCARD = max(1, NCARD)

    work_a = OPEN_MIN
    work_b = total - END_KEEP - CARD_ANIM
    # ★★ ② 卡片分散铁律（2026-11-04 董事长：卡片全堆在前边看不到真人）
    #   锚点是"这句话说到哪秒"，卡片就在那个点出。
    #   但若连续多张卡挤在一起（30秒内 3 张以上），就把后面那张
    #   往后推到"最近的一张空位"，保证任意 30 秒内最多 2 张卡。
    tmp = []
    for k, t in cand:
        t = max(t, work_a)
        if tmp:
            # 同一 30 秒窗口里已经有 2 张 → 这张往后推
            recent = [x for x in tmp if t - x[1] < 40.0]
            if len(recent) >= 2:
                t = recent[-1][1] + 20.0     # 40秒窗口内最多2张
        if tmp and t <= tmp[-1][1] + 1.0:
            t = tmp[-1][1] + 1.0
        if t < work_b:
            tmp.append((k, t))
    # 末卡若太早，把行动卡挪到片尾留白前（内容仍对得上：行动卡本就是收尾）
    if tmp and tmp[-1][1] < total * 0.72:
        end_t = total - END_KEEP - CARD_ANIM - 1.0
        if len(tmp) == 1 or end_t - tmp[-2][1] >= 8.0:
            tmp[-1] = (tmp[-1][0], end_t)
    picked = tmp
    cand = tmp
    anch = cand

    prev_end = None
    for i, (key, t) in enumerate(anch):
        # 按卡片字数算阅读时长（5字/秒），限制在 2.6~5.5s
        txts = CE.texts_of(n, key)
        cn = sum(len(x) for x in txts)
        hold = min(MAX_HOLD, max(MIN_HOLD, cn / READ_CPS))
        win = CARD_ANIM + hold
        if i == 0 and t < OPEN_MIN:
            t = OPEN_MIN
        if prev_end is not None and t < prev_end + CARD_GAP:
            t = prev_end + CARD_GAP
        tail = END_KEEP if i == len(anch) - 1 else 0.3
        if t + win + tail > total:
            win = max(CARD_ANIM + MIN_HOLD, total - tail - t)
            hold = max(MIN_HOLD, win - CARD_ANIM)
        if t + win > total:
            continue
        cards.append((key, t, win, hold))
        rows.append(dict(card=key, hold=round(hold, 1), win=round(win, 1),
                         t=round(t, 2), end=round(t + win, 2)))
        prev_end = t + win
    # 全局封顶：卡片总时长 ≤ 片长 32%（真人必须占主体）
    # ★ 卡片总量上限：按片长动态定，保证 8-10 张都能停够 8 秒
    #    短于 150s 的片子卡片占比可到 62%（卡片多才不干），长片 50%
    cap = total * 0.56   # ★ 真人必须 ≥44%；超限自动收短卡片
    guard = 0
    while sum(w for _k, _t, w, _h in cards) > cap and guard < 200:
        guard += 1
        idx = max(range(len(cards)), key=lambda i: cards[i][2])
        k, t, w, hh = cards[idx]
        if hh <= 8.0:
            break
        cards[idx] = (k, t, CARD_ANIM + hh - 0.2, hh - 0.2)
        rows[idx]["win"] = round(CARD_ANIM + hh - 0.2, 1)
        rows[idx]["hold"] = round(hh - 0.2, 1)

    return dict(src=src, raw=raw, keep=keep_end, keep_len=keep_len, head=head,
                total=total, sp=sp, cfg=cfg,
                cards=cards, rows=rows, speech_end=speech_end, gaps=gaps)


# ============================================================
# 董事长硬约束（2026-11-03 定，禁改）——每次合成都必须过这些闸门
# ============================================================
HARD_RULES = dict(
    NO_TRIM=True,          # 严禁剪掉任何语音内容
    NO_SPEEDUP=True,       # 严禁把语速调快到超过设定档
    SUB_SAFE_TOP=1300,     # 字幕最高行字顶不得高于此值
    SUB_MAX_ROWS=3,        # 同屏最多 3 行
    GAP_TRIM_N=None,       # 允许的条目：只删空隙，不删语音
)


def _guard(n, total, subs_p):
    """合成前自检，任一不过直接中止"""
    import re as _re
    import io as _io
    # 1) 未剪语音内容（TRIM_CUTS 是删整段内容，永不允许）
    if getattr(CE, "TRIM_CUTS", {}).get(n):
        raise SystemExit("❌ 第%d条 TRIM_CUTS 非空，违反‘内容必须完整’" % n)
    # 2) 字幕不裁切
    ys = []
    for l in _io.open(subs_p, encoding="utf-8"):
        if not l.startswith("Dialogue:"):
            continue
        m = (_re.search(r"\\pos\(\d+,(\d+)\)", l)
             or _re.search(r"\\move\(\d+,(\d+),\d+,(\d+)", l))
        if m:
            ys += [int(g) for g in m.groups() if g]
    if ys and min(ys) - 68 < HARD_RULES["SUB_SAFE_TOP"]:
        raise SystemExit("❌ 第%d条 字幕顶行会被裁切（字顶=%d）"
                         % (n, min(ys) - 68))
    # 3) ★ 字幕不许压字：同屏行数 + 行间距双校验
    rows = []
    for l in _io.open(subs_p, encoding="utf-8"):
        if not l.startswith("Dialogue:"):
            continue
        q = l.split(",", 9)

        def _s2(t):
            h, m_, s_ = t.split(":")
            return int(h) * 3600 + int(m_) * 60 + float(s_)

        a, b = _s2(q[1]), _s2(q[2])
        m2 = (_re.search(r"\\pos\(\d+,(\d+)\)", q[9])
              or _re.search(r"\\move\(\d+,(\d+),\d+,(\d+)", q[9]))
        y0 = int(m2.group(1)) if m2 else -1
        y1 = int(m2.group(2)) if (m2 and m2.lastindex and m2.lastindex >= 2) else y0
        rows.append((a, b, y0, y1))
    if rows:
        # 同一时刻最多 3 条同时在屏
        ts = sorted(set(round(r[0], 2) for r in rows))
        mx = 0
        for t in ts:
            n_live = len([r for r in rows if r[0] <= t < r[1] and r[2] > 0])
            mx = max(mx, n_live)
        if mx > HARD_RULES["SUB_MAX_ROWS"]:
            raise SystemExit("❌ 第%d条 同屏 %d 行，超过 %d 行（会压字）"
                             % (n, mx, HARD_RULES["SUB_MAX_ROWS"]))
        # 同屏两条的行间距必须 > 字高 68，否则视觉上贴在一起
        worst = 999
        for t in ts:
            live = [r for r in rows if r[0] <= t < r[1] and r[2] > 0]
            ys_t = sorted(r[2] for r in live)
            for i_ in range(len(ys_t) - 1):
                worst = min(worst, ys_t[i_ + 1] - ys_t[i_])
        if worst != 999 and worst < 68:
            raise SystemExit("❌ 第%d条 字幕行间距仅 %dpx（<68px 即压字）"
                             % (n, worst))
        print("   ✅ 闸门: 未剪语音 / 不裁切 / 同屏≤%d行 / 最小行距%dpx"
              % (mx, worst if worst != 999 else 0))


def build(n):
    P = plan(n)
    cfg, total, rows, sp = P["cfg"], P["total"], P["rows"], P["sp"]
    print("=" * 90)
    print("【第%d条】%s" % (n, cfg["title"]))
    print("  素材 %.1fs ÷%.3f → 成片 %.1fs (%.1f:%04.1f)" % (P["raw"], sp, total, total//60, total%60))
    for r in rows:
        print("   卡 %-22s t=%6.1f  时长%.1f" % (r["card"], r["t"], r["win"]))
    _gaps = P.get("gaps") if "P" in dir() else None

    os.makedirs(os.path.join(ANIM, str(n)), exist_ok=True)
    # ① 卡片资源检查
    miss = [k for k, *_ in P["cards"]
            if not os.path.exists(os.path.join(ANIM, str(n), k + ".mp4"))]
    if miss:
        raise SystemExit("❌ 缺卡片: %s" % miss)

    # ② 字幕
    sub, nsub, srcx = SR.build(n, speech_end=P["speech_end"], speed=sp, gaps=P.get("gaps"))
    print("  字幕 %d 条 → %s" % (nsub, sub))
    _guard(n, P.get("total", 0), sub)   # ★ 硬约束闸门：未剪内容 + 字幕不裁切

    # ③ 滤镜图
    f = []
    # ★ 气口剪除：把保留区间拼成一条连续流（只删空隙，语音完整）
    if _gaps:
        _kp = [iv for iv in _gaps["keep"]]
        _p = []
        # 同一输入流不能被子 filter 重复消费，先 split 成 N 份
        _n = len(_kp)
        _p.append("[0:v]split=%d%s;" % (_n, "".join("[sv%d]" % i for i in range(_n))))
        _p.append("[0:a]asplit=%d%s;" % (_n, "".join("[sa%d]" % i for i in range(_n))))
        for _i, (_a, _b) in enumerate(_kp):
            _p.append("[sv%d]trim=%.3f:%.3f,setpts=PTS-STARTPTS[gv%d];"
                      % (_i, _a, _b, _i))
            _p.append("[sa%d]atrim=%.3f:%.3f,asetpts=PTS-STARTPTS[ga%d];"
                      % (_i, _a, _b, _i))
        for _i in range(len(_kp)):
            _p.append("[gv%d][ga%d]" % (_i, _i))
        _p.append("concat=n=%d:v=1:a=1[gvc][gac]" % len(_kp))
        f.append("".join(_p).rstrip(";"))
        SRCV, SRCA = "[gvc]", "[gac]"
    else:
        SRCV, SRCA = "[0:v]", "[0:a]"
    # 电影级调色链 K1（batch2 实测定档：均值136/标准差52/人脸182）
    # ★ 先删冗余区间（与字幕同步），再重排时间轴
    _cuts = getattr(CE, "TRIM_CUTS", {}).get(n, [])
    if _cuts:
        _keep = "+".join(["between(t,%.3f,%.3f)" % (a, b) for a, b in _cuts])
        _sel = "[0:v]select='not(%s)',setpts=N/FRAME_RATE/TB[dv]" % _keep
        _asel = "[0:a]aselect='not(%s)',asetpts=N/SR/TB[da]" % _keep
    else:
        _sel = SRCV + "null[dv]"
        _asel = SRCA + "anull[da]"
    f.append(_sel)
    # ★ 专业调色链 v2（2026-11-04 董事长要求"更专业更好看"）
    #    实测：人脸205 / 背景113 / 分隔92 / 均值147 / 标准差63 / 过曝1.6%
    #    关键：高光滚降防白墙过曝、青影橙高光双色分离、轻降噪保清晰、细颗粒不糊
    # ★ 原生裁切：素材 1920x1080 横屏 → 取 1080x1440 竖屏区（不放大、不损失像素）
    #    原来裁 810x1440 再拉大到 1080 = 放大 1.33 倍，画面必糊
    # ★★ 真人画面（2026-11-04 董事长定稿）：原样使用，不做任何调整。
    #    素材 5-11 带 rotation=90 元数据，ffmpeg 会自动转成 1080×1920 竖屏。
    #    绝不许再 crop/调色/加颗粒——之前 crop=1080:1440 是按未旋转的
    #    1920×1080 去裁，裁出来的根本不是人，所以"都只看到头了"。
    f.append("[dv]setpts=PTS/%.4f,scale=%d:%d:flags=lanczos,setsar=1,fps=30[graded]"
             % (sp, SW, SH))
    # 字幕（在缩放后的画面上烧，ASS 以 1080x1920 为坐标系，需先缩放回去）
    # ASS 烧录：把字幕文件放相对路径（cd 到字幕目录跑），彻底避开 Windows 盘符转义
    import shutil as _sh
    _cwd_sub = os.path.dirname(sub)
    _ass_name = os.path.basename(sub)
    f.append("[graded]ass=%s,scale=%d:%d,setsar=1[withsub]"
             % (_ass_name, SW, SH))

    # 卡片：全屏原样叠加
    cur = "withsub"
    for ci, (key, ct, cwin, chold) in enumerate(P["cards"]):
        _anim = 4.0                       # 卡片动画时长（渲染时 120 帧 @30fps）
        _hold = max(0.5, cwin - _anim)
        # ★ 卡片流：先归零（绝不用 PTS+大偏移，会溢出吞掉后面整条链）
        f.append("[%d:v]trim=start=0:end=%.3f,setpts=N/(30*TB),fps=30,"
                 "scale=1080:1920:force_original_aspect_ratio=disable,setsar=1[ca%d]"
                 % (ci + 1, _anim, ci))
        # 末帧克隆补停留
        f.append("[%d:v]trim=start=%.3f:end=%.3f,setpts=N/(30*TB),fps=30,"
                 "scale=1080:1920:force_original_aspect_ratio=disable,setsar=1,"
                 "tpad=stop_mode=clone:stop_duration=%.2f[cb%d]"
                 % (ci + 1, max(0.0, _anim - 0.05), _anim, _hold, ci))
        f.append("[ca%d][cb%d]concat=n=2:v=1:a=0,setpts=PTS-STARTPTS[cc%d]" % (ci, ci, ci))
        # 用 tpad 前置黑帧，把卡片推到正确时刻（不用 PTS 偏移）
        f.append("[cc%d]tpad=start_duration=%.3f:start_mode=add:color=black[c%d]" % (ci, ct, ci))
        f.append("[%s][c%d]overlay=0:0:enable='between(t,%.3f,%.3f)'[o%d]"
                 % (cur, ci, ct, ct + cwin, ci))
        cur = "o%d" % ci

    # LOGO + AI 声明
    #   ① 视频讲解 LOGO 缩小到 130px（董事长：现在太大）
    #   ② 卡片段不显示讲解 LOGO（卡片上已有 LOGO，避免两个重影）
    #   ③ 底部合规字/AI声明靠右，不居中
    li = len(P["cards"]) + 1
    f.append("[%d:v]scale=130:-1[logo]" % li)
    # 卡片出现的时间窗（取并集）
    if P["cards"]:
        card_win = "+".join(["between(t,%.3f,%.3f)" % (ct, ct + cwin) for _k, ct, cwin, _h in P["cards"]])
        logo_enable = ":enable='not(%s)'" % card_win
    else:
        logo_enable = ""
    f.append("[%s][logo]overlay=24:24%s[wi]" % (cur, logo_enable))
    f.append("[%d:v]null[note]" % (li + 1))
    # 靠右：右边距 40px
    f.append("[wi][note]overlay=W-w-40:H-h-30[pre]")
    # 最终统一到交付规格 1080x1920 + TV range
    f.append("[pre]scale=1080:1920:flags=lanczos,setsar=1,"
             "scale=in_range=full:out_range=tv,format=yuv420p,"
             "setparams=range=tv:colorspace=bt709[vout]")

    # 音频
    # BGM 是最后一个 -i 输入，序号 = 1 + 卡片数 + 2(LOGO+声明)
    bgm_idx = 1 + len(P["cards"]) + 2
    # BGM：循环补齐全片（源头可能比片子短）、音量严格低于人声 15dB、首尾淡入淡出
    af = (_asel + ";" + "[da]volume=%.1fdB,atempo=%.4f[voice];"
          "[%d:a]aloop=loop=-1:size=2e9,atrim=0:%.2f,"
             # ★ BGM 音色铁律（2026-11-04）：董事长说像鬼故事 = 低频浑浊把声音蒙住了
             #   ① 高通160Hz 切掉闷响低音 ② 提亮2.8kHz 让旋律出来 ③ 压低450Hz闷区
             "highpass=f=160:poles=2,highpass=f=140:poles=2,"
             "equalizer=f=2800:t=q:w=1.0:g=3.5,"
             "equalizer=f=450:t=q:w=1.2:g=-2.5,"
             "acompressor=threshold=0.12:ratio=2.5:attack=20:release=250,"
             "volume=0.62,"
          "afade=t=in:st=0:d=2.5,afade=t=out:st=%.2f:d=3.5[bgm];"
          "[voice][bgm]amix=inputs=2:duration=first:normalize=0:dropout_transition=0,"
          "alimiter=limit=0.55:attack=1:release=80:level=false[aout]"
          % (VOICE_DB, sp, bgm_idx, total, total - 3.5))

    os.makedirs(os.path.join(ROOT, "05-成片", cfg["line"]), exist_ok=True)
    out = os.path.join(ROOT, "05-成片", cfg["line"], cfg["name"] + ".tmp.mp4")
    # 素材按 trim 掐头：-ss 跳过开头闲聊，-t 限住好用长度
    _tr = getattr(CE, "TRIM", {}).get(n, dict(head=0.0, tail=999))
    _head = float(_tr["head"])
    _len = float(P["keep_len"])
    cmd = [FF, "-y", "-v", "warning", "-stats"]
    if _gaps:
        # 剪气口模式：整段素材进 filter，由 trim/concat 拼接
        cmd += ["-i", P["src"]]
    else:
        if _head > 0.01:
            cmd += ["-ss", "%.3f" % _head]
        cmd += ["-t", "%.3f" % _len, "-i", P["src"]]
    for key, *_ in P["cards"]:
        cmd += ["-i", os.path.join(ANIM, str(n), key + ".mp4")]
    cmd += ["-i", LOGO, "-i", NOTICE, "-i", cfg["bgm"]]
    _fc = ";".join([x for x in f if x.strip()]) + ";" + af
    io.open("E:/tmp/fc.txt","w",encoding="utf-8").write(_fc)
    cmd += ["-filter_complex", _fc,
            "-map", "[vout]", "-map", "[aout]",
            "-t", "%.2f" % (TEST_SEC if TEST_SEC > 0 else total),
            # ★ 兼容性铁律（2026-11-04）：手机/微信/抖音要能直接播
            #   profile=main + level=4.1 是全网通吃档；High@5.0 大量播放器直接拒播
            "-c:v", "libx264", "-preset", "medium", "-profile:v", "main", "-level", "4.1",
            "-crf", "20", "-maxrate", "8M", "-bufsize", "16M",
            "-refs", "3", "-x264-params", "keyint=60:min-keyint=60:scenecut=0:bframes=2",
            "-pix_fmt", "yuv420p", "-r", "30", "-g", "60",
            "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", out]
    t0 = time.time()
    print("  → 合成中 ...")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=_cwd_sub)
    if r.returncode != 0:
        print("❌ ffmpeg 失败:\n", r.stderr[-3000:])
        return False
    print("  ✅ 合成完成: %s  %.1fMB  用时 %.1f 分钟"
          % (out, os.path.getsize(out) / 1048576, (time.time() - t0) / 60))
    return True


if __name__ == "__main__":
    ns = [int(v) for v in (sys.argv[1:] or ["1"])]
    for n in ns:
        ok = build(n)
        print("RESULT", ok)
        if not ok:
            break
# ============================================================
# 董事长硬约束（2026-11-03 定，禁改）——每次合成都必须过这些闸门
# ============================================================
