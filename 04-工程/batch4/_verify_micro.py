# -*- coding: utf-8 -*-
"""微片重转：把关键音节窗口切成 1-2 秒，base/small 分别转，看稳定性"""
import os, sys, json, subprocess

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
def get_model(name):
    if name not in _cache:
        _cache[name] = WhisperModel(name, device="cpu", compute_type="int8", download_root=MODEL_ROOT)
    return _cache[name]

def cut(src, dst, ss, t):
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(ss), "-t", str(t), "-i", src,
                    "-vn", "-ac", "1", "-ar", "16000",
                    "-af", "highpass=f=80,afftdn=nf=-25", "-c:a", "pcm_s16le", dst], check=True)

def run(mname, wav, prompt):
    m = get_model(mname)
    segs, _ = m.transcribe(wav, language="zh", beam_size=5, vad_filter=False,
                           initial_prompt=prompt, condition_on_previous_text=False,
                           temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    return " ".join(s.text.strip() for s in segs).strip()

if __name__ == "__main__":
    # (tag, src, ss, dur, prompt, note)
    micro = [
        # ---- A: 1_开头.mp3 (原片 2.0s ~ 12.0s) ----
        ("A1_断x了", "1_开头.mp3", 3.6, 1.5, "接下来 断更了两天", "断更/断根"),
        ("A1b_断x了无prompt", "1_开头.mp3", 3.6, 1.5, "", "无限定"),
        ("A1c_断x了长", "1_开头.mp3", 3.2, 2.0, "这几天断更了", "断更/断根"),
        ("A2_算x算三天", "1_开头.mp3", 4.9, 1.6, "算钱就算三天", "算钱/算前"),
        ("A2b_算x算三天无prompt", "1_开头.mp3", 4.9, 1.6, "", "无限定"),
        ("A2c_算x长", "1_开头.mp3", 4.6, 2.2, "算一下 加上今天", "算钱/算上"),
        # ---- B: 5_画数.mp3 (原片 118.0s ~ 126.0s) ----
        ("B1_不给x", "5_画数.mp3", 6.9, 1.6, "我不给你画数", "画数/画素"),
        ("B1b_不给x无prompt", "5_画数.mp3", 6.9, 1.6, "", "无限定"),
        ("B1c_不给x长", "5_画数.mp3", 6.3, 2.4, "那怎么办呢 我不给你", "画数/画圈"),
        ("B2_后续句", "5_画数.mp3", 7.6, 1.6, "你自己看一样东西就够了", "看是哪句"),
    ]
    out = {}
    for tag, fname, ss, dur, prompt, note in micro:
        src = os.path.join(LISTEN, fname)
        for mname in ("small", "base"):
            wav = os.path.join(TMP, "%s_%s.wav" % (tag, mname))
            cut(src, wav, ss, dur)
            try:
                txt = run(mname, wav, prompt or None)
            except Exception as e:
                txt = "ERR:%s" % e
            out["%s|%s|%s" % (tag, note, mname)] = dict(ss=ss, t=dur, prompt=prompt, text=txt)
            print("%-22s %-6s p=%-12s => %s" % (tag, mname, (prompt or "-")[:12], txt), flush=True)
    with open(os.path.join(TMP, "results_micro.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("DONE")
