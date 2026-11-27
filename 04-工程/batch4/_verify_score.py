# -*- coding: utf-8 -*-
"""候选打分裁决：同一音频，用不同强约束 prompt 诱发候选，再看模型自发输出 vs 偏置输出的差异
+ 每个微片跑 5 个温度，统计字面命中
"""
import os, json, subprocess

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HOME"] = r"E:\工具环境\whisper\models"
from faster_whisper import WhisperModel

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"
LISTEN = r"E:/心理咨询IP/04-工程/batch4/_listen"
TMP = r"E:/心理咨询IP/04-工程/batch4/_verify_tmp"

_cache = {}
def get_model(n):
    if n not in _cache:
        _cache[n] = WhisperModel(n, device="cpu", compute_type="int8", download_root=r"E:\工具环境\whisper\models")
    return _cache[n]

def cut(src, dst, a, b):
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(round(a, 2)), "-t", str(round(b - a, 2)),
                    "-i", src, "-vn", "-ac", "1", "-ar", "16000",
                    "-af", "highpass=f=80,afftdn=nf=-25", "-c:a", "pcm_s16le", dst], check=True)

def run(mname, wav, prompt=None, temp=0.0):
    segs, _ = get_model(mname).transcribe(
        wav, language="zh", beam_size=5, vad_filter=False,
        condition_on_previous_text=False, temperature=[temp],
        without_timestamps=True, initial_prompt=prompt)
    return "".join(s.text.strip() for s in segs).strip()

WINDOWS = [
    ("A1_断x了",   "1_开头.mp3", 1.3, 3.2),
    ("A1b_断x了紧", "1_开头.mp3", 1.9, 3.0),
    ("A2_算x算三天", "1_开头.mp3", 2.7, 5.0),
    ("B1_不给x整窗", "5_画数.mp3", 4.6, 8.0),
    ("B2_不给x紧切", "5_画数.mp3", 5.9, 7.7),
]
PROMPTS = {
    "A1_断x了":   [None, "断更", "断根", "接下来断更了两天", "接下来断根了两天"],
    "A1b_断x了紧": [None, "断更", "断根"],
    "A2_算x算三天": [None, "算钱就算三天", "算前就算三天", "算上今天算三天", "算今天就算三天"],
    "B1_不给x整窗": [None, "画数", "画圈", "计数", "说话"],
    "B2_不给x紧切": [None, "画数", "画圈", "计数", "说话"],
}
TEMPS = [0.0, 0.3, 0.6, 0.9, 1.0]

out = {}
for tag, fname, a, b in WINDOWS:
    for mname in ("small", "base"):
        wav = os.path.join(TMP, "w_%s_%s.wav" % (tag.split("_")[0], mname))
        cut(os.path.join(LISTEN, fname), wav, a, b)
        for p in PROMPTS[tag]:
            lines = [run(mname, wav, p, t) for t in TEMPS]
            out["%s|%s|%s" % (tag, mname, p)] = lines
            print("%-14s %-5s prompt=%-12s %s" % (tag, mname, str(p)[:12], json.dumps(lines, ensure_ascii=False)), flush=True)

with open(os.path.join(TMP, "results_score.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("DONE")
