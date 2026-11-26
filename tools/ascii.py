"""Turns the painted scene into a colored ASCII artwork (SVG) with text in the sky.

The material of a cell picks its character set (water ~, grass ", trees /\\^ ...),
edges between materials get outline characters, and the painted color tints it.
"""
import colorsys
import html
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import paint as p

FONT_SIZE = 10.0
ADVANCE = 6.0
LINE = 11.0
PAD_X, PAD_Y = 26, 22
BACKGROUND = "#0c0c0d"

TITLE = "Dav1d-Fn"
TITLE_AT = (8, 4)
INFO_AT = (9, 16.8)
INFO_SIZE = 16.5
INFO_LINE = 27.0
INFO = [
    ("hobby developer from germany · linux, games and self-hosting", "#d6d6d8"),
    ("react · typescript · tauri · rust · fedora kde", "#909094"),
]
EXTRA_ROWS = 2
PROJECTS = []
PROJECTS_ROW = 21
PROJECT_W, PROJECT_GAP = 224, 16

FILL = {
    p.STAR: "*+.'",
    p.MOON_ID: "@%#@&%",
    p.CRATER: "oO0o",
    p.MOUNTAIN_FAR: ".:.:'.",
    p.MOUNTAIN_NEAR: ";:;=:;",
    p.TREELINE: "^A^^Mx",
    p.TREE: "*#x*A#%",
    p.TREE_SHADE: "#%&#",
    p.TRUNK: "|H|",
    p.LAKE: "~-~ ~~- ",
    p.GLINT: "=~=-=",
    p.GRASS: "\"',v\"w;,",
    p.ROCK: "@Oo0@",
    p.DEER: "#&#M",
    p.ANTLER: "Y/\\",
    p.FIREFLY: "*",
}
OUTLINED = {p.MOUNTAIN_FAR, p.MOUNTAIN_NEAR, p.TREE, p.TREE_SHADE, p.TREELINE, p.ROCK, p.DEER}
TWINKLING = {p.STAR, p.FIREFLY}


def cells(scene):
    color = np.asarray(scene.color).astype(float).reshape(p.ROWS, p.CELL_H, p.COLUMNS, p.CELL_W, 3).mean(axis=(1, 3))
    material_blocks = np.asarray(scene.material).reshape(p.ROWS, p.CELL_H, p.COLUMNS, p.CELL_W)
    material = np.zeros((p.ROWS, p.COLUMNS), dtype=int)
    for r in range(p.ROWS):
        for c in range(p.COLUMNS):
            values, counts = np.unique(material_blocks[r, :, c, :], return_counts=True)
            material[r, c] = values[counts.argmax()]
    return color, material


def title_cells():
    """The title as half-block characters (two pixel rows per character row)."""
    font = ImageFont.truetype("/usr/share/fonts/rsms-inter-fonts/Inter-Black.ttf", 200)
    left, top, right, bottom = font.getbbox(TITLE)
    image = Image.new("L", (right - left, bottom - top), 0)
    ImageDraw.Draw(image).text((-left, -top), TITLE, font=font, fill=255)
    pixel_rows = 18
    columns = int(round(image.width / image.height * pixel_rows * p.CELL_H / p.CELL_W / 2))
    bitmap = np.asarray(image.resize((columns, pixel_rows), Image.LANCZOS)) > 110
    result = {}
    for r in range(pixel_rows // 2):
        for c in range(columns):
            upper, lower = bitmap[2 * r, c], bitmap[2 * r + 1, c]
            char = "█" if upper and lower else "▀" if upper else "▄" if lower else None
            if char:
                result[(TITLE_AT[1] + r, TITLE_AT[0] + c)] = char
    return result, columns


def tint(color, material):
    r, g, b = (np.array(color) / 255).tolist()
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if material == p.MOON_ID:
        v = 0.25 + 0.85 * v ** 1.6
        s = s * 0.8
    elif material == p.SKY:
        v = 0.22 + 0.5 * v
    else:
        v = 0.38 + 0.62 * v ** 0.6
        s = min(1.0, s * 1.2)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#%02x%02x%02x" % tuple(int(round(x * 255 / 12) * 12) if x < 1 else 255 for x in (r, g, b))


def pick(material, row, column, grid, color):
    noise = (row * 73856093 ^ column * 19349663) % 997
    if material == p.SKY:
        # faint texture that grows near the moon
        mx, my = p.MOON[0] / p.CELL_W, p.MOON[1] / p.CELL_H + EXTRA_ROWS
        distance = ((column - mx) ** 2 + ((row - my) * 2) ** 2) ** 0.5
        chance = 0.05 + max(0.0, 0.35 - distance / 120)
        return ("." if noise % 3 else "`") if noise / 997 < chance else " "
    if material in OUTLINED:
        up = grid[row - 1, column] if row > 0 else p.SKY
        left = grid[row, column - 1] if column > 0 else material
        right = grid[row, column + 1] if column < p.COLUMNS - 1 else material
        if material == p.DEER:
            behind = lambda m: m not in (p.DEER, p.ANTLER)
        else:
            behind = lambda m: m in (p.SKY, p.STAR, p.MOUNTAIN_FAR, p.MOUNTAIN_NEAR, p.LAKE, p.GLINT) and m != material
        if behind(up):
            if behind(left) and not behind(right):
                return "/"
            if behind(right) and not behind(left):
                return "\\"
            if material == p.DEER:
                return "_"
            return "^" if material in (p.TREE, p.TREE_SHADE, p.TREELINE) else "_"
        if behind(left):
            return "/"
        if behind(right):
            return "\\"
    chars = FILL.get(material, ".")
    if material == p.MOON_ID:
        luminance = color.mean() / 255
        ramp = "+*o#%&@"
        return ramp[min(len(ramp) - 1, max(0, int((luminance - 0.45) / 0.5 * len(ramp))))]
    return chars[noise % len(chars)]


def build(out_path):
    scene = p.paint()
    color, grid = cells(scene)
    top_color = color[0].mean(axis=0) * 0.92
    extra_color = np.broadcast_to(top_color, (EXTRA_ROWS, p.COLUMNS, 3)).copy()
    extra_grid = np.full((EXTRA_ROWS, p.COLUMNS), p.SKY, dtype=int)
    for index in range(26):
        r, c = (index * 7919) % EXTRA_ROWS, (index * 104729) % p.COLUMNS
        if c > 110:
            extra_grid[r, c] = p.STAR
            extra_color[r, c] = (200, 200, 190)
    color = np.vstack([extra_color, color])
    grid = np.vstack([extra_grid, grid])
    total_rows = p.ROWS + EXTRA_ROWS
    title, title_width = title_cells()
    info_rows = {}
    for index, (line, _) in enumerate(INFO):
        info_rows[index] = line
    rows_svg = []
    twinkles = []
    for row in range(total_rows):
        spans, current, buffer = [], None, []
        for column in range(p.COLUMNS):
            material = grid[row, column]
            if (row, column) in title:
                char = " "
                fill = current
            elif material in TWINKLING:
                noise = (row * 92821 + column * 68917) % 1000
                char = "*" if material == p.FIREFLY else "+*.'"[noise % 4]
                twinkles.append((row, column, char, tint(color[row, column], material), noise))
                char, fill = " ", current
            else:
                char = pick(material, row, column, grid, color[row, column])
                fill = tint(color[row, column], material)
            if char == " ":
                fill = current
            if fill != current and buffer:
                spans.append((current, "".join(buffer)))
                buffer = []
            current = fill
            buffer.append(char)
        spans.append((current, "".join(buffer)))
        y = PAD_Y + (row + 1) * LINE
        tspans = "".join(f'<tspan fill="{f or BACKGROUND}">{html.escape(t)}</tspan>' for f, t in spans)
        rows_svg.append(f'<text x="{PAD_X}" y="{y:.1f}" textLength="{p.COLUMNS * ADVANCE}" lengthAdjust="spacingAndGlyphs">{tspans}</text>')
    twinkle_svg = []
    for row, column, char, fill, noise in twinkles:
        y = PAD_Y + (row + 1) * LINE
        x = PAD_X + column * ADVANCE
        twinkle_svg.append(f'<text class="tw" x="{x:.1f}" y="{y:.1f}" fill="{fill}" style="animation-duration:{2.5 + noise % 30 / 10:.1f}s;animation-delay:-{noise % 40 / 10:.1f}s">{html.escape(char)}</text>')
    title_svg = []
    for r in range(TITLE_AT[1], TITLE_AT[1] + 9):
        line = "".join(title.get((r, c), " ") for c in range(TITLE_AT[0], TITLE_AT[0] + title_width))
        if line.strip():
            y = PAD_Y + (r + 1) * LINE
            title_svg.append(f'<text class="title" x="{PAD_X + TITLE_AT[0] * ADVANCE}" y="{y:.1f}" textLength="{title_width * ADVANCE}" lengthAdjust="spacing">{html.escape(line)}</text>')
    info_svg = []
    for index, (line, fill) in enumerate(INFO):
        if line:
            y = PAD_Y + INFO_AT[1] * LINE + index * INFO_LINE
            info_svg.append(f'<text class="info" x="{PAD_X + INFO_AT[0] * ADVANCE}" y="{y:.1f}" fill="{fill}">{html.escape(line)}</text>')
    import base64, io
    project_svg = []
    project_h = PROJECT_W / 2
    for index, (path, name) in enumerate(PROJECTS):
        image = Image.open(path).convert("RGB").resize((int(PROJECT_W * 2), int(project_h * 2)), Image.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=86)
        data = base64.b64encode(buffer.getvalue()).decode()
        x = PAD_X + INFO_AT[0] * ADVANCE + index * (PROJECT_W + PROJECT_GAP)
        y = PAD_Y + PROJECTS_ROW * LINE
        project_svg.append(f'<clipPath id="clip{index}"><rect x="{x:.1f}" y="{y:.1f}" width="{PROJECT_W}" height="{project_h:.1f}" rx="12"/></clipPath>')
        project_svg.append(f'<image href="data:image/jpeg;base64,{data}" x="{x:.1f}" y="{y:.1f}" width="{PROJECT_W}" height="{project_h:.1f}" clip-path="url(#clip{index})"><title>{html.escape(name)}</title></image>')
        project_svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{PROJECT_W}" height="{project_h:.1f}" rx="12" fill="none" stroke="#ffffff" stroke-opacity=".10"/>')
    width = PAD_X * 2 + p.COLUMNS * ADVANCE
    height = PAD_Y * 2 + total_rows * LINE + 4
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">
<style>
text {{ font-family: ui-monospace, "SFMono-Regular", "DejaVu Sans Mono", Menlo, Consolas, monospace; font-size: {FONT_SIZE}px; white-space: pre; }}
.info {{ font-size: {INFO_SIZE}px; }}
.tw {{ animation: twinkle 3s ease-in-out infinite; }}
@keyframes twinkle {{ 0%, 100% {{ opacity: 1 }} 50% {{ opacity: .2 }} }}
.title {{ font-size: {LINE * 1.02:.2f}px; fill: url(#title); }}
</style>
<defs><linearGradient id="title" x1="0" x2="1"><stop offset="0" stop-color="#f3ead0"/><stop offset="1" stop-color="#9fb0ee"/></linearGradient></defs>
<rect width="100%" height="100%" rx="16" fill="{BACKGROUND}"/>
{chr(10).join(rows_svg)}
{chr(10).join(twinkle_svg)}
{chr(10).join(title_svg)}
{chr(10).join(info_svg)}
{chr(10).join(project_svg)}
</svg>'''
    open(out_path, "w").write(svg)


if __name__ == "__main__":
    build(sys.argv[1])
