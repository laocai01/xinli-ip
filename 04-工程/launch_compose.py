"""脱离式重合成启动器 v2 —— 设 UTF-8 输出，避开 GBK 控制台 emoji 崩溃
用法: python launch_compose.py new|base [A4 A5 ...]
"""
import os, sys, subprocess

P = r"E:/心理咨询IP/04-工程"
PY = sys.executable

JOBS = {
    "new":  ["A4", "A5", "B3", "B4"],
    "base": ["A2", "A3", "B1", "B2"],
}

key = sys.argv[1] if len(sys.argv) > 1 else "new"
keys = sys.argv[2:] if len(sys.argv) > 2 else JOBS[key]

for k in keys:
    log = os.path.join(P, f"_cmp_{k}.log")
    # ★ 关键：PYTHONIOENCODING=utf-8，否则 print(emoji) 在 GBK 控制台崩
    inner = (f'cd /d "{P}" && set PYTHONIOENCODING=utf-8 && '
             f'"{PY}" make_episode.py {k} > "{log}" 2>&1')
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
        f'Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{{CommandLine=\'cmd /c {inner}\'}} | Select-Object -ExpandProperty ProcessId'],
        capture_output=True, text=True, timeout=60)
    print(f"  [{key}] {k} → pid {r.stdout.strip()}")
