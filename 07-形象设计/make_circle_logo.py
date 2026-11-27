"""生成圆形标（圆形裁切 + 透明底 PNG）
从 交付_v5/老蔡说_头像_1080.png 切出真正的圆形，四个角透明
"""
from PIL import Image, ImageDraw
from pathlib import Path

BASE = Path(r"E:/嘉泰利贸易有限公司/08-心理咨询IP/07-形象设计")
SRC = BASE / "交付_v5" / "老蔡说_头像_1080.png"
OUT = BASE / "交付_v5" / "圆形标"
OUT.mkdir(parents=True, exist_ok=True)

src = Image.open(SRC).convert("RGBA")
W, H = src.size

# 圆形遮罩（超采样抗锯齿）
SS = 4
mask = Image.new("L", (W * SS, H * SS), 0)
ImageDraw.Draw(mask).ellipse((0, 0, W * SS - 1, H * SS - 1), fill=255)
mask = mask.resize((W, H), Image.LANCZOS)

circle = Image.new("RGBA", (W, H), (0, 0, 0, 0))
circle.paste(src, (0, 0))
circle.putalpha(mask)
circle.save(OUT / "老蔡说_圆形标_1080.png")
print("1080 圆形标 done")

# 各尺寸
for size in [400, 256, 180, 128, 64]:
    circle.resize((size, size), Image.LANCZOS).save(OUT / f"老蔡说_圆形标_{size}.png")
    print(f"{size} 圆形标 done")

# 透明底验证
im = Image.open(OUT / "老蔡说_圆形标_1080.png")
print("\n角上像素(应为全透明):", im.getpixel((3, 3)))
print("正中像素:", im.getpixel((540, 540)))
print("尺寸:", im.size)
