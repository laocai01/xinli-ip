#!/bin/bash
cd "E:/心理咨询IP/04-工程/batch2"
# 重新生成卡片渲染任务（4-6 集，按 plan 实际用到的卡）
python - <<'PY'
import json, os, sys
sys.path.insert(0, ".")
import compose_batch2 as C
R = "E:/心理咨询IP/04-工程/batch2"
tasks = []
for n in [4,5,6]:
    p = C.plan(n)
    for name, start, hold, tail in p["cards"]:
        h = os.path.join(R, "cards_v2_out", str(n), name + ".html")
        if not os.path.exists(h):
            print("缺HTML", n, name); continue
        os.makedirs(os.path.join(R, "cards_mp4_v2", str(n)), exist_ok=True)
        tasks.append({"html": h,
                      "out": os.path.join(R, "cards_mp4_v2", str(n), name + ".mp4"),
                      "frames": 96, "fps": 30})
json.dump(tasks, open(os.path.join(R,"tasks_v2_346.json"),"w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("渲染任务数", len(tasks))
PY
for i in 0 1 2 3; do
  python render_cards.py tasks_v2_346.json $i 4 > _rcL$i.log 2>&1 &
done
wait
echo "卡片mp4完成: $(ls cards_mp4_v2/4/*.mp4 cards_mp4_v2/5/*.mp4 cards_mp4_v2/6/*.mp4 2>/dev/null | wc -l)"
