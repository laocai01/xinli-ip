"""重做视频左上角角标：用最终版圆形标
- 左上角：圆形标（缩放 + 白色描边，保证在深色画面上清晰）
- 右下角：AI 声明条
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

BASE = Path(r"E:/嘉泰利贸易有限公司/08-心理咨询IP")
LOGO_SRC = BASE / "07-形象设计/交付_v5/圆形标/老蔡说_圆形标_1080.png"
OUT = BASE / "04-工程/overlay_new"
OUT.mkdir(parents=True, exist_ok=True)

# ===== 1. 左上角圆标（180px + 白色描边）=====
SIZE = 180
logo = Image.open(LOGO_SRC).convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)

# 白色描边环（在深色画面上清晰）
PAD = 5
canvas = Image.new("RGBA", (SIZE + PAD * 2, SIZE + PAD * 2), (0, 0, 0, 0))
d = ImageDraw.Draw(canvas)
d.ellipse((0, 0, SIZE + PAD * 2 - 1, SIZE + PAD * 2 - 1), fill=(255, 255, 255, 235))
canvas.alpha_composite(logo, (PAD, PAD))
canvas.save(OUT / "logo_corner.png")
print("左上角圆标:", canvas.size)

# ===== 2. 右下角 AI 声明 =====
TEXT = "本视频含有AI制作内容"
FS = 32
font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", FS)
tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
bbox = tmp.textbbox((0, 0), TEXT, font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
PADX, PADY = 22, 13
W, H = tw + PADX * 2, th + PADY * 2
bar = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d2 = ImageDraw.Draw(bar)
d2.rounded_rectangle((0, 0, W - 1, H - 1), radius=10, fill=(0, 0, 0, 160))
d2.text((PADX - bbox[0], PADY - bbox[1]), TEXT, font=font, fill=(255, 255, 255, 255))
bar.save(OUT / "ai_notice.png")
print("AI声明条:", bar.size)

# ===== 3. 坐标（1080x1920）=====
MARGIN = 44
TOP = 120
LOGO_X, LOGO_Y = MARGIN, TOP
NOTICE_X = 1080 - MARGIN - W
NOTICE_Y = 1920 - MARGIN - H
print(f"圆标位置: ({LOGO_X}, {LOGO_Y})")
print(f"声明位置: ({NOTICE_X}, {NOTICE_Y})")
(OUT / "pos.txt").write_text(f"{LOGO_X} {LOGO_Y} {NOTICE_X} {NOTICE_Y}", encoding="utf-8")
