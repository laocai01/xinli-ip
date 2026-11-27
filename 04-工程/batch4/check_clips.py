# -*- coding: utf-8 -*-
"""对 raw_N 转录里可疑片段用 base 模型做小切片交叉验证（不落盘到 batch4，只打印）"""
import os, sys, json, subprocess
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ.setdefault("HF_HOME", r"E:\工具环境\whisper\models")
from faster_whisper import WhisperModel

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
SRC = "E:/心理咨询IP/素材"
TMP = r"E:/tmp"

# (n, start, end) 每段取前后各留 1.2s 余量
CLIPS = [(int(a), float(b), float(c)) for a, b, c in (x.split(",") for x in sys.argv[1:])]

model = WhisperModel("base", device="cpu", compute_type="int8", download_root=r"E:\工具环境\whisper\models")
for n, s, e in CLIPS:
    s0 = max(0.0, s - 1.2); d = (e - s) + 2.4
    wav = os.path.join(TMP, "chk_%d_%d.wav" % (n, int(s * 10)))
    subprocess.run([FF, "-y", "-v", "error", "-ss", "%.2f" % s0, "-t", "%.2f" % d,
                    "-i", os.path.join(SRC, "%d.mp4" % n), "-vn", "-ac", "1", "-ar", "16000",
                    "-af", "highpass=f=80,afftdn=nf=-25", "-c:a", "pcm_s16le", wav], check=True)
    segs, _ = model.transcribe(wav, language="zh", beam_size=5, condition_on_previous_text=False,
                               initial_prompt="心理咨询 情绪 孩子 老蔡")
    print("%d @%.1f-%.1f base => %s" % (n, s, e, " | ".join(x.text.strip() for x in segs)), flush=True)
    try: os.remove(wav)
    except OSError: pass
