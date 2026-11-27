# -*- coding: utf-8 -*-
"""第二批（11-16）：字幕 ASS + 卡片锚点 + 每集参数"""
import json, io, os, re

ROOT = "E:/心理咨询IP"
R = ROOT + "/04-工程/batch2"
FONTDIR = ROOT + "/07-形象设计/fonts/fonts-main/DouyinSans"

# 素材序号 → 集配置
EPS = {
 1: dict(line="没人可说", title="A线第4讲_怎么跟一个不说话的人把话说上",
         name="第23条_没人可说第4讲_怎么跟一个不说话的人把话说上_20261024.mp4",
         bgm=ROOT + "/06-音乐/国际民谣_免版税/A_沉静反思_02_Forever_in_My_Heart.mp3", speed=1.196),
 2: dict(line="没人可说", title="A线第5讲_你一歇下来就发慌",
         name="第24条_没人可说第5讲_你一歇下来就发慌_20261024.mp4",
         bgm=ROOT + "/06-音乐/国际民谣_免版税/C_夜静陪伴_03_Irenko.mp3", speed=1.264),
 3: dict(line="没人可说", title="A线第6讲_两口子没话说了是从哪一天开始的",
         name="第25条_没人可说第6讲_两口子没话说了是从哪一天开始的_20261024.mp4",
         bgm=ROOT + "/06-音乐/国际民谣_免版税/A_沉静反思_01_Through_Ups_and_Down.mp3", speed=1.027),
 4: dict(line="我是不是没用了", title="B线第4讲_怎么把话说到孩子心里去",
         name="第26条_我是不是没用了第4讲_怎么把话说到孩子心里去_20261024.mp4",
         bgm=ROOT + "/06-音乐/国际民谣_免版税/E_旧日微温_03_Wedding_03.mp3", speed=1.138),
 5: dict(line="我是不是没用了", title="B线第5讲_你越来越不敢麻烦孩子了",
         name="第27条_我是不是没用了第5讲_你越来越不敢麻烦孩子了_20261024.mp4",
         bgm=ROOT + "/06-音乐/温柔轻音乐_新/BGM02_Galaxys_Endless_Expanse.mp3", speed=1.163),
 6: dict(line="我是不是没用了", title="B线第6讲_如果遇见二十岁的自己你会说什么",
         name="第28条_我是不是没用了第6讲_如果遇见二十岁的自己你会说什么_20261024.mp4",
         bgm=ROOT + "/06-音乐/_试听/17_F_纯器乐民谣_02_Goin_Back_to_Alabama.wav", speed=1.061),
}

# 卡片 → 锚点关键字（在已校对字幕里搜，取该条的 start；找不到回退到 fallback 秒）
ANCH = {
 1: [("01_主_你越想跟他说开", "你越想跟他把话说开", 5.2),
     ("02_副_不是关心是查岗", "不是关心", 31.9),
     ("03_金句_不用挨批的机会", "不用挨批的机会", 56.7),
     ("04_方法_三句递话", "就三句，你记一下", 119.6)],
 2: [("01_主_你不是不想歇", "你不是不想歇", 2.7),
     ("02_副_歇着也在过账", "所以你不是懒", 57.5),
     ("03_金句_你是在证明自己", "你是在证明自己", 93.3),
     ("04_方法_两件小事", "就做两件事情", 118.4)],
 3: [("01_主_不是不爱了", "不再互相", 7.4),
     ("02_副_通知和收到", "都是一句通知", 34.9),
     ("03_金句_没被接住", "感情不是被时间磨掉", 78.6),
     ("04_方法_两件事", "特别简单，两件事", 101.8)],
 4: [("01_主_说成了考核", "说成了", 7.3),
     ("02_副_三句问进度", "三句：吃饭了没有", 15.0),
     ("03_金句_两个字的天花板", "把天花板压到", 91.2),
     ("04_方法_换成递话头", "记住这两句", 105.6)],
 5: [("01_主_怕成负担", "怕自己变", 4.1),
     ("02_副_把门关上", "把门，一点一点关", 35.6),
     ("03_金句_没人等着你", "没有人等着", 100.4),
     ("04_方法_找个小口子", "给自己找一个", 94.4)],
 6: [("01_主_都留给了别人", "你把最好的话", 4.8),
     ("02_副_对谁都宽", "你对谁都宽", 30.7),
     ("03_金句_最该说辛苦了", "这辈子最该被你", 200.1),
     ("04_方法_睡前五分钟", "说三句话", 112.5)],
}

# 关键词高亮：字幕里出现这些词就染亮黄 + 微放大，制造视线跳点
KEYWORDS = [
    "发慌", "不敢闲", "不敢歇", "算账", "一把尺子", "随时待命",
    "不是懒", "架得太久", "应该", "可以", "五分钟", "两件事",
    "没话说", "一句话", "接住", "心里", "孩子", "应该的",
    "二十年", "辛苦了", "懂事", "争气", "累坏了",
]


import re as _re

# ASS 时间标签精度：\k 的单位是 1/100 秒（centisecond）
# 七彩配色（每句一个主色，全片轮换；同一句内统一，避免花）
# 顺序为 ASS 的 &HBBGGRR&：亮丽但不荧光，保证在深色画面与浅色卡片上都看得清
RAINBOW = [
    "&H004AD2FF&",   # 亮金 #FFD24A
    "&H003C9AFF&",   # 暖橙 #FF9A3C
    "&H008A7BFF&",   # 珊瑚粉 #FF7B8A
]

_sent_idx = [0]   # 全局句子计数，保证相邻两句不同色


def build_flow(n, cues, sp, out_lines):
    """「上滚字幕流」：同一时刻屏上出现三段，讲到哪段哪段亮。

    董事长 2026-10-26 定的效果（业内叫 Kinetic Typography 动态字幕）：
      · 一行字太长 → 拆成 ≤8 字的短段，按口播逐段推进
      · 未讲到的段：淡色（半透明）、小字号，在下方等待
      · 正在讲的段：变清晰 + 放大 165% + 同色光边
      · 讲过的段：先变淡，再消失
      · 整条流缓缓往上走（跟着口播节奏，慢速）
    """
    # ---- 1) 拆短段：每段 ≤8 字，按标点与语义切 ----
    segs = []          # [(开始秒, 结束秒, 文本)]
    for c in cues:
        st = c["start"] / sp
        en = c["end"] / sp
        txt = strip_quotes(c["text"]).replace("\n", " ")
        if not txt:
            continue
        # 先按标点切，再按 8 字硬约束切
        raw = _re.split(r"(?<=[，。！？；：、])", txt)
        chunks = []
        for r_ in raw:
            r_ = r_.strip()
            if not r_:
                continue
            while len(r_) > 4:
                chunks.append(r_[:4])
                r_ = r_[4:]
            if r_:
                chunks.append(r_)
        if not chunks:
            continue
        total = sum(len(x) for x in chunks) or 1
        acc = st
        for k, ch in enumerate(chunks):
            d = (en - st) * len(ch) / total
            segs.append([acc, acc + d, ch])
            acc += d

    # ---- 2) 逐段出三层：等待层(淡) / 当前层(亮+大+光边) / 已讲层(淡出) ----
    CX = 350            # 176pt、每段≤4字（约700px），居左
    for i, (st, en, txt) in enumerate(segs):
        col = RAINBOW[i % len(RAINBOW)]
        # 当前段：淡入 → 清晰放大 165% + 光边 → 变淡
        d_cs = max(20, int(round((en - st) * 100)))
        # 当前段从下方缓缓升起（慢速，跟着口播）
        y0, y1 = 1560, 1500
        head = (r"{\an2\move(%d,%d,%d,%d,0,%d)\fad(120,180)\fscx100\fscy100}"
                % (CX, y0, CX, y1, d_cs))
        # 主体放大 + 光边（底层）
        glow = (r"{\alpha&H9E&\1c%s\3c%s\bord12\shad0"
                r"\t(0,10,\fscx165\fscy165\alpha&H72&)"
                r"\t(%d,%d,\fscx100\fscy100\alpha&H9E&)}" % (col, col, d_cs - 16, d_cs))
        out_lines.append("Dialogue: 0,%s,%s,Sub,,0,0,0,,%s%s%s"
                         % (tc(st), tc(en), head, glow, txt))
        body = (r"{\1c%s\3c&H00201008&\bord9\shad7"
                r"\t(0,10,\fscx165\fscy165)"
                r"\t(%d,%d,\fscx100\fscy100)}" % (col, d_cs - 16, d_cs))
        out_lines.append("Dialogue: 1,%s,%s,Sub,,0,0,0,,%s%s%s"
                         % (tc(st), tc(en), head, body, txt))

    return len(segs)


ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,DouyinSansBold,68,&H0066E0FF,&H001A7AFF,&H002A1A08,&HCC000000,-1,0,0,0,100,100,2.2,0,1,9.5,8.5,2,110,110,430,1
Style: SubS,DouyinSansBold,68,&H0066E0FF,&H0000E8FF,&H002A1A08,&HCC000000,-1,0,0,0,100,100,2.2,0,1,9.5,8.5,2,110,110,430,1\nStyle: Roll,DouyinSansBold,118,&H000000FF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,2,0,1,8,5,2,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def tc(s):
    s = max(0.0, s)
    h = int(s // 3600); m = int((s % 3600) // 60); sec = s % 60
    return "%d:%02d:%05.2f" % (h, m, sec)


def strip_quotes(t):
    t = t.strip()
    while t and t[-1] in "“”‘’\"'":
        t = t[:-1]
    while t and t[0] in "”’\"'":
        t = t[1:]
    return t



def paint_rainbow(txt, phase=0):
    """给一段文字逐字上七彩（每字一个色，循环）。

    为什么敢这么用：董事长 2026-10-26 定 —— 字幕已拆成 ≤8 字的短段，
    一行字很短，逐字七彩不会像长句那样显得乱、反而更活泼不土。
    """
    out = []
    for k, ch in enumerate(txt):
        c = RAINBOW[(phase + k) % len(RAINBOW)]
        out.append("{\\1c%s}%s" % (c, ch))
    return "".join(out)


def build_subs(n):
    """Roll-up 滚动字幕（2026-10-26 按全网实查标准重写）

    依据：E:/心理咨询IP/09-方案文档/字幕改动依据_全网实查_20261026.md
      · W3C Roll-up Captions：屏上保留 2~4 行，来新的一行，旧行整行上推
      · 字号 200pt（实际字高 144px，占屏高 7.5%，落在抖音 6~9% 标准内）
      · 每次 4 个中文字，每条停留 ≥0.3 秒
      · 位置 y=1100~1400（避开顶部 220px 与底部 440px 禁区）
      · 每行一个主色（4 色轮换），不逐字换色
      · 动效只保留缩放：正在讲的一行 1.0→1.3，其余不加发光不叠位移
    """
    # ★ 用 ASR 细段（draft_N.json）而不是粗句（final_N.json）：
    #   draft 的分段跟着语音停顿走，时间戳更贴近真实口播；粗句会把两句话并成一条，导致时间前快后慢
    _dp = os.path.join(R, "draft_%d.json" % n)
    d = json.load(io.open(_dp if os.path.exists(_dp) else os.path.join(R, "final_%d.json" % n), encoding="utf-8"))
    sp = EPS[n]["speed"]
    path = os.path.join(R, "subs", "%d.ass" % n)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # ---- 1) 按「口播字数速率」切行：每段只在说到它时才出现 ----
    #   ★ 关键：起止时间必须由该段在句中的字数位置换算，不能整句平均分
    #     （平均分 = 后半句的字提前出现，就是董事长说的"字幕先出"）
    rows = []          # [(开始秒, 结束秒, 文本)]
    CPS = 5.2          # 中文口播语速（字/秒），由实测 218 字/分换算
    # ★ 过滤片尾下集预告（「下一讲…」「你们俩就没话了」），否则字幕会多出 10 秒
    _ENDWORD = ("下一讲", "下一期", "你们俩，就没话说了")
    for c in d["cues"]:
        if any(w in c["text"] for w in _ENDWORD):
            continue
        st = c["start"] / sp
        en = c["end"] / sp
        # 预告开始后的所有段落一律不收
        if st > 223.0 / sp:
            continue
        txt = strip_quotes(c["text"]).replace("\n", " ").strip()
        import re as _re
        txt = _re.sub(r"[^0-9A-Za-z\u4e00-\u9fa5]", "", txt)
        if not txt:
            continue
        dur = max(0.40, en - st)
        # ★ 段数按「本句时长」定：每段至少 0.85 秒（说 3 个字约需 1 秒）
        #   不能固定 3 字——短句会被切太碎、时间对不上口播
        n_ch = len(txt)
        n_row = max(1, min(n_ch, int(round(dur / 1.0))))   # 每段约 1 秒
        per = max(1, min(4, (n_ch + n_row - 1) // max(1, n_row)))
        n_row = (n_ch + per - 1) // per
        # ★ 按「本句真实语速」映射时间：语速 = 本句字数 ÷ 本句真实时长
        #   （实测：用全局 5.2 字/秒会让慢句的字幕超前一倍——本片实际 3.0 字/秒）
        #   每段起始 = 句首 + 前面已说字数 ÷ 本句语速，这样字幕刚好在说到时出现，不提前
        cps = n_ch / dur if dur > 0.1 else 4.0      # 本句真实语速（字/秒）
        for k in range(n_row):
            a = k * per
            b = min(n_ch, a + per)
            piece = txt[a:b]
            if not piece:
                continue
            seg_st = st + a / cps                  # 说到第 a 个字时出现
            seg_en = st + b / cps                  # 说到第 b 个字时收起
            seg_en = min(seg_en, st + dur)
            if seg_en - seg_st < 0.55:             # 读不完就不给它单独成段
                continue
            rows.append([seg_st, seg_en, piece])

    # ---- 2) 照搬抖音主流做法：**一句话一个事件**，边讲边从下往上慢慢升 ----
    #   之前搞三格位复制 = 同一句在三个位置闪，必然看不清。这才是「什么都没有变/看不清」的根因。
    #   标准做法（剪映/抖音大字口播）：
    #     · 一句一条事件，不复制、不多格
    #     · 整句在讲话期间从下方缓慢升到上方（\move 一个事件内完成）
    #     · 讲到 → 放大 1.2 倍 → 缩回；讲完 → 淡出
    #     · 位置在左侧，字号大
    CX = 260                    # 靠左（左沿约 40px 呼吸位）
    Y_START = 1600              # 开始位置（下方，更靠底）
    Y_END = 620                 # 结束位置（上方，一路升到画面顶部才消失）—— 一句说完就升到这里淡出
    ALPHA_GONE = "FF"

    # ★★ 固定滚动窗口（真正的 Roll-up）：屏上恒定 3 行，每行只在「上移一行」的距离内移动
    #   之前的问题：一段要从 y=1700 走到 y=760（940px），但只活 1.8 秒 → 必然快得像闪。
    #   现在：每段只上移一行高（LINE_H=280px），移动时长 = 本段存活时长（≥2.6s）
    #        → 速度降到 100px/s 以下，而屏上始终只有 3 行，不会堆叠。
    CX = 260
    LINE_H = 400                # 行距（字高 108px + 292px 空隙，实测必须拉开）
    Y_BOTTOM = 1140             # 最新一段落点
    SLOT = [Y_BOTTOM, Y_BOTTOM - LINE_H, Y_BOTTOM - 2 * LINE_H]   # 三行固定位 1140/740/340

    lins = []
    n_rows = len(rows)
    Y_TOP = 340                 # 一路升到这里（真人头顶）
    Y_START = Y_BOTTOM + LINE_H # 从最下一行的下方冒出

    for i, (st, en, txt) in enumerate(rows):
        # ★ 一段 = 一个事件：全程匀速上升，绝不拆成多个事件（拆了就跳）
        # ★ 存活越长 → 同样的上升距离走得越慢（速度 = 距离 ÷ 存活时长）
        life = en + 2.8                       # 讲完再留 2.8 秒慢慢走、慢慢缩、慢慢淡
        if i + 2 < n_rows:
            life = max(life, rows[i + 2][0] + 2.2)
        life = min(life, en + 5.2)
        span = max(1200, int((life - st) * 1000))

        painted = "{\\1c%s}" % RAINBOW[i % len(RAINBOW)] + txt
        col0 = RAINBOW[i % len(RAINBOW)]

        # 上升：一次 \move 走完（Y_START → Y_TOP），匀速，无分段
        # 消亡：最后 45% 时间内「逐渐缩小 + 淡到透明」，这是唯一的变化
        a0 = int(span * 0.55)
        anim = r"\t(%d,%d,\fscx62\fscy62\alpha&HFF&)" % (a0, span)
        mv = r"\move(%d,%d,%d,%d,0,%d)" % (CX, Y_START, CX, Y_TOP, span)

        head = (r"{\an2" + mv + r"\fad(280,0)"
                r"\3c&H00000000&\bord8\shad5\fscx100\fscy100" + anim + "}")
        glow = (r"{\an2" + mv + r"\fad(280,0)"
                r"\1c%s\3c%s\bord16\shad0\alpha&H88&\blur6"
                r"\fscx100\fscy100" % (col0, col0)) + anim + "}"
        lins.append("Dialogue: 0,%s,%s,Roll,,0,0,0,,%s%s"
                    % (tc(st), tc(life), glow, txt))
        lins.append("Dialogue: 1,%s,%s,Roll,,0,0,0,,%s%s"
                    % (tc(st), tc(life), head, painted))

    with io.open(path, "w", encoding="utf-8") as f:
        f.write(ASS_HEAD)
        for l in lins:
            f.write(l + "\n")

    lasts = rows[-1][1] if rows else 0
    return path, len(rows), min(lasts + 2.2, d["duration"] / sp)


def anchors(n):
    """卡片锚点：返回 [(卡片名, 秒, 是否命中关键字), ...]

    ★ 2026-10-26 扩展（董事长："就4张卡片怎么穿插整个视频，增加卡片"）：
      - 优先用 cards_v2.CARDS_V2（每集 12-13 张），退回旧 ANCH（4 张）
      - 锚点按台词顺序**自动排正序**并强制最小间隔，绝不允许两张卡叠在同一秒
      - 间隔超过 MAX_GAP 秒就自动补一张"接力卡"，保证全片无大段空窗
    """
    # ★ 用 ASR 细段（draft_N.json）而不是粗句（final_N.json）：
    #   draft 的分段跟着语音停顿走，时间戳更贴近真实口播；粗句会把两句话并成一条，导致时间前快后慢
    _dp = os.path.join(R, "draft_%d.json" % n)
    d = json.load(io.open(_dp if os.path.exists(_dp) else os.path.join(R, "final_%d.json" % n), encoding="utf-8"))
    spd = EPS[n]["speed"]
    cues = d["cues"]
    lasts = cues[-1]["end"] / spd
    MAX_GAP = 22.0          # 相邻两张卡最大间隔（秒）
    MIN_GAP = 3.2           # 两张卡最短间隔（秒），防重叠

    src = None
    try:
        from cards_v2 import CARDS_V2
        src = CARDS_V2.get(n)
    except Exception:
        src = None

    out = []
    if src:
        for item in src:
            name, kind, kw = item[0], item[1], item[2]
            t = None
            for c in cues:
                if kw and kw in c["text"]:
                    t = c["start"] / spd
                    break
            out.append([name, round(t, 2) if t is not None else None, t is not None])

        # 未命中的按前后已命中点线性插值，保证不扎堆、不留大洞
        for i, r in enumerate(out):
            if r[1] is None:
                prev = next((out[j][1] for j in range(i - 1, -1, -1) if out[j][1] is not None), 0.0)
                nxt = next((out[j][1] for j in range(i + 1, len(out)) if out[j][1] is not None), lasts)
                r[1] = round((prev + nxt) / 2.0, 2)

        # 排正序 + 强制最小间隔
        out.sort(key=lambda x: x[1])
        for i in range(1, len(out)):
            if out[i][1] < out[i - 1][1] + MIN_GAP:
                out[i][1] = round(out[i - 1][1] + MIN_GAP, 2)

        # 末卡不压片尾（留 2s），超出就往前挤
        for i in range(len(out) - 1, -1, -1):
            cap = lasts - 2.0 - (len(out) - 1 - i) * MIN_GAP
            if out[i][1] > cap:
                out[i][1] = round(max(0.3, cap), 2)

        return [(r[0], r[1], r[2]) for r in out]

    # ===== 旧口径兜底（4 张）=====
    for card, kw, fb in ANCH[n]:
        t = None
        for c in cues:
            if kw in c["text"]:
                t = c["start"] / spd
                break
        out.append((card, round(t if t is not None else fb, 2),
                    kw in "".join(c["text"] for c in cues)))
    return out


if __name__ == "__main__":
    for n in sorted(EPS):
        p, cnt, total = build_subs(n)
        print("ep%d %s 字幕 %d 条 成片预计 %.1fs (%.1f%%)" %
              (n, os.path.basename(p), cnt, total, 100.0))
        for card, t, found in anchors(n):
            print("    %-24s 锚点 %6.1fs %s" % (card, t, "" if found else "❌关键字没找到(用兜底)"))
