"""Generate assets/xm2wav.ico - a clean audio-waveform app icon (no external assets)."""

import os

from PIL import Image, ImageDraw

SS = 4          # supersample factor for anti-aliasing
BASE = 256
S = BASE * SS


def _lerp(a, b, t):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(len(a)))


def draw_icon() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # Vertical gradient background (deep blue -> near-black).
    top, bot = (44, 52, 82), (17, 19, 28)
    grad = Image.new("RGB", (1, S))
    for y in range(S):
        grad.putpixel((0, y), _lerp(top, bot, y / (S - 1)))
    grad = grad.resize((S, S))

    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=56 * SS, fill=255)
    bg = grad.convert("RGBA")
    bg.putalpha(mask)
    img = Image.alpha_composite(img, bg)

    # Subtle inner top highlight for depth.
    hi = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hi)
    hd.rounded_rectangle([6 * SS, 6 * SS, (BASE - 6) * SS, (BASE - 6) * SS],
                         radius=50 * SS, outline=(255, 255, 255, 28), width=2 * SS)
    img = Image.alpha_composite(img, hi)

    draw = ImageDraw.Draw(img)

    # Symmetric "audio waveform" bars, colour graded left(cyan) -> right(blue).
    heights = [0.34, 0.54, 0.80, 0.50, 0.96, 0.66, 1.0, 0.60, 0.90, 0.44, 0.76, 0.50, 0.38]
    left_c, right_c = (94, 234, 212), (59, 130, 246)  # #5eead4 -> #3b82f6
    n = len(heights)
    margin = 46 * SS
    span = S - 2 * margin
    slot = span / n
    bar_w = slot * 0.52
    cx_line = S / 2
    max_half = 74 * SS
    radius = bar_w / 2

    for i, h in enumerate(heights):
        x0 = margin + i * slot + (slot - bar_w) / 2
        x1 = x0 + bar_w
        half = h * max_half
        color = _lerp(left_c, right_c, i / (n - 1))
        draw.rounded_rectangle([x0, cx_line - half, x1, cx_line + half],
                               radius=radius, fill=color + (255,))

    # Thin centre baseline through the waveform.
    draw.rounded_rectangle([margin - 4 * SS, cx_line - 2 * SS, S - margin + 4 * SS, cx_line + 2 * SS],
                           radius=2 * SS, fill=(255, 255, 255, 70))

    return img  # full-resolution (S x S) master; callers downscale as needed


def main() -> None:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(here, "assets")
    os.makedirs(out_dir, exist_ok=True)
    master = draw_icon()  # S x S (1024)

    # Windows .ico (multi-resolution up to 256).
    ico_path = os.path.join(out_dir, "xm2wav.ico")
    master.resize((256, 256), Image.LANCZOS).save(
        ico_path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    # PNGs for Linux .desktop icons and the website.
    master.resize((512, 512), Image.LANCZOS).save(os.path.join(out_dir, "xm2wav.png"))
    master.resize((256, 256), Image.LANCZOS).save(os.path.join(out_dir, "xm2wav-256.png"))
    master.resize((128, 128), Image.LANCZOS).save(os.path.join(out_dir, "xm2wav-128.png"))

    # macOS .icns (Pillow writes the required size set from a large master).
    try:
        master.resize((1024, 1024), Image.LANCZOS).save(os.path.join(out_dir, "xm2wav.icns"))
        icns_status = "xm2wav.icns"
    except Exception as exc:  # noqa: BLE001
        icns_status = f"(.icns skipped: {exc})"

    # Runtime copies inside the package (shipped in the wheel, found at run time).
    pkg_assets = os.path.join(here, "xmwav", "assets")
    os.makedirs(pkg_assets, exist_ok=True)
    master.resize((256, 256), Image.LANCZOS).save(
        os.path.join(pkg_assets, "xm2wav.ico"),
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    master.resize((256, 256), Image.LANCZOS).save(os.path.join(pkg_assets, "xm2wav.png"))

    print(f"wrote {ico_path}, xm2wav.png, {icns_status}, and xmwav/assets/ runtime icons")


if __name__ == "__main__":
    main()
