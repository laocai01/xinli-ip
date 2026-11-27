# -*- coding: utf-8 -*-
"""新字幕样式 v2（2026-11-02 董事长定稿要求）

一、动态规律：完全照参考视频 46e12a4b... 逐帧实测（12fps 抽帧量化）
   每次换句：
     帧A  字高82  底y=1461   <- 起点：偏下、偏小
     帧B  字高86  底y=1448
     帧C  字高89  底y=1439
     帧D  字高91  底y=1436   <- 落定：标准大小、标准位置
   -> 入场 = 从下方升起 + 同时放大，历时约 0.33s（4帧@12fps）
   -> 句子首尾相接，不停留空档

二、立体字（董事长要"高大上的立体字"）
   - 纯白字面 + 深棕黑描边 4px（浅色衣服上也清晰）
   - 暖金阴影 3px 向右下（立体厚度感）
   - 柔和投影

三、位置（按素材实测人像位置，不挡人）
   人脸下沿约 y=1400（4条素材实测），字底 y=1610 = 脸下方 210px，
   且与底部 AI 声明（y1800+）留出 190px 间距，不挤
   左边距 x=58（同参考）
   单行 <=8 字，按语义切句
"""
import re
import json, os, io, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fix import fix_text
import cards_ep as _CE

ROOT = "E:/心理咨询IP"
R = ROOT + "/04-工程/batch2"
OUTDIR = ROOT + "/04-工程/batch3/subs_ref"

FONTSIZE = 96
MARGIN_L = 58
BASELINE_Y = 1600
MAX_CHARS = 14   # ★ 一行可容 14 字（68号字 ×14≈952px < 可用964px）；8 太碎，会把句子切出"起床"这种残渣

ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Ref,DouyinSansBold,%d,&H0066E0FF,&H001A7AFF,&H002A1A08,&HCC000000,-1,0,0,0,100,100,2.2,0,1,9.5,8.5,2,%d,%d,%d,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" % (FONTSIZE, MARGIN_L, 40, 1920 - BASELINE_Y)

PUNC = "，。、；：？！“”‘’（）《》【】…—,.;:?!\"'()[]~· "


def tc(s):
    if s < 0:
        s = 0
    h = int(s // 3600)
    m = int(s % 3600 // 60)
    sec = s % 60
    return "%d:%02d:%05.2f" % (h, m, sec)


def clean(t):
    t = t.strip()
    for p in PUNC:
        t = t.replace(p, "")
    return t


def load_cues(n):
    # ★ 2026-11-04 修：必须优先 batch3。batch2 目录里也残留 raw_5~11.json，
    #   但那是旧批次的内容，与素材 5-11 对不上 → 字幕会整体错位错字。
    #   规则：素材 5-11 只认 batch3；素材 1-4 才用 batch2。
    order = ("batch3", "batch2") if n >= 5 else ("batch2", "batch3")
    for bt in order:
        p = ROOT + "/03-内容/转录/%s/raw_%d.json" % (bt, n)
        if os.path.exists(p):
            d = json.load(io.open(p, encoding="utf-8"))
            segs = d["segs"] if isinstance(d, dict) else d
            return segs, "%s/raw_%d.json" % (bt, n)
    raise FileNotFoundError("找不到 raw_%d.json" % n)


def split_short(text, maxc=MAX_CHARS):
    """★ 断句铁律（2026-11-04 董事长定稿）：
      1) 只在标点处断句（，。！？、；：），绝不按字数硬切
      2) 切出来 <5 字的片段，跟相邻片段合并（"说说你"这种并到前或后）
      3) 合并后仍 >maxc 的，保留整句由 wrap() 缩字号，
         绝不在词中间劈开（"给孩/子做早饭"这种是错的）
    """
    text = text.strip()
    if not text:
        return []
    # ★ 必须先按标点切，再 clean —— clean 会删标点，先 clean 就切不开了
    parts = [clean(p) for p in re.split(r"[，。！？、；：,]+", text)]
    parts = [p for p in parts if p]
    if not parts:
        return []
    # 合并过短片段：只把 <5 字的并到相邻句，且合并后不超过 maxc
    merged = []
    for p in parts:
        if merged and (len(p) < 5 or len(merged[-1]) < 5) and (len(merged[-1]) + len(p)) <= maxc:
            merged[-1] = merged[-1] + p
        else:
            merged.append(p)
    # 若只有多段且总字数 <= maxc，合成一句读着更顺
    if len(merged) > 1 and sum(len(x) for x in merged) <= maxc:
        merged = ["".join(merged)]
    # ★ 仍超过 maxc 的单段：只在该段内找"语义停顿词"再切一次，绝不按字数硬切
    STOP = ("的时候", "的时候", "然后", "所以", "但是", "其实", "就是", "因为",
            "如果", "现在", "自己", "没有", "什么", "起来", "出来", "回来")
    out = []
    for p in merged:
        if len(p) <= maxc:
            out.append(p); continue
        cut = None
        for w in STOP:
            k = p.find(w, 4)
            if 4 <= k and k <= len(p) - 4 and abs(k - len(p) // 2) < abs((cut or 0) - len(p) // 2):
                cut = k
        if cut:
            out += [p[:cut], p[cut:]]
        else:
            out.append(p)
    return [x for x in out if x]
    return [x for x in merged if x]


# ---- 动画参数：照参考视频实测 ----
T_IN = 330      # 入场动画时长 ms
SCALE0 = 88     # 起点缩放（参考实测 82/91≈90%，取88）
DY0 = 26        # 起点向下偏移 26px（参考实测 1461->1436）
THICK = 9       # 立体厚度像素（加大让金色露出来）
# 参考实测：新句起点 横向展开(宽409→452=90%) 纵向略小(高82→91=90%) 底y 1448→1436
SCALE_X0 = 90
SCALE_Y0 = 90
T_UP = 90       # 90ms 处开始上浮
T_IN = 330      # 上浮总时长 ms
OUT_T = 130     # 末 130ms 缩小淡出
# 删除冗余口播区间（秒，素材原时间轴）：绕圈重复的论述
CUT_RANGES = {
 1: [(118.4, 120.2),   # "他把情绪给压下去了" 重复上句
     (124.0, 150.0)],  # 绕圈子重复提问约 26s
}
# ===== 第一版配色（董事长要求回用第一版）=====
RAINBOW = [
    "&H0066E0FF&",   # 第一版暖金（主色）
    "&H001A7AFF&",   # 第一版橙金（次色）
    "&H0066E0FF&",   # 回到暖金，三句一循环不花
]
FONT_SIZE = 68
BORDER = 9.0
SHADOW = 7.5

# ===== 滚动参数（参考视频逐帧实测）=====
LINE_H = 88        # 行距（原片实测 105px@2400h → 换成 1920 高约 95px）
SCROLL_S = 0.42     # 一次上移时长
HOLD_MAX = 5.0

# ===== 三段动效（董事长 2026-11-02 描述 + 逐帧实测）=====
# ① 往上推时放大：宽 413→389→339→311，起点 135%
PUSH_SCALE = 135
# ② 再往上暗下来：均亮 218→215→209，亮度衰减到 55%
DIM_ALPHA = "&H72&"   # 约 55% 不透明
# ③ 最后消失：宽 314→160，缩小到 52% 并淡出
OUT_SCALE = 52


def _tag(x, y_from, y_to, sec, sc0=100, sc1=100, dim=None, col="&H004AD2FF&"):
    """一条字幕的标签：位置移动 + 缩放 + 可选变暗

    sc0=起点缩放百分比  sc1=终点缩放百分比
    dim=终点透明度（如 &H72& 表示变暗到 55%）
    """
    t = ["\\an1", "\\fad(60,60)",
         "\\1c" + col, "\\3c&H2A1A08&",
         "\\bord%.1f" % BORDER, "\\shad%.1f" % SHADOW]
    if abs(y_to - y_from) > 0.5:
        t.append("\\move(%d,%d,%d,%d,0,%d)" % (x, int(y_from), x, int(y_to), int(sec * 1000)))
    else:
        t.append("\\pos(%d,%d)" % (x, int(y_from)))
    if sc0 != 100 or sc1 != 100:
        if abs(sc0 - sc1) > 0.5:
            # 有缩放过程：从 sc0 渐变到 sc1
            t.append("\\fscx%d\\fscy%d\\t(0,%d,\\fscx%d\\fscy%d)"
                     % (sc0, sc0, int(sec * 1000), sc1, sc1))
        else:
            t.append("\\fscx%d\\fscy%d" % (sc0, sc0))
    if dim:
        t.append("\\alpha%s" % dim)
        t.append("\\t(0,%d,\\alpha&HFF&)" % int(sec * 1000))
    return "{" + "".join(t) + "}"


MAX_LINE = 14   # ★ 与 MAX_CHARS 一致（68号 × 14 ≈ 952px）


# ============================================================
# 错字修正表（ASR 同音/口误，人工逐句校对，2026-11-03）
# 格式: (错, 对)，按顺序替换；只在字幕文本上生效，不动语音
# ============================================================
TYPO_FIX = [
    # —— 第31条 ——
    ("后边讲说的话", "后面想说的话"),
    ("你说话他说他儿子", "后来他说他儿子"),
    ("不代表不想好就好了", "不代表不想，就好了"),
    ("的时候是不是怕我", "你说话的时候是不是怕我"),
    ("肯定是有的是办法", "肯定是有办法"),
    ("你越管他越远", "你越管得他越远"),
    # —— 第29条 ——
    ("你又没有说过这几句话", "你有没有说过这几句话"),
    ("这没什么意思", "这有什么"),
    ("他学会的是学会", "他学会的是"),
    ("压情绪压遇住", "压情绪、压抑住"),
    ("别在心里不说出来", "憋在心里不说出来"),
    ("连口子吵架了", "两口子吵架了"),
    ("记住上句话第一句", "记住三句话，第一句"),
    ("你问他刚才是委屈呢", "你问他是不是委屈呢"),
    ("慢慢慢慢地", "慢慢地"),
    # —— 第30条 ——
    ("并不是他胖你", "并不是他烦你"),
    ("是你第一句听着就像省", "是你第一句听着就像审"),
    ("就是一开口他就嫌犯了", "就是一开口他就嫌烦了"),
    ("被阻碍被抛开", "被阻碍被推开"),
    ("先说一句跟解释", "先说一句跟学习"),
    ("你们把那个小黑还跟你玩吗", "你们班那个小黑还跟你玩吗"),
    ("开口就察感的人", "开口就查岗的人"),
    ("关注老赛评论区", "关注老蔡评论区"),
    ("你再一次跟孩子聊", "你上一次跟孩子聊"),
    # —— 第32条 ——
    ("就你越管得他越远就离的越来越远", "你越管他他离得越远"),
    ("他周末想谈一天", "他周末想玩一天"),
    ("别直接点个表或定时", "别直接定个表或定时"),
    ("边界不用怕轻", "边界不用怕清"),
    ("就怕不轻不处", "就怕不清不处"),
    ("太浮的边界", "太松的边界"),
]

# 重复句去重：这些内容在原片里被 ASR 重复识别，字幕只保留第一次
DEDUP_DROP = [
    "他妈妈跑过去他第一句话是妈我没事",   # 第2次出现删掉
    "他把情绪给压下去了",                 # 第2次出现删掉
]

def fix_typo(t):
    for a, b in TYPO_FIX:
        if a in t:
            t = t.replace(a, b)
    return t

def _text_px(t, size):
    """★ 真实字宽估算（2026-11-04 董事长：有字溢出屏幕）。
    中文全角字宽 = 字号；标点/数字 = 0.5 字号；加粗再 ×1.06。
    之前用 len*size*0.5 把宽算小了一半，所以 96 号长句直接冲出右边。
    """
    w = 0.0
    for ch in t:
        if ch == " ":
            w += size * 0.30
        elif ord(ch) < 128:
            w += size * 0.55
        else:
            w += size * 1.00
    return w * 1.06          # 加粗膨胀


def wrap(t, maxc=MAX_LINE):
    """不折行：超长句返回 (文本, 字号)，字号按真实字宽算到安全区内。

    可用宽度 SAFE_W 必须留足左右边距：
      屏幕 1080 - 左边距 60 - 右安全 30 = 990，取 940 留余量。
    """
    t = t.replace("\\N", "").replace("\n", "")
    SAFE_W = 880.0    # 左边距58 + 右侧安全30，1080-58-30=992，再留余量取880
    size = FONT_SIZE
    # 先按字数快速判断，再按真实字宽迭代收缩
    if _text_px(t, size) > SAFE_W:
        # 按比例一次算到位，再微调（字宽与字号线性相关）
        ratio = SAFE_W / _text_px(t, size)
        size = int(size * ratio * 0.98)          # 0.98 留余量
        while size > 40 and _text_px(t, size) > SAFE_W:
            size -= 1
        size = max(40, size)
    return t, size


def _wordfade_ms(dur_sec, txt, per_char=80):
    """★ 逐字淡入（不动位置）：把整句拆成「一个字一条 \\t 时间点」的 alpha 渐变。
    ASS 里逐字控制的可靠做法是给每个字包一层 {\\alpha&HFF&\\t(t0,t1,\\alpha&H00&)}。
    返回已处理好逐字透明度的字幕正文（含 \\an1 定位仍在外层）。"""
    n = len(txt)
    if n == 0:
        return txt
    total = min(n * per_char, int(dur_sec * 1000 * 0.55))
    step = total / float(n)
    out = []
    for i, ch in enumerate(txt):
        t0 = int(i * step)
        t1 = int(t0 + step)
        out.append("{\\alpha&HFF&\\t(%d,%d,\\alpha&H00&)}%s" % (t0, t1, ch))
    return "".join(out)


def build(n, out_path=None, speech_end=None, speed=1.0, gaps=None):
    segs, src = load_cues(n)
    items = []
    for s in segs:
        st, en = float(s["start"]), float(s["end"])
        pieces = split_short(fix_text(n, s["text"]))
        if not pieces:
            continue
        tot = sum(len(p) for p in pieces) or 1
        t = st
        for p in pieces:
            dur = (en - st) * len(p) / tot
            items.append([t, t + dur, p])
            t += dur
    if speech_end:
        items = [x for x in items if x[0] < speech_end]
    for i in range(len(items)):
        if i + 1 < len(items):
            items[i][1] = min(items[i][1], items[i + 1][0])
        if items[i][1] - items[i][0] < 0.30:
            items[i][1] = items[i][0] + 0.30
    # ★ 气口重映射：剪掉空隙后，时间轴要同步压缩
    if gaps:
        _cuts = gaps.get("cuts", [])
        def _rm(t):
            sh = 0.0
            for a, b in _cuts:
                if t <= a:
                    break
                if t >= b:
                    sh += b - a
                else:
                    return a - sh
            return t - sh
        for it in items:
            it[0] = _rm(it[0])
            it[1] = _rm(it[1])
            if it[1] - it[0] < 0.25:
                it[1] = it[0] + 0.25
        items = [x for x in items if x[1] > x[0] + 0.05]

    # ★ 先扣掉掐头（head），再按倍速折算 → 成片时间
    _tr = getattr(_CE, "TRIM", {}).get(n, dict(head=0.0, tail=999))
    head = float(_tr["head"])
    tail = float(_tr["tail"])
    # ★ 删掉冗余区间
    cuts = getattr(_CE, 'TRIM_CUTS', {}).get(n, [])
    if cuts:
        kept = []
        for a, b, t in items:
            mid = (a + b) / 2
            if any(c0 <= mid < c1 for c0, c1 in cuts):
                continue
            kept.append([a, b, t])
        items = kept
    items = [[a, b, t] for a, b, t in items if b > head + 0.05 and a < tail]
    # 删段后所有时间要前移（前面积累的剪切时长）
    def _shift(x):
        acc = 0.0
        for c0, c1 in sorted(cuts):
            if x >= c1:
                acc += c1 - c0
            elif x > c0:
                acc += x - c0
                break
        return x - acc
    items = [[(_shift(a) - head) / speed, (_shift(min(b, tail)) - head) / speed, t]
             for a, b, t in items]

    # ===== 字幕时间轴整理（顺序不能乱）=====
    # ★ 2026-11-04 修：先按时间强制排序，否则气口重映射后会出现乱序
    items.sort(key=lambda x: (x[0], x[1]))
    # ①.0 砍掉片尾下一讲预告（不属于本条内容）
    _cut = None
    for _i, (_a, _b, _t) in enumerate(items):
        if any(k in _t for k in ("下一讲", "下集", "下一期", "下一课", "下一家", "下期")):
            _cut = _i
            break
    if _cut is not None:
        items = items[:_cut]


    # ① 合并入场时间重合的重复句（源转录把一句话拆成两条）
    merged_items = []
    for it in items:
        if merged_items and it[0] - merged_items[-1][0] < 0.08:
            prev = merged_items[-1]
            prev[1] = max(prev[1], it[1])
            if it[2] and it[2] not in prev[2]:
                prev[2] = prev[2] + it[2]
        else:
            merged_items.append(it)
    items = merged_items

    # ①.5 把极短碎片（<4字）并入相邻句，减少抢行
    merged2 = []
    k = 0
    while k < len(items):
        it = list(items[k])
        def _frag(t):
            c = clean(t)
            if len(c) <= 2:          # ★ 单字/两字碎片（"起床""有""床"）必须并掉
                return True
            if len(c) < 6 and c[-1] not in "。！？":
                return True
            # 以虚词/代词结尾 = 句子没说完，必须并到下一句
            return c[-1] in "他她也的就都是而和跟把被给在"
        while _frag(it[2]) and k + 1 < len(items):
            k += 1
            it[1] = max(it[1], items[k][1])
            it[2] = it[2] + items[k][2]
        merged2.append(it)
        k += 1
    items = merged2

    # ★★ 超宽强制拆分（2026-11-04 董事长：有字溢出屏幕）：
    #   单句在最小可读字号(52)下仍放不下 = 必须拆，不许靠缩字硬塞
    def _too_wide(t):
        return _text_px(t, 52) > 940.0
    STOPW = ("的时候", "然后", "所以", "但是", "其实", "就是", "因为", "如果",
             "现在", "自己", "没有", "什么", "起来", "出来", "回来", "一句话")
    _wq = list(items)
    for _round in range(4):                 # 最多拆 4 轮，确保全部放得下
      _nx = []
      for _it in _wq:
        _a, _b, _t = _it[0], _it[1], _it[2]
        if not _too_wide(_t) or len(_t) <= 8:
            _nx.append(_it); continue
        # 找最接近中间、且两边都>=6字的停顿词切点
        best = None
        for w in STOPW:
            k = _t.find(w, 6)
            while k != -1:
                if k >= 6 and len(_t) - k >= 6:
                    if best is None or abs(k - len(_t) / 2.0) < abs(best - len(_t) / 2.0):
                        best = k
                k = _t.find(w, k + 1)
        if best is None:
            best = len(_t) // 2          # 兜底：正中切（比缩到40号看不清强）
        r1, r2 = _t[:best], _t[best:]
        # 按字数比例分配时间
        share = len(r1) / float(len(_t))
        mid = _a + (_b - _a) * share
        _nx.append((_a, mid - 0.02, r1))
        _nx.append((mid + 0.02, _b, r2))
      _wq = _nx
    items = [list(x) for x in _wq]

    # ★★ 最终兜底（2026-11-04）：任何 ≤4 字的残渣，无条件并进前一句。
    #    这一步必须放在所有拆分逻辑之后，否则还会漏。
    _fin2 = []
    for it in items:
        _c = clean(it[2])
        if _fin2 and len(_c) <= 4:
            _fin2[-1][1] = max(_fin2[-1][1], it[1])
            _fin2[-1][2] = _fin2[-1][2] + _c
        else:
            _fin2.append(it)
    items = _fin2
    # ===== ★★ 字幕时间轴 v5（2026-11-04 董事长定稿）=====
    #  原则：位置绝对不动（不滚动、不漂移），动效只在「字本身」上。
    #  1) 每句起止 = 真实口播时间，不人为错开、不人为延长
    #  2) 三行固定槽位 1600 / 1512 / 1424，新句填最下面的空槽
    #  3) 同屏最多 3 句；要进第 4 句时，最早那句立即结束（让位）
    #  4) 逐字淡入跟随口播节奏
    items.sort(key=lambda x: (x[0], x[1]))
    # ★ 碎片清理：字数 ≤3 或时长 <0.6s 的句子，一律并给前一句（"起床""有"这种不能单独成行）
    _m = []
    for it in items:
        _c = clean(it[2])
        if _m and (len(_c) <= 3 or it[1] - it[0] < 0.6):
            _m[-1][1] = max(_m[-1][1], it[1])
            _m[-1][2] = _m[-1][2] + it[2]
        else:
            _m.append(it)
    items = _m
    # ★ 兜底：合并后仍 ≤3 字且不是首句，再并一次
    _m2 = []
    for it in items:
        if _m2 and len(clean(it[2])) <= 3:
            _m2[-1][1] = max(_m2[-1][1], it[1])
            _m2[-1][2] = _m2[-1][2] + it[2]
        else:
            _m2.append(it)
    items = _m2
    # ★ 尾巴延伸：每句多留 0.35 秒，让前后句自然交叠，形成三行递进的层次感
    for k in range(len(items) - 1):
        items[k][1] = max(items[k][1], min(items[k + 1][0] + 0.35, items[k][1] + 0.35))

    # 同屏 ≤3：第 k 句的结束，不得晚于第 k+3 句的起点
    for k in range(len(items) - 3):
        items[k][1] = min(items[k][1], items[k + 3][0])
    # 每句至少显示 0.5 秒（太短会闪）
    for k in range(len(items)):
        if items[k][1] - items[k][0] < 0.5:
            items[k][1] = items[k][0] + 0.5

    # ★ 槽位分配 v7（2026-11-04 定稿）：位置一经分配就固定，绝不移动。
    #   找"本句进场那一刻，屏幕上还活着的最少 3 句"，取它们没占用的空槽。
    #   空槽从下往上：1600(底) → 1512(中) → 1424(顶)
    row_of = [0] * len(items)
    for k in range(len(items)):
        used = set()
        for j in range(k):
            if items[j][1] > items[k][0]:        # j 句在本句进场时还活着
                used.add(row_of[j])
        free = [r for r in (0, 1, 2) if r not in used]
        row_of[k] = free[0] if free else 2        # 全满就放顶上（随后会被挤掉）

    out_path = out_path or (OUTDIR + "/%d.ass" % n)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    x, y = MARGIN_L, BASELINE_Y
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(ASS_HEAD)
        # ===== 一段式滚动字幕（一句 = 一条 Dialogue，绝不叠层）=====
        # 闪烁根因：原来一句拆 3~6 段，段边界落在同一时刻 → 多层文字重叠 = 花眼。
        # 现在全部动画塞进同一条里：
        #   位置：\move 从下一行滚到位（整块上推的感觉由行距连续衔接产生）
        #   缩放：\t 入场放大 100→108 再回 100；出场 100→88
        #   亮度：出场 alpha 0→DIM→全透明，用 \\t 两段完成
        # ===== 3 行滚动（分段式，边界严丝合缝，不重叠一帧）=====
        # 每句寿命内会被后来的句子往上顶 0~2 次。
        # 每次"被顶"切成一段：段与段首尾相接（prev_end == next_start），
        # 所以任意时刻每句只有 1 条在显示 → 不会叠字、不会闪。
        # ===== 三行同步滚动（整块一起上移，各句永不相交）=====
        # 关键：所有句子的位移量必须一致 —— 位置 = 基准行 - 全局滚动量。
        # 全局滚动量在"新句进场"这一刻从 k 平滑变到 k+1，历时 SCROLL_S。
        # 每句在它的存活期内跟随同一个进度，所以彼此永远相差整数倍 LINE_H。
        SCROLL_S = 0.38

        # ★ 三行同屏：先按「最多 3 句同时可见」裁剪每句存活期，再排行
        #   行 0=底(1600) 1=中(1512) 2=顶(1424)
        items = [list(it) for it in items]

        for idx, (a, b, txt) in enumerate(items):
            col = RAINBOW[idx % len(RAINBOW)]
            # ★★ 董事长 2026-11-04 定稿：字幕位置绝对不动，绝不滚动、绝不漂移。
            #   一句一条 Dialogue，只用一个 \pos；入场动效只做「逐字淡入」。
            #   机器闸门会逐帧校验 y 不漂移，违者不出片。
            y_fix = y - LINE_H * row_of[idx]
            _t, _fs = wrap(fix_typo(txt))
            _body = _wordfade_ms(b - a, _t)
            tags = ["\\an1", "\\1c%s" % col, "\\3c&H2A1A08&",
                    "\\bord9.5", "\\shad8.5",
                    "\\pos(%d,%d)" % (x, int(round(y_fix)))]
            if _fs != FONT_SIZE:
                tags.append("\\fs%d" % _fs)
            f.write("Dialogue: 2,%s,%s,Ref,,0,0,0,,{%s}%s\n"
                    % (tc(a), tc(b), "".join(tags), _body))

    return out_path, len(items), src
