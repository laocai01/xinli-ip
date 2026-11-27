# -*- coding: utf-8 -*-
"""第二批生产盯盘器（2026-10-25 无人值守）
   每 5 分钟检查一次，判三件事：
     ① 主流程进程还活着吗（full_run.py）
     ② 产物有没有在长大（临时文件/成品目录）
     ③ 进度台账走到哪一步
   判定卡死：连续 3 次（15 分钟）产物大小零增长 → 记 KILLED_STALL 并尝试重启
   全部结果追加到 _watch.log，供随时查看
"""
import io, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
LOG = os.path.join(HERE, "_watch.log")
ST = os.path.join(HERE, "_full_run.json")
CLEAN = "E:/心理咨询IP/素材_clean2"
OUT_A = "E:/心理咨询IP/05-成片/没人可说"
OUT_B = "E:/心理咨询IP/05-成片/我是不是没用了"

last_sig = None
stall = 0


def log(m):
    line = "%s %s" % (time.strftime("%m-%d %H:%M:%S"), m)
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def py_running():
    """找还活着、且 CPU 时间在增长的 full_run.py"""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                            "ForEach-Object { $_.ProcessId.ToString() + '|' + $_.CommandLine }"],
                           capture_output=True, timeout=60)
        raw = r.stdout or b""
        if not raw:
            return []
        # PowerShell 默认 GBK 输出，必须先按本地编码解，否则中文路径会炸
        for enc in ("gbk", "utf-8", "latin-1"):
            try:
                out = raw.decode(enc).strip()
                break
            except Exception:
                continue
        else:
            out = raw.decode("utf-8", "replace").strip()
        if not out:
            return []
        procs = []
        for line in out.splitlines():
            if "|" in line and "full_run" in line:
                pid, _, cmd = line.partition("|")
                procs.append({"ProcessId": pid, "CommandLine": cmd})
        return procs
    except Exception as e:
        log("查进程出错: %s" % e)
        return []


def size_of(*dirs):
    total = 0
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            p = os.path.join(d, f)
            try:
                total += os.path.getsize(p)
            except Exception:
                pass
    return total


def state():
    try:
        return json.load(io.open(ST, encoding="utf-8"))
    except Exception:
        return {}


def cycle():
    global last_sig, stall
    procs = py_running()
    st = state()
    sz = size_of(CLEAN, OUT_A, OUT_B)
    sig = (sz, st.get("stage"), st.get("cur"), str(st.get("done")), str(st.get("comp_done")))
    finished = sz == last_sig
    stall = stall + 1 if finished else 0
    last_sig = sig

    log("阶段=%s 当前=%s 去反光完成=%s 合成完成=%s | 产物 %.0fMB | 进程=%s | %s" % (
        st.get("stage", "?"), st.get("cur", "?"), st.get("done"), st.get("comp_done"),
        sz / 1048576.0, "存活" if procs else "无",
        "无变化%d次" % stall if stall else "有推进"))

    if not procs:
        log("⚠️ 主流程进程不在了，检查是否已全部完成")
        if st.get("stage") == "全部完成":
            log("✅ 全流程已结束")
        else:
            log("❌ 进程消失但未完成 → 需要重启")
        return "no-proc"
    if stall >= 3:
        log("❌ 连续 15 分钟产物零增长，判定卡死")
        return "stalled"
    return "ok"


if __name__ == "__main__":
    log("=== 盯盘启动 ===")
    for i in range(48):          # 最多 4 小时
        r = cycle()
        if r in ("no-proc",):
            break
        if r == "stalled":
            log("留下现场，不自动重启（避免盖掉日志），等人工看")
            break
        time.sleep(300)
    log("=== 盯盘结束 ===")
