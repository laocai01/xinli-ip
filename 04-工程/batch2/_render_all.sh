#!/bin/bash
# 并行渲染 51 张卡片（4 lane）
cd "E:/心理咨询IP/04-工程/batch2"
for i in 0 1 2 3; do
  python render_cards.py tasks_v2_346.json $i 4 > _rc$i.log 2>&1 &
done
wait
echo "ALL_DONE"
ls cards_mp4_v2/3/*.mp4 cards_mp4_v2/4/*.mp4 cards_mp4_v2/5/*.mp4 cards_mp4_v2/6/*.mp4 2>/dev/null | wc -l
