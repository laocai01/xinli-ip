# -*- coding: utf-8 -*-
"""出片监督：判定"真在跑 / 真跑完 / 真跑空"

铁律（2026-11-02 董事长要求：不允许跑空和卡死）：
  1) 文件在长 = 在跑，不报错
  2) 文件不长 且 ffmpeg 还在 = 可能在收尾/写 moov，继续等，不判定完成
  3) 文件不长 且 ffmpeg 已退 = 才叫完成，且必须验证 moov 可读（能 ffprobe 出时长）
  4) 文件不长 且 ffmpeg 已退 且 moov 坏 = 跑空，立即报错停下

用法：
  python watch.py <输出文件路径> [--timeout 1500]
"""
import subprocess, sys, os, time

FF = r"C:/Users/Dell/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin"


def ffmpeg_count():
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "(Get-CimInstance Win32_Process|Where-Object{$_.Name -eq 'ffmpeg.exe'}).Count"],
                       capture_output=True, text=True)
    t = (r.stdout or "").strip()
    return int(t) if t.isdigit() else 0


def probe_ok(path):
    """能不能读出来时长（能=文件完整）"""
    r = subprocess.run([FF + "/ffprobe.exe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=nw=1:nk=1", path],
                       capture_output=True, text=True)
    t = (r.stdout or "").strip()
    try:
        return float(t) > 0
    except Exception:
        return False


def main():
    path = sys.argv[1]
    timeout = float(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 1500
    t0 = time.time()
    last_size, stall = 0, 0
    while True:
        time.sleep(20)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        n = ffmpeg_count()
        grow = size - last_size
        el = time.time() - t0
        print("[%s] %5.0fs %5.0fMB 增长%6.1fMB ffmpeg=%d"
              % (time.strftime("%H:%M:%S"), el, size / 1048576, grow / 1048576, n))
        if grow < 200 * 1024:
            stall += 1
        else:
            stall = 0
        last_size = size

        # 只有 ffmpeg 退出才算结束
        if n == 0:
            if size > 0 and probe_ok(path):
                print("✅ 完成且文件完整 %.1fs" % el)
                return 0
            print("❌ 跑空：ffmpeg 已退但文件不可读（%d MB）" % (size // 1048576))
            return 2

        if stall >= 8:   # 160 秒不增长但 ffmpeg 还在 → 告警，不判完成
            print("⚠️  %.0fs 文件无增长，但 ffmpeg 仍在跑（可能在收尾写 moov），继续等" % (stall * 20))

        if el > timeout:
            print("❌ 超时 %.0fs，卡死" % el)
            return 3


if __name__ == "__main__":
    sys.exit(main())
