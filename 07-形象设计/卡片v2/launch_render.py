"""脱离式渲染启动器 —— 用 WMI 启动，不受 Hermes 会话生命周期影响
用法: python E:/心理咨询IP/07-形象设计/卡片v2/launch_render.py [组号]
"""
import os, sys, subprocess

P = r"E:/心理咨询IP/07-形象设计/卡片v2"
PY = sys.executable

GROUPS = {
    "n1": ["A5n_01钩子", "B3n_01钩子", "B3n_02痛点", "B4n_02反常识"],   # 新四条剩余4张
    "b1": ["A2n_01钩子", "A2n_02痛点", "A2n_03机制", "A2n_04转折", "A2n_05方法", "A2n_06收束"],
    "b2": ["A3n_01钩子", "A3n_02总览", "A3n_03停", "A3n_04退", "A3n_05看", "A3n_06做", "A3n_07收束"],
    "b3": ["B1n_01钩子", "B1n_02场景", "B1n_03机制", "B1n_04点破", "B1n_05转折", "B1n_06方法", "B1n_07收束"],
    "b4": ["B2n_01钩子", "B2n_02痛点", "B2n_03机制", "B2n_04对比", "B2n_05方法", "B2n_06收束"],
    "b5": ["封面_新_第1讲", "封面_新_第2讲", "B1封面_第1讲", "B2封面_第2讲"],
    "b6": ["闭环_第1讲", "闭环_第2讲", "闭环_第3讲", "闭环_第4讲"],
}

key = sys.argv[1] if len(sys.argv) > 1 else "n1"
names = GROUPS[key]
log = os.path.join(P, f"_x{key}.log")
cmd = f'cd /d "{P}" && "{PY}" render_all.py {" ".join(names)} > "{log}" 2>&1'

# 用 WMI Win32_Process.Create 启动 —— 完全脱离父进程，Hermes 会话结束也不影响
r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
    f'Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{{CommandLine=\'cmd /c {cmd}\'}} | Select-Object -ExpandProperty ProcessId'],
    capture_output=True, text=True, timeout=60)
print(f"[{key}] {len(names)} 张 → pid {r.stdout.strip()}")
