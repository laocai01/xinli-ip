# -*- coding: utf-8 -*-
"""从原片重新切两段（正确区间）：
  A: 1.mp4 2.0~12.0s   B: 5.mp4 116.5~128.0s
然后 base/small 各转一次，并对关键窗口做无 prompt 微片。
"""
import os, json, subprocess

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HOME"] = r"E:\工具环境\whisper\models"
from faster_whisper import WhisperModel

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"
SRC = r"E:/心理咨询IP/素材"
TMP = r"E:/心理咨询IP/04-工程/batch4/_verify_tmp"

_cache = {}
def get_model(n):
    if n not in _cache:
        _cache[n] = WhisperModel(n, device="cpu", compute_type="int8", download_root=r"E:\工具环境\whisper\models")
    return _cache[n]

def cut(src, dst, ss, t, af="highpass=f=80,afftdn=nf=-25"):
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(ss), "-t", str(t), "-i", src,
                    "-vn", "-ac", "1", "-ar", "16000", "-af", af, "-c:a", "pcm_s16le", dst], check=True)

def run(mname, wav, prompt=None, temps=(0.0,)):
    all_out = []
    for t in temps:
        segs, info = get_model(mname).transcribe(
            wav, language="zh", beam_size=5, vad_filter=False, condition_on_previous_text=False,
            temperature=[t], word_timestamps=True, initial_prompt=prompt)
        rows = [(round(s.start, 2), round(s.end, 2), s.text.strip()) for s in segs]
        all_out.append(dict(t=t, rows=rows, dur=round(info.duration, 2)))
    return all_out

if __name__ == "__main__":
    jobs = [("A_full", os.path.join(SRC, "1.mp4"), 2.0, 10.0),
            ("B_full", os.path.join(SRC, "5.mp4"), 116.5, 11.5)]
    res = {}
    for tag, src, ss, t in jobs:
        wav = os.path.join(TMP, "%s.wav" % tag)
        cut(src, wav, ss, t)
        for mname in ("small", "base"):
            r = run(mname, wav, None, temps=(0.0, 0.4))
            res["%s|%s" % (tag, mname)] = r
            print("%-8s %-5s %s" % (tag, mname, json.dumps(r, ensure_ascii=False)), flush=True)
    with open(os.path.join(TMP, "results_full.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("DONE")
