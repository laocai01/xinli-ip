# -*- coding: utf-8 -*-
"""第 2–6 条统一重出（2026-10-25 董事会长指示：第1条已交付不再改，只改后5条）
   与 full_run.py 的区别：full_run 会跑去反光+合成+验收全套；
   这里只做「等去反光齐 → 合成 2..6 → 验收 2..6」，避免与主流程重复合成抢 CPU。
   调色已加重（对比1.16/亮度-0.045/gamma1.10/暗角PI/5.6/颗粒6）。
"""
import io, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
PY = sys.executable
ST = os.path.join(HERE, "_run56.json")


def save(**kw):
    d = {}
    if os.path.exists(ST):
        try:
            d = json.load(io.open(ST, encoding="utf-8"))
        except Exception:
            d = {}
    d.update(kw)
    d["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    io.open(ST, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2))


def run(cmd, logf):
    with io.open(logf, "a", encoding="utf-8") as f:
        f.write("\n$ %s\n" % " ".join(cmd))
        f.flush()
        return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode


def wait_clean(n, timeout=3600):
    """等第 n 条去反光成品出现（素材_clean2/n.mp4），超时返回 False"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.exists("%s/素材_clean2/%d.mp4" % (HERE.replace("/04-工程/batch2", ""), n)):
            return True
        time.sleep(20)
    return False


if __name__ == "__main__":
    t0 = time.time()
    save(stage="等去反光", waiting=[5, 6], comp_done=[], comp_fail=[])
    # 眼窗先补齐（合成要用）
    for n in range(2, 7):
        src = "E:/心理咨询IP/素材_clean/eye_%d.mp4" % n
        dst = "E:/心理咨询IP/素材_clean2/eye_%d.mp4" % n
        if os.path.exists(src) and not os.path.exists(dst):
            import shutil
            shutil.copy2(src, dst)

    done, fail = [], []
    for n in range(2, 7):
        # 缺去反光就自己补（find_eyes/calibrate 都是幂等的）
        if not os.path.exists("E:/心理咨询IP/素材_clean2/%d.mp4" % n):
            save(stage="补去反光", cur=n, comp_done=done, comp_fail=fail)
            rc0 = run([PY, "rebuild_clean.py", str(n)], "_run56_clean.log")
            if rc0 != 0 or not os.path.exists("E:/心理咨询IP/素材_clean2/%d.mp4" % n):
                fail.append(n)
                continue
        save(stage="合成", cur=n, comp_done=done, comp_fail=fail)
        rc = run([PY, "-c",
                  "import sys; sys.path.insert(0,'.'); import compose_batch2 as C; "
                  "sys.exit(0 if C.build(%d) else 1)" % n], "_run56_compose.log")
        (done if rc == 0 else fail).append(n)
    save(stage="合成完成", comp_done=done, comp_fail=fail)

    if done:
        run([PY, "verify_batch2.py"] + [str(i) for i in done], "_run56_verify.log")
    save(stage="全部完成", comp_done=done, comp_fail=fail,
         minutes=round((time.time() - t0) / 60, 1))
