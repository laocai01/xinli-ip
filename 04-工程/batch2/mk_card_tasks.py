# -*- coding: utf-8 -*-
"""重出全部 24 张卡片动画（_vc3 清理误删后重建）。
   ROOT 指向 batch2，frames 落在 batch2/_frames_card，出片到 batch2/cards_mp4/<ep>/
"""
import json, os, glob

R = "E:/心理咨询IP/04-工程/batch2"
HTML = "E:/心理咨询IP/04-卡片/batch2"
tasks = []
for n in range(1, 7):
    for h in sorted(glob.glob(os.path.join(HTML, str(n), "*.html"))):
        name = os.path.splitext(os.path.basename(h))[0]
        tasks.append({"html": h,
                      "out": os.path.join(R, "cards_mp4", str(n), name + ".mp4"),
                      "frames": 66, "fps": 30})   # 2.2s × 30fps：动画走完即静止
for n in range(1, 7):
    os.makedirs(os.path.join(R, "cards_mp4", str(n)), exist_ok=True)
json.dump(tasks, open(os.path.join(R, "tasks_all.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("任务数", len(tasks))
