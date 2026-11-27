# -*- coding: utf-8 -*-
"""重出眼窗（脸部特写 PIP）：从源素材按 YuNet 检测到的脸框裁 16:9，输出 480x270
   之前 pipeline2_one 用肤色块估位置，脸区 ROI 落到天花板/窗帘上，眼窗全废 → 本次纠正
   用法: python redo_eye.py 1 2 3 4 5 6
"""
import io, json, os, subprocess, sys

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
FFP = FF.replace("ffmpeg.exe", "ffprobe.exe")
ROOT = "E:/心理咨询IP"
OUT = ROOT + "/素材_clean"
CROPS = json.load(io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "eye_crop.json")))


def run(n):
    src = "%s/素材/%d.mp4" % (ROOT, n)
    x, y, w, h = CROPS[str(n)]
    dst = "%s/eye_%d.mp4" % (OUT, n)
    for suf in (".mid.mp4",):
        try:
            os.remove(dst + suf)
        except OSError:
            pass
    # 源带 rotation=90，ffmpeg 会自动转正；先按显示坐标裁，再缩到 480x270
    vf = "crop=%d:%d:%d:%d,scale=480:270:flags=lanczos,setsar=1" % (w, h, x, y)
    r = subprocess.run([FF, "-y", "-v", "error", "-i", src, "-vf", vf,
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                        "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", dst],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("[%d] 失败 %s" % (n, r.stderr[-300:]), flush=True)
        return False
    p = subprocess.run([FFP, "-v", "error", "-show_entries", "format=duration:stream=width,height",
                        "-of", "csv=p=0", dst], capture_output=True, text=True)
    print("[%d] 眼窗完成 %s → %s" % (n, p.stdout.strip().replace("\n", " | "), os.path.basename(dst)), flush=True)
    return True


if __name__ == "__main__":
    for n in [int(a) for a in sys.argv[1:]]:
        run(n)
