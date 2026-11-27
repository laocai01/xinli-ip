#!/bin/bash
cd "E:/心理咨询IP/04-工程/batch2"
rm -f "E:/心理咨询IP/05-成片/我是不是没用了/"*.tmp.mp4 2>/dev/null
for n in 4 5 6; do
  echo "===== EP$n START $(date '+%H:%M:%S') ====="
  python run_one_c.py $n > _ep$n.log 2>&1
  grep "RESULT" _ep$n.log
done
echo ALL_DONE
