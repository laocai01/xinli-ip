# -*- coding: utf-8 -*-
"""第四批 6 条（1-6）· 本地 faster-whisper 转录
输入: E:/心理咨询IP/素材/<n>.mp4  (n=1..6)
输出: E:/心理咨询IP/03-内容/转录/batch4/raw_<n>.json + raw_<n>.md
格式与 batch3/raw_5.json 一致: [{start, end, text}, ...]
"""
import os, sys, json, subprocess, tempfile, time

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ.setdefault("HF_HOME", r"E:\工具环境\whisper\models")

from faster_whisper import WhisperModel

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
ROOT = "E:/心理咨询IP"
SRC = ROOT + "/素材"
OUT = ROOT + "/03-内容/转录/batch4"
TMPDIR = r"E:/tmp"
os.makedirs(OUT, exist_ok=True)
os.makedirs(TMPDIR, exist_ok=True)

MODEL_ROOT = r"E:\工具环境\whisper\models"
model = None


def get_model():
    global model
    if model is None:
        model = WhisperModel("small", device="cpu", compute_type="int8", download_root=MODEL_ROOT)
    return model


def one(n):
    t0 = time.time()
    src = os.path.join(SRC, "%d.mp4" % n)
    tmp = os.path.join(TMPDIR, "asr_b4_%d.wav" % n)  # ASCII 路径，避开中文路径报错
    subprocess.run([FF, "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000",
                    "-af", "highpass=f=80,afftdn=nf=-25", "-c:a", "pcm_s16le", tmp], check=True)
    segs, info = get_model().transcribe(
        tmp, language="zh", beam_size=5, vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        initial_prompt="心理咨询 情绪 孩子 老婆 老公 退休 睡不着 老蔡说 海南",
        condition_on_previous_text=False)
    rows = []
    for s in segs:
        txt = s.text.strip()
        if not txt:
            continue
        rows.append(dict(start=round(s.start, 2), end=round(s.end, 2), text=txt))
    with open(os.path.join(OUT, "raw_%d.json" % n), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "raw_%d.md" % n), "w", encoding="utf-8") as f:
        f.write("# 素材 %d.mp4 转录（faster-whisper small，%.1fs）\n\n" % (n, info.duration))
        for r in rows:
            f.write("[%7.2f -> %7.2f] %s\n" % (r["start"], r["end"], r["text"]))
    try:
        os.remove(tmp)
    except OSError:
        pass
    print("OK %d  dur=%.1fs  segs=%d  cost=%.1fs" % (n, info.duration, len(rows), time.time() - t0), flush=True)
    return dict(n=n, dur=round(info.duration, 2), segs=len(rows), last=rows[-1]["end"] if rows else 0)


if __name__ == "__main__":
    ns = [int(x) for x in (sys.argv[1:] or ["1", "2", "3", "4", "5", "6"])]
    summary = []
    for n in ns:
        summary.append(one(n))
    print(json.dumps(summary, ensure_ascii=False))
