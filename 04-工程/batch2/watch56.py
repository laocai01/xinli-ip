# -*- coding: utf-8 -*-
"""盯盘 v3：盯 run_2to6.py（合成 2-6 + 补去反光）
   只读文件时间戳，不查进程。每 5 分钟一条写 _watch56.log。
   判卡死：产物 + 进度文件连续 25 分钟无写入。
"""
import io, json, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
LOG = os.path.join(HERE, "_watch56.log")
ST = os.path.join(HERE, "_run56.json")
DIRS = ["E:/心理咨询IP/素材_clean2",
        "E:/心理咨询IP/05-成片/没人可说",
        "E:/心理咨询IP/05-成片/我是不是没用了"]


def log(m):
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write("%s %s\n" % (time.strftime("%m-%d %H:%M:%S"), m))


def scan():
    total, newest = 0, 0
    for d in DIRS:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            p = os.path.join(d, f)
            try:
                total += os.path.getsize(p)
                newest = max(newest, os.path.getmtime(p))
            except Exception:
                pass
    return total, newest


if __name__ == "__main__":
    log("=== 盯盘 v3 启动（盯 run_2to6）===")
    last = -1
    for _ in range(60):
        sz, newest = scan()
        try:
            st = json.load(io.open(ST, encoding="utf-8"))
        except Exception:
            st = {}
        age = (time.time() - max(newest, os.path.getmtime(ST) if os.path.exists(ST) else 0)) / 60.0
        grew = sz != last
        last = sz
        info = "阶段=%s 当前=%s 合成完成=%s 失败=%s" % (
            st.get("stage"), st.get("cur"), st.get("comp_done"), st.get("comp_fail"))
        log("%s | 产物 %.0fMB | 最后写入 %.1f 分钟前 | %s" % (
            info, sz / 1048576.0, age, "有推进" if grew else "无变化"))
        if age > 25:
            log("❌ 卡死：25 分钟无写入")
            break
        if st.get("stage") == "全部完成":
            log("✅ 全部完成 %s" % info)
            break
        time.sleep(300)
    log("=== 盯盘结束 ===")
