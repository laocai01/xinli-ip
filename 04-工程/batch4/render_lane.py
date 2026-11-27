# -*- coding: utf-8 -*-
"""batch4 卡片渲染车道（复用 batch2 已验证的 CDP 逐帧截图）

用法: python render_lane.py <任务json> <lane号> <总车道数>
"""
import os
import sys

R4 = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("CARD_ROOT", R4)
sys.path.insert(0, "E:/心理咨询IP/04-工程/batch2")

import render_cards as RC   # noqa: E402

# 换成本工程的字符级动画引擎
RC.ANIM = open(os.path.join(R4, "anim_ch.js"), encoding="utf-8").read()

if __name__ == "__main__":
    sys.argv = [sys.argv[0]] + sys.argv[1:]
    # 端口错开，避免与别的渲染抢
    _idx = int(sys.argv[2])
    RC.Lane.__init__  # noqa
    orig = RC.Lane.__init__

    def patched(self, idx, port):
        import time
        orig(self, idx, 9400 + idx * 3)
        # 独立 profile，避免上一次残留占用
        self.prof = os.path.join(R4, "chrome_prof", "lane%d_%d" % (idx, int(time.time()) % 100000))
        os.makedirs(self.prof, exist_ok=True)
    RC.Lane.__init__ = patched
    RC.main()
