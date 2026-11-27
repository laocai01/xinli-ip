# -*- coding: utf-8 -*-
"""重出全部 6 条（K1调色 + 删段修复 + 去眼窗）"""
import io, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose_batch2 as C

ROOT = "E:/心理咨询IP/04-工程/batch2"
ST = os.path.join(ROOT, "_run_all6.json")

def save(d):
    json.dump(d, io.open(ST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

st = {"stage": "合成", "done": [], "fail": [], "cur": None, "t0": time.strftime("%H:%M:%S")}
save(st)
for n in range(1, 7):
    st["cur"] = n; save(st)
    t = time.time()
    try:
        ok = C.build(n)
    except Exception as e:
        ok = False
        print("[%d] 异常 %s" % (n, e))
    if ok:
        st["done"].append(n)
        print("[%d] OK %.1f 分钟" % (n, (time.time()-t)/60))
    else:
        st["fail"].append(n)
        print("[%d] FAIL" % n)
    save(st)
st["stage"] = "全部完成"; save(st)
print("汇总:", st["done"], "失败:", st["fail"])
