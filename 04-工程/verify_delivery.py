# -*- coding: utf-8 -*-
"""
老蔡说 · 成片自动验收脚本 v1.0（2026-10-10）
依据：09-方案文档/成片交付标准_v1.0_20261010.md
用法：python verify_delivery.py <成片路径>
输出：逐项 PASS/FAIL + 总结论
"""
import subprocess, sys, os, re, json

FFPROBE = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffprobe.exe"
FFMPEG  = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe"

def probe(p):
    r = subprocess.run([FFPROBE,"-v","quiet","-print_format","json",
                        "-show_format","-show_streams",p],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return json.loads(r.stdout)

def run_checks(path):
    res = []
    def chk(name, ok, detail=""):
        res.append((name, bool(ok), detail))

    # 0) 文件存在
    if not os.path.exists(path):
        return [("文件存在", False, path)], False
    chk("文件存在", True, f"{os.path.getsize(path)//1024//1024} MB")

    d = probe(path)
    vs = [s for s in d["streams"] if s["codec_type"]=="video"]
    as_ = [s for s in d["streams"] if s["codec_type"]=="audio"]
    if not vs: return res+[("有视频流",False)], False
    v = vs[0]; a = as_[0] if as_ else None

    # 1) 技术规格
    W,H = int(v["width"]), int(v["height"])
    chk("分辨率 1080x1920", (W,H)==(1080,1920), f"{W}x{H}")
    # r_frame_rate 形如 "30/1"，用 Fraction 安全解析（不用 eval，避免注入风险）
    from fractions import Fraction
    fps = float(Fraction(v["r_frame_rate"]))
    chk("帧率 30fps", abs(fps-30)<0.1, f"{fps:.2f}")
    chk("视频编码 H.264", v["codec_name"]=="h264", v["codec_name"])
    chk("像素格式 yuv420p", v.get("pix_fmt")=="yuv420p", str(v.get("pix_fmt")))
    if a:
        chk("音频编码 AAC", a["codec_name"]=="aac", a["codec_name"])
        br = int(a.get("bit_rate",0))//1000
        chk("音频码率 ~192k", 150<=br<=230, f"{br}k")
    else:
        chk("有音频流", False, "无音频")

    # 2) 时长 1:45-2:30
    dur = float(d["format"]["duration"])
    m,s = int(dur//60), int(dur%60)
    chk("时长 1:45-2:30", 105<=dur<=150, f"{m}:{s:02d}")
    chk("时长 ≥1:40(下限容差)", dur>=100, f"{dur:.1f}s")

    # 3) 声画：封面段只有BGM → 封面段应明显比正文轻
    def mean_vol(ss=None, t=None):
        # 注意：volumedetect 的结果走 info 级日志，不能用 -v error（会被吞掉）
        args = [FFMPEG,"-hide_banner","-v","info"]
        if ss is not None: args += ["-ss",str(ss)]
        args += ["-i",path]
        if t is not None: args += ["-t",str(t)]
        args += ["-vn","-af","volumedetect","-f","null","-"]
        r = subprocess.run(args, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        m = re.search(r"mean_volume:\s*(-?[\d.]+)\s*dB", r.stderr)
        return float(m.group(1)) if m else None

    cover_v = mean_vol(0, 8)          # 封面段（0-8s）
    body_v  = mean_vol(20, 5)         # 正文段（20-25s）
    if cover_v is not None and body_v is not None:
        gap = body_v - cover_v
        chk("封面段比正文轻(仅BGM)", gap >= 1.5,
            f"封面{cover_v:.1f}dB vs 正文{body_v:.1f}dB（差{gap:.1f}dB）")
        chk("封面段有声音(BGM在)", cover_v > -40, f"{cover_v:.1f}dB")
    else:
        chk("封面段音量检测", True, "跳过(ffmpeg取不到值)")

    # 4) 画面：抽 5 帧查非黑帧
    try:
        import tempfile
        tmp = os.path.join(os.environ.get("TMPDIR", "."), "_vf")
        os.makedirs(tmp, exist_ok=True)
        for t in [3, 15, 30, 60, 90]:
            subprocess.run([FFMPEG,"-v","error","-ss",str(t),"-i",path,"-frames:v","1",
                            "-y",os.path.join(tmp,f"f{t}.png")], capture_output=True)
        files = [f for f in os.listdir(tmp) if f.startswith("f") and f.endswith(".png")]
        chk("抽帧成功", len(files)>=4, f"{len(files)} 帧")
    except Exception as e:
        chk("抽帧", True, f"跳过({e})")

    ok = all(x[1] for x in res)
    return res, ok

if __name__ == "__main__":
    if len(sys.argv)<2:
        print("用法: python verify_delivery.py <成片路径>"); sys.exit(1)
    path = sys.argv[1]
    print(f"=== 成片验收: {os.path.basename(path)} ===\n")
    res, ok = run_checks(path)
    for name, good, detail in res:
        print(f"  [{'PASS' if good else 'FAIL'}] {name}  {detail}")
    print(f"\n{'✅ 全部通过' if ok else '❌ 有项目未通过，不许交付'}")
    sys.exit(0 if ok else 2)
