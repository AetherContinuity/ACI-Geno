#!/usr/bin/env python3
"""Generate the cover for The Weight of a Bunch (1600x2560).

Design: night forest at 61N, a warm glass wall of greenhouse 3 at the right,
the snowman as a small instrument in front of it, one hanging bunch silhouette
inside the glass, and the title in cream. All shapes drawn with Pillow.
"""
import math
import random
from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 2560
random.seed(181617)

# ---------- palette ----------
SKY_TOP = (10, 15, 26)
SKY_MID = (21, 30, 48)
SKY_LOW = (36, 46, 66)
GLASS_WARM_1 = (244, 186, 84)
GLASS_WARM_2 = (196, 122, 44)
TREE = (8, 12, 20)
CREAM = (241, 230, 206)
DIM = (206, 196, 172)
SILH = (12, 16, 24)
CARROT = (232, 130, 52)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


img = Image.new('RGB', (W, H), SKY_TOP)
d = ImageDraw.Draw(img)

# ---------- sky gradient ----------
for y in range(H):
    if y < H * 0.55:
        t = y / (H * 0.55)
        c = lerp(SKY_TOP, SKY_MID, t)
    else:
        t = (y - H * 0.55) / (H * 0.45)
        c = lerp(SKY_MID, SKY_LOW, min(1.0, t))
    d.line([(0, y), (W, y)], fill=c)

# ---------- stars ----------
for _ in range(140):
    x = random.randint(0, W - 1)
    y = random.randint(0, int(H * 0.5))
    r = random.choice((1, 1, 1, 2))
    fade = 1 - y / (H * 0.55)
    c = lerp(SKY_TOP, (225, 225, 210), fade * random.uniform(0.5, 1.0))
    d.ellipse([x - r, y - r, x + r, y + r], fill=c)

# ---------- glass wall (right half, glowing) ----------
gx0, gx1 = int(W * 0.52), W
gy0, gy1 = int(H * 0.30), int(H * 0.78)
glass = Image.new('RGB', (gx1 - gx0, gy1 - gy0), (0, 0, 0))
gd = ImageDraw.Draw(glass)
gw, gh = glass.size
for yy in range(gh):
    t = yy / gh
    gd.line([(0, yy), (gw, yy)], fill=lerp(GLASS_WARM_1, GLASS_WARM_2, t))
# vertical light falloff overlay
for yy in range(gh):
    t = yy / gh
    dark = int(60 * t)
    gd.line([(0, yy), (gw, yy)], fill=(max(0, GLASS_WARM_1[0] - dark), GLASS_WARM_1[1], GLASS_WARM_1[2]))
img.paste(glass, (gx0, gy0))

# pane lines
for fx in [0.18, 0.42, 0.66, 0.88]:
    x = gx0 + int(gw * fx)
    d.line([(x, gy0), (x, gy1)], fill=(40, 44, 40), width=4)
for fy in [0.24, 0.5, 0.76]:
    y = gy0 + int(gh * fy)
    d.line([(gx0, y), (gx1, y)], fill=(40, 44, 40), width=4)
# glass frame
d.rectangle([gx0, gy0, gx1 - 1, gy1 - 1], outline=(16, 20, 28), width=10)

# ---------- bunch silhouette inside the glass ----------
bx = gx0 + int(gw * 0.30)
by = gy0 + int(gh * 0.13)
# rachis: gentle curve from the crown down
ts = [(bx, by)]
for i in range(1, 13):
    t = i / 12
    ts.append((bx + int(60 * math.sin(t * 2.2)), by + int(gh * 0.30 * t)))
for (x0, y0), (x1, y1) in zip(ts, ts[1:]):
    d.line([(x0, y0), (x1, y1)], fill=SILH, width=14)

# one pendulant hand of banana fingers, hanging crescents
hand_x, hand_y = ts[3][0] + 12, ts[3][1] + 8
for i, (dx0, dy0, r0, th) in enumerate([
        (-96, 6, 128, 30), (-52, 26, 120, 32), (-6, 40, 118, 34),
        (38, 32, 122, 32), (82, 14, 126, 30), (-30, 78, 96, 26), (22, 92, 98, 28)]):
    cx = hand_x + dx0
    cy = hand_y + dy0
    d.arc([cx - r0, cy - r0, cx + r0, cy + r0], start=18, end=162, fill=SILH, width=th)
    # tiny stem connecting finger to the rachis
    d.line([(cx, cy - r0), (cx + (hand_x - cx) // 3, hand_y)], fill=SILH, width=8)

# ---------- snowman in front of the glass ----------
sx = gx0 - 120
base_y = int(H * 0.815)
# melted base puddle: ellipse
d.ellipse([sx - 150, base_y - 26, sx + 150, base_y + 26], fill=(230, 236, 244))
d.ellipse([sx - 92, base_y - 120, sx + 92, base_y + 6], fill=SILH)      # lower tier
d.ellipse([sx - 60, base_y - 216, sx + 60, base_y - 106], fill=SILH)    # upper tier
d.ellipse([sx - 34, base_y - 282, sx + 34, base_y - 196], fill=SILH)    # head
# bucket hat
d.polygon([(sx - 44, base_y - 282), (sx + 44, base_y - 282),
           (sx + 30, base_y - 330), (sx - 30, base_y - 330)], fill=SILH)
# scarf
d.rectangle([sx - 36, base_y - 196, sx + 36, base_y - 178], fill=SILH)
# eyes: dark hollows; carrot as the one warm point
d.ellipse([sx - 18, base_y - 252, sx - 6, base_y - 240], fill=(230, 236, 244))
d.ellipse([sx + 6, base_y - 252, sx + 18, base_y - 240], fill=(230, 236, 244))
d.polygon([(sx - 4, base_y - 236), (sx + 120, base_y - 224), (sx - 4, base_y - 224)], fill=CARROT)

# ---------- spruce line ----------
def spruce(cx, height, width):
    tiers = 5
    for i in range(tiers):
        t = i / tiers
        y_top = base_y - height + t * height * 0.55
        half_w = width * (0.25 + 0.75 * t) / 2
        d.polygon([(cx, y_top), (cx - half_w, base_y - height * 0.25 + t * height * 0.12),
                   (cx + half_w, base_y - height * 0.25 + t * height * 0.12)], fill=TREE)
    d.rectangle([cx - width * 0.05, base_y - height * 0.25, cx + width * 0.05, base_y], fill=TREE)


step = 118
for x in range(-40, gx0 + 200, step):
    h = random.randint(250, 420)
    w = random.randint(150, 230)
    spruce(x, h, w)
for x in range(gx0 + 60, W + 120, step + 36):
    h = random.randint(180, 300)
    spruce(x, h, random.randint(120, 190))
# ground snow band
d.rectangle([0, base_y - 8, W, H], fill=(226, 232, 240))
d.rectangle([0, base_y - 8, W, base_y + 10], fill=(200, 208, 220))

# ---------- typography ----------
def font(sz):
    return ImageFont.load_default(size=sz)


title_f1 = font(200)
title_f2 = font(200)
sub_f = font(64)
tag_f = font(44)
epi_f = font(40)
alt_f = font(34)

d.text((120, 250), 'THE', font=title_f1, fill=CREAM)
d.text((120, 470), 'WEIGHT', font=title_f1, fill=CREAM)
d.text((120, 690), 'OF A', font=title_f2, fill=CREAM)
d.text((120, 910), 'BUNCH', font=title_f1, fill=CREAM)

# thin rule
d.line([(128, 1180), (700, 1180)], fill=CREAM, width=6)
d.text((128, 1230), 'A  N O V E L', font=sub_f, fill=DIM)

# tagline
d.text((120, 2260), 'Being a book of the wet season at Mustakorpi,', font=epi_f, fill=DIM)
d.text((120, 2320), 'and of one banana.', font=epi_f, fill=DIM)
d.text((120, 2420), 'after the Bannanivaltio chronicles', font=alt_f, fill=(160, 170, 190))

# latitude pin
d.text((W - 320, 2420), '61° N', font=font(56), fill=(160, 170, 190))

img.save('cover.jpg', quality=92)
print('cover.jpg', img.size)
