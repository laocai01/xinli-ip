# -*- coding: utf-8 -*-
"""第二批重出（2026-10-24 按董事长意见全面返工）
   修三件事：
     ① 真人画面朝向（deglare.probe 双重旋转 bug）
     ② 镜片反光（方案A：压到不刺眼，自然为主）
     ③ BGM 太轻（按实测重定增益）
     ④ 电影级调色 + 影视级字幕样式
   串行执行，每集：去反光 → 合成 → 验收
"""
import io, os, subprocess, sys, time
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deglare2 as DG

ROOT = "E:/心理咨询IP"
FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
FFP = FF.replace("ffmpeg.exe", "ffprobe.exe")
LOG = os.path.join(HERE, "_rebuild2.log")

# 去反光工作分辨率（输出 1080x1920，处理在 810x1440 上做，省一半 CPU）
WORK_W, WORK_H = 810, 1440


def log(m):
    line = "%s %s" % (time.strftime("%H:%M:%S"), m)
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def clean_one(n):
    """去反光：源素材 → 素材_clean2/<n>.mp4（正立 + 压反光）"""
    src = "%s/素材/%d.mp4" % (ROOT, n)
    dst = "%s/素材_clean2/%d.mp4" % (ROOT, n)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".tmp.mp4"

    w, h, fps = DG.probe(src)
    eyes = DG.find_eyes(src, w, h, n_samples=6)
    base = DG.calibrate_lens(src, w, h, eyes, n=20)
    if eyes is None or base is None:
        log("[%d] ❌ 找不到眼睛/镜片，跳过去反光" % n)
        return False
    log("[%d] 眼位 右(%.0f,%.0f) 左(%.0f,%.0f) 底稿L=%.0f"
        % (n, eyes["rx"], eyes["ry"], eyes["lx"], eyes["ly"], base["L"]))

    # 音轨必须带上：画面走 rawvideo 管道，声音直接从原素材 copy（不重编码、零损失）
    p = subprocess.Popen([FF, "-y", "-v", "error",
                          "-f", "rawvideo", "-pix_fmt", "bgr24",
                          "-s", "%dx%d" % (WORK_W, WORK_H), "-r", "%.4f" % fps, "-i", "-",
                          "-i", src,
                          "-map", "0:v:0", "-map", "1:a:0?",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                          "-pix_fmt", "yuv420p", "-c:a", "copy",
                          "-movflags", "+faststart", tmp],
                         stdin=subprocess.PIPE, bufsize=2 ** 30)
    prev = None
    cnt = 0
    k = WORK_W / float(w)
    eyes_w = dict(rx=eyes["rx"] * k, ry=eyes["ry"] * k, lx=eyes["lx"] * k, ly=eyes["ly"] * k)
    for fr in DG.read_frames(src, WORK_W, WORK_H):
        box = DG.lens_box(fr.shape, eyes_w, 1.0)
        out, prev = DG.deglare_frame(fr, None, prev, 1.0, base=base, box=box)
        if p.poll() is not None:
            raise RuntimeError("编码器提前退出 @%d 帧" % cnt)
        p.stdin.write(out.tobytes())
        cnt += 1
    p.stdin.close()
    p.wait()
    if p.returncode != 0:
        log("[%d] ❌ 编码失败" % n)
        return False
    # 校验 + 改名
    r = subprocess.run([FFP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", tmp],
                       capture_output=True, text=True)
    if not r.stdout.strip():
        log("[%d] ❌ 成品读不出" % n)
        return False
    # 硬校验：音视频都在，缺一个就不许认
    r2 = subprocess.run([FFP, "-v", "error", "-show_entries", "stream=codec_type",
                         "-of", "csv=p=0", tmp], capture_output=True, text=True)
    types = (r2.stdout or "").strip()
    if "video" not in types or "audio" not in types:
        log("[%d] ❌ 成品缺流（%s），删掉重来" % (n, types.replace(chr(10), "/")))
        os.remove(tmp)
        return False
    os.replace(tmp, dst)
    log("[%d] 去反光完成 %d 帧 → %s（音轨已带）" % (n, cnt, os.path.basename(dst)))
    return True


if __name__ == "__main__":
    for a in sys.argv[1:]:
        t0 = time.time()
        ok = clean_one(int(a))
        log("[%s] 用时 %.1f 分钟 %s" % (a, (time.time() - t0) / 60, "OK" if ok else "FAIL"))
