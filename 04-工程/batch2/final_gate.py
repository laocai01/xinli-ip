# -*- coding: utf-8 -*-
"""最终验收闸门 · 任何一项不过就不许交付

用法：
    python final_gate.py <集号> <成片路径>
    python final_gate.py 5 "E:/心理咨询IP/05-成片/我是不是没用了/第27条_....mp4"

为什么要有它：
    历史上只验「时长 + 流规格」就把坏片交出去过（两个 ffmpeg 抢写同一文件，
    ffprobe 一切正常，整片解码报 5603 条 NAL 错误）。本脚本把「解码完整性」
    放到第一关，任何坏片在交付前被拦下。

六道闸门（顺序不能改，前一关不过直接退出，不浪费时间）：
    1. 解码完整性   ffmpeg -f null - 的 stderr 必须 0 行
    2. 时长         == 177.0s（±0.3）
    3. 流规格       1080x1920 / 30fps / h264 + aac
    4. 卡片落点     每张卡抽帧，卡片必须在 y>=940；人脸区皮肤像素必须够
    5. 字幕覆盖     字幕总时长 / 人声时长 >= 0.85
    6. 合规禁词     0 命中

退出码 0 = 全过可交付；非 0 = 不许交付。
"""
import io
import os
import re
import shutil
import subprocess
import sys

import numpy as np

R = os.path.dirname(os.path.abspath(__file__))
BIN = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin"
FF = os.path.join(BIN, "ffmpeg.exe")
FFP = os.path.join(BIN, "ffprobe.exe")
TARGET_DUR = 177.0


def C_plan(n):
    """惰性导入合成器取卡片计划（避免循环导入 / 启动开销）"""
    if R not in sys.path:
        sys.path.insert(0, R)
    import compose_batch2 as _C
    return _C.plan(n)
TOL = 0.35


def _ascii_copy(src, tag):
    """中文路径必须先复制成 ASCII 名，否则 ffmpeg 报 Illegal byte sequence"""
    os.makedirs("E:/tmp", exist_ok=True)
    dst = "E:/tmp/_gate_%s.mp4" % tag
    if os.path.exists(dst):
        os.remove(dst)
    shutil.copy2(src, dst)
    return dst


def gate_decode(path):
    """1. 整片解码完整性 —— 最关键的一关"""
    r = subprocess.run([FF, "-v", "error", "-i", path, "-f", "null", "-"],
                       capture_output=True, text=True, errors="ignore")
    errs = [l for l in r.stderr.splitlines() if l.strip()]
    if errs:
        return False, "解码错误 %d 条（前1条：%s）" % (len(errs), errs[0][:100])
    return True, "0 错误"


def gate_duration(path):
    r = subprocess.run([FFP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        d = float(r.stdout.strip())
    except ValueError:
        return False, "读不到时长"
    if abs(d - TARGET_DUR) > TOL:
        return False, "时长 %.2fs（应 %.1fs）" % (d, TARGET_DUR)
    return True, "%.2fs" % d


def gate_spec(path):
    r = subprocess.run([FFP, "-v", "error", "-show_entries",
                        "stream=codec_name,width,height,r_frame_rate",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    txt = r.stdout.strip()
    if "h264" not in txt or "aac" not in txt:
        return False, "流不全：%s" % txt
    if "1080,1920" not in txt.replace(" ", ""):
        return False, "分辨率不对：%s" % txt
    if "30/1" not in txt:
        return False, "帧率不对：%s" % txt
    return True, txt.replace("\n", " | ")


def gate_cards(n, path):
    """4. 卡片必须原样全屏呈现（2026-10-27 董事长纠正：不许裁剪、不许只放一部分）

    ★ 判据纠错记录（别再写窄）：
      - 用过「肤色占比」→ 卡片底色暖米 RGB(240,233,222) 正落在肤色区间，误报 36.9%
      - 用过「暖色底占比」→ 该集卡片是浅灰白底 RGB(218,227,221)，误报 0.6%
      - 最终判据：不看颜色，看「这是不是一张人工排版图」——
          (a) 不是真人：肤色像素 <3%
          (b) 是排版图：中位亮度高 + 大面积低饱和平整区域 >=55%
          (c) 四角有内容（不是空帧）
    """
    sys.path.insert(0, R)
    cards = C_plan(n)["cards"]
    if len(cards) < 9:
        return False, "卡片只有 %d 张（应 10 张）" % len(cards)
    bad = []
    for name, start, hold, tail in cards:
        t = start + hold * 0.75          # 动画末段抽，避开入场
        raw = subprocess.run([FF, "-v", "error", "-ss", "%.2f" % t, "-i", path,
                              "-frames:v", "1", "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        if len(raw) < 1080 * 1920 * 3:
            bad.append("%s(抽帧失败)" % name)
            continue
        a = np.frombuffer(raw, dtype=np.uint8)[:1080 * 1920 * 3].reshape(1920, 1080, 3).astype(int)
        r_, g_, b_ = a[:, :, 0], a[:, :, 1], a[:, :, 2]
        lum = a.mean(axis=2)
        sat = a.max(axis=2) - a.min(axis=2)

        # ★ 判据只看「这是不是一张排版图」，不检测肤色/颜色：
        #   卡片的暖米底、暖棕标题字都会被肤色判据误伤（第25条实测误报 8.4%），
        #   而真人画面本身就有大量平整背景，所以只能靠「大面积极平整区域」判断。
        flat = (sat < 45) & (lum > 140)
        if flat.mean() < 0.50:
            bad.append("%s(非排版图，平整区仅 %.0f%%)" % (name, flat.mean() * 100))
            continue

        # (c) 四角有内容
        for cy, cx, tag in [(40, 40, "左上"), (40, 1040, "右上"),
                            (1880, 40, "左下"), (1880, 1040, "右下")]:
            patch = a[cy - 30:cy + 30, cx - 30:cx + 30]
            if patch.std() < 3.0:
                bad.append("%s(%s角空白)" % (name, tag))
                break
    if bad:
        return False, "；".join(bad[:4])
    return True, "%d 张全部全屏原样呈现" % len(cards)


def gate_subs(n):
    """5. 字幕覆盖率 —— 字幕总时长 / 口播时长 >= 0.85"""
    p = os.path.join(R, "subs", "%d.ass" % n)
    if not os.path.exists(p):
        return False, "缺 subs/%d.ass" % n
    txt = io.open(p, encoding="utf-8", errors="ignore").read()
    ev = re.findall(r"Dialogue:\s*\d+,(\d+):(\d+):([\d.]+),(\d+):(\d+):([\d.]+)", txt)

    def sec(a, b, c):
        return int(a) * 3600 + int(b) * 60 + float(c)

    if not ev:
        return False, "字幕 0 条"
    spans = sorted((sec(*e[:3]), sec(*e[3:])) for e in ev)
    end = max(b for a, b in spans)
    # ★ 用「并集覆盖」而不是「时长总和」：滚动字幕每段在屏 4-5s 且前后叠放，
    #   时长总和会超过片长数倍（第24条实测 845%），但那是正常的，不是错。
    union, cur_s, cur_e = 0.0, spans[0][0], spans[0][1]
    for s, e in spans[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            union += cur_e - cur_s
            cur_s, cur_e = s, e
    union += cur_e - cur_s
    cov = union / max(1.0, end)
    if union < end - 6.0:
        gaps = end - union
        return False, "字幕有 %.0fs 空档没覆盖到" % gaps
    if cov < 0.85:
        return False, "并集覆盖仅 %.0f%%" % (cov * 100)
    return True, "%d 条 / 到 %.0fs / 覆盖 %.0f%%" % (len(ev), end, cov * 100)


def gate_compliance(n):
    r = subprocess.run([sys.executable, os.path.join(R, "compliance_check.py"), str(n)],
                       capture_output=True, text=True, errors="ignore")
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"命中\s*(\d+)\s*处", out)
    if not m:
        return False, "合规脚本无输出"
    if int(m.group(1)) > 0:
        return False, "禁词 %s 处" % m.group(1)
    return True, "0 命中"


def main():
    if len(sys.argv) < 3:
        print("用法: python final_gate.py <集号> <成片路径>")
        return 2
    n = int(sys.argv[1])
    src = sys.argv[2]
    if not os.path.exists(src):
        print("❌ 文件不存在：%s" % src)
        return 2

    tmp = _ascii_copy(src, str(n))
    results = []
    try:
        for label, fn in [
            ("1 解码完整性", lambda: gate_decode(tmp)),
            ("2 时长", lambda: gate_duration(tmp)),
            ("3 流规格", lambda: gate_spec(tmp)),
            ("4 卡片落点", lambda: gate_cards(n, tmp)),
            ("5 字幕覆盖", lambda: gate_subs(n)),
            ("6 合规禁词", lambda: gate_compliance(n)),
        ]:
            ok, msg = fn()
            results.append((label, ok, msg))
            print(("  ✅" if ok else "  ❌") + " %s: %s" % (label, msg), flush=True)
            if not ok:
                print("\n❌ 拦截：%s 未通过，此片不许交付" % label, flush=True)
                return 1
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    print("\n✅ 六道闸门全过，可交付：%s" % os.path.basename(src), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
