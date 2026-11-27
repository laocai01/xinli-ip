# -*- coding: utf-8 -*-
"""B 段专项：5_画数.mp3 只有 8 秒，127.6s 处的「我不给你画X」不在文件内。
用 ffmpeg silencedetect 确认边界，并逐窗口转 4.6~8.0 全部剩余音频。
"""
import os, json, subprocess, re

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HOME"] = r"E:\工具环境\whisper\models"
from faster_whisper import WhisperModel

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"
SRC = r"E:/心理咨询IP/04-工程/batch4/_listen/5_画数.mp3"
TMP = r"E:/心理咨询IP/04-工程/batch4/_verify_tmp"

r = subprocess.run([FF, "-hide_banner", "-i", SRC, "-af", "silencedetect=noise=-32dB:d=0.25",
                    "-f", "null", "NUL"], capture_output=True, text=True, errors="replace")
det = r.stderr
print("SILENCE:")
for ln in det.splitlines():
    if "silence" in ln:
        print("  ", ln.strip())

_cache = {}
def get_model(n):
    if n not in _cache:
        _cache[n] = WhisperModel(n, device="cpu", compute_type="int8", download_root=r"E:\工具环境\whisper\models")
    return _cache[n]

def cut(dst, a, b):
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(a), "-t", str(round(b - a, 2)), "-i", SRC,
                    "-vn", "-ac", "1", "-ar", "16000",
                    "-af", "highpass=f=80,afftdn=nf=-25,dynaudnorm=f=150:g=7",
                    "-c:a", "pcm_s16le", dst], check=True)

def run(mname, wav, prompt=None):
    segs, _ = get_model(mname).transcribe(
        wav, language="zh", beam_size=5, vad_filter=False, condition_on_previous_text=False,
        temperature=[0.0], without_timestamps=True, initial_prompt=prompt)
    return "".join(s.text.strip() for s in segs).strip()

res = {}
for a, b in [(6.4, 8.0), (6.9, 8.0), (7.1, 8.0), (5.5, 8.0)]:
    for mname in ("small", "base"):
        wav = os.path.join(TMP, "B_tail_%.1f_%s.wav" % (a, mname))
        cut(wav, a, b)
        for p in (None, "我不给你画数", "我不给你画圈"):
            t = run(mname, wav, p)
            print("[%.1f-%.1f] %-5s prompt=%-8s => %s" % (a, b, mname, str(p)[:8], t), flush=True)
            res["%.1f-%.1f|%s|%s" % (a, b, mname, p)] = t

with open(os.path.join(TMP, "results_B_tail.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("DONE")
