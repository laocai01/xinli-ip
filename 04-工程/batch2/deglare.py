# -*- coding: utf-8 -*-
"""去屏幕反光（眼镜/眼睛里的电脑倒影）
思路：只在脸/眼区域做局部处理，不碰其它画面
  1) 抽样 24 帧，自动找到"高亮度 + 高细节"的反射聚集区 → ROI（每集自适应，不写死坐标）
  2) 逐帧在 ROI 内：反射 = 高亮度 且 有细碎边缘（屏幕上的字/窗口）
  3) 只把这块"压亮 + 抹掉细节 + 去绿偏色"，保留自然眼神光；羽化融合，不出现补丁感
  4) 时域稳定：掩膜取前后帧并集，防闪烁
用法: python deglare.py in.mp4 out.mp4 [--roi x0,y0,x1,y1]
"""
import os, sys, subprocess, numpy as np
import cv2
from scipy.ndimage import gaussian_filter, binary_dilation, median_filter

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"


def probe(p):
    """返回【解码后真实画面】的宽高/帧率/滤镜。
    ★ 铁律（2026-10-24 董事长指出真人朝向全错后修正）：
    字节数无法区分 1920x1080 与 1080x1920（乘积相同），所以必须用
    ffprobe 的 stream_side_data=rotation 明确判断：有 rotation 就说明
    存储是横的、显示要转正；ffmpeg 解码时会 autorotate，因此我们【不加】
    任何 transpose 滤镜。之前加 transpose 就是双重旋转，导致人像横躺。"""
    SPEC = FF.replace("ffmpeg.exe", "ffprobe.exe")
    r = subprocess.run([SPEC, "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height,r_frame_rate",
                        "-of", "csv=p=0", p], capture_output=True, text=True)
    first = r.stdout.strip().splitlines()[0]
    parts = [x for x in first.split(",") if x.strip()]
    a, b = int(parts[0]), int(parts[1])
    fr = parts[2] if len(parts) > 2 else "24/1"
    num, den = fr.split("/")
    fps = float(num) / float(den)
    # 单独读旋转元数据
    rr = subprocess.run([SPEC, "-v", "error", "-select_streams", "v:0",
                         "-show_entries", "stream_side_data=rotation", "-of", "csv=p=0", p],
                        capture_output=True, text=True)
    rot = 0
    txt = (rr.stdout or "").strip().splitlines()
    if txt:
        try:
            rot = int(float(txt[0]))
        except ValueError:
            rot = 0
    if abs(rot) == 90:
        # 存储是横的、显示是竖的；ffmpeg 已 autorotate，不用再转
        return b, a, fps, ""
    return a, b, fps, ""


def read_frames(p, w, h, vf=""):
    """流式读出原始帧（已转正）。
       ffmpeg 的 rawvideo 输出尺寸必须和真实画面完全一致，否则会自行缩放导致画面错位。
       这里按源画面真实尺寸输出，再用 cv2 缩放到调用方要的 w/h。"""
    sw, sh, _fps, _vf = probe(p)
    cmd = [FF, "-v", "error", "-i", p]
    if vf:
        cmd += ["-vf", vf]
    # 转正后尺寸：竖拍横存时 w/h 互换
    dw, dh = (sh, sw) if vf else (sw, sh)
    cmd += ["-threads", "4", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    pr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10 ** 8)
    n = dw * dh * 3
    while True:
        buf = pr.stdout.read(n)
        if len(buf) < n:
            break
        fr = np.frombuffer(buf, np.uint8).reshape(dh, dw, 3)
        if (dw, dh) != (w, h):
            fr = cv2.resize(np.ascontiguousarray(fr), (w, h), interpolation=cv2.INTER_AREA)
        yield fr.copy()
    try:
        pr.stdout.close()
        pr.terminate()
    except Exception:
        pass


def find_roi(p, w, h, n_frames, vf=""):
    """抽样找反射聚集区"""
    acc = np.zeros((h // 4, w // 4), np.float32)
    got = 0
    for i, fr in enumerate(read_frames(p, w, h, vf)):
        if i % 37:
            continue
        g = fr.mean(2)
        sm = g[::4, ::4]
        blur = gaussian_filter(sm, 3)
        det = np.abs(sm - blur)
        m = ((sm > 185) & (det > 5)).astype(np.float32)
        acc += m
        got += 1
        if got >= 24:
            break
    acc /= max(1, got)
    # 排除顶部/底部（Logo、字幕区、衣物高光），只在中间偏上找
    band = acc.copy()
    band[: int(h / 4 / 4), :] = 0
    band[int(h * 0.72 / 4):, :] = 0
    ys, xs = np.nonzero(band > 0.35)
    if len(xs) < 20:
        ys, xs = np.nonzero(band > np.percentile(band[band > 0], 99.5))
    x0, x1 = xs.min() * 4, xs.max() * 4
    y0, y1 = ys.min() * 4, ys.max() * 4
    pad = 60
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(w, x1 + pad), min(h, y1 + pad)
    return (x0, y0, x1, y1), float(acc.max())


def faces_roi(src, w, h, vf, n=16):
    """抽样定位头部：用一帧画网格让看，不能靠瞎猜 —— 改为人工锚定 + 结构兜底
       兜底规则（自拍固定机位）：取画面上部 55% 内、横向 12%~88%、纵向最亮且最密的暖色块"""
    boxes = []
    for i, fr in enumerate(read_frames(src, w, h, vf)):
        if i % 29:
            continue
        small = fr[::6, ::6].astype(np.float32)
        small = cv2.GaussianBlur(small, (0, 0), 2.5)
        bch, gch, rch = small[..., 0], small[..., 1], small[..., 2]
        hh, ww = bch.shape
        band = np.zeros_like(bch, bool)
        band[int(hh * 0.08):int(hh * 0.55), int(ww * 0.10):int(ww * 0.90)] = True
        skin = (rch > 110) & (rch - bch > 22) & (rch - gch > 10) & (rch - gch < 70) & (gch - bch > -5) & band
        ys, xs = np.nonzero(skin)
        if len(xs) < 80:
            continue
        # 以最密的一列/一行定中心，滤掉窗帘等大片色块
        hist_x = np.bincount(xs, minlength=ww)
        cx = int(np.argmax(np.convolve(hist_x, np.ones(25), "same")))
        keep = np.abs(xs - cx) < 28
        ys2 = ys[keep]
        if len(ys2) < 40:
            continue
        y0 = int(np.percentile(ys2, 10)); y1 = int(np.percentile(ys2, 92))
        xs2 = xs[keep]
        x0, x1 = int(np.percentile(xs2, 5)), int(np.percentile(xs2, 95))
        boxes.append((x0 * 6, y0 * 6, x1 * 6, y1 * 6))
        if len(boxes) >= n:
            break
    if not boxes:
        return None
    b = np.array(boxes, float)
    x0, x1 = np.median(b[:, 0]), np.median(b[:, 2])
    y0, y1 = np.median(b[:, 1]), np.median(b[:, 3])
    pw_, ph_ = (x1 - x0), (y1 - y0)
    return (int(max(0, x0 - pw_ * 0.20)), int(max(0, y0 - ph_ * 0.35)),
            int(min(w, x1 + pw_ * 0.20)), int(min(h, y1 + ph_ * 0.25)))


def process(src, dst, roi=None, thresh=34, strength=0.85, log=True):
    w, h, fps, vf = probe(src)
    if roi is None:
        roi = faces_roi(src, w, h, vf)
        src_kind = "自动"
    else:
        src_kind = "指定"
    x0, y0, x1, y1 = roi
    rw, rh = x1 - x0, y1 - y0
    if log:
        print("  视频 %dx%d @%.2ffps vf=%s  头部ROI(%s)=(%d,%d)-(%d,%d) %dx%d" %
              (w, h, fps, vf or "-", src_kind, x0, y0, x1, y1, rw, rh))

    # 先把"转正 + 压缩"交给 ffmpeg 硬件友好的编码器并行做完，Python 只做逐帧局部修补
    RW = int(w * 0.75) // 2 * 2
    RH = int(h * 0.75) // 2 * 2
    cmd = [FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "%dx%d" % (RW, RH),
           "-r", "%.4f" % fps, "-i", "-", "-i", src,
           "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "15",
           "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", dst + ".mid.mp4"]
    pw = subprocess.Popen(cmd, stdin=subprocess.PIPE, bufsize=10 ** 8)

    prev = None
    n = hit = 0
    k = RH / float(h)          # ROI 坐标随缩小比例换算
    rx0, ry0, rx1, ry1 = int(x0 * k), int(y0 * k), int(x1 * k), int(y1 * k)
    for fr in read_frames(src, RW, RH, vf):
        fr = fr[:RH, :RW]
        roi_img = fr[ry0:ry1, rx0:rx1].astype(np.float32)
        g = roi_img.mean(2)
        face_l = float(np.median(g))
        # 反射：比同区中位数亮很多 且 有细碎高频（屏幕上的字/窗口）
        hi = gaussian_filter(g, 10.0)
        det = np.abs(g - hi)
        a1 = np.clip((g - (face_l + thresh)) / 55.0, 0, 1)
        a1 = a1 * np.clip((det - 2.0) / 7.0, 0, 1)
        a2 = np.clip((g - (face_l + thresh + 30)) / 60.0, 0, 1) * 0.7
        m = np.clip(np.maximum(a1, a2), 0, 1)
        if m.max() < 0.08:
            pw.stdin.write(fr.tobytes())
            prev = None
            n += 1
            continue
        if prev is not None and prev.shape == m.shape:
            m = np.maximum(m, prev * 0.8)
        prev = m
        soft = gaussian_filter(m, 4.0) * strength
        # 就地压亮：把该像素亮度拉到 (脸中位 + thresh*0.45)，保留色相、保留结构
        tgt = face_l + thresh * 0.45
        cur = roi_img.mean(2, keepdims=True) + 1e-3
        scale = np.clip(tgt / cur, 0, 1)
        rep = roi_img * scale
        # 反射区细节抹平（屏幕上的字），但只抹高频、不动大结构
        lowp = gaussian_filter(roi_img, 3.0)
        rep = lowp * 0.72 + rep * 0.28
        aa = soft[..., None]
        out = roi_img * (1 - aa) + rep * aa
        fr[ry0:ry1, rx0:rx1] = np.clip(out, 0, 255).astype(np.uint8)
        pw.stdin.write(fr.tobytes())
        n += 1
        hit += int(m.max() > 0.5)
    pw.stdin.close()
    pw.wait()
    # 中间件（ultrafast 近乎无损）→ 正式成品（medium 高质量）
    cmd2 = [FF, "-y", "-v", "error", "-i", dst + ".mid.mp4", "-c:v", "libx264", "-preset", "medium",
            "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", dst]
    subprocess.run(cmd2, check=True)
    try:
        os.remove(dst + ".mid.mp4")
    except OSError:
        pass
    if log:
        print("  处理 %d 帧，命中反射 %d 帧" % (n, hit))
    return roi


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    roi = None
    if "--roi" in sys.argv:
        roi = tuple(int(x) for x in sys.argv[sys.argv.index("--roi") + 1].split(","))
    process(src, dst, roi)
