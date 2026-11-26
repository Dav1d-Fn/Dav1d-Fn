"""Project cards for the profile README: one small SVG per project in the artwork's night style.

Fixed width cards sit side by side on desktop and wrap to one column on phones.
"""
import base64
import html
import sys
import textwrap

WIDTH, HEIGHT = 380, 318
BANNER_H = 190
FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif'
MONO = 'ui-monospace, "SFMono-Regular", "DejaVu Sans Mono", Menlo, Consolas, monospace'

PROJECTS = [
    ("albedo", "Albedo", ["Tauri", "Rust", "React"],
     "Controller-first launcher for Moonlight on the Steam Deck, with device profiles, a Sunshine companion and Wake-on-LAN."),
    ("fliq", "Fliq", ["Tauri", "React"],
     "A floating flip clock for your desktop, with weather, calendar and a drag & drop layout editor."),
    ("gif-color-changer", "GIF Color Changer", ["Rust", "React"],
     "Recolor animated GIFs frame by frame or make colors transparent. Batch processing, fully offline."),
    ("better-volume-mixer", "Better Volume Mixer", ["Python"],
     "Per-app volume for the Stream Deck on Linux, with live levels and custom icons. StreamController plugin."),
]


def banner_data(path):
    import io
    from PIL import Image
    image = Image.open(path).convert("RGBA")
    flat = Image.new("RGB", image.size, (14, 14, 15))
    flat.paste(image, mask=image.split()[3])
    flat = flat.resize((WIDTH * 2, BANNER_H * 2), Image.LANCZOS)
    buffer = io.BytesIO()
    flat.save(buffer, "JPEG", quality=84)
    return base64.b64encode(buffer.getvalue()).decode()


def card(icon_path, name, tech, description, banner_path):
    icon = base64.b64encode(open(icon_path, "rb").read()).decode()
    banner = banner_data(banner_path)
    top = BANNER_H
    lines = textwrap.wrap(description, 52)[:3]
    text_lines = "".join(
        f'<text x="20" y="{top + 84 + index * 18}" class="d">{html.escape(line)}</text>' for index, line in enumerate(lines)
    )
    chips, x = [], 76
    for label in tech:
        width = len(label) * 7.2 + 14
        chips.append(f'<rect x="{x:.1f}" y="{top + 40}" width="{width:.1f}" height="18" rx="9" class="chip"/>'
                     f'<text x="{x + width / 2:.1f}" y="{top + 53}" class="c" text-anchor="middle">{html.escape(label)}</text>')
        x += width + 6
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
<style>
.t {{ font: 600 17px {FONT}; fill: #f2f2f3; }}
.d {{ font: 400 12.5px {FONT}; fill: #b2b2b6; }}
.c {{ font: 500 10.5px {MONO}; fill: #cfcfd3; }}
.chip {{ fill: #ffffff; fill-opacity: .07; }}
</style>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#19191b"/><stop offset="1" stop-color="#0e0e0f"/></linearGradient>
<clipPath id="ic"><rect x="20" y="{top + 18}" width="44" height="44" rx="11"/></clipPath>
<clipPath id="card"><rect width="{WIDTH}" height="{HEIGHT}" rx="14"/></clipPath>
</defs>
<rect width="{WIDTH}" height="{HEIGHT}" rx="14" fill="url(#bg)"/>
<image href="data:image/jpeg;base64,{banner}" x="0" y="0" width="{WIDTH}" height="{BANNER_H}" preserveAspectRatio="xMidYMid slice" clip-path="url(#card)"/>
<image href="data:image/png;base64,{icon}" x="20" y="{top + 18}" width="44" height="44" clip-path="url(#ic)"/>
<text x="76" y="{top + 33}" class="t">{html.escape(name)}</text>
{"".join(chips)}
{text_lines}
</svg>'''


def main(icon_folder, out_folder):
    banners = icon_folder.rsplit("/", 1)[0]
    for key, name, tech, description in PROJECTS:
        svg = card(f"{icon_folder}/{key}.png", name, tech, description, f"{banners}/{key}.png")
        open(f"{out_folder}/{key}.svg", "w").write(svg)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
