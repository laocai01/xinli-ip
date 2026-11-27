# -*- coding: utf-8 -*-
"""第二批 6 条（11-16）· 本地 faster-whisper 转录
输入: E:/心理咨询IP/素材/<n>.mp4  (n=1..6)
输出: E:/心理咨询IP/03-内容/转录/batch2/raw_<n>.json + raw_<n>.md
"""
import os, sys, json, subprocess, tempfile

os.environ.setdefault("HF_HOME", r"E:\工具环境\whisper\models")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from faster_whisper import WhisperModel

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
ROOT = "E:/心理咨询IP"
SRC = ROOT + "/素材"
OUT = ROOT + "/03-内容/转录/batch2"
os.makedirs(OUT, exist_ok=True)

model = WhisperModel("small", device="cpu", compute_type="int8",
                     download_root=r"E:\工具环境\whisper\models")

def one(n):
    src = os.path.join(SRC, "%d.mp4" % n)
    tmp = os.path.join(tempfile.gettempdir(), "asr_b%d.wav" % n)
    subprocess.run([FF, "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000",
                    "-af", "highpass=f=80,afftdn=nf=-25", "-c:a", "pcm_s16le", tmp], check=True)
    segs, info = model.transcribe(tmp, language="zh", beam_size=5, vad_filter=True,
                                  initial_prompt="心理咨询 情绪 孩子 老婆 老公 退休 睡不着 老蔡说 海南")
    rows = []
    for s in segs:
        rows.append(dict(start=round(s.start, 2), end=round(s.end, 2), text=s.text.strip()))
    json.dump(dict(n=n, src=os.path.basename(src), duration=round(info.duration, 2), segs=rows),
              open(os.path.join(OUT, "raw_%d.json" % n), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "raw_%d.md" % n), "w", encoding="utf-8") as f:
        f.write("# 素材 %d.mp4 转录（faster-whisper small，%.1fs）\n\n" % (n, info.duration))
        for r in rows:
            f.write("[%7.2f -> %7.2f] %s\n" % (r["start"], r["end"], r["text"]))
    os.remove(tmp)
    print("OK %d  %.1fs  %d segs" % (n, info.duration, len(rows)), flush=True)

if __name__ == "__main__":
    for n in [int(x) for x in (sys.argv[1:] or ["1", "2", "3", "4", "5", "6"])]:
        one(n)
