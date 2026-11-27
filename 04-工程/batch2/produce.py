# -*- coding: utf-8 -*-
"""★ 唯一合法出片入口 · 自检 → 合成 → 闸门 → 自动固定

用法：
    python produce.py 5              # 出第5集，全流程闭环
    python produce.py 5 6 7          # 串行出多集（绝不并发）

这个脚本存在的意义：
    以前是「人手动开跑 → 人自己记得验收 → 人自己改名」，三个环节全靠记性，
    任何一个忘了就出坏片。现在把三步焊死成一条链，任何一关不过就停，
    不允许产出未过闸门的"成品"。

流程：
    1. 统一并发锁   —— 已有 ffmpeg/run_one_c 在跑就拒绝启动
    2. 开跑前自检   —— preflight.py 七项，全过才继续
    3. 合成         —— compose_batch2.build(n)，成品落 .tmp.mp4
    4. 六道闸门     —— final_gate.py，全过才算合格
    5. 自动固定     —— 只有闸门全过才 mv 成正式名；不过就保留 .tmp.mp4 报警

退出码 0 = 已交付；非 0 = 未交付（看日志）。
"""
import os
import shutil
import subprocess
import sys
import time

R = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(R))
sys.path.insert(0, R)

EP_NAMES = {
    2: ("没人可说", "第24条_没人可说第5讲_你一歇下来就发慌_20261024.mp4"),
    3: ("没人可说", "第25条_没人可说第6讲_两口子没话说了是从哪一天开始的_20261024.mp4"),
    4: ("我是不是没用了", "第26条_我是不是没用了第4讲_怎么把话说到孩子心里去_20261024.mp4"),
    5: ("我是不是没用了", "第27条_我是不是没用了第5讲_你越来越不敢麻烦孩子了_20261024.mp4"),
    6: ("我是不是没用了", "第28条_我是不是没用了第6讲_如果遇见二十岁的自己你会说什么_20261024.mp4"),
}


def _run(cmd, log=None):
    kw = {}
    if log:
        f = open(log, "w", encoding="utf-8")
        kw = dict(stdout=f, stderr=subprocess.STDOUT)
    try:
        return subprocess.run([sys.executable] + cmd, cwd=R, text=True,
                              encoding="utf-8", errors="ignore", **kw)
    finally:
        if log:
            f.close()


def produce(n):
    line = "=" * 60
    print("\n" + line + "\nEP%d 开跑 %s\n%s" % (n, time.strftime("%H:%M:%S"), line), flush=True)

    # ── 第1步：自检（含并发锁）────────────────────────────
    r = _run(["preflight.py", str(n)], log=os.path.join(R, "_pf%d.log" % n))
    if r.returncode != 0:
        print("❌ EP%d 自检未过，拒绝开跑。看 _pf%d.log" % (n, n), flush=True)
        print(open(os.path.join(R, "_pf%d.log" % n), encoding="utf-8").read()[-800:], flush=True)
        return False
    print("✅ 自检通过", flush=True)

    # ── 第2步：合成 ───────────────────────────────────────
    print("→ 合成中（约 16 分钟）...", flush=True)
    t0 = time.time()
    r = _run(["run_one_c.py", str(n)], log=os.path.join(R, "_ep%d.log" % n))
    if r.returncode != 0 or "RESULT True" not in open(os.path.join(R, "_ep%d.log" % n),
                                                      encoding="utf-8", errors="ignore").read():
        print("❌ EP%d 合成失败，看 _ep%d.log" % (n, n), flush=True)
        return False
    print("✅ 合成完成 %.1f 分钟" % ((time.time() - t0) / 60), flush=True)

    # ── 第3步：找成品（.tmp.mp4）──────────────────────────
    folder, name = EP_NAMES[n]
    outdir = os.path.join(ROOT, "05-成片", folder)
    tmp = os.path.join(outdir, name + ".tmp.mp4")
    if not os.path.exists(tmp):
        final = os.path.join(outdir, name)
        if not os.path.exists(final):
            print("❌ 找不到成品", flush=True)
            return False
        tmp = final

    # ── 第4步：六道闸门 ───────────────────────────────────
    print("→ 验收闸门...", flush=True)
    r = _run(["final_gate.py", str(n), tmp], log=os.path.join(R, "_gate%d.log" % n))
    gate_log = open(os.path.join(R, "_gate%d.log" % n), encoding="utf-8", errors="ignore").read()
    print(gate_log.strip(), flush=True)
    if r.returncode != 0:
        print("❌ EP%d 未过闸门，不交付。坏片留在 %s 供排查"
              % (n, os.path.basename(tmp)), flush=True)
        return False

    # ── 第5步：只有全过才固定 ─────────────────────────────
    final = os.path.join(outdir, name)
    try:
        if os.path.exists(final):
            os.remove(final)
        os.replace(tmp, final)
        print("✅ EP%d 已交付：%s  %.0fMB"
              % (n, name, os.path.getsize(final) / 1048576), flush=True)
        return True
    except OSError as e:
        print("⚠️ EP%d 改名失败（%s），成品仍在 %s" % (n, e, os.path.basename(tmp)), flush=True)
        return False


def main():
    eps = [int(x) for x in sys.argv[1:]] or [2]
    ok_all = True
    for n in eps:            # ★ 严格串行，绝不并发
        if not produce(n):
            ok_all = False
            print("\n⚠️ EP%d 未交付，停止后续（避免带病连跑）" % n, flush=True)
            break
    print("\n" + ("🎉 全部交付完成" if ok_all else "❌ 有未交付项"), flush=True)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
