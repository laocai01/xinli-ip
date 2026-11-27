import base64, os, subprocess, glob

BASE = r"E:/心理咨询IP/07-形象设计/双线样张"
CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
LOGO = r"E:/心理咨询IP/07-形象设计/交付_v5/圆形标/老蔡说_圆形标_400.png"

logo_uri = "data:image/png;base64," + base64.b64encode(open(LOGO, "rb").read()).decode()

for html in glob.glob(os.path.join(BASE, "*.html")):
    src = open(html, encoding="utf-8").read().replace("__LOGO__", logo_uri)
    tmp = os.path.join(BASE, "_tmp.html")
    open(tmp, "w", encoding="utf-8").write(src)
    out = os.path.splitext(html)[0] + ".png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", "--window-size=1080,1920",
                    "--screenshot=" + out, "--default-background-color=00000000",
                    "file:///" + tmp.replace("\\", "/")],
                   capture_output=True, timeout=120)
    print(("OK  " if os.path.exists(out) else "FAIL"), os.path.basename(out),
          os.path.getsize(out) if os.path.exists(out) else "")

os.remove(os.path.join(BASE, "_tmp.html"))
print("完成")
