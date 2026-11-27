#!/bin/bash
cd "E:/心理咨询IP/04-工程/batch2"
powershell -NoProfile -Command "Get-Process ffmpeg -ErrorAction SilentlyContinue | Stop-Process -Force" 2>/dev/null
sleep 2

# 1) 重新生成 5 集卡片 HTML
for n in 2 3 4 5 6; do
  python render_cards_v2.py $n > _rc$n.log 2>&1 || echo "HTML失败 ep$n"
done
echo "HTML: $(ls cards_v2_out/*/*.html 2>/dev/null | wc -l) 个"

# 2) 生成渲染任务（只渲染本次 plan 用到的卡片）
python - <<'PY'
import json, os, sys
sys.path.insert(0, ".")
import compose_batch2 as C
R = "E:/心理咨询IP/04-工程/batch2"
tasks = []
for n in [2,3,4,5,6]:
    p = C.plan(n)
    for name, start, hold, tail in p["cards"]:
        h = os.path.join(R, "cards_v2_out", str(n), name + ".html")
        if not os.path.exists(h):
            print("缺HTML", n, name); continue
        tasks.append({"html": h,
                      "out": os.path.join(R, "cards_mp4_v2", str(n), name + ".mp4"),
                      "frames": 96, "fps": 30})
json.dump(tasks, open(os.path.join(R,"tasks_v2_all.json"),"w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("任务数", len(tasks))
PY

# 3) 4 lane 并行渲染卡片
for i in 0 1 2 3; do
  python render_cards.py tasks_v2_all.json $i 4 > _rcL$i.log 2>&1 &
done
wait
echo "卡片完成: $(ls cards_mp4_v2/*/*.mp4 2>/dev/null | wc -l)"

# 4) 串行合成 2-6
for n in 2 3 4 5 6; do
  echo "===== EP$n START $(date '+%H:%M:%S') ====="
  python run_one_c.py $n > _ep$n.log 2>&1
  grep "RESULT" _ep$n.log
done
echo ALL_EPISODES_DONE
