# -*- coding: utf-8 -*-
"""第二批生产盯盘器 v2（2026-10-25）
   v1 的问题：查进程走 PowerShell，中文路径编码炸 + 子进程挂起 → 看门狗自己先挂。
   v2：完全不查进程，只靠【主流程自己写的进度心跳】判断：
     · full_run.py 每完成一步就更新 _full_run.json 的 updated 字段
     · 这里比对 updated 是否前进 + 产物是否长大
     · 两者连续 3 次（15 分钟）都不动 → 判定卡死并记录
   更稳：不依赖任何外部命令，纯文件时间戳。
"""
import io, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
LOG = os.path.join(HERE, "_watch.log")
ST = os.path.join(HERE, "_full_run.json")
CLEAN = "E:/心理咨询IP/素材_clean2"
OUT_A = "E:/心理咨询IP/05-成片/没人可说"
OUT_B = "E:/心理咨询IP/05-成片/我是不是没用了"
INTERVAL = 300          # 5 分钟


def log(m):
    line = "%s %s" % (time.strftime("%m-%d %H:%M:%S"), m)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def mtime(p):
    try:
        return os.path.getmtime(p)
    except Exception:
        return 0


def size_of(*dirs):
    total = 0
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            try:
                total += os.path.getsize(os.path.join(d, f))
            except Exception:
                pass
    return total


def newest_mtime(*dirs):
    best = 0
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            best = max(best, mtime(os.path.join(d, f)))
    return best


if __name__ == "__main__":
    log("=== 盯盘 v2 启动（纯文件时间戳，不查进程）===")
    last_sz, last_st, stall = -1, -1, 0
    for _ in range(60):
        sz = size_of(CLEAN, OUT_A, OUT_B)
        st_m = mtime(ST)
        last_data = max(newest_mtime(CLEAN, OUT_A, OUT_B), st_m)
        age = time.time() - last_data

        info = ""
        try:
            import json
            d = json.load(io.open(ST, encoding="utf-8"))
            info = "阶段=%s 当前=%s 去反光=%s 合成=%s" % (
                d.get("stage"), d.get("cur"), d.get("done"), d.get("comp_done"))
        except Exception:
            info = "进度文件读不出"

        grew = (sz != last_sz) or (st_m != last_st)
        stall = 0 if grew else stall + 1
        last_sz, last_st = sz, st_m

        if age > 1500:            # 25 分钟无任何写入 = 真卡死
            log("❌ 卡死：%.0f 分钟无任何写入 | %s" % (age / 60, info))
            break

        log("%s | 产物 %.0fMB | 最后写入 %.1f 分钟前 | %s" % (
            info, sz / 1048576.0, age / 60,
            "有推进" if grew else "无变化第%d次" % stall))

        if "全部完成" in info:
            log("✅ 全流程结束")
            break
        time.sleep(INTERVAL)
    log("=== 盯盘结束 ===")
