"""Draw the connector proposal without changing the game or the earlier maps.

Run: python3 docs/art/corridors/build-connector-maps.py
Geometry is metric unless explicitly marked as an unfolded or symbolic view.
Text bounds are checked for overlap; no image inspection is required to build.
"""

import json
from functools import lru_cache
from math import hypot, isclose
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
ATLAS = HERE.parent / "ship" / "3d" / "ship_atlas.json"
SIZE = (2400, 1350)
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
BG = "#f5f5f0"
INK = "#142b36"
MUTED = "#3c5360"
RULE = "#a7b8b9"
FAINT = "#cbd6d8"
BUILT = "#08735b"
GREEN_BG = "#ddede3"
MOVED = "#996017"
MOVED_BG = "#f4ead7"
PROPOSED = "#245981"
BLUE_BG = "#e2edf4"
RUST = "#a04732"
PLAYER = "#f4cf61"


@lru_cache(maxsize=None)
def font(size):
    assert size >= 26
    return ImageFont.truetype(FONT, size)


class Sheet:
    def __init__(self, title, subtitle):
        self.image = Image.new("RGB", SIZE, BG)
        self.d = ImageDraw.Draw(self.image)
        self.labels = []
        self.text((60, 32), title, 46)
        self.text((62, 100), subtitle, 29, MUTED)
        self.line([(60, 146), (2340, 146)])

    def text(self, at, text, size=28, color=INK, anchor="lt"):
        bounds = self.d.textbbox(at, text, font=font(size), anchor=anchor)
        assert 10 <= bounds[0] < bounds[2] <= 2390, (text, bounds)
        assert 10 <= bounds[1] < bounds[3] <= 1340, (text, bounds)
        for other, value in self.labels:
            assert (bounds[2] <= other[0] or other[2] <= bounds[0]
                    or bounds[3] <= other[1] or other[3] <= bounds[1]), (
                        "Text overlap", text, value, bounds, other)
        self.labels.append((bounds, text))
        self.d.text(at, text, fill=color, font=font(size), anchor=anchor)

    def lines(self, at, values, size=28, color=INK, spacing=38):
        for i, value in enumerate(values):
            self.text((at[0], at[1] + i * spacing), value, size, color)

    def line(self, points, color=RULE, width=2, dashed=False):
        if not dashed:
            self.d.line(points, fill=color, width=width, joint="curve")
            return
        for a, b in zip(points, points[1:]):
            distance = hypot(b[0] - a[0], b[1] - a[1])
            if not distance:
                continue
            for start in range(0, int(distance), 19):
                self.d.line([(a[0] + (b[0] - a[0]) * t / distance,
                              a[1] + (b[1] - a[1]) * t / distance)
                             for t in (start, min(start + 11, distance))],
                            fill=color, width=width)

    def arrow(self, points, color=PROPOSED, dashed=False, width=3):
        self.line(points, color, width, dashed)
        a, b = points[-2:]
        distance = hypot(b[0] - a[0], b[1] - a[1])
        ux, uy = (b[0] - a[0]) / distance, (b[1] - a[1]) / distance
        self.d.polygon([b, (b[0] - 14 * ux - 7 * uy, b[1] - 14 * uy + 7 * ux),
                        (b[0] - 14 * ux + 7 * uy, b[1] - 14 * uy - 7 * ux)], fill=color)

    def leader(self, points, color=MUTED):
        self.line(points, color)
        x, y = points[-1]
        self.d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=color)

    def rect(self, bounds, fill=None, outline=PROPOSED, width=3):
        self.d.rectangle(bounds, fill=fill, outline=outline, width=width)

    def wheel(self, at, color=PROPOSED):
        x, y = at
        self.d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=BG, outline=color, width=3)
        self.line([(x - 8, y), (x + 8, y)], color)
        self.line([(x, y - 8), (x, y + 8)], color)

    def button(self, at):
        x, y = at
        self.d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=BG, outline=PROPOSED, width=2)
        self.d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=PROPOSED)

    def card(self, at):
        x, y = at
        self.rect((x - 6, y - 9, x + 6, y + 9), BG, PROPOSED, 2)
        self.line([(x - 4, y - 2), (x + 4, y - 2)], PROPOSED)

    def hatch(self, at, state="hand", halfheight=29):
        x, y = at
        color = RUST if state in ("rust", "sealed") else PROPOSED
        self.rect((x - 10, y - halfheight, x + 10, y + halfheight), BLUE_BG, color, 3)
        self.wheel(at, color)
        if state in ("rust", "sealed"):
            self.line([(x - 16, y - 21), (x + 16, y + 21)], color, 4)
            self.line([(x - 16, y + 21), (x + 16, y - 21)], color, 4)
        self.button((x + 25, y - halfheight + 5))
        self.card((x + 25, y - halfheight + 29))

    def number(self, n, at, target=None, color=BUILT):
        if target is not None:
            self.leader([at, target], color)
        x, y = at
        self.d.ellipse((x - 20, y - 20, x + 20, y + 20), fill=color, outline=BG, width=2)
        self.text(at, str(n), 28, "white", "mm")

    def scale(self, at, meters, ppm, vertical=False):
        x, y = at
        length = meters * ppm
        if vertical:
            self.line([(x, y), (x, y + length)], INK, 5)
            for v in (y, y + length):
                self.line([(x - 9, v), (x + 9, v)], INK, 3)
            self.text((x + 20, y), "0", 26)
            self.text((x + 20, y + length), f"{meters:g} m", 26, anchor="lm")
        else:
            for i in range(4):
                self.rect((x + i * length / 4, y, x + (i + 1) * length / 4, y + 10),
                          INK if i % 2 == 0 else BG, INK, 1)
            self.text((x, y + 18), "0", 26)
            self.text((x + length, y + 18), f"{meters:g} m", 26, anchor="rt")

    def swatch(self, at, text, color, fill):
        x, y = at
        self.rect((x, y + 3, x + 26, y + 25), fill, color)
        self.text((x + 40, y), text, 27, color)

    def save(self, name):
        path = HERE / name
        self.image.save(path)
        with Image.open(path) as result:
            assert result.size == SIZE and result.format == "PNG"
            result.verify()
        print(f"{path}: 2400x1350 PNG; {path.stat().st_size:,} bytes; "
              f"{len(self.labels)} non-overlapping labels, all >=26 px")


def room(s, p, bounds, fill, color, width=4):
    x0, x1, z0, z1 = bounds
    s.rect((*p(x0, z1), *p(x1, z0)), fill, color, width)


def floor_y(deck, atlas):
    return (14 - deck) * atlas["coordinate_system"]["deck_pitch"]


def hull_span(profile, value, field):
    """Clip a horizontal deck/spine line to the piecewise-linear hull."""
    result = []
    for a, b in zip(profile, profile[1:]):
        if a[field] >= value:
            result.append(a["x"])
        if (a[field] - value) * (b[field] - value) < 0:
            result.append(a["x"] + (b["x"] - a["x"]) *
                          (value - a[field]) / (b[field] - a[field]))
    if profile[-1][field] >= value:
        result.append(profile[-1]["x"])
    return min(result), max(result)


def ship_scale(atlas, facilities):
    s = Sheet("Where the built rooms are on the ship",
              "Built so far: about 30 m of a 2,400 m ship, on one of 30 decks.")
    ppm = 0.8
    profile = atlas["coordinate_system"]["hull_profile"]

    def side(x, y):
        return 240 + (x + 1200) * ppm, 350 - y * ppm

    def plan(x, z):
        return 240 + (x + 1200) * ppm, 935 - z * ppm

    assert side(1200, 0)[0] - side(-1200, 0)[0] == 2400 * ppm
    assert side(0, 0)[1] - side(0, 1)[1] == ppm or isclose(side(0, 0)[1] - side(0, 1)[1], ppm)
    s.text((65, 163), "SIDE ELEVATION / X and Y at equal scale", 30)
    s.text((240, 215), "BOW -X", 28)
    s.text((2160, 215), "STERN +X", 28, anchor="rt")
    s.scale((740, 180), 250, ppm)
    polygon = [side(v["x"], v["halfheight"]) for v in profile]
    polygon += [side(v["x"], -v["halfheight"]) for v in reversed(profile)]
    s.d.polygon(polygon, fill=BLUE_BG, outline=PROPOSED, width=3)
    for deck in range(1, 31):
        y = floor_y(deck, atlas)
        a, b = hull_span(profile, abs(y), "halfheight")
        s.line([side(a, y), side(b, y)], PROPOSED if deck == 14 else FAINT,
               2 if deck == 14 else 1)
    for sector in atlas["grid"]["sectors"]:
        a, b = sector["x"]
        s.text((side((a + b) / 2, 0)[0], 247), f"Sector {sector['id']}", 26, anchor="mt")
        if a != -1200:
            height = next(v["halfheight"] for v in profile if v["x"] == a)
            s.line([side(a, height), side(a, -height)], RULE, 1)
    for name in atlas["routes"]["through_trunks"]:
        x = facilities[name]["xyz"][0]
        s.line([side(x, floor_y(1, atlas)), side(x, floor_y(30, atlas))], RULE, 2)
    for x in range(-1200, 1201, 30):
        u, v = side(x, 0)
        s.line([(u, v - 4), (u, v + 4)], RULE, 1)
    for key, at, text, elbow in (
            ("bridge", (1670, 163), "D03 bridge anchor", (1635, 205)),
            ("primary", (1770, 470), "D27 primary generation", (1760, 455))):
        x, y, _ = facilities[key]["xyz"]
        target = side(x, y)
        s.d.ellipse((target[0] - 4, target[1] - 4, target[0] + 4, target[1] + 4), fill=PROPOSED)
        s.text(at, text, 28, PROPOSED)
        s.leader([elbow, target], PROPOSED)
    s.text((1000, 195), "D13 crew quarters (proposed)", 28, PROPOSED)
    s.leader([(1190, 233), (1190, 265), side(35, 5.5)], PROPOSED)
    s.text((65, 460), "atlas trunks (earlier proposal)", 27, MUTED)
    s.leader([(570, 475), (690, 475), side(-550, -70)])
    for deck, at in ((1, (2200, 280)), (14, (2200, 345)), (30, (2200, 415))):
        s.text(at, f"D{deck:02}", 27, PROPOSED if deck == 14 else MUTED)
        s.leader([(2190, at[1] + 14), side(1190, floor_y(deck, atlas))])
    # The actual slice remains a tiny mark, not an enlarged ship district.
    a, b = side(facilities["hall"]["bounds"]["x"][0], 3.2), side(facilities["power_room"]["bounds"]["x"][1], 0)
    s.rect((*a, *b), BUILT, BUILT, 1)
    s.leader([side(14, 0), (1370, 440), (1370, 505), (650, 505), (650, 555)], BUILT)
    s.text((930, 465), "Tiny green mark = built opening", 27, BUILT)

    s.rect((70, 520, 650, 800), BG, RULE, 2)
    s.text((90, 537), "10x magnifier / D14 proposal", 28)
    p = lambda x, z: (100 + x * 8, 690 - z * 8)
    room(s, p, (6, 30, -1.5, 1.5), GREEN_BG, BUILT)
    room(s, p, (21, 33, -9.7, -1.7), GREEN_BG, BUILT)
    room(s, p, (11, 19, 1.7, 13.7), MOVED_BG, MOVED)
    s.text((430, 595), "Moved bay", 26, MOVED)
    s.leader([(420, 610), p(19, 9)], MOVED)
    s.text((430, 665), "Hall", 26, BUILT)
    s.leader([(420, 680), p(29, 0)], BUILT)
    s.text((430, 735), "Backup", 26, BUILT)
    s.leader([(420, 750), p(33, -6)], BUILT)
    s.scale((100, 753), 10, 8)
    s.text((730, 550), "D14 TOP-DOWN / X and Z at equal scale", 30)
    polygon = [plan(v["x"], v["halfwidth"]) for v in profile]
    polygon += [plan(v["x"], -v["halfwidth"]) for v in reversed(profile)]
    s.d.polygon(polygon, fill=BLUE_BG, outline=PROPOSED, width=3)
    for sector in atlas["grid"]["sectors"][1:]:
        x = sector["x"][0]
        width = next(v["halfwidth"] for v in profile if v["x"] == x)
        s.line([plan(x, width), plan(x, -width)], FAINT, 1)
    for z in atlas["routes"]["longitudinal_passages_z"]:
        # The atlas route nodes only span X=-850..850, not the entire envelope.
        s.line([plan(-850, z), plan(850, z)], RULE, 3)
    for name in atlas["routes"]["through_trunks"]:
        x, _, z = facilities[name]["xyz"]
        u, v = plan(x, z)
        s.rect((u - 3, v - 3, u + 3, v + 3), RULE, RULE, 1)
    s.line([plan(-1200, 0), plan(1200, 0)], PROPOSED, 2)
    for x in range(-1200, 1201, 30):
        u, v = plan(x, 0)
        s.line([(u, v - 5), (u, v + 5)], RULE, 1)
    for key in ("bay", "hall", "power_room"):
        b = facilities[key]["bounds"]
        room(s, plan, (*b["x"], *b["z"]), BUILT, BUILT, 1)
    s.text((750, 600), "atlas spines (earlier proposal), Z=+/-90 m", 27, MUTED)
    s.leader([(980, 637), (980, 790), plan(-300, 90)])
    s.text((80, 1040), "Opening on D14", 28, BUILT)
    s.text((80, 1080), "True-scale footprint", 26, BUILT)
    s.leader([(400, 1060), (700, 1060), plan(16, 0)], BUILT)
    s.lines((1740, 565), ["Whole-ship scale", "0.8 pixels = 1 m"], 26, MUTED, 36)
    s.scale((1750, 655), 500, ppm)
    s.text((1940, 775), "Starboard +Z", 26, MUTED)
    s.text((1940, 1120), "Port -Z", 26, MUTED)
    s.text((750, 1240), "Faint ticks: ~30 m connector pitch, about 80 along a full-length deck.", 27, MUTED)
    s.swatch((70, 1290), "Built", BUILT, GREEN_BG)
    s.swatch((330, 1290), "Moved", MOVED, MOVED_BG)
    s.swatch((610, 1290), "Proposed ship / routes", PROPOSED, BLUE_BG)
    s.text((1170, 1290), "Hull and deck dimensions are atlas proposals, not exterior measurements.", 27, MUTED)
    s.save("ship-scale.png")


def local_plan(atlas, facilities):
    s = Sheet("D14 near the opening: sections and connectors (proposal)",
              "Local crop: X=-30..66 m of a 2,400 m ship. D14 is one of 30 decks; room footprints share one metric scale.")
    ppm = 22
    p = lambda x, z: (804 + x * ppm, 700 - z * ppm)
    assert p(66, 0)[0] - p(-30, 0)[0] == 96 * ppm
    assert isclose(p(0, 0)[1] - p(0, 1)[1], ppm)
    s.text((90, 174), "BOW -X  /  fore", 29)
    s.text((2300, 174), "aft  /  STERN +X  →", 29, anchor="rt")
    s.text((90, 222), "Starboard +Z up; port -Z down", 28, MUTED)
    for a, b, text, y in ((-24, 0, "Fore section: X=-24..0", 285),
                           (0, 6, "Fore connector: X=0..6", 335),
                           (6, 30, "Opening: X=6..30", 285),
                           (30, 36, "Aft connector: X=30..36", 335),
                           (36, 60, "Aft section: X=36..60", 285)):
        mid = p((a + b) / 2, 0)[0]
        s.text((mid, y), text, 27, PROPOSED if a != 6 else BUILT, "mt")
    for a, b in ((-24, 0), (36, 60)):
        room(s, p, (a, b, -1.5, 1.5), None, PROPOSED, 3)
        for x in (a + 3, a + 9, a + 15):
            for z in (-1.5, 1.5):
                leaf(s, p, x, z, PROPOSED)
        s.text((p((a + b) / 2, 0)[0], 610), "next section (not built)", 28, PROPOSED, "mt")
    for a, b in ((0, 6), (30, 36)):
        room(s, p, (a, b, -1.5, 1.5), BLUE_BG, PROPOSED)
    room(s, p, (6, 30, -1.5, 1.5), GREEN_BG, BUILT)
    room(s, p, (21, 33, -9.7, -1.7), GREEN_BG, BUILT)
    room(s, p, (11, 19, 1.7, 13.7), MOVED_BG, MOVED)
    # Erase the paired wall segments to make actual doorways, not wall symbols.
    for x, z, width in ((15, 1.5, 1.2), (15, 1.7, 1.2),
                         (27, -1.5, 1), (27, -1.7, 1)):
        u, v = p(x, z)
        s.line([(u - width * ppm / 2, v), (u + width * ppm / 2, v)], BG, 6)
    for x in (9, 15, 21):
        for z in (-1.5, 1.5):
            if (x, z) != (15, 1.5):
                leaf(s, p, x, z, BUILT)
    leaf(s, p, 15, 1.5, MOVED, width=1.2)
    leaf(s, p, 27, -1.5, BUILT)
    pod_points = []
    for i in range(7):
        x, _, z = facilities[f"pod_{i}"]["xyz"]
        pod_points.append((x, z))
        s.d.rounded_rectangle((*p(x - 1.1, z + .45), *p(x + 1.1, z - .45)),
                              radius=7, fill=PLAYER if i == 6 else BG, outline=MOVED, width=3)
        s.line([p(x - .7, z), p(x + .7, z)], MOVED)
    rx, _, rz = facilities["rod"]["xyz"]
    rod = (rx, rz)
    s.line([p(rod[0], rod[1] - .5), p(rod[0], rod[1] + .5)], MOVED, 6)
    u, v = p(16.2, 1.45)
    s.rect((u - 6, v - 6, u + 6, v + 6), PLAYER, MOVED, 3)
    for x in (0, 6, 30, 36):
        s.hatch(p(x, 0), "hand")
    for ladder_x, lift_x in ((3, 3), (34.5, 33)):
        # The aft well clears the unchanged power-room back at X=33.
        room(s, p, (ladder_x - .85, ladder_x + .85, -5.8, -1.5), BLUE_BG, PROPOSED)
        s.line([p(ladder_x - .65, -1.5), p(ladder_x + .65, -1.5)], BG, 8)
        for x in (ladder_x - .55, ladder_x + .55):
            s.line([p(x, -2.5), p(x, -5.5)], PROPOSED, 3)
        for z in (-2.7, -3.3, -3.9, -4.5, -5.1):
            s.line([p(ladder_x - .55, z), p(ladder_x + .55, z)], PROPOSED, 3)
        u, v = p(ladder_x, -4)
        s.arrow([(u - 32, v + 28), (u - 32, v - 28)])
        s.arrow([(u + 32, v - 28), (u + 32, v + 28)])
        room(s, p, (lift_x - 1.1, lift_x + 1.1, 1.5, 4.5), BLUE_BG, PROPOSED)
        leaf(s, p, lift_x, 1.5, PROPOSED, width=1.8)
        s.line([p(lift_x, 1.2), p(lift_x, 1.8)], PROPOSED, 3)
        s.button(p(lift_x + 1.6, 1.5))
        s.text((p(lift_x, 0)[0], 557), "dead", 27, PROPOSED, "mt")
    s.text((700, 490), "Lift + call", 27, PROPOSED)
    s.leader([(810, 525), p(3, 4.5)], PROPOSED)
    s.text((1740, 540), "Lift + call", 27, PROPOSED)
    s.leader([(1730, 553), (1660, 553), p(33, 4.5)], PROPOSED)
    s.lines((90, 410), ["Five side doors stay closed:", "X=9 both walls; X=15 port;", "X=21 both walls. No hub rooms."], 28, INK)
    s.leader([(560, 499), (670, 499), (670, 637), p(9, 1.5)])
    s.lines((1600, 400), ["Moved stasis bay: 8 x 12 m", "X=11..19; Z=1.7..13.7", "Quarter-turn; seven pods retained."], 28, MOVED)
    s.leader([(1580, 424), (1360, 424), p(19, 12)], MOVED)
    s.text((1290, 210), "Player pod 6: far from door", 28, MOVED)
    s.leader([(1390, 250), (1390, 370), p(*pod_points[6])], MOVED)
    s.lines((90, 785), ["D14 hatches: crank", "Connectors not built yet."], 28, RUST)
    s.leader([(420, 801), (710, 801), p(0, 0)], RUST)
    s.lines((630, 890), ["Open ladder doorway", "Port wall; up / down"], 27, PROPOSED)
    s.leader([(870, 879), p(3, -5.8)], PROPOSED)
    s.lines((1670, 850), ["Open ladder doorway at X=34.5", "Up to D13 crew quarters (proposed)", "Down to D15"], 27, PROPOSED)
    s.leader([(1650, 872), (1620, 872), p(34.5, -5.8)], PROPOSED)
    s.text((1050, 961), "Unchanged power room / local backup", 28, BUILT)
    s.leader([(1370, 949), p(33, -9.7)], BUILT)
    room(s, p, (21, 21.56, -8.125, -6.875), BUILT, BUILT, 1)
    u, v = p(27, -5.7)
    s.d.ellipse((u - 18, v - 18, u + 18, v + 18), fill=INK, outline=BUILT, width=3)
    trail = [(17.9, 11.6), (15, 10), rod, (15, 6), (15, 1.5), (16.2, .2),
             (27, .2), (27, -1.5), (27, -3.6), (24, -5.5), (22.05, -7.5)]
    s.arrow([p(*point) for point in trail], MOVED, width=3)
    s.arrow([p(*point) for point in [(22.05, -7.5), (24, -5.5), (27, -3.6),
                                    (27, -1.5), (27, -.6), (30, -.6),
                                    (34.5, -.6), (34.5, -3)]],
            PROPOSED, dashed=True)
    s.text((1590, 765), "then →", 27, PROPOSED)
    markers = [(p(17.9, 14.8), p(*pod_points[6])),
               (p(9.6, 7.6), p(*rod)), (p(12, 2.8), p(15, 1.5)),
               (p(19, 3), p(16.2, 1.45)), (p(29, -3), p(27, -1.5)),
               (p(23, -7.5), p(22.05, -7.5))]
    for i, (at, target) in enumerate(markers, 1):
        s.number(i, at, target, MOVED if i < 5 else BUILT)
    s.scale((180, 980), 10, ppm)
    s.text((1740, 989), "22 pixels = 1 m; symbols enlarged", 26, MUTED)
    s.line([(60, 1040), (2340, 1040)])
    for i, text in enumerate(("Pod 6", "Pick up rod", "Pry bay door", "Hall switch",
                               "Power-room door", "Working console"), 1):
        x = 90 + ((i - 1) % 3) * 770
        y = 1073 + ((i - 1) // 3) * 57
        s.number(i, (x, y), color=MOVED if i < 5 else BUILT)
        s.text((x + 34, y), text, 29, anchor="lm")
    s.swatch((70, 1180), "Built / unchanged", BUILT, GREEN_BG)
    s.swatch((500, 1180), "Moved", MOVED, MOVED_BG)
    s.swatch((800, 1180), "Proposed", PROPOSED, BLUE_BG)
    s.swatch((1150, 1180), "Rust + X: won't open", RUST, BG)
    s.swatch((1700, 1180), "Gold: player pod", MOVED, PLAYER)
    s.wheel((90, 1240))
    s.text((115, 1225), "Wheel: opens by hand (Space)", 26, PROPOSED)
    s.button((655, 1237))
    s.card((685, 1237))
    s.text((715, 1225), "Button + card reader: after main power", 26, PROPOSED)
    s.text((1510, 1225), "Split doors + call button: dead lift", 26, PROPOSED)
    s.text((70, 1271), "ladder on the port wall, lifts on the starboard wall: ladder on your left walking aft", 28)
    s.text((70, 1310), "Bay, hall and backup room use the built layout export. Connectors and neighboring sections remain proposals.", 26, MUTED)
    s.save("d14-local-plan.png")


def leaf(s, p, x, z, color, width=1):
    u, v = p(x, z)
    half = width * 22 / 2
    s.rect((u - half, v - 5, u + half, v + 5), BG, color, 3)
    s.line([(u - half + 3, v - 8), (u + half - 3, v + 8)], color, 2)


def connector_section(atlas):
    s = Sheet("Through the aft connector: decks D12 to D16 (proposal)",
              "Unfolded side section: opposite-wall ladder and lift shown beside each other. Vertical scale: 32 pixels = 1 m.")
    s.text((70, 170), "Five of 30 decks; one ~6 m connector in a 2,400 m ship", 30)
    s.text((70, 215), "example pattern; per-deck states TBD", 29, PROPOSED)
    ppm = 32
    deck_y = lambda deck: 340 + (floor_y(12, atlas) - floor_y(deck, atlas)) * ppm
    assert deck_y(13) - deck_y(12) == 5.5 * ppm
    s.text((540, 265), "FORE -X", 27, PROPOSED)
    s.text((1460, 265), "AFT +X", 27, PROPOSED, "rt")
    s.text((850, 215), "PORT ladder", 28, PROPOSED)
    s.text((1140, 215), "STARBOARD lift", 28, PROPOSED)
    s.leader([(930, 251), (930, 270), (900, 285)], PROPOSED)
    s.leader([(1240, 251), (1240, 270), (1160, 280)], PROPOSED)
    s.rect((860, 285, 940, 1085), BLUE_BG, PROPOSED, 3)
    s.rect((1100, 285, 1230, 1085), BLUE_BG, PROPOSED, 3)
    for x in (880, 920):
        s.line([(x, 290), (x, 1080)], PROPOSED, 4)
    for y in range(300, 1080, 19):
        s.line([(880, y), (920, y)], PROPOSED, 3)
    for deck in range(12, 17):
        y = deck_y(deck)
        color = BUILT if deck == 14 else PROPOSED
        for a, b in ((480, 650), (650, 860), (940, 1100), (1230, 1430), (1430, 1550)):
            built_stub = deck == 14 and b == 650
            s.rect((a, y - 80, b, y), GREEN_BG if built_stub else BLUE_BG, None, 1)
            s.line([(a, y), (b, y)], BUILT if built_stub else PROPOSED, 5)
            s.line([(a, y - 80), (b, y - 80)], RULE, 2)
        # Cutaway corridor floors do not bridge the continuous ladder/lift wells.
        fore = "hand" if deck == 14 else "sealed"
        aft = "hand" if deck == 14 else "sealed"
        s.hatch((650, y - 40), fore, 38)
        s.hatch((1430, y - 40), aft, 38)
        s.text((70, y - 77), f"D{deck:02}", 32, color)
        detail = {12: "Both sealed: won't open", 13: "Both sealed: won't open",
                  14: "built opening", 15: "Both sealed: won't open", 16: "Both sealed: won't open"}[deck]
        s.text((70, y - 30), detail, 27, color)
        if deck == 14:
            s.text((1630, y - 60), f"D{deck:02}: both open by hand", 28, PROPOSED)
            s.leader([(1610, y - 43), (1510, y - 43), (1440, y - 43)], PROPOSED)
    s.arrow([(837, 420), (837, 320)])
    s.arrow([(964, 320), (964, 420)])
    # One parked car, with its doors and a call button at each floor.
    y = deck_y(15)
    s.rect((1110, y - 104, 1220, y - 8), BG, PROPOSED, 4)
    s.line([(1165, y - 100), (1165, y - 12)], PROPOSED, 3)
    for deck in range(12, 17):
        s.button((1250, deck_y(deck) - 42))
    s.lines((1630, 715), ["Parked lift car: dead", "Call buttons do not restore power."], 28, PROPOSED)
    s.leader([(1610, 735), (1535, 735), (1535, 790), (1220, y - 60)], PROPOSED)
    s.scale((1580, 800), 5.5, ppm, vertical=True)
    s.text((1630, 1020), "Deck pitch", 26, MUTED)
    s.rect((1770, 810, 2330, 1065), BG, RULE, 2)
    s.text((1790, 830), "End-of-deck connector", 27)
    s.text((1790, 873), "Symbolic inset / not metric", 26, MUTED)
    s.rect((1800, 943, 2190, 1010), BLUE_BG, PROPOSED, 3)
    s.line([(2190, 943), (2190, 1010)], PROPOSED, 8)
    s.hatch((1870, 977))
    s.text((1930, 1029), "One hatch; outer end closed", 26, anchor="mt")
    s.text((1630, 295), "Hatch states are examples only.", 28, MUTED)
    s.text((1630, 340), "Shaft widths are diagrammatic.", 28, MUTED)
    s.line([(60, 1130), (2340, 1130)])
    s.swatch((70, 1160), "Built D14 corridor reference", BUILT, GREEN_BG)
    s.swatch((730, 1160), "Proposed connector / vertical access", PROPOSED, BLUE_BG)
    s.swatch((1650, 1160), "Rust + X: won't open", RUST, BG)
    s.wheel((90, 1230))
    s.text((120, 1215), "Hand wheel: Space; wheel turns", 28, PROPOSED)
    s.button((760, 1230))
    s.card((795, 1230))
    s.text((825, 1215), "Button and card reader: after main power", 28, PROPOSED)
    s.text((70, 1280), "Port ladder: open doorway on every deck, up and down. Starboard lift: doors with call buttons, dead.", 28)
    s.text((70, 1314), "Longitudinal hatch spacing is symbolic in this unfolded view; floor datums retain the atlas 5.5 m pitch.", 26, MUTED)
    s.save("connector-section.png")


def main():
    atlas = json.loads(ATLAS.read_text(encoding="utf-8"))
    facilities = {item["id"]: item.copy() for item in atlas["facilities"]}
    built = json.loads((ATLAS.parent / "built-layout.json").read_text())["facilities"]
    for name, placement in built.items():
        if name in facilities:
            facilities[name].update(placement)
    assert sum(b - a + 1 for a, b in (g["decks"] for g in atlas["grid"]["groups"])) == 30
    assert atlas["coordinate_system"]["envelope_max"]["x"] == [-1200, 1200]
    assert atlas["coordinate_system"]["deck_pitch"] == 5.5
    assert facilities["hall"]["bounds"] == {"x": [6, 30], "z": [-1.5, 1.5]}
    assert facilities["power_room"]["bounds"] == {"x": [21, 33], "z": [-9.7, -1.7]}
    assert 34.5 - .85 > facilities["power_room"]["bounds"]["x"][1]
    ship_scale(atlas, facilities)
    local_plan(atlas, facilities)
    connector_section(atlas)


if __name__ == "__main__":
    main()
