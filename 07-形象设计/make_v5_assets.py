"""生成多尺寸 PNG + 圆形裁切安全检查 + 深浅双版
母版：老蔡说_LOGO_母版_v5.svg
"""
import base64, subprocess, os
from pathlib import Path

BASE = Path(r"E:/嘉泰利贸易有限公司/08-心理咨询IP/07-形象设计")
CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
OUT = BASE / "交付_v5"
OUT.mkdir(exist_ok=True)

svg = (BASE / "老蔡说_LOGO_母版_v5.svg").read_text(encoding="utf-8")
b64 = base64.b64encode(svg.encode("utf-8")).decode()

def shot(html, png, size):
    p = BASE / html
    p.write_text(f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{{margin:0;padding:0;background:transparent}}
svg{{display:block;width:{size}px;height:{size}px}}</style></head>
<body><img src="data:image/svg+xml;base64,{b64}" width="{size}" height="{size}"></body></html>""",
                 encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--default-background-color=00000000",
                    f"--window-size={size},{size}", "--virtual-time-budget=4000",
                    f"--screenshot={OUT/png}", f"http://127.0.0.1:8933/{html}"],
                   capture_output=True)

for size in [1080, 400, 256, 128, 64]:
    shot(f"r_v5_{size}.html", f"老蔡说_头像_{size}.png", size)
    print(f"{size}px done")

# === 圆形裁切安全检查 ===
from PIL import Image
im = Image.open(OUT / "老蔡说_头像_1080.png").convert("RGBA")
W, H = im.size
bg = im.getpixel((5, 5))
cx, cy = W / 2, H / 2
R = W / 2
safe = R * 0.8
px = im.load()
maxd, over = 0, 0
for y in range(0, H, 2):
    for x in range(0, W, 2):
        r, g, b, a = px[x, y]
        if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > 24:
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if d > maxd:
                maxd = d
            if d > safe:
                over += 1
total, tested = over, (H // 2) * (W // 2)
print(f"\n元素距圆心最远: {maxd:.0f}px  (画布半径 {R:.0f}px)")
print(f"80%安全区半径: {safe:.0f}px")
print(f"超出安全区采样点: {over} / {tested}  ({over/tested*100:.2f}%)")
print("判定:", "✅ 圆切安全" if over == 0 else f"❌ 有 {over} 点越界，需缩小")
