"""Paints a night lake scene twice: as colors (RGB) and as materials (one id per area).

ascii.py turns both into a colored ASCII artwork: the material decides which
characters an area uses, the color decides how each character is tinted.
"""
import math
import random
import sys

import numpy as np
from PIL import Image, ImageDraw

COLUMNS, ROWS = 200, 76
CELL_W, CELL_H = 6, 12
W, H = COLUMNS * CELL_W, ROWS * CELL_H

SKY, STAR, MOON_ID, CRATER, MOUNTAIN_FAR, MOUNTAIN_NEAR, TREELINE, TREE, TREE_SHADE, TRUNK, LAKE, GLINT, GRASS, ROCK, DEER, ANTLER, FIREFLY = range(17)

HORIZON = int(H * 0.70)
MOON = (int(W * 0.80), int(H * 0.22), int(H * 0.105))


class Scene:
    def __init__(self):
        random.seed(11)
        self.color = Image.new("RGB", (W, H))
        self.material = Image.new("L", (W, H), SKY)
        self.draw_color = ImageDraw.Draw(self.color)
        self.draw_material = ImageDraw.Draw(self.material)

    def polygon(self, points, color, material):
        self.draw_color.polygon(points, fill=color)
        self.draw_material.polygon(points, fill=material)

    def ellipse(self, box, color, material):
        self.draw_color.ellipse(box, fill=color)
        self.draw_material.ellipse(box, fill=material)

    def rectangle(self, box, color, material):
        self.draw_color.rectangle(box, fill=color)
        self.draw_material.rectangle(box, fill=material)

    def line(self, points, color, material, width):
        self.draw_color.line(points, fill=color, width=width)
        self.draw_material.line(points, fill=material, width=width)

    # ------------------------------------------------------------------ sky
    def sky(self):
        t = np.linspace(0, 1, H)[:, None, None]
        top, bottom = np.array([12, 12, 13]), np.array([40, 40, 43])
        arr = np.broadcast_to(top * (1 - t) + bottom * t, (H, W, 3)).copy()
        yy, xx = np.mgrid[0:H, 0:W]
        mx, my, mr = MOON
        glow = np.clip(1 - np.hypot(xx - mx, yy - my) / (mr * 3.6), 0, 1) ** 2
        arr += glow[:, :, None] * np.array([62, 62, 60])
        self.color = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        self.draw_color = ImageDraw.Draw(self.color)

    def stars(self, keep_clear):
        mx, my, mr = MOON
        for _ in range(150):
            x, y = random.uniform(0, W), random.uniform(0, HORIZON * 0.8)
            if math.hypot(x - mx, y - my) < mr * 1.5 or keep_clear(x, y):
                continue
            b = random.choice([150, 190, 230, 255])
            self.rectangle([x, y, x + CELL_W - 1, y + CELL_H - 1], (b, b, int(b * random.uniform(0.8, 1))), STAR)

    def moon(self):
        """Full moon with limb darkening, dark maria and a few rimmed craters."""
        mx, my, mr = MOON
        rx, ry = mr * 1.12, mr * 1.12
        yy, xx = np.mgrid[0:H, 0:W]
        nx, ny = (xx - mx) / rx, (yy - my) / ry
        r2 = nx ** 2 + ny ** 2
        disc = r2 <= 1
        shade = 0.72 + 0.28 * np.sqrt(np.clip(1 - r2, 0, 1))
        maria = np.zeros_like(nx)
        for cx, cy, sx, sy, depth in [(-0.35, -0.25, 0.30, 0.22, 0.20), (0.05, -0.35, 0.22, 0.16, 0.16), (0.25, 0.15, 0.26, 0.30, 0.18), (-0.15, 0.35, 0.20, 0.14, 0.12), (-0.55, 0.15, 0.12, 0.20, 0.12)]:
            maria += depth * np.exp(-(((nx - cx) / sx) ** 2 + ((ny - cy) / sy) ** 2))
        value = shade * (1 - np.clip(maria * 1.9, 0, 0.5))
        for cx, cy, r in [(0.45, -0.45, 0.10), (-0.10, 0.62, 0.09), (0.58, 0.32, 0.07), (-0.62, -0.38, 0.06), (0.15, 0.55, 0.05)]:
            d = np.hypot(nx - cx, ny - cy) / r
            value = np.where(d < 0.8, value * 0.78, value)
            value = np.where((d >= 0.8) & (d < 1.15), np.minimum(1, value * 1.12), value)
        arr = np.asarray(self.color).astype(float)
        mat = np.asarray(self.material).copy()
        base = np.array([244, 236, 206])
        arr[disc] = value[disc][:, None] * base
        mat[disc] = MOON_ID
        self.color = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        self.material = Image.fromarray(mat)
        self.draw_color = ImageDraw.Draw(self.color)
        self.draw_material = ImageDraw.Draw(self.material)

    # ------------------------------------------------------------------ land
    def mountains(self):
        def ridge(base, amp, freqs, phase):
            pts = []
            for x in range(0, W + 8, 8):
                y = base + sum(amp * a * math.sin(x / W * f * math.tau + phase * f) for f, a in freqs)
                pts.append((x, y))
            return pts
        far = ridge(HORIZON - H * 0.17, H * 0.06, [(1.3, 1.0), (3.1, 0.4), (7.0, 0.15)], 0.4)
        self.polygon(far + [(W, HORIZON), (0, HORIZON)], (70, 78, 128), MOUNTAIN_FAR)
        near = ridge(HORIZON - H * 0.08, H * 0.045, [(1.9, 1.0), (4.3, 0.5), (9.0, 0.2)], 2.1)
        self.polygon(near + [(W, HORIZON), (0, HORIZON)], (44, 52, 92), MOUNTAIN_NEAR)

    def pine(self, x, ground, height, light, dark, material=TREE):
        width = height * 0.46
        tiers = 4
        for i in range(tiers):
            top = ground - height + i * height * 0.2
            bottom = top + height * 0.36
            half = width * (0.4 + 0.6 * (i + 1) / tiers) / 2
            self.polygon([(x, top), (x - half, bottom), (x + half, bottom)], light, material)
            if material == TREE:
                self.polygon([(x, top), (x + half, bottom), (x + half * 0.2, bottom)], dark, TREE_SHADE)
        if material == TREE:
            self.rectangle([x - CELL_W * 0.5, ground - height * 0.14, x + CELL_W * 0.5, ground], (110, 78, 60), TRUNK)

    def treeline(self):
        x = -10
        while x < W + 10:
            h = random.uniform(H * 0.06, H * 0.10)
            self.pine(x, HORIZON + 2, h, (40, 96, 90), (30, 74, 72), TREELINE)
            x += random.uniform(CELL_W * 1.6, CELL_W * 3)

    def lake(self):
        arr = np.asarray(self.color).copy()
        mat = np.asarray(self.material).copy()
        t = np.linspace(0, 1, H - HORIZON)[:, None, None]
        arr[HORIZON:] = (np.array([46, 58, 110]) * (1 - t) + np.array([16, 22, 54]) * t).astype(np.uint8)
        mat[HORIZON:] = LAKE
        mx = MOON[0]
        for row in range(HORIZON + CELL_H, H, CELL_H):
            depth = (row - HORIZON) / (H - HORIZON)
            half = CELL_W * (2.5 + depth * 7 + random.uniform(-1.5, 1.5))
            off = random.uniform(-CELL_W, CELL_W)
            x0, x1 = int(mx - half + off), int(mx + half + off)
            arr[row:row + CELL_H, max(0, x0):x1] = (np.array([240, 230, 196]) * (1 - depth * 0.45)).astype(np.uint8)
            mat[row:row + CELL_H, max(0, x0):x1] = GLINT
        self.color = Image.fromarray(arr)
        self.material = Image.fromarray(mat)
        self.draw_color = ImageDraw.Draw(self.color)
        self.draw_material = ImageDraw.Draw(self.material)

    def shore(self):
        top = HORIZON + H * 0.07
        pts = [(0, top)] + [(x, top + 6 * math.sin(x * 0.02)) for x in range(0, int(W * 0.40), 8)]
        pts += [(W * 0.47, H * 0.90), (W * 0.44, H), (0, H)]
        self.polygon(pts, (52, 104, 66), GRASS)
        self.polygon([(W * 0.84, H), (W * 0.90, HORIZON + H * 0.15), (W, HORIZON + H * 0.10), (W, H)], (58, 66, 84), ROCK)
        for x, y, r in [(W * 0.88, H * 0.95, 3.2), (W * 0.95, H * 0.90, 2.4)]:
            self.ellipse([x - r * CELL_W, y - r * CELL_H * 0.45, x + r * CELL_W, y + r * CELL_H * 0.45], (96, 104, 122), ROCK)

    def forest(self):
        ground = HORIZON + H * 0.09
        for fx, fh in [(0.03, 0.46), (0.10, 0.38), (0.17, 0.30), (0.93, 0.40), (0.985, 0.48)]:
            self.pine(W * fx, ground, H * fh, (46, 128, 84), (30, 90, 64))

    def deer(self):
        """A standing deer seen from the side, head up, on the shore."""
        x, ground, s = W * 0.27, HORIZON + H * 0.18, 2.5
        body, light = (176, 120, 78), (222, 170, 118)
        self.ellipse([x - 28 * s, ground - 52 * s, x + 26 * s, ground - 24 * s], body, DEER)
        self.ellipse([x - 24 * s, ground - 44 * s, x + 18 * s, ground - 38 * s], light, DEER)
        for lx, lean in ((-20, -2), (-13, 2), (12, -1), (19, 3)):
            self.line([(x + lx * s, ground - 32 * s), (x + (lx + lean) * s, ground)], body, DEER, int(5 * s))
        self.polygon([(x + 8 * s, ground - 48 * s), (x + 24 * s, ground - 40 * s), (x + 33 * s, ground - 66 * s), (x + 21 * s, ground - 72 * s)], body, DEER)
        self.polygon([(x + 22 * s, ground - 72 * s), (x + 30 * s, ground - 74 * s), (x + 40 * s, ground - 64 * s), (x + 36 * s, ground - 60 * s), (x + 26 * s, ground - 62 * s)], body, DEER)
        self.polygon([(x + 22 * s, ground - 72 * s), (x + 16 * s, ground - 80 * s), (x + 24 * s, ground - 74 * s)], light, DEER)
        antler = (226, 204, 166)
        base = (x + 27 * s, ground - 74 * s)
        for tip in [(x + 12 * s, ground - 104 * s), (x + 40 * s, ground - 106 * s)]:
            self.line([base, tip], antler, ANTLER, int(3 * s))
        for a, b in [((x + 21 * s, ground - 86 * s), (x + 8 * s, ground - 90 * s)), ((x + 33 * s, ground - 88 * s), (x + 46 * s, ground - 92 * s)), ((x + 17 * s, ground - 94 * s), (x + 22 * s, ground - 108 * s)), ((x + 37 * s, ground - 96 * s), (x + 32 * s, ground - 110 * s))]:
            self.line([a, b], antler, ANTLER, int(2.6 * s))
        self.ellipse([x - 30 * s, ground - 44 * s, x - 24 * s, ground - 38 * s], (230, 220, 200), DEER)

    def fireflies(self):
        for _ in range(12):
            x = random.uniform(W * 0.02, W * 0.42)
            y = random.uniform(HORIZON - H * 0.12, H * 0.96)
            self.rectangle([x, y, x + CELL_W - 1, y + CELL_H - 1], (250, 226, 120), FIREFLY)


def text_area(x, y):
    """Top left part of the sky stays free for the text."""
    return x < W * 0.62 and y < H * 0.50


def paint():
    scene = Scene()
    scene.sky()
    scene.stars(text_area)
    scene.moon()
    scene.mountains()
    scene.lake()
    scene.treeline()
    scene.shore()
    scene.forest()
    scene.deer()
    scene.fireflies()
    return scene


if __name__ == "__main__":
    scene = paint()
    scene.color.save(sys.argv[1])
