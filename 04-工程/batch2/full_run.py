# -*- coding: utf-8 -*-
"""第二批全流程无人值守（2026-10-24 返工版）
   顺序：① 去反光(素材_clean2) → ② 合成成片 → ③ 26 项验收
   写进度到 _full_run.json，供随时查"跑到哪了"。
"""
import io, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
PY = sys.executable
ST = os.path.join(HERE, "_full_run.json")


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
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    return r.returncode


if __name__ == "__main__":
    t0 = time.time()
    save(stage="去反光", cur=0, done=[], fail=[])
    done, fail = [], []
    for n in range(1, 7):
        save(stage="去反光", cur=n, done=done, fail=fail)
        rc = run([PY, "rebuild_clean.py", str(n)], "_full_clean.log")
        (done if rc == 0 else fail).append(n)
    save(stage="去反光完成", done=done, fail=fail)

    done2, fail2 = [], []
    for n in range(1, 7):
        save(stage="合成", cur=n, clean_done=done, clean_fail=fail,
             comp_done=done2, comp_fail=fail2)
        rc = run([PY, "-c",
                  "import sys; sys.path.insert(0,'.'); import compose_batch2 as C; "
                  "sys.exit(0 if C.build(%d) else 1)" % n], "_full_compose.log")
        (done2 if rc == 0 else fail2).append(n)
    save(stage="合成完成", comp_done=done2, comp_fail=fail2)

    rc = run([PY, "verify_batch2.py"] + [str(i) for i in range(1, 7)], "_full_verify.log")
    save(stage="全部完成", verify_rc=rc,
         minutes=round((time.time() - t0) / 60, 1),
         clean_done=done, clean_fail=fail, comp_done=done2, comp_fail=fail2)
