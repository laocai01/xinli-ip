# -*- coding: utf-8 -*-
"""批量去屏幕反光（眼镜/眼睛里的电脑倒影）
按 1..6 跑，先自动找头部 ROI，再逐帧局部压掉反光；
处理结果存到 E:/心理咨询IP/素材_clean/<n>.mp4（不动原始素材），供 compose 使用。
用法: python deglare_all.py 1 2 3
"""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deglare

ROOT = "E:/心理咨询IP"
OUT = ROOT + "/素材_clean"
R = ROOT + "/04-工程/batch2"


def run(n):
    os.makedirs(OUT, exist_ok=True)
    src = "%s/素材/%d.mp4" % (ROOT, n)
    dst = "%s/%d.mp4" % (OUT, n)
    if os.path.exists(dst) and os.path.getsize(dst) > 1e6:
        print("[%d] 已存在，跳过 %s" % (n, dst), flush=True)
        return True
    t = time.time()
    print("[%d] 开始 %s" % (n, src), flush=True)
    roi = deglare.faces_roi(src, *deglare.probe(src)[:2], vf=deglare.probe(src)[3])
    print("[%d] 头部ROI %s" % (n, roi), flush=True)
    tmp = dst + ".part.mp4"
    used = deglare.process(src, tmp, roi=roi)
    os.replace(tmp, dst)
    print("[%d] 完成 %.1f 分钟 %s %.1fMB ROI=%s" %
          (n, (time.time() - t) / 60, dst, os.path.getsize(dst) / 1e6, used), flush=True)
    with open(R + "/_deglare.json", "a", encoding="utf-8") as f:
        f.write(json.dumps({"n": n, "roi": used, "sec": round(time.time() - t, 1)}, ensure_ascii=False) + "\n")
    return True


if __name__ == "__main__":
    for n in [int(x) for x in sys.argv[1:]]:
        run(n)
