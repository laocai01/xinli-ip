# -*- coding: utf-8 -*-
"""第二批（11-16）单条流水线 v2 —— 一次解码，两路输出
   raw.mp4 : 裁掉脸区反光的干净素材（供合成）
   eye.mp4 : 脸区特写 ×2.2 放大（供 PIP 小窗轮插，解决"看着像照念稿"）
   用法: python pipeline2_one.py <n> [<n> ...]
"""
import os, sys, io, json, subprocess, time
import numpy as np, cv2
from scipy.ndimage import gaussian_filter

R = "E:/心理咨询IP/04-工程/batch2"
sys.path.insert(0, R)
import deglare

FF = deglare.FF
ROOT = "E:/心理咨询IP"
OUT = ROOT + "/素材_clean"
LOGF = R + "/_pipeline.log"


def log(m):
    line = "%s %s" % (time.strftime("%H:%M:%S"), m)
    print(line, flush=True)
    io.open(LOGF, "a", encoding="utf-8").write(line + "\n")


def run(n):
    os.makedirs(OUT, exist_ok=True)
    src = "%s/素材/%d.mp4" % (ROOT, n)
    dst = "%s/%d.mp4" % (OUT, n)
    if os.path.exists(dst) and os.path.getsize(dst) > 1e6:
        chk = subprocess.run([deglare.FF.replace("ffmpeg.exe", "ffprobe.exe"), "-v", "error",
                              "-show_entries", "format=duration", "-of", "csv=p=0", dst],
                             capture_output=True, text=True)
        if chk.stdout.strip():
            log("[%d] 已存在且可读，跳过" % n)
            return dst
        log("[%d] 已有文件但读不出（写坏），重做" % n)
        os.remove(dst)
    src_w, src_h, fps, vf = deglare.probe(src)
    roi = deglare.faces_roi(src, src_w, src_h, vf)
    x0, y0, x1, y1 = roi
    # 眼/镜片区：脸区上 1/3，横向略放大（眼镜 + 眼周）
    fx0 = max(0, x0 - int((x1 - x0) * 0.12))
    fx1 = min(src_w, x1 + int((x1 - x0) * 0.12))
    fy0 = max(0, y0 - int((y1 - y0) * 0.05))
    fy1 = min(src_h, y0 + int((y1 - y0) * 0.46))
    RW, RH = int(src_w * 0.60) // 2 * 2, int(src_h * 0.60) // 2 * 2   # 720x1280：够 1080 输出，CPU 减半
    # 眼窗固定 16:9 竖切片（PIP 小窗用），按脸区宽度放大 1.35 倍取样
    ew, eh = 480, 270        # PIP 小窗源尺寸（16:9），合成时再放大到 720 宽，够清晰又省一半码率
    cx, cy = (fx0 + fx1) // 2, fy0 + int((fy1 - fy0) * 0.42)
    sw = int(ew / 0.90)      # 源取样宽（比输出略大，留住细节）
    sh = int(sw * 9 / 16)
    ex0 = max(0, min(src_w - sw, int(cx - sw / 2)))
    ey0 = max(0, min(src_h - sh, int(cy - sh / 2)))
    fw2, fh2 = ew, eh

    k = RH / float(src_h)
    rx0, ry0, rx1, ry1 = int(x0 * k), int(y0 * k), int(x1 * k), int(y1 * k)
    # 眼窗在主画面上对应的像素区（再放大到 720x404）
    ex0, ey0 = int(ex0 * k), int(ey0 * k)
    ex1, ey1 = ex0 + int(sw * k), ey0 + int(sh * k)
    ex0, ex1 = max(0, ex0), min(RW, ex1)
    ey0, ey1 = max(0, ey0), min(RH, ey1)

    mid = dst + ".mid.mp4"
    p1 = subprocess.Popen([FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                           "-s", "%dx%d" % (RW, RH), "-r", "%.4f" % fps, "-i", "-",
                           "-i", src, "-map", "0:v", "-map", "1:a?",
                           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "15",
                           "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", mid],
                          stdin=subprocess.PIPE, bufsize=2 ** 30)
    p2 = subprocess.Popen([FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                           "-s", "%dx%d" % (RW, RH), "-r", "%.4f" % fps, "-i", "-",
                           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-g", "48",
                           "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", "%s/eye_%d.mp4" % (OUT, n)],
                          stdin=subprocess.PIPE, bufsize=2 ** 28)

    prev = None
    cnt = hit = 0
    for fr in deglare.read_frames(src, RW, RH, vf):
        fr = fr[:RH, :RW]
        roi_img = fr[ry0:ry1, rx0:rx1].astype(np.float32)
        g = roi_img.mean(2)
        face_l = float(np.median(g))
        hi = gaussian_filter(g, 10.0)
        det = np.abs(g - hi)
        a1 = np.clip((g - (face_l + 34)) / 55.0, 0, 1) * np.clip((det - 2.0) / 7.0, 0, 1)
        a2 = np.clip((g - (face_l + 64)) / 60.0, 0, 1) * 0.7
        m = np.clip(np.maximum(a1, a2), 0, 1)
        if m.max() >= 0.08:
            if prev is not None and prev.shape == m.shape:
                m = np.maximum(m, prev * 0.8)
            prev = m
            soft = gaussian_filter(m, 4.0) * 0.85
            tgt = face_l + 34 * 0.45
            cur = roi_img.mean(2, keepdims=True) + 1e-3
            rep = roi_img * np.clip(tgt / cur, 0, 1)
            lowp = gaussian_filter(roi_img, 3.0)
            rep = lowp * 0.72 + rep * 0.28
            aa = soft[..., None]
            fr[ry0:ry1, rx0:rx1] = np.clip(roi_img * (1 - aa) + rep * aa, 0, 255).astype(np.uint8)
            hit += 1
        else:
            prev = None
        if p1.poll() is not None:
            raise RuntimeError("raw 编码器提前退出（磁盘/内存问题），停在第 %d 帧" % cnt)
        p1.stdin.write(fr.tobytes())
        eye = fr[ey0:ey1, ex0:ex1]
        if eye.shape[0] < 2 or eye.shape[1] < 2:
            eye = fr[:eh, :ew]
        _e = cv2.resize(np.ascontiguousarray(eye), (ew, eh), interpolation=cv2.INTER_LANCZOS4)
        if p2.poll() is not None:
            raise RuntimeError("眼窗编码器提前退出，停在第 %d 帧" % cnt)
        p2.stdin.write(cv2.resize(_e, (RW, RH), interpolation=cv2.INTER_LINEAR).tobytes())
        cnt += 1
    for p in (p1, p2):
        p.stdin.close()
        p.wait()
    tmp = dst + ".tmp.mp4"
    subprocess.run([FF, "-y", "-v", "error", "-i", mid, "-c:v", "libx264", "-preset", "medium",
                    "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", tmp],
                   check=True)
    # 校验成品可读（moov atom 完整）再改名
    chk = subprocess.run([deglare.FF.replace("ffmpeg.exe", "ffprobe.exe"), "-v", "error", "-show_entries",
                          "format=duration", "-of", "csv=p=0", tmp], capture_output=True, text=True)
    if not chk.stdout.strip() or float(chk.stdout.strip() or 0) < 30:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise RuntimeError("成品校验失败（moov 缺失或时长过短）：%s" % chk.stderr[:120])
    os.replace(tmp, dst)
    try:
        os.remove(mid)
    except OSError:
        pass
    log("[%d] 去反光完成 %d 帧(命中%d) → %s  眼窗 %dx%d" % (n, cnt, hit, dst, fw2, fh2))
    return dst


if __name__ == "__main__":
    for n in [int(x) for x in sys.argv[1:]]:
        t = time.time()
        run(n)
        log("[%d] 用时 %.1f 分钟" % (n, (time.time() - t) / 60))
