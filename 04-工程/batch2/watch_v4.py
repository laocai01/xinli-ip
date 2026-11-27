# -*- coding: utf-8 -*-
"""心跳看门狗 v4：每 5 分钟检查一次，25 分钟无推进就报警。
   判据（不靠进程存活，靠产物是否真的在长）：
     - 转录阶段：draft_*.json 数量是否增加
     - 出图阶段：插画目录文件数是否增加
     - 合成阶段：_run_*.json 的 done 是否增加 / tmp.mp4 是否在长
   只写 _beat.log，不改任何生产文件。"""
import os
import time
import io

ROOT = "E:/心理咨询IP/04-工程/batch2"
LOG = os.path.join(ROOT, "_beat.log")
INTERVAL = 300          # 5 分钟
STALL_LIMIT = 5 * 60    # 5 分钟无推进 = 立刻报警（董事长要求）

STAT_JSON = os.path.join(ROOT, "_run_current.json")  # 由当前任务写入，避免读到历史状态
ILLUST = os.path.join(ROOT, "illust")


def snap():
    """返回一个'推进指纹'，能反映任何阶段的进展"""
    parts = []
    # 转录
    n_draft = len([f for f in os.listdir(ROOT) if f.startswith("draft_") and f.endswith(".json")])
    parts.append("draft=%d" % n_draft)
    # 插画
    n_il = 0
    if os.path.isdir(ILLUST):
        n_il = len([f for f in os.listdir(ILLUST) if f.endswith((".png", ".mp4"))])
    parts.append("illust=%d" % n_il)
    # 合成进度
    done = []
    if os.path.exists(STAT_JSON):
        try:
            import json
            d = json.load(io.open(STAT_JSON, encoding="utf-8"))
            done = d.get("done", [])
            parts.append("done=%s cur=%s" % (done, d.get("cur")))
        except Exception:
            parts.append("stat_err")
    else:
        parts.append("done=[]")
    # 正在写的成片
    tot = 0
    for d in ["E:/心理咨询IP/05-成片/没人可说", "E:/心理咨询IP/05-成片/我是不是没用了"]:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.endswith(".tmp.mp4"):
                try:
                    tot += os.path.getsize(os.path.join(d, f))
                except Exception:
                    pass
    parts.append("writing=%dMB" % (tot // 1048576))
    return " | ".join(parts), len(done), n_il, n_draft, tot


def main():
    last_fp = None
    last_change = time.time()
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write("\n%s === 心跳看门狗 v4 启动（每5分钟，5分钟无推进即报警）===\n"
                % time.strftime("%m-%d %H:%M:%S"))
    while True:
        try:
            fp, nd, ni, nr, wb = snap()
            now = time.time()
            # 判推进：指纹变了 或 tmp 在长
            key = (nd, ni, nr, wb // 3)   # tmp 每 3MB 算一次变化
            if last_fp is None or key != last_fp:
                last_fp = key
                last_change = now
                state = "有推进"
            else:
                idle = now - last_change
                state = "⚠️无变化 %.0f 分钟" % (idle / 60)
                if idle > STALL_LIMIT:
                    state = "🚨 卡死 %.0f 分钟，需立刻处理" % (idle / 60)
            with io.open(LOG, "a", encoding="utf-8") as f:
                f.write("%s %s | %s\n" % (time.strftime("%m-%d %H:%M:%S"), state, fp))
        except Exception as e:
            with io.open(LOG, "a", encoding="utf-8") as f:
                f.write("%s 看门狗异常 %s\n" % (time.strftime("%m-%d %H:%M:%S"), e))
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
