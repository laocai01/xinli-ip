# -*- coding: utf-8 -*-
"""单条流水线：去反光 → 合成 → 校验（逐条串行，省内存）
   用法: python pipeline_one.py <n> [<n> ...]
"""
import os, sys, io, json, subprocess, time

R = "E:/心理咨询IP/04-工程/batch2"
sys.path.insert(0, R)
import deglare_all
import compose_batch2 as C

LOG = R + "/_pipeline.log"


def log(msg):
    line = "%s %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


if __name__ == "__main__":
    for n in [int(x) for x in sys.argv[1:]]:
        t0 = time.time()
        log("=== EP%d 去反光 开始" % n)
        deglare_all.run(n)
        log("=== EP%d 反光完成 %.1f 分钟" % (n, (time.time() - t0) / 60))

        # 合成：优先用已修好的 clean 素材
        clean = "E:/心理咨询IP/素材_clean/%d.mp4" % n
        orig_plan = C.plan
        if os.path.exists(clean):
            def plan_with_clean(k, _o=orig_plan, _c=clean, _n=n):
                P = _o(k)
                if k == _n:
                    P["src"] = _c
                    P["raw"] = C.dur(_c)
                    P["total"] = P["raw"] / P["speed"]
                return P
            C.plan = plan_with_clean
        log("=== EP%d 合成 开始" % n)
        ok = C.build(n)
        log("=== EP%d 合成 %s 用时 %.1f 分钟" % (n, "成功" if ok else "失败", (time.time() - t0) / 60))
