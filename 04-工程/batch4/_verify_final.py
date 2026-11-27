# -*- coding: utf-8 -*-
"""A 段末字精查 + B 段尾「一样东西就够了」核对"""
import os, json, subprocess

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HOME"] = r"E:\工具环境\whisper\models"
from faster_whisper import WhisperModel

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"
TMP = r"E:/心理咨询IP/04-工程/batch4/_verify_tmp"
_cache = {}
def get_model(n):
    if n not in _cache:
        _cache[n] = WhisperModel(n, device="cpu", compute_type="int8", download_root=r"E:\工具环境\whisper\models")
    return _cache[n]

def cut(src, dst, ss, t):
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(ss), "-t", str(t), "-i", src,
                    "-vn", "-ac", "1", "-ar", "16000", "-af", "highpass=f=80,afftdn=nf=-25",
                    "-c:a", "pcm_s16le", dst], check=True)

def run(mname, wav, prompt=None, temp=0.0, words=False):
    segs, _ = get_model(mname).transcribe(
        wav, language="zh", beam_size=5, vad_filter=False, condition_on_previous_text=False,
        temperature=[temp], word_timestamps=words, without_timestamps=not words,
        initial_prompt=prompt)
    txt = ""; wl = []
    for s in segs:
        txt += s.text.strip()
        if words and s.words:
            wl += [dict(w=w.word, p=round(w.probability, 3)) for w in s.words]
    return txt, wl

A = r"E:/心理咨询IP/素材/1.mp4"
B = r"E:/心理咨询IP/素材/5.mp4"
jobs = [
    # B 尾：128.0s 之后
    ("Btail", B, 127.0, 2.0, [None, "你自己看一样东西就够了"]),
    # A 相对 2.0s 起点：算X算三天 = 3.88~5.12 -> 原片 5.88~7.12
    ("A2_cal", A, 5.6, 1.9, [None, "算钱就算三天", "算前就算三天", "算今天算三天"]),
    # A 断X了：1.94~3.18 -> 原片 3.94~5.18
    ("A1_cal", A, 3.7, 1.8, [None, "断更", "断根"]),
]
out = {}
for tag, src, ss, t, prompts in jobs:
    for mname in ("small", "base"):
        wav = os.path.join(TMP, "x_%s_%s.wav" % (tag, mname))
        cut(src, wav, ss, t)
        for p in prompts:
            for temp in (0.0, 0.5):
                txt, wl = run(mname, wav, p, temp, words=(p is None))
                out["%s|%s|%s|%.1f" % (tag, mname, p, temp)] = dict(text=txt, words=wl)
                print("%-7s %-5s p=%-14s T=%.1f => %s %s" % (tag, mname, str(p)[:14], temp, txt,
                      json.dumps(wl, ensure_ascii=False) if wl else ""), flush=True)
with open(os.path.join(TMP, "results_final.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("DONE")
