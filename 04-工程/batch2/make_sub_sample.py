# -*- coding: utf-8 -*-
"""出字幕效果对比样：同一句、同一时刻，只改放大倍数/光边强度。

用法：python make_sub_sample.py <n> <时刻秒> <放大%> <光边宽> <输出名>
"""
import io, os, sys, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subs_and_anchors as S

FF = "C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"
R = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(R, "_cmp")
os.makedirs(OUT, exist_ok=True)


def make(n, t_at, scale, glow_w, tag):
    """按指定放大倍数与光边宽重建 ASS，抽一帧。"""
    src = os.path.join(R, "subs", "%d.ass" % n)
    base = io.open(src, encoding="utf-8").read()

    # 只替换本轮的两处数值：光边 bord / 放大 fscx-fscy
    # 只改 \\t(...) 里的放大目标值，不能碰 \\fscx100 这些基础值
    out = base.replace("\\bord26", "\\bord%d" % glow_w)
    out = out.replace("\\t(0,9,\\fscx145\\fscy145",
                      "\\t(0,9,\\fscx%d\\fscy%d" % (scale, scale))
    assert "\\\\fscx%d" % scale in out or ("fscx%d" % scale) in out, "放大值未写入"
    tmp = os.path.join(OUT, "t_%s.ass" % tag)
    io.open(tmp, "w", encoding="utf-8").write(out)

    esc = tmp.replace("\\", "/").replace(":", "\\:")
    fdir = S.FONTDIR.replace("\\", "/").replace(":", "\\:")
    vf = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
          "subtitles=filename='%s':fontsdir='%s'" % (esc, fdir))
    png = os.path.join(OUT, "%s.jpg" % tag)
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(t_at),
                    "-i", os.path.join("E:/心理咨询IP/素材_clean2", "%d.mp4" % n),
                    "-frames:v", "1", "-vf", vf, "-q:v", "2", png], check=True)
    print(tag, os.path.getsize(png))


if __name__ == "__main__":
    n, t_at, scale, glow_w, tag = (int(sys.argv[1]), float(sys.argv[2]),
                                   int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    make(n, t_at, scale, glow_w, tag)
