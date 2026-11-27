# -*- coding: utf-8 -*-
"""把 cards_v2 的 12-15 张卡片方案渲染成 HTML（含品牌区/背景/四角/颗粒），
结构和 gen_cards.build() 完全一致，只是数据源换成 cards_v2.CARDS_V2。

用法：
    python render_cards_v2.py 2       # 只渲第2条（15张）
"""
import os
import sys
import io

R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, R)

from cards_v2 import CARDS_V2
import gen_cards as G

# 集数编号 -> 主题键
THEME_KEY = {2: "12", 3: "13", 4: "14", 5: "15", 6: "16", 1: "11"}


def to_gen_format(n):
    rows = []
    for name, kind, kw, a in CARDS_V2[n]:
        if kind == "main":
            args = (a["l1"], a["l2"], a["sub"])
        elif kind == "three":
            args = (a["lead"], a["items"], a.get("tail"))
        elif kind == "quote":
            big = a["big"]
            if "\n" not in big and len(big) > 9:
                mid = len(big) // 2
                put = None
                for d in range(0, 6):
                    for cut in (mid - d, mid + d):
                        if 0 < cut < len(big) and big[cut] in "，、 /":
                            put = cut
                            break
                    if put:
                        break
                if put is None:
                    put = mid
                big = big[:put] + "\n" + big[put + 1 if big[put:put + 1] in "，、 " else put:]
            args = (a["lead"], big)
        elif kind == "steps":
            args = (a["lead"], a["items"])
        else:
            raise ValueError("未知版式 %s" % kind)
        rows.append((name, kind, args))
    return rows


def build_v2(n, out_root=None):
    """渲染 EPn 的 15 张卡片，返回 {文件名: 文案列表}"""
    out_root = out_root or os.path.join(R, "cards_v2_out", str(n))
    os.makedirs(out_root, exist_ok=True)
    for f in os.listdir(out_root):
        if f.endswith(".html"):
            os.remove(os.path.join(out_root, f))

    t = G.THEMES[THEME_KEY[n]]
    rows = to_gen_format(n)
    texts = {}
    for name, kind, args in rows:
        body = G.brand() + G.brandline(t["rule"]) + G.bg(t) + G.motif(t) + G.corners(t["accent"])
        if kind == "main":
            body += G.card_main(t, *args)
            up = [args[0], args[1], args[2]]
        elif kind == "three":
            body += G.card_three(t, *args)
            up = [args[0]] + list(args[1]) + ([args[2]] if args[2] else [])
        elif kind == "quote":
            body += G.card_quote(t, *args)
            up = [args[0], args[1].replace("\n", "")]
        else:
            body += G.card_steps(t, *args)
            up = [args[0]] + list(args[1])
        body += G.sig(t["ink2"], t["accent"]) + G.GRAIN
        html = G.HEAD + "</head><body>\n" + body + "\n</body></html>"
        io.open(os.path.join(out_root, name + ".html"), "w", encoding="utf-8").write(html)
        texts[name + ".html"] = up
    return texts


if __name__ == "__main__":
    nums = [int(x) for x in sys.argv[1:]] or [2]
    for n in nums:
        if n not in CARDS_V2:
            print("EP%d 无 15 张方案，跳过" % n)
            continue
        txt = build_v2(n)
        print("EP%d 生成 %d 张卡片 → %s" % (n, len(txt), os.path.join(R, "cards_v2_out", str(n))))
