# -*- coding: utf-8 -*-
"""校准版微片：按 small raw 时间戳定位，无偏置 prompt + 多温度采样 + 双模型"""
import os, json, subprocess, collections

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HOME"] = r"E:\工具环境\whisper\models"
from faster_whisper import WhisperModel

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"
LISTEN = r"E:/心理咨询IP/04-工程/batch4/_listen"
TMP = r"E:/心理咨询IP/04-工程/batch4/_verify_tmp"
MODEL_ROOT = r"E:\工具环境\whisper\models"

_cache = {}
def get_model(n):
    if n not in _cache:
        _cache[n] = WhisperModel(n, device="cpu", compute_type="int8", download_root=MODEL_ROOT)
    return _cache[n]

def cut(src, dst, ss, t, pad=0.25):
    a = max(0.0, ss - pad); b = t + pad
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(a), "-t", str(round(b - a, 2)), "-i", src,
                    "-vn", "-ac", "1", "-ar", "16000",
                    "-af", "highpass=f=80,afftdn=nf=-25", "-c:a", "pcm_s16le", dst], check=True)
    return a, round(b - a, 2)

def run(mname, wav, temps=(0.0, 0.3, 0.6, 0.9, 1.0)):
    outs = []
    for t in temps:
        m = get_model(mname)
        segs, _ = m.transcribe(wav, language="zh", beam_size=5, vad_filter=False,
                               condition_on_previous_text=False, temperature=[t],
                               without_timestamps=True)
        outs.append("".join(s.text.strip() for s in segs).strip())
    return outs

micro = [
    # 窗口(秒, 在 listen 文件坐标系)  —— 按 small raw 时间戳
    ("A1_断x了",      "1_开头.mp3", 1.3, 3.0),
    ("A2_算x算三天",  "1_开头.mp3", 2.7, 5.0),
    ("A3_下一讲",      "1_开头.mp3", 4.9, 8.0),
    ("B1_不给x整窗",   "5_画数.mp3", 4.6, 8.0),
    ("B2_不给x紧切",   "5_画数.mp3", 5.8, 7.6),
]
res = {}
for tag, fname, ss, tt in micro:
    wav0 = os.path.join(TMP, "_w.wav")
    a, d = cut(os.path.join(LISTEN, fname), wav0, ss, tt)
    line = {}
    for mname in ("small", "base"):
        wav = os.path.join(TMP, "%s_%s.wav" % (tag, mname))
        os.replace(wav0, wav)
        cut(os.path.join(LISTEN, fname), wav, ss, tt)
        outs = run(mname, wav)
        line[mname] = outs
        print("%-16s %-6s win=[%.2f,+%.2f] => %s" % (tag, mname, a, d, json.dumps(outs, ensure_ascii=False)), flush=True)
    res[tag] = line
with open(os.path.join(TMP, "results_micro2.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("DONE")
