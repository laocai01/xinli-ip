#!/bin/bash
cd "E:/心理咨询IP/04-工程/batch2"
# 重新生成任务清单
python - <<'PY'
import json, os, glob
R = "E:/心理咨询IP/04-工程/batch2"
tasks = []
for n in [3,4,5,6]:
    for h in sorted(glob.glob(os.path.join(R, "cards_v2_out", str(n), "*.html"))):
        name = os.path.splitext(os.path.basename(h))[0]
        os.makedirs(os.path.join(R, "cards_mp4_v2", str(n)), exist_ok=True)
        tasks.append({"html": h,
                      "out": os.path.join(R, "cards_mp4_v2", str(n), name + ".mp4"),
                      "frames": 66, "fps": 30})
json.dump(tasks, open(os.path.join(R,"tasks_v2_346.json"),"w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("任务数", len(tasks))
PY
# 4 lane 并行渲染
for i in 0 1 2 3; do
  python render_cards.py tasks_v2_346.json $i 4 > _rc$i.log 2>&1 &
done
wait
echo "卡片完成: $(ls cards_mp4_v2/3/*.mp4 cards_mp4_v2/4/*.mp4 cards_mp4_v2/5/*.mp4 cards_mp4_v2/6/*.mp4 2>/dev/null | wc -l)"
# 串行合成 3-6
for n in 3 4 5 6; do
  echo "===== EP$n START $(date '+%H:%M:%S') ====="
  python run_one_c.py $n > _ep$n.log 2>&1
  grep "RESULT" _ep$n.log
done
echo ALL_EPISODES_DONE
