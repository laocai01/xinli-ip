# -*- coding: utf-8 -*-
"""把卡片动画时间表统一收紧：最迟 1.30s 起、最长 0.90s 完成
   → 卡片停 3.6~8s，前面 2.2s 动完，后面全静止，一眼能看清
   直接改 gen_cards.py 源码里的 data-delay / data-dur
"""
import io, re

P = "E:/心理咨询IP/04-工程/batch2/gen_cards.py"
BS = "\\" * 3          # 源码里是 三层转义 + 引号
Q = BS + '"'

s = io.open(P, encoding="utf-8").read()


def clamp(m):
    d = float(m.group(1))
    u = float(m.group(2))
    return ("data-delay=" + Q + "%.2f" % min(d, 1.30) + Q +
            " data-dur=" + Q + "%.2f" % min(max(u, 0.55), 0.90) + Q)


pat = re.compile(r"data-delay=" + re.escape(Q) + r"([0-9.]+)" + re.escape(Q) +
                 r"\s*data-dur=" + re.escape(Q) + r"([0-9.]+)" + re.escape(Q))
hits = pat.findall(s)
print("命中元素", len(hits))
s2 = pat.sub(clamp, s)
io.open(P, "w", encoding="utf-8").write(s2)
print("延迟档:", sorted(set(re.findall(r"data-delay=" + re.escape(Q) + r"([0-9.]+)", s2))))
print("时长档:", sorted(set(re.findall(r"data-dur=" + re.escape(Q) + r"([0-9.]+)", s2))))
