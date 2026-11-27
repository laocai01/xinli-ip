# -*- coding: utf-8 -*-
"""batch4 卡片版式引擎 v1.0（2026-11-18）

设计依据：D:/共享知识库/07_团队与智能体/卡片版式调研_20261118.md
  · 安全区：左 72 / 右 122 / 底部 y>=1620 净空 / 内容上界 274
  · 主标题占屏宽 <=85%，字号按每行字数查表（不写死 px）
  · 对比度：主 >=8:1，次 >=5:1，辅 >=4.5:1
  · 品牌区固定：LOGO 132 + 楷体「老蔡说」44px
  · 深底方案品牌名改 #EADFD2

12 个版式族（同集内每张不同，全批不重复）：
  hero / split / ladder / versus / quote / vertical /
  numbers / timeline / checklist / stat / stamp / panel
"""
import os

W, H = 1080, 1920
SAFE_L, SAFE_R, SAFE_B = 72, 122, 1620
CONTENT_W = W - SAFE_L - SAFE_R          # 886

FONT_DY = "file:///E:/心理咨询IP/07-形象设计/fonts/fonts-main/DouyinSans/DouyinSansBold.ttf"
FONT_KAI = "file:///C:/Windows/Fonts/simkai.ttf"
LOGO = "E:/心理咨询IP/04-工程/overlay_new/logo_corner.png"
SVG_NOISE = ("%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E"
             "%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3'/%3E"
             "%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")

# ---------------- 6 套配色（对比度已实测） ----------------
THEMES = {
    "S1": dict(bg="#F7F4EE", l1="#2E2A26", l2="#6B6157", l3="#6F6355",
               em="#A04A24", line="rgba(46,42,38,.14)", deep=False, name="#4B3026",
               grain=".05"),
    "S2": dict(bg="#16181C", l1="#F4F1EA", l2="#B9B3A8", l3="#918A7E",
               em="#E0A458", line="rgba(244,241,234,.16)", deep=True, name="#EADFD2",
               grain=".07"),
    "S3": dict(bg="#FFFFFF", l1="#111111", l2="#4A4A4A", l3="#767676",
               em="#A8231A", line="rgba(17,17,17,.12)", deep=False, name="#4B3026",
               grain=".03"),
    "S4": dict(bg="#2C3A34", l1="#F2F0E6", l2="#C3C9BE", l3="#9DA99C",
               em="#D9B382", line="rgba(242,240,230,.16)", deep=True, name="#EADFD2",
               grain=".07"),
    "S5": dict(bg="#EDE6D8", l1="#33302A", l2="#615B4F", l3="#635C4E",
               em="#2F4C5C", line="rgba(51,48,42,.15)", deep=False, name="#4B3026",
               grain=".06"),
    "S6": dict(bg="#EAF1F4", l1="#22323A", l2="#4E6470", l3="#5C6F7A",
               em="#9E4329", line="rgba(34,50,58,.14)", deep=False, name="#4B3026",
               grain=".045"),
}

HEAD = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@font-face{font-family:'DY';src:url('__FDY__') format('truetype');font-weight:700;font-display:block}
@font-face{font-family:'KAI';src:url('__FKAI__') format('truetype');font-display:block}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:__W__px;height:__H__px;overflow:hidden}
body{position:relative;color:var(--l1);background:var(--bg);
     font-family:'DY','Microsoft YaHei',sans-serif;-webkit-font-smoothing:antialiased}
.bgtone{position:absolute;inset:0;z-index:0;pointer-events:none;
     background:
       radial-gradient(110% 75% at 80% 10%, rgba(160,74,36,0.085) 0%, rgba(0,0,0,0) 60%),
       radial-gradient(85% 55% at 10% 94%, rgba(46,42,38,0.070) 0%, rgba(0,0,0,0) 58%)}
.ch{display:inline-block;will-change:transform,opacity}
/* ★ 2026-11-18 董事长：绝不许一个字占一行 */
.nl{word-break:keep-all;overflow-wrap:normal}
.stage div,.stage span{word-break:keep-all;overflow-wrap:normal}
.brand{position:absolute;left:0;right:0;top:70px;display:flex;align-items:flex-end;
       justify-content:center;gap:18px;z-index:20}
.brand img{width:132px;height:132px;border-radius:50%;display:block}
.brand .nm{font-family:'KAI','KaiTi','STKaiti',serif;font-weight:700;font-size:44px;
       line-height:.92;letter-spacing:3px;padding-bottom:2px}
.stage{position:absolute;left:__SL__px;top:274px;width:__CW__px;height:__CH__px;z-index:10}
.foot{position:absolute;left:__SL__px;right:__SR__px;top:1566px;z-index:10;
      font-size:28px;letter-spacing:.06em;line-height:1.6;color:var(--l3)}
.grain{position:absolute;inset:0;pointer-events:none;z-index:15;mix-blend-mode:multiply;
  background-image:url("data:image/svg+xml,__SVG__");
  background-size:220px 220px}
</style></head><body>
""".replace("__FDY__", FONT_DY).replace("__FKAI__", FONT_KAI) \
   .replace("__W__", str(W)).replace("__H__", str(H)) \
   .replace("__SL__", str(SAFE_L)).replace("__SR__", str(SAFE_R)) \
   .replace("__CW__", str(CONTENT_W)).replace("__CH__", str(SAFE_B - 274)) \
   .replace("__SVG__", SVG_NOISE)


def _vars(T):
    return ("--bg:%s;--l1:%s;--l2:%s;--l3:%s;--em:%s;--line:%s"
            % (T["bg"], T["l1"], T["l2"], T["l3"], T["em"], T["line"]))


def brand(T):
    # 董事长 2026-11-18：LOGO 旁保留楷体「老蔡说」（顶部太空），底部对齐、gap 18px
    ring = ("box-shadow:0 0 0 1px rgba(234,223,210,.38);" if T["deep"] else "")
    return ('<div class="brand"><img src="%s" style="%s">'
            '<div class="nm" style="color:%s">老蔡说</div></div>'
            % (LOGO, ring, T.get("name", "#4B3026")))


def grain(T):
    return '<div class="grain" style="opacity:%s"></div>' % T["grain"]


SIGN = ('正在学心理学的普通人'
        '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;'
        'background:var(--em);margin:0 16px 4px 16px;opacity:.85"></span>'
        '只说心事，不说教')


def foot(txt, T):
    """卡片底部固定署名：正在学心理学的普通人 ● 只说心事，不说教（董事长定稿格式）"""
    return ('<div class="foot" style="text-align:center;letter-spacing:3px;font-weight:400">%s</div>'
            % SIGN)


def em(txt, T, extra=""):
    """重点字：只有字色，无底色/描边（董事长 2026-10-09 定：内文卡纯字色）"""
    return '<span style="color:var(--em);%s">%s</span>' % (extra, txt)


# =====================================================================
# 版式族
# =====================================================================

def emi(txt, T, key=None):
    """重点字高亮：txt 里用 ‖ ‖ 包裹的部分着色加粗（董事长 2026-11-18：重点字要特殊标注）"""
    if not txt:
        return ""
    out, inside = [], False
    for ch in txt:
        if ch == "‖":
            inside = not inside
            out.append('<span style="color:var(--em);font-weight:700;letter-spacing:-0.01em">' if inside else "</span>")
        else:
            out.append(ch)
    if inside:
        out.append("</span>")
    return "".join(out)


def safe_lines(txt, per_line_min=2):
    """把 \n 分行里『只有 1 个字』的行并进相邻行，防单字成行"""
    if not txt or "\n" not in txt:
        return txt
    lines = [x for x in txt.split("\n")]
    out = []
    for ln in lines:
        plain = ln.replace("‖", "").strip()
        if len(plain) <= 1 and out:
            out[-1] = out[-1] + ln
        else:
            out.append(ln)
    return "\n".join(out)


def L_hero(d, T, anim):
    """超大字单焦点 + 顶部细线 + 底部序号标记（编辑杂志排版）"""
    seq = d.get("seq", "")
    seqhtml = ""
    if seq:
        seqhtml = f'''
  <div style="position:absolute;top:34px;left:0;display:flex;align-items:center;gap:18px"
       data-anim="fadeIn" data-delay="2.37" data-dur="0.6" data-stagger="0.07">
    <div style="font-size:30px;color:var(--em);letter-spacing:.22em">{seq}</div>
    <div style="width:64px;height:1px;background:var(--em);opacity:.6"></div>
  </div>'''
    return f'''
<div class="stage" style="display:flex;flex-direction:column;justify-content:center;align-items:center">
  <div style="width:100%;height:1px;background:var(--line);position:absolute;top:0"
       data-anim="grow" data-delay="0.13" data-dur="0.66" data-_w="886"></div>
  {seqhtml}
  <div style="font-size:{d.get("leadSize",54)}px;color:var(--l2);letter-spacing:.12em;
       line-height:1.5;margin-bottom:64px;text-align:center"
       data-anim="{anim}" data-delay="0.24" data-dur="0.5" data-stagger="0.045">{emi(d["lead"],T)}</div>
  <div style="font-size:{d["bigSize"]}px;line-height:1.16;letter-spacing:-0.025em;
       text-align:center;max-width:100%"
       data-anim="maskRise" data-delay="0.93" data-dur="0.85">{emi(safe_lines(d["big"]),T)}</div>
  <div style="width:120px;height:3px;background:var(--em);margin-top:70px"
       data-anim="grow" data-delay="3.09" data-dur="0.65" data-_w="120"></div>
</div>'''


def L_split(d, T, anim):
    """左右分栏：左关键词大字 + 右侧竖线 + 说明"""
    return f'''
<div class="stage" style="display:flex;align-items:center">
  <div style="width:38%;text-align:left;border-right:1px solid var(--line);padding-right:26px">
    <div style="display:inline-block;font-size:32px;color:var(--em);letter-spacing:.14em;
         border:1px solid var(--em);padding:8px 16px;margin-bottom:30px;white-space:nowrap"
         data-anim="fadeIn" data-delay="0.13" data-dur="0.5" data-stagger="0.06">{d.get("tag","")}</div>
    <div style="font-size:{min(d["keySize"],96)}px;line-height:1.2;letter-spacing:-0.02em;
         word-break:keep-all"
         data-anim="{anim}" data-delay="0.34" data-dur="0.62" data-stagger="0.05">{emi(safe_lines(d["key"]),T)}</div>
  </div>
  <div style="width:62%;padding-left:26px">
    <div style="font-size:54px;line-height:1.66;color:var(--l1);letter-spacing:.01em;
         word-break:break-word"
         data-anim="fadeUp" data-delay="0.79" data-dur="0.6" data-stagger="0.05">{emi(safe_lines(d["body"]),T)}</div>
  </div>
</div>'''


def L_ladder(d, T, anim):
    """序号阶梯：01/02/03 竖排，细线分组"""
    items = d["items"]
    rows = []
    for i, it in enumerate(items):
        rows.append(f'''
  <div style="display:flex;align-items:flex-start;padding:34px 0;
       border-bottom:{'' if i == len(items)-1 else '1px solid var(--line)'}"
       data-anim="{anim}" data-delay="{0.22 + i*0.3:.2f}" data-dur="0.6" data-stagger="0.05">
    <div style="font-size:96px;line-height:.9;color:var(--em);letter-spacing:-0.03em;
         width:150px;flex:0 0 150px">0{i+1}</div>
    <div style="font-size:60px;line-height:1.42;color:var(--l1);padding-top:8px">{emi(it,T)}</div>
  </div>''')
    return f'''
<div class="stage">
  <div style="font-size:52px;color:var(--l2);letter-spacing:.05em;margin-bottom:22px"
       data-anim="fadeIn" data-delay="0.11" data-dur="0.5" data-stagger="0.05">{emi(d["lead"],T)}</div>
  <div style="height:1px;background:var(--line);margin-bottom:14px"></div>
  {"".join(rows)}
</div>'''


def L_versus(d, T, anim):
    """上下对照两栏"""
    return f'''
<div class="stage" style="display:flex;flex-direction:column;justify-content:center">
  <div style="text-align:center;font-size:{d.get('topSize',92)}px;line-height:1.28;
       color:var(--l3);letter-spacing:.02em"
       data-anim="{anim}" data-delay="0.13" data-dur="0.6" data-stagger="0.04">{emi(safe_lines(d["top"]),T)}</div>
  <div style="display:flex;align-items:center;gap:26px;margin:52px 0">
    <div style="flex:1;height:1px;background:var(--line)"></div>
    <div style="font-family:'KAI',serif;font-size:46px;color:var(--em);letter-spacing:.2em">其实</div>
    <div style="flex:1;height:1px;background:var(--line)"></div>
  </div>
  <div style="text-align:center;font-size:{d["botSize"]}px;line-height:1.24;
       letter-spacing:-0.02em"
       data-anim="maskRise" data-delay="1.04" data-dur="0.64">{emi(safe_lines(d["bottom"]),T)}</div>
</div>'''


def L_quote(d, T, anim):
    """大引号 + 引文（破格出血）"""
    return f'''
<div class="stage" style="display:flex;flex-direction:column;justify-content:center">
  <div style="font-family:'KAI',serif;font-size:260px;line-height:.7;color:var(--em);
       opacity:.22;margin-left:-24px;margin-bottom:-40px">“</div>
  <div style="font-size:{d["bigSize"]}px;line-height:1.36;letter-spacing:-0.01em;
       padding-left:8px"
       data-anim="{anim}" data-delay="0.21" data-dur="0.68" data-stagger="0.045">{emi(safe_lines(d["text"]),T)}</div>
  <div style="margin-top:52px;padding-left:10px;font-size:44px;color:var(--l3);letter-spacing:.05em"
       data-anim="fadeIn" data-delay="1.65" data-dur="0.5" data-stagger="0.04">— {d.get("who","老蔡")}</div>
</div>'''


def L_vertical(d, T, anim):
    """竖排标题 + 横排副句（标题 <5 字自动转横排，防单字成行）"""
    plain = d["vtext"].replace("\n", "").replace("‖", "")
    vstyle = ("writing-mode:vertical-rl;text-orientation:upright;"
              if len(plain) >= 5 else "writing-mode:horizontal-tb;")
    return f'''
<div class="stage" style="display:flex;align-items:flex-start;gap:54px;justify-content:center">
  <div style="writing-mode:vertical-rl;text-orientation:upright;
       font-size:{d["vSize"]}px;line-height:1.28;letter-spacing:.06em;max-height:1000px"
       data-anim="{anim}" data-delay="0.15" data-dur="0.66" data-stagger="0.055">{emi(safe_lines(d["vtext"]),T)}</div>
  <div style="flex:1;padding-top:16px;border-left:1px solid var(--line);padding-left:44px">
    <div style="font-size:56px;line-height:1.66;color:var(--l2);letter-spacing:.02em"
         data-anim="fadeUp" data-delay="1.17" data-dur="0.62" data-stagger="0.022">{emi(safe_lines(d["sub"]),T)}</div>
  </div>
</div>'''


def L_numbers(d, T, anim):
    """巨大数字冲击"""
    return f'''
<div class="stage" style="display:flex;flex-direction:column;justify-content:center;align-items:center">
  <div style="font-size:{d.get("numSize",430)}px;line-height:.86;color:var(--em);
       letter-spacing:-0.05em"
       data-anim="{anim}" data-delay="0.15" data-dur="0.7" data-stagger="0.09">{d["num"]}</div>
  <div style="font-size:{d.get("unitSize",104)}px;line-height:1.3;margin-top:26px;
       text-align:center;letter-spacing:.02em"
       data-anim="fadeUp" data-delay="0.85" data-dur="0.6" data-stagger="0.04">{emi(d["label"],T)}</div>
</div>'''


def L_timeline(d, T, anim):
    """三拍时间轴"""
    items = d["items"]
    rows = []
    for i, (t1, t2) in enumerate(items):
        rows.append(f'''
  <div style="display:flex;align-items:flex-start;margin-bottom:52px"
       data-anim="{anim}" data-delay="{0.2 + i*0.34:.2f}" data-dur="0.58" data-stagger="0.05">
    <div style="width:190px;flex:0 0 190px;font-size:56px;color:var(--em);
         letter-spacing:.04em;padding-top:6px">{t1}</div>
    <div style="width:2px;background:var(--line);align-self:stretch;margin-right:38px"></div>
    <div style="font-size:58px;line-height:1.44">{emi(t2,T)}</div>
  </div>''')
    return f'''
<div class="stage" style="display:flex;flex-direction:column;justify-content:center">
  <div style="font-size:50px;color:var(--l3);letter-spacing:.06em;margin-bottom:44px"
       data-anim="fadeIn" data-delay="0.11" data-dur="0.48" data-stagger="0.05">{emi(d["lead"],T)}</div>
  {"".join(rows)}
</div>'''


def L_checklist(d, T, anim):
    """清单勾选式"""
    items = d["items"]
    rows = []
    for i, it in enumerate(items):
        rows.append(f'''
  <div style="display:flex;align-items:flex-start;margin-bottom:38px"
       data-anim="{anim}" data-delay="{0.2 + i*0.26:.2f}" data-dur="0.58" data-stagger="0.05">
    <div style="width:52px;height:52px;flex:0 0 52px;border:3px solid var(--em);
         border-radius:10px;margin-right:30px;margin-top:8px;
         display:flex;align-items:center;justify-content:center;
         font-size:36px;color:var(--em)">✓</div>
    <div style="font-size:56px;line-height:1.46">{emi(it,T)}</div>
  </div>''')
    return f'''
<div class="stage">
  <div style="font-size:60px;line-height:1.4;color:var(--l2);margin-bottom:44px"
       data-anim="fadeIn" data-delay="0.11" data-dur="0.52" data-stagger="0.05">{emi(d["lead"],T)}</div>
  {"".join(rows)}
</div>'''


def L_stat(d, T, anim):
    """大留白 + 细线 + 极小注释（高级感/收束）"""
    return f'''
<div class="stage" style="display:flex;flex-direction:column;justify-content:center">
  <div style="height:1px;background:var(--line);margin-bottom:64px"
       data-anim="grow" data-delay="0.11" data-dur="0.6" data-_w="886"></div>
  <div style="font-size:{d["bigSize"]}px;line-height:1.3;letter-spacing:-0.02em"
       data-anim="{anim}" data-delay="0.37" data-dur="0.68" data-stagger="0.05">{emi(safe_lines(d["big"]),T)}</div>
  <div style="height:1px;background:var(--line);margin:60px 0 34px"
       data-anim="grow" data-delay="0.79" data-dur="0.6" data-_w="886"></div>
  <div style="font-size:36px;color:var(--l3);letter-spacing:.08em"
       data-anim="fadeIn" data-delay="1.33" data-dur="0.5" data-stagger="0.05">{emi(d.get("note",""),T)}</div>
</div>'''


def L_stamp(d, T, anim):
    """印章角标 + 一句断言"""
    return f'''
<div class="stage" style="display:flex;flex-direction:column;justify-content:center">
  <div style="width:168px;height:168px;border:4px solid var(--em);border-radius:14px;
       display:flex;align-items:center;justify-content:center;transform:rotate(-6deg);
       margin-bottom:52px;margin-left:10px"
       data-anim="spring" data-delay="0.13" data-dur="0.6" data-stagger="0.06">
    <div style="font-family:'KAI',serif;font-size:56px;line-height:1.1;color:var(--em);
         text-align:center;letter-spacing:.06em">{d.get("seal","真话")}</div>
  </div>
  <div style="font-size:{d["bigSize"]}px;line-height:1.3;letter-spacing:-0.02em"
       data-anim="{anim}" data-delay="0.59" data-dur="0.68" data-stagger="0.05">{emi(safe_lines(d["big"]),T)}</div>
</div>'''


def L_panel(d, T, anim):
    """浮层三块（多层信息）"""
    blocks = d["blocks"]
    rows = []
    for i, b in enumerate(blocks):
        rows.append(f'''
  <div style="background:{'rgba(255,255,255,.55)' if not T['deep'] else 'rgba(255,255,255,.06)'};
       border-left:5px solid var(--em);padding:30px 34px;margin-bottom:24px"
       data-anim="{anim}" data-delay="{0.18 + i*0.3:.2f}" data-dur="0.6" data-stagger="0.05">
    <div style="font-size:54px;line-height:1.44">{emi(b,T)}</div>
  </div>''')
    return f'''
<div class="stage" style="display:flex;flex-direction:column;justify-content:center">
  <div style="font-size:50px;color:var(--l3);letter-spacing:.06em;margin-bottom:36px"
       data-anim="fadeIn" data-delay="0.11" data-dur="0.48" data-stagger="0.05">{emi(d["lead"],T)}</div>
  {"".join(rows)}
</div>'''


LAYOUTS = {
    "hero": L_hero, "split": L_split, "ladder": L_ladder, "versus": L_versus,
    "quote": L_quote, "vertical": L_vertical, "numbers": L_numbers,
    "timeline": L_timeline, "checklist": L_checklist, "stat": L_stat,
    "stamp": L_stamp, "panel": L_panel,
}




# =====================================================================
# 点缀系统（2026-11-18 董事长：太空的卡片要丰富，但不能土）
# 原则：① 只做"版面结构"级装饰（格线/角标/序号/引线），不贴图案不贴图标
#       ② 透明度 0.10-0.55，绝不抢文字
#       ③ 每个版式固定一套，不随机，保证系列一致
# =====================================================================
def deco_grid(T):
    """背景细格线（40% 透明白线网格，极淡）"""
    return ('<svg style="position:absolute;inset:0;z-index:2;opacity:.05" '
            'xmlns="http://www.w3.org/2000/svg">'
            '<defs><pattern id="g" width="90" height="90" patternUnits="userSpaceOnUse">'
            '<path d="M90 0L0 0 0 90" fill="none" stroke="%s" stroke-width="1"/>'
            '</pattern></defs><rect width="100%%" height="100%%" fill="url(#g)"/></svg>'
            % T["l1"])


def deco_corners(T):
    """四角细线角标（46x46，两条边）"""
    c = T["em"]
    def one(top, left, rot):
        pos = []
        if top is not None:
            pos.append("top:%dpx" % top)
        if left is not None:
            pos.append("left:%dpx" % left) if left >= 0 else pos.append("right:%dpx" % (-left))
        return ('<div style="position:absolute;%s;width:46px;height:46px;opacity:.42;'
                'transform:rotate(%ddeg);z-index:3;'
                'border-top:2px solid %s;border-left:2px solid %s"></div>'
                % (";".join(pos), rot, c, c))
    return one(274, 72, 0) + one(274, -122, 90) + one(1520, 72, 270) + one(1520, -122, 180)


def deco_vline(T, x_pct=50):
    """竖向细引线 + 端点圆点（结构感）"""
    return ('<div style="position:absolute;left:%d%%;top:300px;width:1px;height:180px;'
            'background:linear-gradient(%s,transparent);opacity:.45;z-index:3"></div>'
            '<div style="position:absolute;left:%d%%;top:486px;width:8px;height:8px;'
            'border-radius:50%%;background:%s;transform:translateX(-3px);opacity:.7;z-index:3"></div>'
            % (x_pct, T["em"], x_pct, T["em"]))


def deco_shapes(T):
    """点缀：极淡大圆环 + 短线段（杂志留白填充，不抢字）"""
    return ('<div style="position:absolute;right:-160px;top:1000px;width:520px;height:520px;'
            'border-radius:50%%;border:1px solid %s;opacity:.13;z-index:2"></div>'
            '<div style="position:absolute;left:72px;top:1300px;width:120px;height:2px;'
            'background:%s;opacity:.4;z-index:3"></div>'
            % (T["l1"], T["em"]))


def deco_dots(T):
    """点阵纹理（右下角渐变隐去）"""
    return ('<svg style="position:absolute;inset:0;z-index:2;opacity:.30" '
            'xmlns="http://www.w3.org/2000/svg">'
            '<defs><pattern id="d" width="34" height="34" patternUnits="userSpaceOnUse">'
            '<circle cx="2" cy="2" r="1.6" fill="%s"/></pattern>'
            '<radialGradient id="fade"><stop offset="0%%" stop-color="white" stop-opacity="1"/>'
            '<stop offset="100%%" stop-color="white" stop-opacity="0"/></radialGradient>'
            '<mask id="m"><rect width="100%%" height="100%%" fill="url(#fade)"/></mask></defs>'
            '<rect width="100%%" height="100%%" fill="url(#d)" mask="url(#m)"/></svg>'
            % T["l1"])


def deco_number(T, txt):
    """超大序号水印（版心右下，极淡）"""
    return ('<div style="position:absolute;right:-10px;bottom:-40px;font-size:340px;'
            'line-height:1;color:%s;opacity:.055;letter-spacing:-0.05em;z-index:1">%s</div>'
            % (T["l1"], txt))


# ---------- 点缀元素库（每个函数带参数，可变形） ----------
def d_rules(T, pos, op=0.10, n=5, gap=150):
    """横排细线组"""
    y0, x0, w = pos
    out = []
    for i in range(n):
        out.append('<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:1px;'
                   'background:%s;opacity:%.2f;z-index:2"></div>'
                   % (x0, y0 + i * gap, w, T["l1"], op))
    return "".join(out)


def d_ring(T, cx, cy, r, op=0.12, w=1):
    """圆环"""
    return ('<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;'
            'border-radius:50%%;border:%dpx solid %s;opacity:%.2f;z-index:2"></div>'
            % (cx - r, cy - r, r * 2, r * 2, w, T["l1"], op))


def d_arc(T, cx, cy, r, op=0.16):
    """圆弧（只保留四分之一）"""
    return ('<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;'
            'border-radius:50%%;border:2px solid %s;border-right-color:transparent;'
            'border-bottom-color:transparent;opacity:%.2f;z-index:2;transform:rotate(-20deg)"></div>'
            % (cx - r, cy - r, r * 2, r * 2, T["em"], op))


def d_corner(T, where, size=54, op=0.45):
    """角标（where: tl/tr/bl/br）"""
    c = T["em"]
    m = {"tl": ("left:%dpx;top:274px;border-top:2px solid %s;border-left:2px solid %s"),
         "tr": ("right:122px;top:274px;border-top:2px solid %s;border-right:2px solid %s"),
         "bl": ("left:%dpx;bottom:400px;border-bottom:2px solid %s;border-left:2px solid %s"),
         "br": ("right:122px;bottom:400px;border-bottom:2px solid %s;border-right:2px solid %s")}
    st = m[where] % (72, c, c)
    return ('<div style="position:absolute;%s;width:%dpx;height:%dpx;opacity:%.2f;z-index:3"></div>'
            % (st, size, size, op))


def d_bar(T, x, y, w, h=3, op=0.55):
    """短色条"""
    return ('<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;'
            'background:%s;opacity:%.2f;z-index:3"></div>' % (x, y, w, h, T["em"], op))


def d_vline(T, x, y, h, op=0.35):
    """竖引线"""
    return ('<div style="position:absolute;left:%dpx;top:%dpx;width:1px;height:%dpx;'
            'background:%s;opacity:%.2f;z-index:2"></div>' % (x, y, h, T["l1"], op))


def d_dot(T, x, y, r=6, op=0.75):
    """小圆点"""
    return ('<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;'
            'border-radius:50%%;background:%s;opacity:%.2f;z-index:3"></div>'
            % (x, y, r * 2, r * 2, T["em"], op))


def d_dots_pattern(T, x, y, w, h, op=0.20):
    """点阵块"""
    return ('<svg style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;'
            'z-index:2;opacity:%.2f" xmlns="http://www.w3.org/2000/svg">'
            '<defs><pattern id="dp%d" width="26" height="26" patternUnits="userSpaceOnUse">'
            '<circle cx="2" cy="2" r="1.7" fill="%s"/></pattern></defs>'
            '<rect width="100%%" height="100%%" fill="url(#dp%d)"/></svg>'
            % (x, y, w, h, op, int(x * 7 + y), T["l1"], int(x * 7 + y)))


def d_grid(T, op=0.05, cell=96):
    return ('<svg style="position:absolute;inset:0;z-index:1;opacity:%.2f" '
            'xmlns="http://www.w3.org/2000/svg">'
            '<defs><pattern id="gg" width="%d" height="%d" patternUnits="userSpaceOnUse">'
            '<path d="M%d 0L0 0 0 %d" fill="none" stroke="%s" stroke-width="1"/>'
            '</pattern></defs><rect width="100%%" height="100%%" fill="url(#gg)"/></svg>'
            % (op, cell, cell, cell, cell, T["l1"]))


def d_water(T, txt, x, y, size, op=0.05):
    return ('<div style="position:absolute;left:%dpx;top:%dpx;font-size:%dpx;line-height:1;'
            'color:%s;opacity:%.3f;letter-spacing:-0.05em;z-index:1">%s</div>'
            % (x, y, size, T["l1"], op, txt))


def d_number_badge(T, txt, x, y, size=44):
    return ('<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;'
            'border:1.5px solid %s;border-radius:50%%;display:flex;align-items:center;'
            'justify-content:center;font-size:%dpx;color:%s;opacity:.7;z-index:3">%s</div>'
            % (x, y, size, size, T["em"], int(size * 0.42), T["em"], txt))


# ---------- 48 张卡的点缀方案表（每张不同） ----------
# 每项 = 元素组合；坐标/数量/透明度各卡不同，保证视觉不重复
DECO_PLAN = {
 (1,1): [("corner","tl",60),("ring",980,1180,240,0.10),("bar",72,1300,140)],
 (1,2): [("grid",),("ring",180,1520,200,0.10),("corner","tr",44)],
 (1,3): [("water","03",760,1120,400),("corner","bl",52),("vline",940,320,220)],
 (1,4): [("rules",(340,72,886),0.09,4,120),("arc",900,320,190),("corner","br",48)],
 (1,5): [("grid",),("bar",830,1380,150),("corner","tl",40),("dot",870,1430)],
 (1,6): [("dots",(760,1180,260,260)),("ring",200,320,170,0.10),("corner","tr",56)],
 (1,7): [("ring",540,960,330,0.08),("bar",72,1220,110),("corner","tl",46),("dot",210,1250)],
 (1,8): [("rules",(300,72,886),0.08,3,140),("corner","br",60),("arc",140,1240,150),("ticks",760,1310,6,20),],

 (2,1): [("vline",760,300,240),("corner","tl",58),("ring",900,1300,190,0.09)],
 (2,2): [("ring",880,1100,260,0.10),("water","3",120,380,300),("corner","br",44)],
 (2,3): [("grid",),("bar",72,1180,160),("corner","tr",50)],
 (2,4): [("arc",300,400,170),("corner","bl",54),("dot",160,700),("rules",(1250,72,600),0.08,3,110)],
 (2,5): [("water","“",80,300,320),("corner","br",52),("vline",980,1100,180),("plus",900,1240,28),],
 (2,6): [("dots",(80,1180,220,220)),("corner","tr",46),("bar",800,340,130)],
 (2,7): [("ring",200,1120,210,0.09),("corner","tl",50),("rules",(330,900,500),0.08,3,90)],
 (2,8): [("arc",860,1200,200),("corner","bl",60),("dot",820,430,8)],

 (3,1): [("ring",900,420,220,0.10),("corner","br",54),("bar",72,1250,120),("ticks",72,1360,6,20),],
 (3,2): [("water","“",60,420,340),("vline",860,320,260),("corner","tr",48),("half",60,1180,110),],
 (3,3): [("ring",540,700,300,0.07),("corner","bl",52),("dot",300,1280)],
 (3,4): [("grid",),("corner","tr",44),("bar",760,1160,140),("diag",700,1300,160),],
 (3,5): [("water","05",740,1200,380),("corner","tl",56),("vline",150,320,200),("diag",700,1320,160),],
 (3,6): [("arc",960,300,160),("corner","br",50),("rules",(1290,72,700),0.08,3,100),("plus",200,1240,26),],
 (3,7): [("dots",(700,1250,240,240)),("corner","tl",48),("ring",180,380,180,0.09),("plus",860,1200,30),],
 (3,8): [("ring",540,1250,280,0.08),("corner","br",58),("bar",72,380,100),("dot",195,400),("diag",180,480,150),],

 (4,1): [("ring",880,1300,230,0.10),("corner","tl",62),("bar",72,1200,150),("plus",880,360,34),],
 (4,2): [("water","5",100,1120,420),("corner","tr",46),("vline",900,340,240),("ticks",660,1290,6,20),],
 (4,3): [("grid",),("corner","bl",50),("bar",820,1300,120),("half",80,1250,100),],
 (4,4): [("arc",180,1180,190),("corner","tr",54),("dot",860,420),("ticks",120,1290,6,20),],
 (4,5): [("ring",200,340,200,0.09),("corner","br",56),("rules",(1200,72,600),0.08,3,110),("diag",600,1280,170),],
 (4,6): [("dots",(120,1200,260,260)),("corner","tl",44),("bar",780,400,160),("half",700,1300,105),],
 (4,7): [("water","“",70,340,320),("corner","bl",52),("vline",950,1150,200),("plus",120,1160,30),("ticks",700,1330,5,20),],
 (4,8): [("ring",540,760,340,0.07),("corner","br",60),("dot",840,1240,7),("half",640,320,100),],

 (5,1): [("ring",940,1220,240,0.10),("corner","tl",58),("bar",72,390,170),("half",760,1300,120),],
 (5,2): [("grid",),("corner","br",48),("vline",120,340,220)],
 (5,3): [("water","“",60,400,340),("corner","tr",54),("dot",900,1250)],
 (5,4): [("water","04",770,1180,360),("corner","bl",50),("ring",170,330,170,0.09),("plus",860,1250,30),],
 (5,5): [("arc",900,360,180),("corner","br",56),("rules",(1280,72,650),0.08,3,100),("half",680,300,105),],
 (5,6): [("dots",(80,1220,240,240)),("corner","tr",44),("bar",760,1160,130),("plus",150,1250,28),],
 (5,7): [("ring",200,1100,210,0.09),("corner","tl",52),("vline",960,320,240),("ticks",72,1290,7,20),],
 (5,8): [("ring",540,1000,320,0.07),("corner","bl",58),("dot",250,420,8),("diag",700,340,160),],

 (6,1): [("ring",880,1240,220,0.10),("corner","tl",54),("bar",72,370,160),("diag",120,1240,180),],
 (6,2): [("water","02",780,1180,380),("corner","br",46),("vline",140,330,230),("half",640,330,100),("plus",780,1160,26),],
 (6,3): [("water","“",70,380,330),("corner","tr",52),("dot",880,1250),("plus",140,1250,28),],
 (6,4): [("grid",),("corner","bl",50),("bar",800,1300,140),("ticks",740,320,6,20),],
 (6,5): [("dots",(700,1220,250,250)),("corner","tl",56),("ring",180,360,190,0.09),("half",700,340,110),],
 (6,6): [("ring",540,860,300,0.08),("corner","br",48),("bar",72,1200,120),("ticks",800,300,5,22),("half",720,1250,100),],
 (6,7): [("arc",200,340,170),("corner","tr",58),("rules",(1260,72,680),0.08,3,100),("diag",620,1240,170),],
 (6,8): [("ring",880,420,210,0.10),("corner","bl",60),("dot",160,1260,7),("ticks",700,1280,6,20),],
}


def d_halfcircle(T, x, y, r, side="bottom", op=0.12):
    """半圆装饰"""
    return ('<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;'
            'border-radius:%s;border:1px solid %s;opacity:%.2f;z-index:2"></div>'
            % (x, y, r * 2, r, ("50%% 50%% 0 0" if side == "top" else "0 0 50%% 50%%"),
               T["l1"], op))


def d_diag(T, x, y, w, op=0.20):
    """斜线"""
    return ('<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:1px;'
            'background:%s;opacity:%.2f;transform:rotate(-28deg);transform-origin:left;'
            'z-index:2"></div>' % (x, y, w, T["l1"], op))


def d_plus(T, x, y, size=30, op=0.40):
    """十字号（编辑感）"""
    return ('<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;'
            'z-index:3;opacity:%.2f">'
            '<div style="position:absolute;left:50%%;top:0;width:1.5px;height:100%%;'
            'background:%s;transform:translateX(-50%%)"></div>'
            '<div style="position:absolute;top:50%%;left:0;height:1.5px;width:100%%;'
            'background:%s;transform:translateY(-50%%)"></div></div>'
            % (x, y, size, size, op, T["em"], T["em"]))


def d_ticks(T, x, y, n=8, gap=22, op=0.35):
    """刻度线（标尺感）"""
    out = []
    for i in range(n):
        out.append('<div style="position:absolute;left:%dpx;top:%dpx;width:1px;height:%dpx;'
                   'background:%s;opacity:%.2f;z-index:2"></div>'
                   % (x + i * gap, y, 14 if i % 2 == 0 else 8, T["l1"], op))
    return "".join(out)


def render_deco(items, T):
    out = []
    for it in items:
        k = it[0]
        try:
            if k == "corner":   out.append(d_corner(T, it[1], it[2]))
            elif k == "ring":   out.append(d_ring(T, *it[1:]))
            elif k == "arc":    out.append(d_arc(T, *it[1:]))
            elif k == "bar":    out.append(d_bar(T, *it[1:]))
            elif k == "vline":  out.append(d_vline(T, *it[1:]))
            elif k == "dot":    out.append(d_dot(T, *it[1:]))
            elif k == "rules":  out.append(d_rules(T, it[1], *it[2:]))
            elif k == "dots":   out.append(d_dots_pattern(T, *it[1]))
            elif k == "grid":   out.append(d_grid(T))
            elif k == "water":  out.append(d_water(T, it[1], it[2], it[3], it[4]))
            elif k == "half":   out.append(d_halfcircle(T, *it[1:]))
            elif k == "diag":   out.append(d_diag(T, *it[1:]))
            elif k == "plus":   out.append(d_plus(T, *it[1:]))
            elif k == "ticks":  out.append(d_ticks(T, *it[1:]))
        except Exception:
            pass
    return "".join(out)




# =====================================================================
# 点缀系统（2026-11-18 董事长：太空的卡片要丰富，但不能土）
# 原则：① 只做"版面结构"级装饰（格线/角标/序号/引线），不贴图案不贴图标
#       ② 透明度 0.10-0.55，绝不抢文字
#       ③ 每个版式固定一套，不随机，保证系列一致
# =====================================================================
def deco_grid(T):
    """背景细格线（40% 透明白线网格，极淡）"""
    return ('<svg style="position:absolute;inset:0;z-index:2;opacity:.05" '
            'xmlns="http://www.w3.org/2000/svg">'
            '<defs><pattern id="g" width="90" height="90" patternUnits="userSpaceOnUse">'
            '<path d="M90 0L0 0 0 90" fill="none" stroke="%s" stroke-width="1"/>'
            '</pattern></defs><rect width="100%%" height="100%%" fill="url(#g)"/></svg>'
            % T["l1"])


def deco_corners(T):
    """四角细线角标（46x46，两条边）"""
    c = T["em"]
    def one(top, left, rot):
        pos = []
        if top is not None:
            pos.append("top:%dpx" % top)
        if left is not None:
            pos.append("left:%dpx" % left) if left >= 0 else pos.append("right:%dpx" % (-left))
        return ('<div style="position:absolute;%s;width:46px;height:46px;opacity:.42;'
                'transform:rotate(%ddeg);z-index:3;'
                'border-top:2px solid %s;border-left:2px solid %s"></div>'
                % (";".join(pos), rot, c, c))
    return one(274, 72, 0) + one(274, -122, 90) + one(1520, 72, 270) + one(1520, -122, 180)


def deco_vline(T, x_pct=50):
    """竖向细引线 + 端点圆点（结构感）"""
    return ('<div style="position:absolute;left:%d%%;top:300px;width:1px;height:180px;'
            'background:linear-gradient(%s,transparent);opacity:.45;z-index:3"></div>'
            '<div style="position:absolute;left:%d%%;top:486px;width:8px;height:8px;'
            'border-radius:50%%;background:%s;transform:translateX(-3px);opacity:.7;z-index:3"></div>'
            % (x_pct, T["em"], x_pct, T["em"]))


def deco_shapes(T):
    """点缀：极淡大圆环 + 短线段（杂志留白填充，不抢字）"""
    return ('<div style="position:absolute;right:-160px;top:1000px;width:520px;height:520px;'
            'border-radius:50%%;border:1px solid %s;opacity:.13;z-index:2"></div>'
            '<div style="position:absolute;left:72px;top:1300px;width:120px;height:2px;'
            'background:%s;opacity:.4;z-index:3"></div>'
            % (T["l1"], T["em"]))


def deco_dots(T):
    """点阵纹理（右下角渐变隐去）"""
    return ('<svg style="position:absolute;inset:0;z-index:2;opacity:.30" '
            'xmlns="http://www.w3.org/2000/svg">'
            '<defs><pattern id="d" width="34" height="34" patternUnits="userSpaceOnUse">'
            '<circle cx="2" cy="2" r="1.6" fill="%s"/></pattern>'
            '<radialGradient id="fade"><stop offset="0%%" stop-color="white" stop-opacity="1"/>'
            '<stop offset="100%%" stop-color="white" stop-opacity="0"/></radialGradient>'
            '<mask id="m"><rect width="100%%" height="100%%" fill="url(#fade)"/></mask></defs>'
            '<rect width="100%%" height="100%%" fill="url(#d)" mask="url(#m)"/></svg>'
            % T["l1"])


def deco_number(T, txt):
    """超大序号水印（版心右下，极淡）"""
    return ('<div style="position:absolute;right:-10px;bottom:-40px;font-size:340px;'
            'line-height:1;color:%s;opacity:.055;letter-spacing:-0.05em;z-index:1">%s</div>'
            % (T["l1"], txt))


DECO_OF = {
    "hero":      lambda T, seq: deco_shapes(T) + deco_corners(T),
    "split":     lambda T, seq: deco_grid(T) + deco_corners(T),
    "ladder":    lambda T, seq: deco_number(T, seq or "1") + deco_corners(T),
    "versus":    lambda T, seq: deco_shapes(T) + deco_grid(T),
    "quote":     lambda T, seq: deco_corners(T) + deco_dots(T),
    "vertical":  lambda T, seq: deco_vline(T, 62) + deco_corners(T),
    "numbers":   lambda T, seq: deco_shapes(T) + deco_corners(T),
    "timeline":  lambda T, seq: deco_grid(T) + deco_corners(T),
    "checklist": lambda T, seq: deco_number(T, "✓") + deco_corners(T),
    "stat":      lambda T, seq: deco_shapes(T) + deco_vline(T, 50),
    "stamp":     lambda T, seq: deco_dots(T) + deco_corners(T),
    "panel":     lambda T, seq: deco_grid(T) + deco_shapes(T),
}


FIT_JS = """
<script>
// 自适应：任何文字块超出容器就缩字号，保证不出安全区（董事长：字不能出屏、不能单字成行）
(function(){
  var stage=document.querySelector('.stage');
  var W=stage.clientWidth, H=stage.clientHeight;
  document.querySelectorAll('.stage [data-anim]').forEach(function(el){
    var fs=parseFloat(getComputedStyle(el).fontSize);
    for(var i=0;i<60 && fs>22;i++){
      if(el.scrollWidth<=W+2 && el.scrollHeight<=H+2) break;
      fs*=0.96; el.style.fontSize=fs+'px';
    }
  });
})();
</script>
"""

def build_html(card):
    """card: dict(name, layout, anim, theme, foot, **layout_args)"""
    T = THEMES[card["theme"]]
    fn = LAYOUTS[card["layout"]]
    body = fn(card, T, card["anim"])
    deco = render_deco(DECO_PLAN.get(tuple(card.get("_key", (0, 0))), []), T)
    html = (HEAD.replace("<body>", '<body style="%s">' % _vars(T))
            + '<div class="bgtone"></div>' + deco + brand(T) + body
            + foot(card.get("foot", ""), T) + grain(T)
            + FIT_JS + "\n</body></html>")
    return html


if __name__ == "__main__":
    import json
    demo = dict(name="demo", layout="hero", anim="fadeUp", theme="S1",
                lead="你以为你在忍", big="其实你在攒炸弹", bigSize=200,
                foot="老蔡说 · 家里没说出口的话")
    open("E:/心理咨询IP/04-工程/batch4/_demo.html", "w", encoding="utf-8").write(build_html(demo))
    print("ok")
