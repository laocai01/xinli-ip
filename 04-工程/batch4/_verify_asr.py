# -*- coding: utf-8 -*-
"""多模型交叉验证：base / small 重转两段不确定音频 + 微片重转
只在 batch4/ 下写临时文件，不改动已有文件。
"""
import os, sys, json, subprocess

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HOME"] = r"E:\工具环境\whisper\models"
os.environ["HF_HUB_CACHE"] = r"E:\工具环境\whisper\models"

from faster_whisper import WhisperModel

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"
LISTEN = r"E:/心理咨询IP/04-工程/batch4/_listen"
TMP = r"E:/心理咨询IP/04-工程/batch4/_verify_tmp"
os.makedirs(TMP, exist_ok=True)
MODEL_ROOT = r"E:\工具环境\whisper\models"

def to_wav(src, dst, af="highpass=f=80,afftdn=nf=-25", extra=None):
    cmd = [FF, "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000"]
    if af:
        cmd += ["-af", af]
    cmd += ["-c:a", "pcm_s16le", dst]
    subprocess.run(cmd, check=True)

def cut(src, dst, ss, t):
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(ss), "-t", str(t), "-i", src,
                    "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", dst], check=True)

_cache = {}
def get_model(name):
    if name not in _cache:
        _cache[name] = WhisperModel(name, device="cpu", compute_type="int8", download_root=MODEL_ROOT)
    return _cache[name]

def run(mname, wav, prompt="", beam=5, vad=False):
    m = get_model(mname)
    segs, info = m.transcribe(
        wav, language="zh", beam_size=beam,
        vad_filter=vad,
        vad_parameters=dict(min_silence_duration_ms=300) if vad else None,
        initial_prompt=prompt or None,
        condition_on_previous_text=False,
        temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    )
    out = [dict(start=round(s.start, 2), end=round(s.end, 2), text=s.text.strip(),
                p=round(s.avg_logprob, 3), nsp=round(s.no_speech_prob, 3)) for s in segs]
    return out

if __name__ == "__main__":
    results = {}
    jobs = [
        ("A_1_开头", os.path.join(LISTEN, "1_开头.mp3"),
         "心理咨询 情绪 孩子 老婆 老公 退休 睡不着 老蔡说 海南"),
        ("B_5_画数", os.path.join(LISTEN, "5_画数.mp3"),
         "心理咨询 情绪 孩子 老婆 老公 退休 睡不着 老蔡说 海南"),
    ]
    for tag, src, prompt in jobs:
        # 三种预处理 x 两个模型
        variants = {
            "raw": None,                                    # 原始音频直接喂（无滤波）
            "denoise": "highpass=f=80,afftdn=nf=-25",
            "loud": "highpass=f=80,afftdn=nf=-25,dynaudnorm=f=150:g=7",
        }
        for vname, af in variants.items():
            wav = os.path.join(TMP, "%s_%s.wav" % (tag, vname))
            to_wav(src, wav, af=af)
            for mname in ("small", "base"):
                key = "%s|%s|%s" % (tag, vname, mname)
                try:
                    results[key] = run(mname, wav, prompt=prompt, vad=False)
                except Exception as e:
                    results[key] = [dict(error=str(e))]
                print(key, "=>", json.dumps(results[key], ensure_ascii=False), flush=True)
    with open(os.path.join(TMP, "results_models.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print("DONE")
