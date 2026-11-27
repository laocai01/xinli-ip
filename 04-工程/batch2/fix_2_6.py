# -*- coding: utf-8 -*-
"""只重出 EP2、EP6（修音视频等长）"""
import io, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose_batch2 as C

ROOT = "E:/心理咨询IP/04-工程/batch2"
ST = os.path.join(ROOT, "_fix26.json")


def save(d):
    json.dump(d, io.open(ST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


st = {"stage": "合成", "done": [], "fail": [], "cur": None, "t0": time.strftime("%H:%M:%S")}
save(st)
for n in [2, 6]:
    st["cur"] = n
    save(st)
    t = time.time()
    try:
        ok = C.build(n)
    except Exception as e:
        ok = False
        print("[%d] 异常 %s" % (n, e))
    if ok:
        st["done"].append(n)
        print("[%d] OK %.1f 分钟" % (n, (time.time() - t) / 60), flush=True)
    else:
        st["fail"].append(n)
        print("[%d] FAIL" % n, flush=True)
    save(st)
st["stage"] = "全部完成"
save(st)
print("汇总:", st["done"], "失败:", st["fail"])
