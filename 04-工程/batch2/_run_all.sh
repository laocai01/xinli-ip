#!/bin/bash
# 批量合成 2-6 集（串行，8 核机器一次只能跑一个 ffmpeg）
cd "E:/心理咨询IP/04-工程/batch2"
for n in 2 3 4 5 6; do
  echo "===== EP$n START $(date '+%H:%M:%S') ====="
  python run_one_c.py $n > _ep$n.log 2>&1
  echo "===== EP$n DONE $(date '+%H:%M:%S') ====="
  grep "RESULT" _ep$n.log
done
echo ALL_EPISODES_DONE
