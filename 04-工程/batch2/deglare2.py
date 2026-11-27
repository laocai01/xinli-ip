# -*- coding: utf-8 -*-
"""眼镜镜片反光去除 v2（2026-10-24 重做）
   v1 的毛病：靠 faces_roi 粗估眼区 → 经常框到额头/头发，镜片反光没压干净。
   v2 做法：
     ① 用 YuNet 人脸检测拿到【双眼精确坐标】（每集一条素材只检一次，稳定）
     ② 由双眼推出两个镜片的椭圆范围
     ③ 只在镜片椭圆内做「高光抑制」：局部压亮 + 去绿偏 + 抹平矩形亮块
     ④ 椭圆外一字不动（不磨皮、不动皮肤），避免补丁感
     ⑤ 帧间掩膜平滑，防止闪烁
"""
import os, subprocess, sys
import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
FFP = FF.replace("ffmpeg.exe", "ffprobe.exe")
ROOT = "E:/心理咨询IP"
HERE = os.path.dirname(os.path.abspath(__file__))
# ★ OpenCV 读不了中文路径下的 ONNX，模型必须放纯英文路径
YUNET = r"E:\Hermes\models\yunet.onnx"
if not os.path.exists(YUNET):                       # 兜底：从工程目录复制过去
    os.makedirs(os.path.dirname(YUNET), exist_ok=True)
    import shutil as _sh
    _sh.copy2(os.path.join(HERE, "yunet.onnx"), YUNET)


# ---------- 探测 ----------
def probe(p):
    SPEC = FFP
    r = subprocess.run([SPEC, "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0", p],
                       capture_output=True, text=True)
    first = r.stdout.strip().splitlines()[0]
    parts = [x for x in first.split(",") if x.strip()]
    a, b = int(parts[0]), int(parts[1])
    fr = parts[2] if len(parts) > 2 else "24/1"
    num, den = fr.split("/")
    fps = float(num) / float(den)
    rr = subprocess.run([SPEC, "-v", "error", "-select_streams", "v:0",
                         "-show_entries", "stream_side_data=rotation", "-of", "csv=p=0", p],
                        capture_output=True, text=True)
    txt = (rr.stdout or "").strip().splitlines()
    rot = 0
    if txt:
        try:
            rot = int(float(txt[0]))
        except ValueError:
            rot = 0
    if abs(rot) == 90:
        return b, a, fps      # 显示是竖的
    return a, b, fps


def read_frames(p, w, h):
    """流式读帧（ffmpeg 自动转正，不加任何滤镜）"""
    sw, sh, _fps = probe(p)
    cmd = [FF, "-v", "error", "-i", p, "-threads", "4",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    pr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10 ** 8)
    n = sw * sh * 3
    while True:
        buf = pr.stdout.read(n)
        if len(buf) < n:
            break
        fr = np.frombuffer(buf, np.uint8).reshape(sh, sw, 3)
        if (sw, sh) != (w, h):
            fr = cv2.resize(np.ascontiguousarray(fr), (w, h), interpolation=cv2.INTER_AREA)
        yield fr.copy()
    try:
        pr.stdout.close(); pr.wait(timeout=10)
    except Exception:
        pass


# ---------- 找眼睛 ----------
def find_eyes(p, w, h, n_samples=6):
    """多次采样求双眼位置中位数（避免某一帧侧脸/闭眼导致偏移）"""
    det = cv2.FaceDetectorYN_create(YUNET, "", (320, 320), 0.6, 0.3, 5000)
    got = []
    for i, fr in enumerate(read_frames(p, w, h)):
        if i % 37:
            continue
        det.setInputSize((w, h))
        ok, f = det.detect(fr)
        if f is None or len(f) == 0:
            continue
        r = max(f, key=lambda a: a[2] * a[3])
        pts = r[4:14].reshape(-1, 2)
        got.append((float(pts[0][0]), float(pts[0][1]), float(pts[1][0]), float(pts[1][1]),
                    float(r[0]), float(r[1]), float(r[2]), float(r[3])))
        if len(got) >= n_samples:
            break
    if not got:
        return None
    a = np.array(got)
    med = np.median(a, axis=0)
    return dict(rx=med[0], ry=med[1], lx=med[2], ly=med[3],
                fx=med[4], fy=med[5], fw=med[6], fh=med[7], n=len(got))


# ---------- 镜片掩膜 ----------
def lens_mask(shape, eyes, grow=1.0):
    """由双眼坐标生成镜片掩膜 v2（2026-10-24 按实测重画）
       实测发现：反光重心比眼睛中心高 108px，而眼距只有 201px，
       说明原椭圆（半高 0.44×眼距=88）框不住镜框上沿的反光。
       → 改为：镜片中心上移到眼睛上方、半高放大到 0.62×眼距，
         横向 0.60×眼距，两镜片之间用鼻梁桥接，整体再羽化。"""
    h, w = shape[:2]
    if eyes is None:
        return None
    rx, ry, lx, ly = eyes["rx"], eyes["ry"], eyes["lx"], eyes["ly"]
    iod = abs(lx - rx)
    if iod < 10:
        return None
    aw = iod * 0.60 * grow
    ah = iod * 0.62 * grow
    # 镜片中心相对眼睛上移（镜框上沿 + 眉下缘都在这一带）
    lift = iod * 0.22
    m = np.zeros((h, w), np.float32)
    for cx, cy in ((rx, ry), (lx, ly)):
        cv2.ellipse(m, (int(round(cx)), int(round(cy - lift))),
                    (int(round(aw)), int(round(ah))), 0, 0, 360, 1.0, -1)
    # 鼻梁桥接：两镜片中间那一块也覆盖（反光常横跨）
    cv2.rectangle(m, (int(min(rx, lx) - aw * 0.15), int(ry - lift - ah * 0.45)),
                  (int(max(rx, lx) + aw * 0.15), int(ry - lift + ah * 0.55)), 1.0, -1)
    m = cv2.GaussianBlur(m, (0, 0), max(2.0, iod * 0.05))
    return m




def lens_box(shape, eyes, grow=1.0):
    """返回镜片区域的裁剪框 (x0,y0,x1,y1)，用于只处理一小块、省 CPU"""
    h, w = shape[:2]
    if eyes is None:
        return None
    rx, ry, lx, ly = eyes["rx"], eyes["ry"], eyes["lx"], eyes["ly"]
    iod = abs(lx - rx)
    if iod < 10:
        return None
    aw = iod * 0.60 * grow
    ah = iod * 0.62 * grow
    lift = iod * 0.22
    x0 = int(max(0, min(rx, lx) - aw - 6))
    x1 = int(min(w, max(rx, lx) + aw + 6))
    y0 = int(max(0, min(ry, ly) - lift - ah - 6))
    y1 = int(min(h, max(ry, ly) - lift + ah + 6))
    return x0, y0, x1, y1


# ---------- 镜片底色标定 ----------
def calibrate_lens(src, w, h, eyes, n=25):
    """跨帧标定镜片真实底色（不用单帧中位数——单帧会被高光本身抬高）
       做法：取多帧镜片区域所有像素的【低分位】作为底色，
       因为镜片底色像素永远占多数，反光只是少数亮点。"""
    sel_all = []
    cnt = 0
    for i, fr in enumerate(read_frames(src, w, h)):
        if i % 43:
            continue
        mask = lens_mask(fr.shape, eyes, 1.0)
        if mask is None:
            continue
        sel = mask > 0.5
        if sel.sum() < 100:
            continue
        lab = cv2.cvtColor(fr, cv2.COLOR_BGR2LAB).astype(np.float32)
        sel_all.append(lab[sel][:, :3])
        cnt += 1
        if cnt >= n:
            break
    if not sel_all:
        return None
    allpx = np.vstack(sel_all)
    return dict(L=float(np.percentile(allpx[:, 0], 35)),
                A=float(np.percentile(allpx[:, 1], 35)),
                B=float(np.percentile(allpx[:, 2], 35)),
                n=cnt)


# ---------- 单帧处理 ----------
def deglare_frame(fr, mask, prev_soft=None, strength=1.0, base=None, box=None):
    """镜片去反光 v10（小块处理，提速用）
       只在镜片裁剪框内做 Lab 转换 + 模糊，框外像素零开销。
       v9 的算法不变：软阈值压亮 + 色偏回中 + 兜底硬压。"""
    if mask is None:
        return fr, prev_soft
    if box is None:
        ys, xs = np.where(mask > 0.3)
        if len(ys) < 100:
            return fr, prev_soft
        box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(fr.shape[1], x1), min(fr.shape[0], y1)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return fr, prev_soft

    patch = fr[y0:y1, x0:x1]
    mp = mask[y0:y1, x0:x1]
    sel = mp > 0.30
    if sel.sum() < 60:
        return fr, prev_soft

    lab = cv2.cvtColor(patch, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    if base is None:
        base = dict(L=float(np.percentile(L[sel], 35)),
                    A=float(np.percentile(A[sel], 35)),
                    B=float(np.percentile(B[sel], 35)))
    bL, bA, bB = base["L"], base["A"], base["B"]

    fL = np.clip((L - (bL + 12.0)) / 40.0, 0, 1)
    fA = np.clip(((bA - 3.0) - A) / 12.0, 0, 1)
    soft = np.clip(np.maximum(fL, fA), 0, 1) * mp
    if prev_soft is not None and prev_soft.shape == soft.shape:
        soft = np.maximum(soft, prev_soft * 0.88)
    k = np.clip(gaussian_filter(soft, 1.4), 0, 1)

    cap = bL + 6.0
    L2 = L * (1 - k) + np.minimum(L, cap) * k
    A2 = A * (1 - k) + (bA + (A - bA) * 0.08) * k
    B2 = B * (1 - k) + (bB + (B - bB) * 0.08) * k

    over = (L2 > cap) & (mp > 0.6)
    if over.any():
        L2 = np.where(over, cap, L2)
        A2 = np.where(over, bA + (A2 - bA) * 0.05, A2)
        B2 = np.where(over, bB + (B2 - bB) * 0.05, B2)

    outp = cv2.cvtColor(cv2.merge([L2, A2, B2]).astype(np.uint8), cv2.COLOR_LAB2BGR)
    w3 = np.clip(mp, 0, 1)[..., None]
    res = patch.astype(np.float32) * (1 - w3) + outp.astype(np.float32) * w3
    fr = fr.copy()
    fr[y0:y1, x0:x1] = np.clip(res, 0, 255).astype(np.uint8)
    return fr, soft
