"""Build the screen-sized ship overview and the metric opening walkthrough.

Run: python3 docs/art/ship/build-simple-guide.py
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
ATLAS = HERE / "3d" / "ship_atlas.json"
PHOTO = HERE / "exterior-concept-v2.png"
SIZE = (2200, 1200)
BG = "#f5f5f0"
INK = "#142b36"
MUTED = "#3c5360"
RULE = "#a7b8b9"
BUILT = "#08735b"
GREEN_BG = "#ddede3"
PROPOSED = "#245981"
BLUE_BG = "#e2edf4"
FLOOR = "#e5edea"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"


def font(size):
    return ImageFont.truetype(FONT, size)


def label(draw, xy, value, size=34, color=INK, anchor=None):
    draw.text(xy, value, font=font(size), fill=color, anchor=anchor)


def lines(draw, x, y, values, size=34, color=INK, spacing=44):
    for index, value in enumerate(values):
        label(draw, (x, y + index * spacing), value, size, color)


def stroke(draw, points, color=RULE, width=4):
    draw.line(points, fill=color, width=width, joint="curve")


def arrow(draw, start, end, color=BUILT, width=7):
    stroke(draw, [start, end], color, width)
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / length, dy / length
    tip = end
    base = (end[0] - ux * 20, end[1] - uy * 20)
    draw.polygon([tip, (base[0] - uy * 11, base[1] + ux * 11),
                  (base[0] + uy * 11, base[1] - ux * 11)], fill=color)


def circle(draw, center, number, color=BUILT):
    x, y = center
    draw.ellipse((x - 22, y - 22, x + 22, y + 22), fill=color,
                 outline=BG, width=3)
    label(draw, (x, y - 1), str(number), 32, "#ffffff", "mm")


def xy(facility):
    x, _, z = facility["xyz"]
    return x, z


def validate(atlas):
    f = {item["id"]: item for item in atlas["facilities"]}
    axes = atlas["coordinate_system"]
    assert axes["opening_deck"] == "D14"
    assert axes["envelope_max"] == {"x": [-1200, 1200],
                                    "y": [-96, 96], "z": [-360, 360]}
    assert f["bay"]["bounds"] == {"x": [-6, 6], "z": [-4, 4]}
    assert f["hall"]["bounds"] == {"x": [6, 30], "z": [-1.5, 1.5]}
    assert f["hall"]["endcap_x"] == 30
    assert f["power_room"]["bounds"] == {"x": [21, 33], "z": [-9.7, -1.7]}
    assert xy(f["pod_6"]) == (-4.8, 2.9) and f["pod_6"]["state"] == "player"
    assert xy(f["rod"]) == (-0.6, -1.55)
    assert xy(f["hatch"]) == (6, 0)
    assert xy(f["switch"]) == (6.22, 0.85)
    assert xy(f["power_door"]) == (27, -1.5)
    assert xy(f["backup"]) == (27, -5.7)
    assert sorted(xy(f[f"pod_{i}"]) for i in range(7)) == sorted([
        (-4.8, -2.9), (-3.4, -2.9), (-2, -2.9), (-0.6, -2.9),
        (-4.8, 2.9), (-3.4, 2.9), (-2, 2.9)])
    assert all(f[f"pod_{i}"]["status"] == "built" for i in range(7))
    assert all(f[f"remote_pod_{i}"]["status"] == "proposed" for i in (1, 2))
    assert all(f[k]["status"] == "proposed" for k in
               ("bridge", "primary", "m_drive", "r1", "r2", "armory", "remote_room"))
    assert f["bridge"]["xyz"][0] > 0
    assert f["primary"]["xyz"][0] > 0 and f["m_drive"]["xyz"][0] > 0
    assert f["r2"]["xyz"][0] < 0
    leaves = [f[f"leaf_{n}_{side}"] for n in (9, 15, 21)
              for side in ("north", "south")]
    assert all(leaf["pierced"] is False for leaf in leaves)
    assert [(xy(f[f"leaf_{n}_{side}"])) for n in (9, 15, 21)
            for side in ("north", "south")] == [
                (n, z) for n in (9, 15, 21) for z in (-1.5, 1.5)]
    built_edges = {(edge["from"], edge["to"]) for edge in atlas["routes"]["edges"]
                   if edge["status"] == "built" and "impassable" not in edge["kind"]}
    assert built_edges == {("bay", "hatch"), ("hatch", "hall"),
                           ("hall", "power_door"), ("power_door", "power_room")}
    assert sum(node["role"] == "primary generation" for node in atlas["power"]["nodes"]) == 1
    assert sum(node["role"] == "backup generation" for node in atlas["power"]["nodes"]) == 1
    return f


def overview(f):
    image = Image.new("RGB", SIZE, BG)
    d = ImageDraw.Draw(image)
    label(d, (70, 40), "THE SHIP  /  WHERE YOU WAKE", 58)
    label(d, (74, 106), "Exterior observation at left; inside locations below are PROPOSED.", 36, MUTED)
    with Image.open(PHOTO) as source:
        photo = source.convert("RGB")
    photo.thumbnail((1060, 700), Image.Resampling.LANCZOS)
    px, py = 70 + (1060 - photo.width) // 2, 159 + (700 - photo.height) // 2
    image.paste(photo, (px, py))
    d.rectangle((px - 2, py - 2, px + photo.width + 2, py + photo.height + 2),
                outline=INK, width=3)
    label(d, (1200, 178), "OBSERVED IN THE PHOTO", 42)
    lines(d, 1200, 243, ["LEFT: broad aft engines", "AFT-MID: raised bridge",
                           "RIGHT: pointed bow"], 35, INK, 53)
    stroke(d, [(1200, 421), (2120, 421)], RULE, 3)
    label(d, (1200, 444), "YOU START IN THE CENTER", 44, BUILT)
    lines(d, 1200, 514, ["D14 seven-pod bay, then a hall",
                           "and one LOCAL BACKUP room.",
                           "These are the built opening only."], 35, INK, 49)
    stroke(d, [(1200, 678), (2120, 678)], RULE, 3)
    lines(d, 1200, 696, ["Crew normally live awake in fore-mid,",
                           "midship and aft housing.",
                           "Stasis: medical / last resort.",
                           "7 pods built + 2 proposed elsewhere."], 34, INK, 43)

    stroke(d, [(70, 871), (2130, 871)], INK, 3)
    label(d, (76, 878), "PROPOSED SHIP-LENGTH ROUTE", 42, PROPOSED)
    positions = [290, 700, 1100, 1510, 1990]
    stroke(d, [(positions[0], 976), (positions[-1], 976)], PROPOSED, 7)
    stations = [
        ("AFT", ["Engineering / M-drive", "ONE main plant + R1"]),
        ("UPPER BRIDGE", ["Awake crew + officer", "neighborhoods"]),
        ("D14 SEVEN-POD BAY", ["YOU START HERE", "Hall + LOCAL BACKUP"]),
        ("FORWARD-MID R2", ["2 isolated proposed pods", "Irradiated armory"]),
        ("BOW", ["Pointed nose"]),
    ]
    annotation_bounds = []
    for x, (title, details) in zip(positions, stations):
        d.ellipse((x - 14, 962, x + 14, 990), fill=BUILT if x == positions[2] else PROPOSED)
        annotations = [(title, 1001, 34, BUILT if x == positions[2] else INK)]
        annotations += [(detail, 1050 + i * 43, 32, INK)
                        for i, detail in enumerate(details)]
        for text, y, size, color in annotations:
            bounds = d.textbbox((x, y), text, font=font(size), anchor="mt")
            assert 70 <= bounds[0] < bounds[2] <= 2130
            assert 0 <= bounds[1] < bounds[3] <= SIZE[1]
            assert all(bounds[2] <= other[0] or other[2] <= bounds[0] or
                       bounds[3] <= other[1] or other[3] <= bounds[1]
                       for other in annotation_bounds)
            annotation_bounds.append(bounds)
            label(d, (x, y), text, size, color, "mt")
    label(d, (76, 1157), "Scale proposed: 2.4 km x 720 m x 192 m; 30 decks. NOT measured from the perspective photo.",
          33, MUTED)
    image.save(HERE / "ship-overview-simple.png")


def start(f):
    image = Image.new("RGB", SIZE, BG)
    d = ImageDraw.Draw(image)
    label(d, (70, 37), "YOUR FIRST ROOMS  /  BUILT NOW", 58)
    label(d, (74, 105), "Metric plan, D14: +X is AFT / LEFT; -Z is UP. Only two doorways pierce walls.",
          35, MUTED)
    scale = 38

    def plan(x, z):
        return 90 + (33 - x) * scale, 190 + (z + 9.7) * scale

    assert abs(plan(1, 0)[0] - plan(0, 0)[0]) == abs(plan(0, 1)[1] - plan(0, 0)[1])

    def rect(bounds):
        a = plan(bounds["x"][1], bounds["z"][0])
        b = plan(bounds["x"][0], bounds["z"][1])
        d.rectangle((*a, *b), fill=FLOOR)

    for key in ("bay", "hall", "power_room"):
        rect(f[key]["bounds"])

    # Traverse the bay, pass the hatch and switch, then enter the power room.
    trail = [plan(*xy(f["pod_6"])), plan(-3.7, 1.6),
             plan(*xy(f["rod"])), plan(1, -0.2), plan(*xy(f["hatch"])),
             plan(*xy(f["switch"])), plan(12, 0), plan(22, 0),
             plan(27, 0), plan(*xy(f["power_door"])), plan(27, -3.0),
             plan(24, -5.5), plan(22.05, -7.5)]
    for a, b in zip(trail, trail[1:]):
        arrow(d, a, b, BUILT, 6)

    wall = 8
    bay = f["bay"]["bounds"]
    hall = f["hall"]["bounds"]
    room = f["power_room"]["bounds"]
    # Each room is enclosed. Leave a 1.6 m hatch and a 1 m power doorway.
    def w(a, b):
        stroke(d, [plan(*a), plan(*b)], INK, wall)

    for z in (-4, 4):
        w((-6, z), (6, z))
    w((-6, -4), (-6, 4))
    w((6, -4), (6, -0.8))
    w((6, 0.8), (6, 4))
    w((6, -1.5), (6, -0.8))
    w((6, 0.8), (6, 1.5))
    w((6, 1.5), (30, 1.5))
    w((6, -1.5), (26.5, -1.5))
    w((27.5, -1.5), (30, -1.5))
    w((30, -1.5), (30, 1.5))  # Solid endcap.
    w((21, -9.7), (33, -9.7))
    w((21, -9.7), (21, -1.7))
    w((33, -9.7), (33, -1.7))
    w((21, -1.7), (26.5, -1.7))
    w((27.5, -1.7), (33, -1.7))
    # Draw the tunnel's sides without a bar across its 0.2 m depth.
    w((26.5, -1.7), (26.5, -1.5))
    w((27.5, -1.7), (27.5, -1.5))
    assert bay["x"] == [-6, 6] and hall["x"] == [6, 30] and room["x"] == [21, 33]
    label(d, (103, 213), "LOCAL BACKUP", 34)
    label(d, (1210, 374), "SEVEN-POD BAY", 34)
    label(d, (556, 643), "CORRIDOR", 34)

    # Solid decorative leaves sit ON the unbroken corridor walls.
    for n in (9, 15, 21):
        for z in (-1.5, 1.5):
            u, v = plan(n, z)
            d.rectangle((u - 18, v - 8, u + 18, v + 8), fill="#915f58",
                        outline=INK, width=2)
            stroke(d, [(u - 12, v - 13), (u + 12, v + 13)], INK, 3)
    for i in range(7):
        u, v = plan(*xy(f[f"pod_{i}"]))
        color = BUILT if i == 6 else "#74908c"
        d.rounded_rectangle((u - 17, v - 30, u + 17, v + 30), radius=13,
                            fill=color, outline=INK, width=2)
    u, v = plan(*xy(f["backup"]))
    d.ellipse((u - 24, v - 24, u + 24, v + 24), fill=INK)
    label(d, (110, 377), "ONE GENERATOR", 32)
    label(d, (385, 315), "CONSOLE", 32)
    # Stop numbers follow the path; full verbs remain below the plan.
    markers = [plan(-5.5, 1.8), plan(-0.6, -0.65), plan(6.1, -0.1),
               plan(7.2, 1.1), plan(27.5, -2.8), plan(22.5, -6.9)]
    for number, center in enumerate(markers, 1):
        circle(d, center, number)
    label(d, (1180, 747), "YOUR POD  /  green", 37, BUILT)
    stroke(d, [(1529, 691), (1529, 731), (1496, 747)], BUILT, 4)
    label(d, (89, 740), "+X  AFT  ←", 35)
    label(d, (567, 740), "→  BOW  -X", 35)
    arrow(d, (71, 358), (71, 279), INK, 5)
    label(d, (90, 282), "-Z  UP", 33)

    stroke(d, [(1620, 174), (1620, 776)], RULE, 3)
    label(d, (1660, 196), "SOLID WALLS", 40)
    lines(d, 1660, 254, ["Six side leaves are", "blocked, not exits.",
                            "The hall ends at", "a solid endcap."], 34, INK, 49)
    stroke(d, [(1660, 466), (2130, 466)], RULE, 3)
    label(d, (1660, 486), "ONE BACKUP HERE", 38, BUILT)
    lines(d, 1660, 545, ["Not the main plant.", "The rest of the ship",
                            "is planned, but not", "built in the game yet.",
                            "Every blocked wall stays built."], 33, INK, 43)
    d.rectangle((1660, 775, 1695, 803), fill=BLUE_BG, outline=PROPOSED, width=3)
    label(d, (1713, 766), "PROPOSED elsewhere", 33, PROPOSED)

    stroke(d, [(70, 831), (2130, 831)], INK, 3)
    steps = [
        ("1  WAKE", "Your pod is pod 6."),
        ("2  GRAB ROD", "Step off aisle for it."),
        ("3  PRY HATCH", "The rod opens it."),
        ("4  FLIP SWITCH", "Hall face, by hatch."),
        ("5  ENTER BACKUP", "Open power room door."),
        ("6  USE CONSOLE", "Start local generator."),
    ]
    for i, (title, detail) in enumerate(steps):
        x = 73 + (i % 3) * 712
        y = 856 + (i // 3) * 148
        label(d, (x, y), title, 39, BUILT)
        label(d, (x, y + 55), detail, 34, INK)
    label(d, (74, 1152), "Built rooms end at these walls. Any connection to the rest of the ship requires new openings.",
          33, MUTED)
    image.save(HERE / "ship-start-simple.png")


def main():
    atlas = json.loads(ATLAS.read_text(encoding="utf-8"))
    facilities = validate(atlas)
    overview(facilities)
    start(facilities)
    for filename in ("ship-overview-simple.png", "ship-start-simple.png"):
        with Image.open(HERE / filename) as result:
            assert result.size == SIZE and result.format == "PNG"
            print(f"{filename}: {result.width}x{result.height} {result.format}")


if __name__ == "__main__":
    main()
