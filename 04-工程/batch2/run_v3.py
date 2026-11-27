# -*- coding: utf-8 -*-
"""全批重出 v3：带定制插画 + 新引导语（旧版成片不删，先出到 _新插画 后缀）"""
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose_batch2 as C

ROOT = "E:/心理咨询IP/04-工程/batch2"
ST = os.path.join(ROOT, "_run_v3.json")


def save(d):
    json.dump(d, io.open(ST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


st = {"stage": "合成", "done": [], "fail": [], "cur": None, "t0": time.strftime("%H:%M:%S")}
save(st)
for n in [2, 3, 4, 5, 6]:
    st["cur"] = n
    save(st)
    t = time.time()
    try:
        ok = C.build(n)
    except Exception as e:
        ok = False
        print("[%d] 异常 %s" % (n, e), flush=True)
    if ok:
        st["done"].append(n)
        print("[%d] OK %.1f 分钟" % (n, (time.time() - t) / 60), flush=True)
    else:
        st["fail"].append(n)
        print("[%d] FAIL" % n, flush=True)
    save(st)
st["stage"] = "全部完成"
save(st)
print("汇总:", st["done"], "失败:", st["fail"], flush=True)
