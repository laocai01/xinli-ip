# -*- coding: utf-8 -*-
"""batch3 卡片：生成 HTML（复用 batch2 已验证的模板/品牌区/主题）"""
import os, sys, json, io
R3 = os.path.dirname(os.path.abspath(__file__))
R2 = "E:/心理咨询IP/04-工程/batch2"
sys.path.insert(0, R3); sys.path.insert(0, R2)
from cards_ep import CARDS as C3
import gen_cards as G

OUT3 = R3 + "/cards_html"
THEME_MAP = {1:"11", 2:"12", 3:"13", 4:"14",
             5:"12", 6:"13", 7:"14", 8:"11", 9:"12", 10:"13", 11:"14"}


def to_gen(n):
    rows = []
    for name, kind, _kw, a in C3[n]:
        if kind == "main":
            args = (a["l1"], a["l2"], a["sub"]); up = [a["l1"], a["l2"], a["sub"]]
        elif kind == "three":
            args = (a["lead"], a["items"], a.get("tail"))
            up = [a["lead"]] + list(a["items"]) + ([a["tail"]] if a.get("tail") else [])
        elif kind == "quote":
            args = (a["lead"], a["big"]); up = [a["lead"], a["big"].replace("\n", "")]
        elif kind == "steps":
            args = (a["lead"], a["items"]); up = [a["lead"]] + list(a["items"])
        else:
            raise ValueError(kind)
        rows.append((name, kind, args, up))
    return rows


def build(n):
    rows = to_gen(n)
    t = G.THEMES[THEME_MAP[n]]
    d = os.path.join(OUT3, str(n))
    os.makedirs(d, exist_ok=True)
    texts = {}
    for ci, (name, kind, args, up) in enumerate(rows):
        body = G.brand() + G.brandline(t["rule"]) + G.bg(t) + G.motif(t) + G.corners(t["accent"])
        if kind == "main":    body += G.card_main(t, *args, idx=ci)
        elif kind == "three": body += G.card_three(t, *args, idx=ci)
        elif kind == "quote": body += G.card_quote(t, *args, idx=ci)
        elif kind == "steps": body += G.card_steps(t, *args, idx=ci)
        body += G.sig(t["ink2"], t["accent"]) + G.GRAIN
        html = G.HEAD + "</head><body>\n" + body + "\n</body></html>"
        io.open(os.path.join(d, name + ".html"), "w", encoding="utf-8").write(html)
        texts[name] = up
    json.dump(texts, io.open(os.path.join(d, "_texts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return d, len(rows)


if __name__ == "__main__":
    for n in [int(v) for v in (sys.argv[1:] or ["1"])]:
        d, c = build(n)
        print("第%d条 → %s  (%d 张)" % (n, d, c))
