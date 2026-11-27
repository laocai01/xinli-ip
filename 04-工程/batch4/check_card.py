# -*- coding: utf-8 -*-
"""单张卡快速验收：渲染末帧 → 检查出界/孤行 → 打印结论
用法: python check_card.py <集号> <卡名>
"""
import os
import sys
import glob
import numpy as np
from PIL import Image

R4 = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("CARD_ROOT", R4)
sys.path.insert(0, "E:/心理咨询IP/04-工程/batch2")
sys.path.insert(0, R4)

import render_cards as RC  # noqa
RC.ANIM = open(os.path.join(R4, "anim_ch.js"), encoding="utf-8").read()


def check(img_path, safe_l=69, safe_r=1011):
    a = np.array(Image.open(img_path).convert("RGB")).astype(float)
    bg = a[5, 5]
    diff = np.abs(a - bg).max(axis=2)
    mask = diff > 40
    mask[:250] = False       # 品牌区
    mask[1500:] = False      # 页脚区
    prof = mask.sum(axis=1)
    blocks, st = [], None
    for y in range(1920):
        if prof[y] > 4:
            if st is None:
                st = y
        else:
            if st is not None:
                if y - st >= 8:
                    blocks.append((st, y - 1))
                st = None
    rows, issues = [], []
    for (y0, y1) in blocks:
        band = mask[y0:y1 + 1]
        cols = band.sum(axis=0)
        xs = [x for x in range(1080) if cols[x] > 0]
        if not xs:
            continue
        x0, x1 = min(xs), max(xs)
        rows.append((y0, y1, x0, x1, x1 - x0, y1 - y0))
        if x0 < safe_l or x1 > safe_r:
            issues.append("出界 y%d-%d x%d..%d（安全 %d..%d）"
                          % (y0, y1, x0, x1, safe_l, safe_r))
        w, h = x1 - x0, y1 - y0
        # ★ 单字成行：宽<高*1.4 且 字高>50（排除横幅/细线；印章/数字框需人工确认）
        if 50 < h < 200 and w < h * 1.05:
            issues.append("可疑单字行 y%d-%d 宽%d 高%d" % (y0, y1, w, h))
    return rows, issues


if __name__ == "__main__":
    n = int(sys.argv[1])
    key = sys.argv[2]
    html = os.path.join(R4, "cards_html", str(n), key + ".html")
    out = os.path.join(R4, "_chk", key)
    import time
    RC.Lane.__init__  # noqa
    _orig = RC.Lane.__init__

    def _patched(self, idx, port):
        _orig(self, idx, port)
        self.prof = os.path.join(R4, "chrome_prof", "chk_%d" % int(time.time() * 1000 % 100000))
        os.makedirs(self.prof, exist_ok=True)
    RC.Lane.__init__ = _patched
    lane = RC.Lane(0, 9360 + (int(time.time()) % 40))
    lane.start()
    try:
        lane.shoot(html, out, 120, 30)
    finally:
        lane.stop()
    rows, issues = check(os.path.join(out, "f0119.jpg"))
    print("=== %s ===" % key)
    for r in rows:
        print("  y%4d-%4d  x%4d..%4d  宽%4d 高%3d" % r)
    print("结论: " + ("✅ 无出界" if not issues else "❌ " + " / ".join(issues)))
