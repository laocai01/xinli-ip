"""★ 四条成片并行合成（加速版）
用法: python make_parallel.py
把 A2/A3/B1/B2 四条各起一个进程同时跑，4 倍提速。
"""
import os, sys, subprocess, time

PROJ = r"E:/心理咨询IP/04-工程"
KEYS = ["A4", "A5", "B3", "B4"]   # ★ 2026-10-08 新四条

if __name__ == "__main__":
    print("=== 并行合成四条成片 ===")
    procs = []
    for k in KEYS:
        p = subprocess.Popen([sys.executable, os.path.join(PROJ, "make_episode.py"), k],
                             cwd=PROJ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, errors="ignore")
        procs.append((k, p))
        print(f"  启动 {k}: pid {p.pid}")
    print("\n4 个进程已启动，等待完成…\n")
    t0 = time.time()
    for k, p in procs:
        out, _ = p.communicate()
        ok = "OK" if p.returncode == 0 else f"FAIL({p.returncode})"
        print(f"  {k} 完成 [{ok}]  用时 {time.time()-t0:.0f}s")
        for line in (out or "").splitlines():
            if "OK ->" in line or "🗑" in line or "exit:" in line:
                print("    ", line.strip())
    print("\n全部完成")
