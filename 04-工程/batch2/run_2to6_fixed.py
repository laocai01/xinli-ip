# -*- coding: utf-8 -*-
"""重出 EP2-EP6（第23条已发布，不动）
   K1调色 + 删段修复 + 去眼窗 + total按真实口播长度计算（防剪尾）
"""
import io, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose_batch2 as C

ROOT = "E:/心理咨询IP/04-工程/batch2"
ST = os.path.join(ROOT, "_run_2to6f.json")


def save(d):
    json.dump(d, io.open(ST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


st = {"stage": "合成", "done": [], "fail": [], "cur": None,
      "t0": time.strftime("%H:%M:%S"), "skip": [1]}
save(st)
for n in [2, 3, 4, 5, 6]:
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
print("汇总: 完成", st["done"], "失败", st["fail"])
