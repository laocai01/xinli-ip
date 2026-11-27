"""★ 成片目录清理器 —— 只保留最终版（2026-10-08 董事长铁律）
规则：E:/心理咨询IP/05-成片/ 每条片子只留 1 个 mp4，其余全删。
用法: python clean_films.py          # 预演（只看不删）
      python clean_films.py --go     # 真删
"""
import os, sys, re, time, subprocess

D = r"E:/心理咨询IP/05-成片"
GO = "--go" in sys.argv

# 最终版命名规范：第XX条_<标题>.mp4（不含 _成片 / v2 / 版 等过程后缀）
FINAL_RE = re.compile(r"^第\d{2}条_.+\.mp4$")
# 过程稿特征词（出现即视为旧版）
BAD_WORDS = ["_成片", "_v2", "_v3", "版_", "_最终", "_备份", "_旧"]
# ★ 保护名单：已发布的正式片，任何情况都不删
PROTECT = ["第01条_我考了个不能赚钱的证_新LOGO版_20261006.mp4"]

def is_final(f):
    if not f.endswith(".mp4"): return False
    if f in PROTECT: return True            # 保护名单优先
    if not FINAL_RE.match(f): return False
    if any(w in f for w in BAD_WORDS): return False
    return True

def main():
    files = [f for f in os.listdir(D) if f.endswith(".mp4")]
    keep, kill = [], []
    for f in files:
        (keep if is_final(f) else kill).append(f)

    print("=" * 70)
    print(f"目录: {D}")
    print(f"{'保留（最终版）':<40} {'大小':>10}")
    print("-" * 70)
    for f in sorted(keep):
        print(f"  ✅ {f:<38} {os.path.getsize(os.path.join(D,f))//1024//1024:>8}MB")
    print()
    print(f"{'删除（过程稿/旧版）':<40}")
    print("-" * 70)
    for f in sorted(kill):
        print(f"  🗑 {f:<38} {os.path.getsize(os.path.join(D,f))//1024//1024:>8}MB")

    print(f"\n保留 {len(keep)} 个 / 删除 {len(kill)} 个")
    if not GO:
        print("\n（预演模式，加 --go 才真删）")
        return

    print("\n执行删除…")
    for f in kill:
        p = os.path.join(D, f)
        for attempt in range(3):
            try:
                os.remove(p); print(f"  ✅ 已删 {f}"); break
            except PermissionError:
                if attempt == 0:
                    print(f"  ⏳ {f} 被占用，尝试解除…")
                    # ★ 只杀 ffmpeg/Chrome 残留，绝不杀 Hermes 本身（否则会中断自己）
                    subprocess.run(["powershell", "-NoProfile", "-Command",
                                    "Get-Process ffmpeg,chrome -EA SilentlyContinue | Stop-Process -Force"],
                                   capture_output=True)
                    time.sleep(2)
                elif attempt == 1:
                    os.rename(p, p + ".todelete")
                    print(f"  ✅ 已改名待删 {f}")
                    break
                else:
                    print(f"  ❌ 删不掉 {f}")
    # 清 .todelete
    for f in os.listdir(D):
        if f.endswith(".todelete"):
            try: os.remove(os.path.join(D,f)); print(f"  ✅ 已清 {f}")
            except Exception: pass

if __name__ == "__main__":
    main()
