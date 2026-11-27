import base64, os, subprocess, sys

BASE = r"E:/心理咨询IP/07-形象设计"
LOGO = os.path.join(BASE, "交付_v5/圆形标/老蔡说_圆形标_400.png")
CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"

# 用法: python render_cover.py [模板名]   默认"封面_第02条"
name = sys.argv[1] if len(sys.argv) > 1 else "封面_第02条"
HTML = os.path.join(BASE, name + ".html")
OUT  = os.path.join(BASE, name + ".png")
assert os.path.exists(HTML), "模板不存在: " + HTML

with open(LOGO, "rb") as f:
    data_uri = "data:image/png;base64," + base64.b64encode(f.read()).decode()

html = open(HTML, encoding="utf-8").read()
assert "__LOGO__" in html, "模板里没有 __LOGO__ 占位符"
html = html.replace("__LOGO__", data_uri)

tmp = os.path.join(BASE, "_render_" + name + ".html")
open(tmp, "w", encoding="utf-8").write(html)

cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
       f"--screenshot={OUT}", "--window-size=1080,1920",
       "--force-device-scale-factor=1",
       "file:///" + tmp.replace("\\", "/")]
r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
print("exit:", r.returncode)
if os.path.exists(OUT):
    print("OK ->", OUT, os.path.getsize(OUT), "bytes")
else:
    print("!! 截图未生成"); print(r.stderr[-1200:]); sys.exit(1)
