# -*- coding: utf-8 -*-
"""C方案 · 单条合成（先做第2条给董事长看）"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose_batch2 as C

n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
t = time.time()
ok = C.build(n)
print("RESULT", ok, "%.1f 分钟" % ((time.time() - t) / 60), flush=True)
