# -*- coding: utf-8 -*-
"""BGM 混音自校准 v2（2026-11-18 董事长「咖啡厅感」）

v1 的错误：拿 astats 整体 RMS 当「人声电平」，那是被静音段拉低的数
（人声整体 -27.4dB，但说话段实际 -20dB、停顿段 -42dB），算出的增益不可靠。

v2 用【说话段电平】做基准：
  · voice_speech = 人声轨 0.25s 窗口 RMS 的 P90（= 正常说话时的电平）
  · bgm_target   = voice_speech - BELOW_SPEECH
  · BELOW_SPEECH = 8.5dB  → BGM 落在约 -33dB
    听感：人声停顿处清楚可闻；说完一句音乐明显在；开口时人声压得住
  · 验收：混音后最静 15% 窗口 RMS 应 ≈ target ±5dB
"""
import subprocess
import numpy as np

FF = ("C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/"
      "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe")

BELOW_SPEECH = 8.5
TOL = 5.0
BGM_ABS_DB = -28.0     # BGM 绝对目标电平（实测人声主体 -32~-19dB，BGM 落 -31 能听见不抢）


def pcm(path, ss=0.0, t=None, sr=16000):
    cmd = [FF, "-v", "error", "-ss", "%.2f" % ss]
    if t:
        cmd += ["-t", "%.2f" % t]
    cmd += ["-i", path, "-map", "0:a:0", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.int16).astype(float)


def _db(v):
    return 20 * np.log10(max(v, 1e-9) / 32768.0)


def window_rms_db(x, sr=16000, win=0.25):
    w = int(sr * win)
    if len(x) < w * 2:
        return np.array([_db(np.sqrt((x ** 2).mean()))]) if len(x) else np.array([-90.0])
    r = np.array([np.sqrt((x[i:i + w] ** 2).mean()) for i in range(0, len(x) - w, w)])
    return np.array([_db(v) for v in r])


def speech_db(path, speed=1.0):
    x = pcm(path)
    if len(x) == 0:
        return None
    return float(np.percentile(window_rms_db(x), 90))


def bgm_db(path, max_s=90.0):
    x = pcm(path, 0, max_s)
    if len(x) == 0:
        return None
    return float(np.percentile(window_rms_db(x), 90))


def calc_gain(voice_path, bgm_path, speed=1.0):
    v = speech_db(voice_path, speed)
    b = bgm_db(bgm_path)
    if v is None or b is None:
        return -18.0, dict(ok=False, why="量不到电平，用默认 -18dB")
    # ★ 2026-11-18：同时满足两个条件，取更响的那个（BGM 宁清楚不闷）
    #   ① 相对：BGM 不低于说话段 -10dB（不抢人声）
    #   ② 绝对：BGM 不低于 -26dB（手机外放听得见）
    by_rel = (v - 8.0) - b
    by_abs = BGM_ABS_DB - b
    gain = max(by_rel, by_abs)
    target = b + gain
    return round(gain, 1), dict(ok=True, voice_speech_db=round(v, 1),
                                bgm_db=round(b, 1), target_db=round(target, 1),
                                diff_vs_voice=round(v - target, 1),
                                gain=round(gain, 1))


def verify_mix(mix_path, voice_speech):
    x = pcm(mix_path)
    if len(x) == 0:
        return dict(ok=False, why="读不到混音")
    r = window_rms_db(x)
    quiet = float(np.percentile(r, 15))
    target = voice_speech - BELOW_SPEECH
    return dict(ok=abs(quiet - target) <= TOL, quiet_db=round(quiet, 1),
                target_db=round(target, 1), diff=round(quiet - target, 1))


if __name__ == "__main__":
    import sys
    v = sys.argv[1] if len(sys.argv) > 1 else "E:/心理咨询IP/素材/1.mp4"
    b = sys.argv[2] if len(sys.argv) > 2 else (
        "E:/心理咨询IP/06-音乐/国际民谣_免版税/B_温暖鼓励_01_Hope_and_Kindness.mp3")
    print(calc_gain(v, b))
