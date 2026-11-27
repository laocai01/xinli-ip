# -*- coding: utf-8 -*-
"""B 窗口 8.98~10.6s 精查：多切法 x 双模型 x 候选偏置 x 温度采样，并输出词级概率"""
import os, json, subprocess

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HOME"] = r"E:\工具环境\whisper\models"
from faster_whisper import WhisperModel

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"
SRC = r"E:/心理咨询IP/素材/5.mp4"
TMP = r"E:/心理咨询IP/04-工程/batch4/_verify_tmp"

_cache = {}
def get_model(n):
    if n not in _cache:
        _cache[n] = WhisperModel(n, device="cpu", compute_type="int8", download_root=r"E:\工具环境\whisper\models")
    return _cache[n]

def cut(dst, ss, t, af="highpass=f=80,afftdn=nf=-25"):
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(ss), "-t", str(t), "-i", SRC,
                    "-vn", "-ac", "1", "-ar", "16000", "-af", af, "-c:a", "pcm_s16le", dst], check=True)

def run(mname, wav, prompt=None, temp=0.0, words=False):
    segs, _ = get_model(mname).transcribe(
        wav, language="zh", beam_size=5, vad_filter=False, condition_on_previous_text=False,
        temperature=[temp], without_timestamps=not words, word_timestamps=words,
        initial_prompt=prompt)
    txt = ""
    wl = []
    for s in segs:
        txt += s.text.strip()
        if words and s.words:
            wl += [dict(w=w.word, p=round(w.probability, 3)) for w in s.words]
    return txt, wl

res = {}
# 原片坐标系：窗口在 118.0+?  -> 用 116.5 起点换算：B_full 中 8.98s 对应原片 125.48s
WINS = [("w1", 125.3, 1.6), ("w2", 125.5, 1.2), ("w3", 125.2, 2.0)]
CANDS = [None, "我不给你画数", "我不给你画素", "我不给你画圈", "我不给你计数", "我不给你说话"]
for wname, ss, t in WINS:
    for mname in ("small", "base"):
        wav = os.path.join(TMP, "b_%s_%s.wav" % (wname, mname))
        cut(wav, ss, t)
        for p in CANDS:
            for temp in (0.0, 0.5):
                txt, wl = run(mname, wav, p, temp, words=(p is None and temp == 0.0))
                key = "%s|%s|%s|%.1f" % (wname, mname, p, temp)
                res[key] = dict(text=txt, words=wl)
                print("%-3s %-5s p=%-8s T=%.1f => %s %s" % (wname, mname, str(p)[:8], temp, txt,
                      json.dumps(wl, ensure_ascii=False) if wl else ""), flush=True)
with open(os.path.join(TMP, "results_B_window.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("DONE")
