# -*- coding: utf-8 -*-
"""全批流水线（无人值守）：缺的去反光 → 逐条合成 → 18 项验收 → 汇总
   规则：全程串行（8 核，去反光与合成禁止并行）；每步都写日志；失败的跳过不阻塞其它条
   用法: python run_all.py  [--skip-compose] [--skip-verify]
"""
import io, os, sys, time, json, subprocess

R = "E:/心理咨询IP/04-工程/batch2"
sys.path.insert(0, R)
ROOT = "E:/心理咨询IP"
FFP = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffprobe.exe"
LOG = R + "/_runall.log"
EPS = [1, 2, 3, 4, 5, 6]


def log(m):
    line = "%s %s" % (time.strftime("%H:%M:%S"), m)
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def readable(p, minsec=30):
    if not os.path.exists(p) or os.path.getsize(p) < 1e6:
        return False
    r = subprocess.run([FFP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip()) > minsec
    except ValueError:
        return False


def main():
    skip_compose = "--skip-compose" in sys.argv
    skip_verify = "--skip-verify" in sys.argv
    import pipeline2_one as P2
    import compose_batch2 as C

    # 1) 去反光补齐（4 号之前写坏了 / 5、6 可能没跑完）
    for n in EPS:
        clean = "%s/素材_clean/%d.mp4" % (ROOT, n)
        eye = "%s/素材_clean/eye_%d.mp4" % (ROOT, n)
        if readable(clean, 60) and readable(eye, 60):
            continue
        log("【%d】去反光补齐" % n)
        try:
            if os.path.exists(clean) and not readable(clean, 60):
                os.remove(clean)
            P2.run(n)
        except Exception as e:
            log("【%d】去反光失败：%s" % (n, e))

    if skip_compose:
        log("按参数跳过合成")
        return

    # 2) 逐条合成
    results = {}
    for n in EPS:
        log("【%d】开始合成" % n)
        try:
            ok = C.build(n)
        except Exception as e:
            ok = False
            log("【%d】合成异常：%s" % (n, e))
        results[n] = {"compose": ok}
        log("【%d】合成 %s" % (n, "成功" if ok else "失败"))

    if skip_verify:
        return

    # 3) 逐条验收
    import verify_batch2 as V
    for n in EPS:
        if not results[n]["compose"]:
            log("【%d】合成未成功，跳过验收" % n)
            continue
        log("【%d】开始验收" % n)
        try:
            ok = V.verify(n)
        except Exception as e:
            ok = False
            log("【%d】验收异常：%s" % (n, e))
        results[n]["verify"] = ok
        log("【%d】验收 %s" % (n, "全过" if ok else "有不通过项"))

    log("汇总：" + json.dumps({k: {"合成": bool(v.get("compose")), "验收": bool(v.get("verify"))}
                              for k, v in results.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
