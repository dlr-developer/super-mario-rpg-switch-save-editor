"""Draws the app icon (a red mushroom with a save badge) and writes assets/icon.png and
assets/icon.ico. Run with:  python tools/make_icon.py   (needs Pillow)."""
import os

from PIL import Image, ImageDraw, ImageFilter

S = 1024                      # draw big, then shrink for crisp small sizes
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

RED, RED_DARK, RED_LIGHT = (229, 57, 53), (127, 24, 24), (255, 110, 100)
STEM, STEM_DARK = (250, 236, 206), (140, 108, 64)
BLUE, BLUE_DARK, METAL, METAL_DARK = (30, 136, 229), (13, 60, 140), (205, 212, 220), (90, 100, 112)
WHITE, OUTLINE = (255, 255, 255), (40, 22, 22)


def mushroom(img):
    d = ImageDraw.Draw(img)
    # soft shadow
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((210, 880, 760, 960), fill=(0, 0, 0, 90))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
    # stem (outline, then fill)
    d.rounded_rectangle((300, 520, 724, 920), radius=150, fill=OUTLINE)
    d.rounded_rectangle((328, 548, 696, 892), radius=126, fill=STEM)
    d.rounded_rectangle((560, 600, 660, 860), radius=50, fill=(236, 214, 172))      # stem shading
    # cap: dome + rounded lip, outlined
    for grow, colour in ((30, OUTLINE), (0, RED)):
        d.pieslice((96 - grow, 110 - grow, 928 + grow, 1010 + grow), 180, 360, fill=colour)
        d.ellipse((96 - grow, 470 - grow, 928 + grow, 680 + grow), fill=colour)
    d.ellipse((150, 520, 874, 650), fill=RED_DARK)                                     # underside rim
    d.ellipse((150, 500, 874, 620), fill=RED)
    # gloss
    gloss = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(gloss).ellipse((190, 170, 520, 390), fill=(255, 255, 255, 70))
    img.alpha_composite(gloss.filter(ImageFilter.GaussianBlur(10)))
    # spots
    for cx, cy, r in ((512, 285, 118), (250, 470, 92), (775, 470, 92), (372, 160, 46), (660, 165, 46)):
        d.ellipse((cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14), fill=RED_DARK)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=WHITE)


def save_badge(img):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 556, 556, 990, 990
    d.rounded_rectangle((x0 - 26, y0 - 26, x1 + 26, y1 + 26), radius=92, fill=WHITE)    # ring that separates it
    d.rounded_rectangle((x0, y0, x1, y1), radius=70, fill=BLUE_DARK)
    d.rounded_rectangle((x0 + 18, y0 + 18, x1 - 18, y1 - 18), radius=56, fill=BLUE)
    d.polygon([(x1 - 18, y0 + 18), (x1 - 18, y0 + 110), (x1 - 110, y0 + 18)], fill=BLUE_DARK)  # clipped corner
    d.rounded_rectangle((x0 + 120, y0 + 18, x1 - 130, y0 + 168), radius=16, fill=METAL)          # shutter
    d.rounded_rectangle((x1 - 230, y0 + 48, x1 - 168, y0 + 140), radius=10, fill=METAL_DARK)
    d.rounded_rectangle((x0 + 74, y0 + 236, x1 - 74, y1 - 40), radius=26, fill=WHITE)            # label
    for k in range(3):
        y = y0 + 286 + k * 46
        d.rounded_rectangle((x0 + 118, y, x1 - 118, y + 18), radius=9, fill=(150, 190, 235))


def main():
    os.makedirs(OUT, exist_ok=True)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mushroom(img)
    save_badge(img)
    img.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "icon.png"))
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [img.resize((n, n), Image.LANCZOS) for n in sizes]
    frames[-1].save(os.path.join(OUT, "icon.ico"), sizes=[(n, n) for n in sizes], append_images=frames[:-1])
    preview = Image.new("RGBA", (sum(sizes) + 20 * len(sizes) + 532, 532), (240, 240, 240, 255))
    x = 10
    for n, f in zip(sizes, frames):
        preview.alpha_composite(f, (x, 532 - n - 10)); x += n + 20
    preview.alpha_composite(img.resize((512, 512), Image.LANCZOS), (x, 10))
    preview.save(os.path.join(OUT, "icon-preview.png"))
    print("wrote", os.listdir(OUT))


if __name__ == "__main__":
    main()
