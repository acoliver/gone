"""Draw the D14 current-build metric corridor plan.

Run with a Python environment containing Pillow:
    python3 docs/art/corridors/build-corridor-maps.py

All geometry uses meters in the X/Z floor plane. Annotation leaders and door
symbols are diagrammatic; room footprints and pod bodies retain their scale.
"""

from functools import lru_cache
from math import cos, hypot, isclose, radians, sin
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
SIZE = (2400, 1350)
BG = "#f5f5f0"
INK = "#142b36"
MUTED = "#3c5360"
RULE = "#a7b8b9"
BUILT = "#08735b"
GREEN_BG = "#ddede3"
RUST = "#a04732"
FLOOR = "#e5edea"
PLAYER = "#f4cf61"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
SCALE = 36
ORIGIN = (350, 735)
PODS = [(-4.8, -2.9), (-3.4, -2.9), (-2.0, -2.9), (-0.6, -2.9),
        (-2.0, 2.9), (-3.4, 2.9), (-4.8, 2.9)]
ROD = (-0.6, -1.55)


@lru_cache(maxsize=None)
def font(size):
    return ImageFont.truetype(FONT, size)


def plan(x, z):
    return ORIGIN[0] + x * SCALE, ORIGIN[1] - z * SCALE



class Sheet:
    def __init__(self, title, subtitle):
        self.image = Image.new("RGB", SIZE, BG)
        self.d = ImageDraw.Draw(self.image)
        self.text_bounds = []
        self.text((60, 35), title, 48)
        self.text((62, 102), subtitle, 30, MUTED)
        self.line([(60, 147), (2340, 147)], RULE, 2)
        self.line([(1730, 177), (1730, 1120)], RULE, 2)

    def text(self, xy, value, size=32, color=INK, anchor="lt"):
        bounds = self.d.textbbox(xy, value, font=font(size), anchor=anchor)
        assert 0 <= bounds[0] < bounds[2] <= SIZE[0], (value, bounds)
        assert 0 <= bounds[1] < bounds[3] <= SIZE[1], (value, bounds)
        for other, other_value in self.text_bounds:
            assert (bounds[2] <= other[0] or other[2] <= bounds[0]
                    or bounds[3] <= other[1] or other[3] <= bounds[1]), (
                        "Text overlap", value, other_value)
        self.text_bounds.append((bounds, value))
        self.d.text(xy, value, font=font(size), fill=color, anchor=anchor)

    def lines(self, xy, values, size=32, color=INK, spacing=41):
        x, y = xy
        for i, value in enumerate(values):
            self.text((x, y + i * spacing), value, size, color)

    def line(self, points, color=RULE, width=3, dashed=False):
        if not dashed:
            self.d.line(points, fill=color, width=width, joint="curve")
            return
        for a, b in zip(points, points[1:]):
            length = hypot(b[0] - a[0], b[1] - a[1])
            if not length:
                continue
            for start in range(0, int(length), 19):
                end = min(start + 11, length)
                self.d.line([(a[0] + (b[0] - a[0]) * t / length,
                              a[1] + (b[1] - a[1]) * t / length)
                             for t in (start, end)], fill=color, width=width)

    def wall(self, a, b, color=BUILT):
        self.line([plan(*a), plan(*b)], color, 7)

    def rect(self, bounds, fill, outline=None, width=3):
        x0, x1, z0, z1 = bounds
        self.d.rectangle((*plan(x0, z1), *plan(x1, z0)), fill=fill,
                         outline=outline, width=width)

    def arrow(self, points, color=BUILT, dashed=False, width=4):
        self.line(points, color, width, dashed)
        a, b = points[-2:]
        length = hypot(b[0] - a[0], b[1] - a[1])
        ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        self.d.polygon([b, (b[0] - ux * 15 - uy * 7, b[1] - uy * 15 + ux * 7),
                        (b[0] - ux * 15 + uy * 7, b[1] - uy * 15 - ux * 7)],
                       fill=color)

    def leader(self, points, color=MUTED):
        self.line(points, color, 2)
        x, y = points[-1]
        self.d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=color)

    def number(self, number, at, target=None, color=BUILT):
        if target is not None:
            self.leader([at, plan(*target)], color)
        x, y = at
        self.d.ellipse((x - 21, y - 21, x + 21, y + 21), fill=color,
                       outline=BG, width=3)
        self.text((x, y), str(number), 29, "#ffffff", "mm")

    def leaf(self, x, z, color=BUILT, vertical=False, width=1.0):
        if vertical:
            bounds = (x - 0.07, x + 0.07, z - width / 2, z + width / 2)
        else:
            bounds = (x - width / 2, x + width / 2, z - 0.07, z + 0.07)
        self.rect(bounds, BG, color, 3)
        u, v = plan(x, z)
        self.d.ellipse((u - 3, v - 3, u + 3, v + 3), fill=color)


    def pod(self, point, player=False, rotated=False, color=BUILT):
        x, z = point
        dx, dz = (1.1, 0.45) if rotated else (0.45, 1.1)
        self.d.rounded_rectangle((*plan(x - dx, z + dz), *plan(x + dx, z - dz)),
                                 radius=9, fill=PLAYER if player else FLOOR,
                                 outline=color, width=3)
        # A cavity line distinguishes the body from a room or door symbol.
        self.rect((x - dx * 0.65, x + dx * 0.65,
                   z - dz * 0.65, z + dz * 0.65), None, color, 2)

    def rod(self, point, rotated=False, color=BUILT):
        angle = radians(82)
        delta = (sin(angle) * 0.5, cos(angle) * 0.5)
        if rotated:
            delta = (delta[1], -delta[0])
        x, z = point
        dx, dz = delta
        self.line([plan(x - dx, z - dz), plan(x + dx, z + dz)], color, 6)

    def switch(self, point, color=BUILT):
        x, y = plan(*point)
        self.d.rectangle((x - 7, y - 7, x + 7, y + 7), fill=BG,
                         outline=color, width=3)
        self.d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=RUST)

    def compass(self):
        self.text((1765, 188), "SHIP AXES / TOP DOWN", 32)
        center = (2055, 320)
        for end in ((1875, 320), (2235, 320), (2055, 262), (2055, 378)):
            self.arrow([center, end], INK, width=3)
        self.text((1845, 320), "Bow -X", 30, anchor="rm")
        self.text((2252, 320), "+X", 30, anchor="lm")
        self.text((2240, 358), "Stern", 30)
        self.text((2055, 227), "Starboard +Z", 30, anchor="mt")
        self.text((2055, 397), "Port -Z", 30, anchor="mt")
        self.text((1765, 461), "SAME SCALE ON BOTH MAPS", 30)
        x, y = 1790, 525
        for i in range(5):
            self.d.rectangle((x + i * SCALE, y, x + (i + 1) * SCALE, y + 13),
                             fill=INK if i % 2 == 0 else BG, outline=INK)
        self.text((x, 550), "0", 30)
        self.text((x + 5 * SCALE, 550), "5 m", 30, anchor="mt")
        self.text((1765, 600), "36 pixels = 1 meter", 30, MUTED)

    def key(self):
        self.line([(60, 1150), (2340, 1150)], INK, 2)
        steps = ["Wake in pod 6", "Pick up rod", "Pry jammed hatch",
                 "Flip hall switch", "Open power-room door", "Use working console"]
        for i, text in enumerate(steps):
            x = 91 + (i % 3) * 770
            y = 1200 + (i // 3) * 77
            self.number(i + 1, (x, y), color=BUILT)
            self.text((x + 34, y), text, 34, anchor="lm")

    def save(self, filename):
        self.image.save(HERE / filename)


def common_rooms(s):
    s.rect((6, 30, -1.5, 1.5), GREEN_BG)
    s.rect((21, 33, -9.7, -1.7), GREEN_BG)
    for z in (-1.5, 1.5):
        if z < 0:
            intervals = [(6, 26.5), (27.5, 30)]
        else:
            intervals = [(6, 30)]
        for a, b in intervals:
            s.wall((a, z), (b, z))
    s.wall((21, -1.7), (26.5, -1.7))
    s.wall((27.5, -1.7), (33, -1.7))
    for a, b in [((21, -1.7), (21, -9.7)), ((33, -1.7), (33, -9.7)),
                 ((21, -9.7), (33, -9.7)), ((26.5, -1.5), (26.5, -1.7)),
                 ((27.5, -1.5), (27.5, -1.7))]:
        s.wall(a, b)
    for x in (9, 15, 21):
        for z in (-1.47, 1.47):
            s.leaf(x, z, BUILT)
    s.leaf(27, -1.47)
    s.rect((21, 21.56, -8.125, -6.875), BUILT)
    u, v = plan(22.05, -7.5)
    s.d.ellipse((u - 4, v - 4, u + 4, v + 4), fill=BUILT)
    u, v = plan(27, -5.7)
    r = 0.8 * SCALE
    s.d.ellipse((u - r, v - r, u + r, v + r), fill=INK, outline=BUILT, width=4)
    s.text((1106, 1104), "POWER ROOM / local backup", 32, BUILT)
    s.text((1545, 913), "Generator", 30, anchor="lm")
    s.leader([(1540, 913), (1390, 913), plan(27.8, -5.7)], BUILT)


def current():
    s = Sheet("Current build: stasis bay, corridor and power room (D14)",
              "Built geometry in green. +X right; +Z up. Route numbers show the opening sequence.")
    common_rooms(s)
    s.rect((-6, 6, -4, 4), GREEN_BG)
    for a, b in [((-6, -4), (6, -4)), ((-6, 4), (6, 4)),
                 ((-6, -4), (-6, 4)), ((6, -4), (6, -0.6)),
                 ((6, 0.6), (6, 4)), ((30, -1.5), (30, 1.5))]:
        s.wall(a, b)
    s.leaf(6, 0, vertical=True, width=1.2)
    for i, point in enumerate(PODS):
        s.pod(point, player=i == 6)
    s.rod(ROD)
    s.switch((6.22, 0.85))
    trail = [(-4.8, 1.5), (-3.0, 0), ROD, (1, 0), (6, 0),
             (8, 0), (25, 0), (27, 0), (27, -3), (24, -5.7), (22.05, -7.5)]
    s.arrow([plan(*p) for p in trail], BUILT, width=3)
    s.text((134, 426), "STASIS BAY / seven pods", 36, BUILT)
    s.text((134, 475), "X=-6..6; Z=-4..4", 32, MUTED)
    s.text((134, 540), "Player pod 6", 32, BUILT)
    s.leader([(260, 577), (177, 577), plan(-4.8, 4)], BUILT)
    s.lines((735, 243), ["Jammed hatch at (6, 0)", "Switch at (6.22, +0.85)"], 32)
    s.leader([(760, 337), (600, 337), (600, 650), plan(6.22, 0.85)])
    s.lines((735, 464), ["Six closed side-door leaves", "X=9, 15, 21 on both walls"], 32)
    for x in (9, 15, 21):
        s.leader([(plan(x, 0)[0], 569), plan(x, 1.5)])
    s.text((670, 840), "CORRIDOR / 24 x 3 m", 34, BUILT)
    s.text((1480, 660), "Solid wall", 32)
    s.leader([(1480, 705), (1460, 705), plan(30, 0)])
    s.lines((135, 932), ["Rod (-0.6, -1.55)", "One-meter pry bar"], 32)
    s.leader([(465, 947), (500, 910), plan(*ROD)])
    s.lines((670, 1025), ["Working console", "(21, -7.5); act (22.05, -7.5)"], 30)
    s.leader([(1025, 1037), plan(21, -7.5)], BUILT)
    s.text((1180, 570), "Power-room door", 30)
    s.leader([(1322, 610), (1385, 650), (1385, 820), plan(27, -1.47)], BUILT)
    markers = [((-5.7, 1.4), PODS[6]), ((-0.6, -0.5), ROD),
               ((5.0, -1), (6, 0)), ((7.6, 0.95), (6.22, 0.85)),
               ((28.3, -2.8), (27, -1.47)), ((23.2, -7.5), (22.05, -7.5))]
    for n, (at, target) in enumerate(markers, 1):
        s.number(n, plan(*at), target)
    s.compass()
    s.lines((1765, 697), ["BUILT NOW", "Green: rooms and fixtures.", "Gold: your starting pod.", "Six side leaves are closed;", "no rooms exist behind them.", "X=30 is a solid endcap."], 30, spacing=43)
    s.lines((1765, 1000), ["Leaf centers: Z=+/-1.47 m.", "Wall stations: Z=+/-1.5 m.", "Door symbols enlarged."], 29, MUTED, 37)
    s.key()
    s.save("corridor-current.png")


def main():
    assert plan(1, 0)[0] - plan(0, 0)[0] == SCALE
    assert plan(0, 0)[1] - plan(0, 1)[1] == SCALE
    current()
    for filename in ("corridor-current.png",):
        path = HERE / filename
        with Image.open(path) as image:
            assert image.size == SIZE and image.format == "PNG"
            image.verify()
        print(f"{path}: {SIZE[0]}x{SIZE[1]} PNG; {path.stat().st_size:,} bytes")
    print("Coordinate note: side/power leaf centers are 0.03 m inside brief wall stations.")


if __name__ == "__main__":
    main()
