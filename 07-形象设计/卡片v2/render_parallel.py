"""★ 并行渲染驱动 —— 把 24 个任务拆成 N 组，每组一个独立 python 进程并行跑
每个进程各有独立的 Chrome/profile，互不干扰。
用法: python render_parallel.py [组数=6]
"""
import os, sys, subprocess, json, time

BASE = r"E:/心理咨询IP/07-形象设计/卡片v2"
PY = sys.executable

# 全部任务（按类型分组 + 负载均衡）★ 2026-10-08 新卡名
GROUPS = {
    "g1": ["封面_新_第1讲", "封面_新_第2讲", "B1封面_第1讲", "B2封面_第2讲"],
    "g2": ["A2n_01钩子", "A2n_02痛点", "A2n_03机制", "A2n_04转折", "A2n_05方法", "A2n_06收束"],
    "g3": ["A3n_01钩子", "A3n_02总览", "A3n_03停", "A3n_04退", "A3n_05看", "A3n_06做", "A3n_07收束"],
    "g4": ["B1n_01钩子", "B1n_02场景", "B1n_03机制", "B1n_04点破", "B1n_05转折", "B1n_06方法", "B1n_07收束"],
    "g5": ["B2n_01钩子", "B2n_02痛点", "B2n_03机制", "B2n_04对比", "B2n_05方法", "B2n_06收束"],
    "g6": ["闭环_第1讲", "闭环_第2讲", "闭环_第3讲", "闭环_第4讲"],
}

if __name__ == "__main__":
    which = sys.argv[1:] or list(GROUPS)
    procs = []
    for g in which:
        names = GROUPS[g]
        cmd = [PY, os.path.join(BASE, "render_all.py")] + names
        log = open(os.path.join(BASE, f"_log_{g}.txt"), "w", encoding="utf-8")
        p = subprocess.Popen(cmd, cwd=BASE, stdout=log, stderr=subprocess.STDOUT)
        procs.append((g, p, log))
        print(f"启动 {g}: {len(names)} 个任务 (pid {p.pid})")
        time.sleep(1.5)          # 错开启动，避免 Chrome 同时抢占
    print(f"\n{len(procs)} 个进程已启动，等待完成…")
    for g, p, log in procs:
        p.wait()
        log.close()
        print(f"  {g} 完成 (exit {p.returncode})")
    print("\n全部完成")
