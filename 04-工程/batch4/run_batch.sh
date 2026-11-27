#!/bin/bash
# 批量出片：卡片渲染串行（避免 Chrome 抢端口），合成串行（避免 ffmpeg 抢写）
cd "E:/心理咨询IP/04-工程/batch4"
PY="E:/Hermes/hermes-agent/venv/Scripts/python.exe"
for n in "$@"; do
  echo "=== 第 $n 条 开始 $(date +%H:%M:%S) ==="
  $PY compose_b4.py $n > _c$n.log 2>&1
  echo "第 $n 条 exit=$? 完成于 $(date +%H:%M:%S)"
  grep -E "RESULT|❌" _c$n.log | tail -3
  sleep 3
done
echo "ALL DONE $(date +%H:%M:%S)"
