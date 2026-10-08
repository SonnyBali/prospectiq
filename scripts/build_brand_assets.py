"""Rebuild local ProspectIQ social and icon assets without network requests.

Requires Pillow in a build/tooling environment (not in the application's runtime):
    python -m pip install Pillow
    python scripts/build_brand_assets.py

Use --font-regular and --font-bold to pin font files for identical typography
across machines. The default prefers Segoe UI on Windows and DejaVu on Linux.
"""
from argparse import ArgumentParser
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
SCALE = 2
BG = "#080f1b"
SURFACE = "#111f32"
BORDER = "#28435a"
TEXT = "#edf4fa"
MUTED = "#9aafc5"
CYAN = "#69d9f4"
MINT = "#95f2ca"


def font_path(explicit, bold=False):
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise ValueError("The specified font file does not exist")
        return path
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else
             "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    return next((path for path in candidates if path.is_file()), None)


def mark(draw, x, y, size):
    """The existing dashboard's three slanted bars, drawn as native geometry."""
    heights = [0.49, 0.79, 0.63]
    colors = [CYAN, MINT, CYAN]
    for index, (height, color) in enumerate(zip(heights, colors)):
        left = x + size * (0.18 + index * 0.225)
        top = y + size * (0.5 - height / 2)
        width = size * 0.13
        slant = size * 0.12
        bottom = top + size * height
        draw.polygon([(left + slant, top), (left + width + slant, top),
                      (left + width, bottom), (left, bottom)], fill=color)


def build_icons():
    for size, name in [(32, "favicon-32.png"), (180, "apple-touch-icon.png")]:
        image = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((0, 0, size * 4 - 1, size * 4 - 1), radius=size * 0.88, fill=BG)
        mark(draw, 0, 0, size * 4)
        image.resize((size, size), Image.Resampling.LANCZOS).save(STATIC / name, optimize=True)
    (STATIC / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="ProspectIQ">\n'
        '<rect width="64" height="64" rx="14" fill="#080f1b"/>\n'
        '<path d="M19 16 27 16 21 48 13 48Z" fill="#69d9f4"/>\n'
        '<path d="M33 7 41 7 32 57 24 57Z" fill="#95f2ca"/>\n'
        '<path d="M47 12 55 12 48 52 40 52Z" fill="#69d9f4"/>\n'
        '</svg>\n', encoding="utf-8",
    )


def build_social(regular_path, bold_path):
    if not regular_path or not bold_path:
        raise RuntimeError("Install a supported font or provide --font-regular and --font-bold")
    image = Image.new("RGB", (1200 * SCALE, 630 * SCALE), BG)
    draw = ImageDraw.Draw(image)

    def font(size, bold=False):
        return ImageFont.truetype(str(bold_path if bold else regular_path), round(size * SCALE))

    def box(bounds, radius=0, fill=None, outline=None, width=1):
        points = tuple(round(value * SCALE) for value in bounds)
        draw.rounded_rectangle(points, radius=round(radius * SCALE), fill=fill,
                               outline=outline, width=round(width * SCALE))

    def text(position, value, size, color=TEXT, bold=False):
        draw.text(tuple(round(value * SCALE) for value in position), value, fill=color, font=font(size, bold))

    def line(points, color=BORDER, width=1):
        draw.line([(round(x * SCALE), round(y * SCALE)) for x, y in points], fill=color, width=round(width * SCALE))

    # Subtle grid and structural lines echo the application, without inventing metrics.
    for x in range(700, 1200, 36):
        line([(x, 0), (x, 630)], color="#101b29")
    for y in range(0, 630, 36):
        line([(686, y), (1200, y)], color="#101b29")
    line([(54, 122), (1146, 122)], color="#233349")
    mark(draw, 51 * SCALE, 34 * SCALE, 62 * SCALE)
    text((123, 38), "Prospect", 38, bold=True)
    width = draw.textlength("Prospect", font=font(38, True)) / SCALE
    text((123 + width, 38), "IQ", 38, CYAN, bold=True)
    text((126, 86), "BY FIREWIREADS", 10, MUTED, bold=True)
    box((923, 51, 1146, 85), 6, "#153430", "#31564e")
    text((941, 58), "PUBLIC SYNTHETIC DEMO", 11, MINT, bold=True)

    text((57, 153), "PYTHON AI ENGINEERING", 12, CYAN, bold=True)
    text((54, 194), "AI Opportunity", 60, TEXT, bold=True)
    text((54, 264), "Intelligence", 60, MINT, bold=True)
    text((58, 365), "Explore evidence. Model scenarios.", 21, MUTED)
    text((58, 398), "Ask a company-specific AI advisor.", 21, MUTED)

    # A diagram of available application surfaces, not a simulated performance dashboard.
    box((756, 157, 1146, 464), 20, SURFACE, BORDER)
    text((779, 179), "EVIDENCE → INSIGHT → ACTION", 12, CYAN, bold=True)
    blocks = [
        (224, "01", "Saved research", "Source citations and unknowns", CYAN),
        (301, "02", "Python simulator", "Your assumptions. Exact results.", MINT),
        (378, "03", "Company AI advisor", "Context, history, and usage traces", "#b7abff"),
    ]
    for y, number, title, description, accent in blocks:
        box((776, y, 1126, y + 66), 10, "#0c1829", "#293a50")
        box((789, y + 16, 820, y + 48), 7, "#162b3e")
        text((797, y + 21), number, 12, accent, bold=True)
        text((836, y + 11), title, 17, TEXT, bold=True)
        text((836, y + 37), description, 11, MUTED)

    line([(54, 500), (1146, 500)], color="#233349")
    chips = [(54, 128, "FastAPI"), (196, 209, "OpenAI Responses"), (419, 212, "Engineering View"),
             (645, 238, "Recorded voice demos")]
    for x, width, label in chips:
        box((x, 522, x + width, 556), 6, "#122337", "#2b4058")
        text((x + 13, 528), label, 13, MUTED)
    text((57, 586), "prospect.firewireads.com", 13, CYAN)
    text((840, 586), "Fictional business data · Real application", 12, MUTED)
    image.resize((1200, 630), Image.Resampling.LANCZOS).save(STATIC / "prospectiq-social.png", optimize=True)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--font-regular")
    parser.add_argument("--font-bold")
    args = parser.parse_args()
    STATIC.mkdir(parents=True, exist_ok=True)
    build_icons()
    build_social(font_path(args.font_regular), font_path(args.font_bold, bold=True))
    print("Built favicon.svg, favicon-32.png, apple-touch-icon.png, and prospectiq-social.png")


if __name__ == "__main__":
    main()
