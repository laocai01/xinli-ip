# -*- coding: utf-8 -*-
"""第二批（11-16）卡片生成器 —— 每集一套配色/纹样/版式，骨架与品牌区照铁律不动
   输出: E:/心理咨询IP/04-卡片/batch2/<ep>/<card>.html
         E:/心理咨询IP/04-工程/batch2/card_texts.json  （compose 算停留字数用）
   版式: A 主卡(双行大字) / B 三行机制卡 / C 金句卡 / D 方法卡
"""
import os, io, json, base64

ROOT = "E:/心理咨询IP"
OUT = ROOT + "/04-卡片/batch2"
LOGO = ROOT + "/04-工程/overlay_new/logo_corner.png"
LOGO_B64 = base64.b64encode(open(LOGO, "rb").read()).decode()
FONT_B = "file:///E:/心理咨询IP/07-形象设计/fonts/fonts-main/DouyinSans/DouyinSansBold.ttf"
FONT_K = "file:///C:/Windows/Fonts/simkai.ttf"

HEAD = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@font-face{font-family:'DY';src:url('%(fb)s');font-weight:700}
@font-face{font-family:'DY';src:url('%(fb)s');font-weight:400}
@font-face{font-family:'KAI';src:url('%(fk)s')}
*{margin:0;padding:0;box-sizing:border-box}
/* ★ 董事长2026-11-04：卡片文字不许顶到右边界，长句强制换行并自动缩字号 */
.h1{max-width:100%%;overflow-wrap:anywhere;word-break:break-word;text-align:center}
html,body{width:1080px;height:1920px;overflow:hidden}
body{position:relative;font-family:'DY','Microsoft YaHei',sans-serif;background:#fff}
[data-anim]{opacity:0}
.h1{font-weight:700;letter-spacing:2px}
</style></head>
""" % dict(fb=FONT_B, fk=FONT_K)

GRAIN = ("<div style=\"position:absolute;inset:0;pointer-events:none;z-index:9;background-image:url("
         "&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E"
         "%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3'/%3E%3C/filter%3E"
         "%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E&quot;);"
         "background-size:220px 220px;mix-blend-mode:multiply;opacity:.05\"></div>")


def brand():
    return ("<div data-anim=\"in\" data-delay=\"0.10\" data-dur=\"0.70\" style=\"position:absolute;left:0;right:0;"
            "top:70px;display:flex;align-items:flex-end;justify-content:center;gap:18px;z-index:8\">\n"
            "  <img src=\"data:image/png;base64," + LOGO_B64 + "\" style=\"width:132px;height:132px;display:block\">\n"
            "  <div style=\"font-family:'KAI','KaiTi','STKaiti',serif;font-weight:700;font-size:44px;"
            "line-height:0.92;color:#4B3026;letter-spacing:3px;padding-bottom:2px\">老蔡说</div>\n"
            "</div>")


def brandline(color):
    return ("<div data-anim=\"grow\" data-delay=\"0.32\" data-dur=\"0.70\" style=\"position:absolute;left:50%;"
            "margin-left:-210px;top:322px;width:420px;height:7px;border-radius:4px;background:" + color +
            ";z-index:8\"></div>")


def corners(color):
    """四角「影视取景框」细角标"""
    c = []
    for x, y, bx, by in ((56, 56, "left", "top"), (1080 - 56, 56, "right", "top"),
                         (56, 1920 - 56, "left", "bottom"), (1080 - 56, 1920 - 56, "right", "bottom")):
        hx = "left:%dpx" % x if bx == "left" else "right:%dpx" % (1080 - x)
        hy = "top:%dpx" % y if by == "top" else "bottom:%dpx" % (1920 - y)
        c.append("<div style=\"position:absolute;%s;%s;width:54px;height:54px;z-index:7;"
                 "border-%s:%s;border-%s:%s\"></div>"
                 % (hx, hy, "top" if by == "top" else "bottom", "2px solid %s" % color,
                    "left" if bx == "left" else "right", "2px solid %s" % color))
    return "".join(c)


def sig(color, dot):
    return ("<div data-anim=\"in\" data-delay=\"0.40\" data-dur=\"0.70\" style=\"position:absolute;left:0;right:0;"
            "bottom:300px;text-align:center;z-index:8\">\n"
            "  <div style=\"font-size:30px;color:%s;letter-spacing:3px;font-weight:400\">"
            "正在学心理学的普通人<span style=\"display:inline-block;width:10px;height:10px;border-radius:50%%;"
            "background:%s;margin:0 16px 4px 16px\"></span>只说心事，不说教</div>\n</div>" % (color, dot))


def bg(t):
    return ("<div style=\"position:absolute;inset:0;background:linear-gradient(%s)\"></div>"
            "<div style=\"position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;border-radius:50%%;"
            "background:radial-gradient(circle,%s,transparent %d%%);filter:blur(%dpx)\"></div>"
            "<div style=\"position:absolute;right:%dpx;bottom:%dpx;width:%dpx;height:%dpx;border-radius:50%%;"
            "background:radial-gradient(circle,%s,transparent %d%%);filter:blur(%dpx)\"></div>"
            "<div style=\"position:absolute;inset:0;background:radial-gradient(ellipse 62%% 44%% at 50%% 46%%,"
            "rgba(255,255,255,%s),transparent 74%%)\"></div>"
            % (t["grad"], t["g1x"], t["g1y"], t["g1s"], t["g1s"], t["g1c"], t["g1t"], t["g1b"],
               t["g2x"], t["g2y"], t["g2s"], t["g2s"], t["g2c"], t["g2t"], t["g2b"], t["veil"]))


def motif(t):
    """每集不同纹样（细、低透明度，不抢字）"""
    k = t["motif"]
    c = t["motif_color"]
    if k == "grid":
        lines = "".join("<div style=\"position:absolute;left:0;right:0;top:%dpx;height:1px;background:%s\"></div>" % (y, c)
                        for y in range(420, 1620, 96))
        return "<div style=\"position:absolute;inset:0;z-index:1\">%s</div>" % lines
    if k == "arc":
        return ("<div style=\"position:absolute;left:-260px;top:240px;width:1600px;height:1600px;border-radius:50%%;"
                "border:1px solid %s;z-index:1\"></div>"
                "<div style=\"position:absolute;left:-140px;top:360px;width:1360px;height:1360px;border-radius:50%%;"
                "border:1px solid %s;z-index:1\"></div>" % (c, c))
    if k == "vlines":
        return ("<div style=\"position:absolute;left:150px;top:400px;width:1px;height:1160px;background:%s;z-index:1\"></div>"
                "<div style=\"position:absolute;right:150px;top:400px;width:1px;height:1160px;background:%s;z-index:1\"></div>"
                % (c, c))
    if k == "beam":
        return ("<div style=\"position:absolute;left:-200px;top:520px;width:1500px;height:260px;z-index:1;"
                "background:linear-gradient(100deg,transparent,%s 45%%,transparent);transform:rotate(-14deg);"
                "filter:blur(6px)\"></div>" % c)
    if k == "dots":
        return ("<div style=\"position:absolute;inset:0;z-index:1;background-image:radial-gradient(%s 1.6px,transparent 1.7px);"
                "background-size:44px 44px;opacity:.75\"></div>" % c)
    if k == "ring":
        return ("<div style=\"position:absolute;left:50%%;top:900px;width:1240px;height:1240px;margin-left:-620px;"
                "margin-top:-620px;border-radius:50%%;border:26px solid %s;z-index:1\"></div>"
                "<div style=\"position:absolute;left:50%%;top:900px;width:900px;height:900px;margin-left:-450px;"
                "margin-top:-450px;border-radius:50%%;border:1px solid %s;z-index:1\"></div>" % (c, c))
    return ""


# ---------------- 四种版式 ----------------

def fit_fs(text, base, maxw=880.0, ratio=0.94):
    """★ 按可用宽度自动缩字号：中文按 base 宽逐字计，超宽则等比缩。
    可用宽度 = 1080 - 左右各100px 内边距 = 880px"""
    if not text:
        return base
    n = max(len(t) for t in str(text).split("\n"))
    need = n * base * ratio
    if need <= maxw:
        return base
    return max(64, int(base * maxw / need))


ANIM_POOL = ["up", "left", "scale", "rise", "blur", "right", "rot", "wipe", "in"]

# ★ 每张卡一套不同的入场组合（董事长 2026-11-04：每张卡动态必须不同）
ANIM_SETS = {
    0:  ("wipe",  "up",    "scale"),
    1:  ("scale", "left",  "in"),
    2:  ("left",  "right", "up"),
    3:  ("blur",  "up",    "rise"),
    4:  ("rise",  "in",    "scale"),
    5:  ("rot",   "left",  "up"),
    6:  ("right", "scale", "in"),
    7:  ("up",    "blur",  "left"),
    8:  ("scale", "rise",  "wipe"),
    9:  ("wipe",  "rot",   "up"),
    10: ("in",    "right", "scale"),
    11: ("blur",  "left",  "rot"),
}


def anim_of(idx, slot=0):
    """按卡片序号取该卡的第 slot 个动效，保证逐张不同。"""
    st = ANIM_SETS.get(idx % len(ANIM_SETS), ANIM_SETS[0])
    return st[slot % len(st)]


def card_main(t, l1, l2, sub, idx=0):
    """A 主卡：双行大字 + 细分割 + 辅助句（居中箴言式）"""
    a0, a1, a2 = anim_of(idx, 0), anim_of(idx, 1), anim_of(idx, 2)
    tpl = (
        '<div style="position:absolute;left:0;right:0;top:360px;bottom:330px;padding:0 100px;text-align:center;z-index:5;display:flex;flex-direction:column;justify-content:center">\n'
        '  <div data-anim="{a0}" data-delay="0.50" data-dur="0.70" class="h1" style="font-size:{f1}px;line-height:1.26;color:{ink};margin-bottom:6px">{l1}</div>\n'
        '  <div data-anim="{a1}" data-delay="0.78" data-dur="0.70" class="h1" style="font-size:{f1s}px;line-height:1.26;color:{ink}">{l2}</div>\n'
        '  <div data-anim="grow2" data-delay="1.10" data-dur="0.70" style="width:120px;height:3px;background:{rule};margin:56px auto 52px"></div>\n'
        '  <div data-anim="{a2}" data-delay="1.30" data-dur="0.70" style="font-size:48px;line-height:1.75;color:{ink2};font-weight:400;letter-spacing:1px">{sub}</div>\n</div>'
    )
    return tpl.format(a0=a0, a1=a1, a2=a2, f1=fit_fs(l1, t["f1"]), f1s=fit_fs(l2, t["f1s"]),
                      ink=t["ink"], ink2=t["ink2"], rule=t["rule"], l1=l1, l2=l2, sub=sub)


def card_three(t, lead, items, tail=None, idx=0):
    """B 三行机制卡：引导语 + 三行（序号 + 文字），左对齐"""
    a0, a1 = anim_of(idx, 0), anim_of(idx, 1)
    rows = []
    for i, s in enumerate(items):
        rows.append(
            '<div data-anim="{a1}" data-delay="{d:.2f}" data-dur="0.70" style="display:flex;align-items:baseline;margin-bottom:44px">\n'
            '  <div style="font-size:34px;font-weight:700;color:{ac};width:78px;letter-spacing:1px;opacity:.85">0{n}</div>\n'
            '  <div style="font-size:{fs}px;line-height:1.5;color:{ink};font-weight:700;flex:1">{txt}</div>\n</div>'
            .format(a1=a1, d=1.05 + i * 0.34, ac=t["accent"], n=i + 1,
                    fs=fit_fs(s, t["f3"], 780), ink=t["ink"], txt=s))
    tailh = ""
    if tail:
        tailh = ('<div data-anim="{a1}" data-delay="{d:.2f}" data-dur="0.70" style="margin-top:24px;font-size:44px;'
                 'line-height:1.7;color:{c};font-weight:400;letter-spacing:1px">{t}</div>'
                 .format(a1=a1, d=1.05 + len(items) * 0.34, c=t["ink2"], t=tail))
    return (
        '<div style="position:absolute;left:110px;right:110px;top:360px;bottom:330px;z-index:5;display:flex;flex-direction:column;justify-content:center">\n'
        '  <div data-anim="{a0}" data-delay="0.40" data-dur="0.70" style="font-size:40px;letter-spacing:8px;color:{ac};font-weight:700;margin-bottom:{mb}px">{lead}</div>\n'
        '  <div data-anim="grow2" data-delay="0.60" data-dur="0.70" style="width:96px;height:3px;background:{rule};margin:0 0 52px"></div>\n{rows}{tailh}\n</div>'
        .format(a0=a0, ac=t["accent"], mb=(54 if not tail else 46), lead=lead,
                rule=t["rule"], rows="".join(rows), tailh=tailh))


def card_quote(t, lead, big, idx=0):
    """C 金句卡：上行小字 + 下行含重点大字（字号三级）"""
    a0, a1, a2 = anim_of(idx, 0), anim_of(idx, 1), anim_of(idx, 2)
    return (
        '<div style="position:absolute;left:0;right:0;top:360px;bottom:330px;padding:0 96px;text-align:center;z-index:5;display:flex;flex-direction:column;justify-content:center">\n'
        '  <div data-anim="{a0}" data-delay="0.40" data-dur="0.70" style="font-size:52px;letter-spacing:6px;color:{c1};font-weight:700;opacity:.9;margin-bottom:26px">{lead}</div>\n'
        '  <div data-anim="{a1}" data-delay="0.74" data-dur="0.70" class="h1" style="font-size:{fs}px;line-height:1.34;color:{ac}">{big}</div>\n'
        '  <div data-anim="grow2" data-delay="1.28" data-dur="0.70" style="width:150px;height:4px;background:{rule};margin:58px auto 0"></div>\n</div>'
        .format(a0=a0, a1=a1, c1=t["ink2"], lead=lead, fs=fit_fs(big, t["f2"], 860),
                ac=t["accent"], big=big, rule=t["rule"]))


def card_steps(t, lead, items, idx=0):
    """D 方法卡：标题 + 三条可抄走的话（序号大字 + 内容）"""
    a0, a1 = anim_of(idx, 0), anim_of(idx, 1)
    rows = []
    for i, s in enumerate(items):
        rows.append(
            '<div data-anim="{a1}" data-delay="{d:.2f}" data-dur="0.70" style="position:relative;padding-left:118px;margin-bottom:52px">\n'
            '  <div style="position:absolute;left:0;top:-6px;font-size:76px;font-weight:700;color:{ac};opacity:.28;letter-spacing:-2px">{n}</div>\n'
            '  <div style="font-size:{fs}px;line-height:1.55;color:{ink};font-weight:700">{txt}</div>\n</div>'
            .format(a1=a1, d=1.00 + i * 0.42, ac=t["accent"], n=i + 1,
                    fs=fit_fs(s, t["f4"], 780), ink=t["ink"], txt=s))
    return (
        '<div style="position:absolute;left:104px;right:104px;top:360px;bottom:330px;z-index:5;display:flex;flex-direction:column;justify-content:center">\n'
        '  <div data-anim="{a0}" data-delay="0.36" data-dur="0.70" style="font-size:44px;letter-spacing:4px;color:{ac};font-weight:700;margin-bottom:16px">{lead}</div>\n'
        '  <div data-anim="grow2" data-delay="0.60" data-dur="0.70" style="width:110px;height:4px;background:{rule};margin:0 0 62px"></div>\n{rows}\n</div>'
        .format(a0=a0, ac=t["accent"], lead=lead, rule=t["rule"], rows="".join(rows)))


# ---------------- 主题（每集一套） ----------------
THEMES = {
 "11": dict(grad="170deg,#fdfaf5 0%,#f6ecdd 46%,#ead9c4 100%",
            g1x=-200, g1y=-180, g1s=1080, g1c="rgba(255,186,110,.45)", g1t=68, g1b=30,
            g2x=-200, g2y=-120, g2s=1000, g2c="rgba(120,150,200,.40)", g2t=68, g2b=32, veil=".56",
            motif="grid", motif_color="rgba(120,90,60,.07)",
            ink="#33291F", ink2="#7A6450", accent="#123A5C", rule="rgba(200,140,60,.62)",
            f1=124, f1s=118, f2=112, f3=58, f4=56),
 "12": dict(grad="165deg,#f7f8fa 0%,#eceff4 50%,#dfe4ec 100%",
            g1x=-180, g1y=-160, g1s=1040, g1c="rgba(255,170,120,.40)", g1t=66, g1b=30,
            g2x=-200, g2y=-140, g2s=980, g2c="rgba(110,140,190,.45)", g2t=70, g2b=32, veil=".58",
            motif="arc", motif_color="rgba(60,80,120,.10)",
            ink="#2B3038", ink2="#6B7480", accent="#B4411A", rule="rgba(180,65,26,.55)",
            f1=126, f1s=120, f2=112, f3=58, f4=56),
 "13": dict(grad="172deg,#fbf8f3 0%,#f1eae0 48%,#e2d8ca 100%",
            g1x=-170, g1y=-150, g1s=1000, g1c="rgba(225,195,150,.48)", g1t=68, g1b=28,
            g2x=-190, g2y=-110, g2s=960, g2c="rgba(150,165,150,.42)", g2t=68, g2b=30, veil=".55",
            motif="vlines", motif_color="rgba(90,70,50,.12)",
            ink="#322A21", ink2="#786A57", accent="#0C4B42", rule="rgba(200,140,60,.58)",
            f1=124, f1s=118, f2=110, f3=58, f4=56),
 "14": dict(grad="168deg,#fdf8f2 0%,#f7eade 50%,#ecd8c6 100%",
            g1x=-200, g1y=-170, g1s=1060, g1c="rgba(255,175,120,.50)", g1t=70, g1b=30,
            g2x=-180, g2y=-130, g2s=980, g2c="rgba(200,150,120,.42)", g2t=66, g2b=30, veil=".54",
            motif="beam", motif_color="rgba(255,255,255,.55)",
            ink="#3A2A1C", ink2="#82604A", accent="#8C3B12", rule="rgba(200,120,60,.55)",
            f1=124, f1s=118, f2=110, f3=58, f4=56),
 "15": dict(grad="174deg,#f8faf9 0%,#eaf0ee 48%,#dbe5e2 100%",
            g1x=-180, g1y=-160, g1s=1020, g1c="rgba(150,215,200,.40)", g1t=70, g1b=30,
            g2x=-200, g2y=-120, g2s=960, g2c="rgba(190,175,140,.42)", g2t=66, g2b=30, veil=".58",
            motif="dots", motif_color="rgba(90,110,100,.10)",
            ink="#2A312D", ink2="#69756E", accent="#5A2E10", rule="rgba(90,46,16,.42)",
            f1=124, f1s=118, f2=110, f3=58, f4=56),
 "16": dict(grad="166deg,#fdf9f2 0%,#f6eeda 46%,#e9dcc0 100%",
            g1x=-190, g1y=-170, g1s=1080, g1c="rgba(255,200,120,.50)", g1t=70, g1b=30,
            g2x=-200, g2y=-140, g2s=1000, g2c="rgba(160,140,200,.38)", g2t=68, g2b=32, veil=".56",
            motif="ring", motif_color="rgba(120,95,60,.09)",
            ink="#352B1E", ink2="#7C6A50", accent="#4A1D6E", rule="rgba(200,160,70,.55)",
            f1=122, f1s=116, f2=108, f3=58, f4=56),
}

# ---------------- 卡片文案（按提词稿语义，每集 4 张） ----------------
CARDS = {
 "11": [
  ("01_主_你越想跟他说开", "main", ("你越想跟他", "把话说开", "不是他不会说，是你第一句问错了")),
  ("02_副_不是关心是查岗", "three", ("这三句话，在他耳朵里", ["你今天到底怎么了", "你又怎么了", "你不说我怎么知道"], "不是关心。是查岗。")),
  ("03_金句_不用挨批的机会", "quote", ("他不是没话说", "是在等一个\n不用挨批的机会")),
  ("04_方法_三句递话", "steps", ("记住这三句，今天是开口还是闭嘴，就看它", ["我这两天有点想你", "我不问你，我就是有点担心你", "你哪天想说，随时跟我说，我不催"])),
 ],
 "12": [
  ("01_主_你不是不想歇", "main", ("你不是不想歇", "你是不敢歇", "你一坐下来，心里就开始算账")),
  ("02_副_歇着也在过账", "three", ("你歇着的每一分钟", ["那事儿还没弄完", "明天那个电话得打", "孩子的钱还没转"], "不是懒。是不敢闲。")),
  ("03_金句_你是在证明自己", "quote", ("你不是在忙事", "你是在\n证明自己")),
  ("04_方法_两件小事", "steps", ("不用一步到位，就做两件小事", ["把\"我应该\"，改成\"我可以\"", "每天留五分钟，什么都不干", "先歇着，慌它自己会走"])),
 ],
 "13": [
  ("01_主_不是不爱了", "main", ("你们不是不爱了", "是不再应声了", "变淡不是从吵架开始，是从\"嗯\"开始")),
  ("02_副_通知和收到", "three", ("你们今天说的话", ["\"吃饭了。\"\"嗯。\"", "\"水烧好了。\"\"哦。\"", "\"几点回来。\"\"再说。\""], "一句通知，加一句收到。")),
  ("03_金句_没被接住", "quote", ("感情不是被时间磨掉的", "是被一次次\n\"没被接住\"磨掉的")),
  ("04_方法_两件事", "steps", ("今天就能做，两件事", ["她说话的时候，你放下手机看她一眼", "每天有六秒钟，你是属于她的", "不用说\"我爱你\"，说一句\"我在呢\""])),
 ],
 "14": [
  ("01_主_说成了考核", "main", ("你说了半天", "他一句没听进去", "因为你把\"关心\"，说成了\"考核\"")),
  ("02_副_三句问进度", "three", ("你打电话，是不是就问这三句", ["吃饭了没有", "忙不忙", "钱够不够花"], "句句是真心。句句是问进度。")),
  ("03_金句_两个字的天花板", "quote", ("你问的都是", "答案只有\n两个字的问题")),
  ("04_方法_换成递话头", "steps", ("把\"问进度\"，换成\"递话头\"", ["我今天煮了个汤，盐放多了", "我看见你瘦了，我心里不踏实", "\"这么难，你是怎么撑到现在的？\""])),
 ],
 "15": [
  ("01_主_怕成负担", "main", ("你不是不想他", "你是怕变成负担", "你把\"我想你\"，说成了\"你忙你的\"")),
  ("02_副_把门关上", "three", ("你有没有干过这些事", ["\"你忙吧，没啥事。\"", "\"没事没事，老毛病了。\"", "\"不用不用，我够花。\""], "这叫把门，一点一点关上。")),
  ("03_金句_没人等着你", "quote", ("人不怕累", "怕的是\n没有人等着你")),
  ("04_方法_找个小口子", "steps", ("给自己找一个\"别人等着你\"的口子", ["早上给老伙计打个电话，叫他起床", "帮邻居接一下孙子", "社区的几盆花，你负责浇"])),
 ],
 "16": [
  ("01_主_都留给了别人", "main", ("你把最好的话", "都留给了别人", "一句都没留给你自己")),
  ("02_副_对谁都宽", "three", ("你有没有在心里骂过自己", ["孩子考上大学，你说\"应该的\"", "孙子满月，你说\"都是人家的功劳\"", "别人一句难听的话，你记三年"], "你对谁都宽。就对自己狠。")),
  ("03_金句_最该说辛苦了", "quote", ("这辈子最该听一句\"辛苦了\"的人", "是你自己")),
  ("04_方法_睡前五分钟", "steps", ("睡前五分钟，跟二十岁的自己说三句", ["这些年，你辛苦了", "有一件事，你当年做得没错", "后面的路，我替你走完了"])),
 ],
}


EP2N = {"11": 1, "12": 2, "13": 3, "14": 4, "15": 5, "16": 6}


def build(ep):
    t = THEMES[ep]
    d = os.path.join(OUT, str(EP2N[ep]))
    os.makedirs(d, exist_ok=True)
    texts = {}
    for name, kind, args in CARDS[ep]:
        body = brand() + brandline(t["rule"]) + bg(t) + motif(t) + corners(t["accent"])
        if kind == "main":
            body += card_main(t, *args); up = [args[0], args[1], args[2]]
        elif kind == "three":
            body += card_three(t, *args); up = [args[0]] + list(args[1]) + ([args[2]] if args[2] else [])
        elif kind == "quote":
            body += card_quote(t, *args); up = [args[0], args[1].replace("\n", "")]
        elif kind == "steps":
            body += card_steps(t, *args); up = [args[0]] + list(args[1])
        body += sig(t["ink2"], t["accent"]) + GRAIN
        html = HEAD + "</head><body>\n" + body + "\n</body></html>"
        io.open(os.path.join(d, name + ".html"), "w", encoding="utf-8").write(html)
        texts["%d|%s.html" % (EP2N[ep], name)] = up
    return texts


if __name__ == "__main__":
    import sys
    eps = sys.argv[1:] or sorted(CARDS)
    allt = {}
    if os.path.exists("E:/心理咨询IP/04-工程/batch2/card_texts.json"):
        allt = json.load(io.open("E:/心理咨询IP/04-工程/batch2/card_texts.json", encoding="utf-8"))
    for ep in eps:
        allt.update(build(ep))
        print("built ep %s: %d cards" % (ep, len(CARDS[ep])))
    json.dump(allt, io.open("E:/心理咨询IP/04-工程/batch2/card_texts.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
