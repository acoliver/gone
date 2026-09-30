"""Build the ship map board from the atlas and approved exterior image.

Run: python3 docs/art/ship/build-map-board.py
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
ATLAS = HERE / "3d" / "ship_atlas.json"
PHOTO = HERE / "exterior-concept-v2.png"
OUTPUT = HERE / "ship-map-board.png"
W, H = 3200, 3200
BG = "#f7f6f1"
INK = "#162936"
MUTED = "#51636a"
RULE = "#c6d0ce"
HULL = "#dce8e6"
BUILT = "#087b76"
PROPOSED = "#345e88"
HAZARD = "#a94742"
SCAR = "#ad8254"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"


def font(size):
    return ImageFont.truetype(FONT, size)


def text(draw, xy, value, size=32, color=INK, anchor=None):
    draw.text(xy, value, font=font(size), fill=color, anchor=anchor)


def line(draw, points, color=RULE, width=3):
    draw.line(points, fill=color, width=width, joint="curve")


def dot(draw, xy, radius, color, outline=None):
    x, y = xy
    draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color,
                 outline=outline or color, width=3)


def heading(draw, number, title, y, subtitle):
    line(draw, [(80, y), (3120, y)], INK, 4)
    text(draw, (88, y+22), number, 32, PROPOSED)
    text(draw, (200, y+16), title, 44)
    text(draw, (3105, y+25), subtitle, 29, MUTED, "ra")


def polygon_profile(profile, xy, axis, scale):
    left, center = xy
    top = [(left-(p["x"]+1200)*scale,
            center-p[axis]*scale) for p in reversed(profile)]
    bottom = [(left-(p["x"]+1200)*scale,
               center+p[axis]*scale) for p in profile]
    return top + bottom


def build():
    atlas = json.loads(ATLAS.read_text(encoding="utf-8"))
    f = {item["id"]: item for item in atlas["facilities"]}
    profile = atlas["coordinate_system"]["hull_profile"]
    pitch = atlas["coordinate_system"]["deck_pitch"]
    assert atlas["coordinate_system"]["envelope_max"]["x"] == [-1200, 1200]
    assert sum(f[f"pod_{i}"]["status"] == "built" for i in range(7)) == 7
    assert all(f[f"remote_pod_{i}"]["status"] == "proposed" for i in (1, 2))
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)

    # 01 | Approved perspective: the image itself is never annotated or stretched.
    text(d, (88, 50), "SHIP / A MAP FOR THE EXTERIOR", 58)
    text(d, (90, 125), "PROPOSAL  /  spatial guide, not game sensor output", 33, PROPOSED)
    with Image.open(PHOTO) as source:
        photo = source.convert("RGB")
    photo.thumbnail((1720, 470), Image.Resampling.LANCZOS)
    px, py = 88+(1720-photo.width)//2, 218+(470-photo.height)//2
    canvas.paste(photo, (px, py))
    d.rectangle((px-2, py-2, px+photo.width+2, py+photo.height+2),
                outline=INK, width=3)
    text(d, (1870, 214), "01  /  APPROVED EXTERIOR", 40)
    for y, s in [(290, "AFT / ENGINES at photo left"),
                 (341, "Pointed BOW at photo right"),
                 (413, "Raised bridge aft-mid"),
                 (464, "Localized outer plating damage")]:
        text(d, (1870, y), s, 33)
    line(d, [(1870, 535), (3110, 535)])
    text(d, (1870, 550), "MAP AXIS / PROPOSED", 32, PROPOSED)
    text(d, (1870, 596), "X=-1200 bow    |    X=+1200 aft", 34)
    text(d, (1870, 650), "Perspective cannot establish hull width.", 29, MUTED)

    # 02 | Horizontal projection, not a single walkable deck.
    heading(d, "02", "PLAN VIEW", 726, "STERN LEFT    /    BOW RIGHT")
    text(d, (93, 806), "Several decks projected into one silhouette; all ship-scale placements are proposed.", 30, MUTED)
    sx, sy, scale = 2090, 1125, 0.72
    def plan(x, z):
        return (sx-(x+1200)*scale, sy+z*scale)
    widest = max(profile, key=lambda p: p["halfwidth"])
    beam = 2*widest["halfwidth"]
    assert abs(abs(plan(100, 0)[0]-plan(0, 0)[0]) - abs(plan(0, 100)[1]-plan(0, 0)[1])) < 1e-9
    assert beam <= atlas["coordinate_system"]["envelope_max"]["z"][1]*2
    hull = [plan(p["x"], -p["halfwidth"]) for p in reversed(profile)]
    hull += [plan(p["x"], p["halfwidth"]) for p in profile]
    top, bottom = plan(widest["x"], -widest["halfwidth"]), plan(widest["x"], widest["halfwidth"])
    assert top in hull and bottom in hull and abs(bottom[1]-top[1] - beam*scale) < 1e-9
    assert 806 < min(y for _, y in hull) and max(y for _, y in hull) < 1434
    assert min(x for x, _ in hull) > 90 and max(x for x, _ in hull) < 2150
    def inside_hull(x, z):
        for lo, hi in zip(profile, profile[1:]):
            if lo["x"] <= x <= hi["x"]:
                width = lo["halfwidth"] + (hi["halfwidth"]-lo["halfwidth"])*(x-lo["x"])/(hi["x"]-lo["x"])
                return abs(z) <= width
        return False
    d.polygon(hull, fill=HULL, outline=INK, width=5)
    line(d, [plan(1200, 0), plan(-1200, 0)], "#aabfbc", 2)
    # The zones are distinct volumes on different decks. Their footprints alone are shown.
    for key in ("r2", "r1"):
        b = f[key]["bounds"]
        assert all(inside_hull(x, z) for x in b["x"] for z in b["z"])
        a, c = plan(b["x"][0], b["z"][0]), plan(b["x"][1], b["z"][1])
        d.rectangle((min(a[0], c[0]), min(a[1], c[1]),
                     max(a[0], c[0]), max(a[1], c[1])),
                    fill="#eabbb2", outline=HAZARD, width=4)
    for key in ("trunk_1", "trunk_2", "trunk_3", "trunk_4"):
        x, _, z = f[key]["xyz"]
        assert inside_hull(x, z)
        u, v = plan(x, z)
        d.rectangle((u-8, v-8, u+8, v+8), fill=PROPOSED)
    # Numbered map locations keep deck-program text clear of the narrow hull.
    # District dots are representative; facility dots use the atlas coordinates.
    def facility_plan(key):
        x, _, z = f[key]["xyz"]
        return (x, z)
    locations = [
        ("01", "BRIDGE  /  aft-mid D03", [facility_plan("bridge")], PROPOSED),
        ("02", "NAV / ASTROMETRY  /  fore-mid D01-04", [(-330, 210)], PROPOSED),
        ("03", "CREW + OFFICERS  /  fore, mid, aft", [(-780, 0), (60, 185), (850, -155)], PROPOSED),
        ("04", "MEDICAL / CIVIC  /  midship D05-08", [(0, -205)], PROPOSED),
        ("05", "ESCAPE / MUSTER  /  mid-aft D09-12", [(400, 205)], PROPOSED),
        ("06", "D14  /  7 built pods + backup x=+27", [facility_plan("bay")], BUILT),
        ("07", "R2  /  remote forward-mid port D21-23", [facility_plan("r2")], HAZARD),
        ("08", "MAIN PLANT / D27 + M-DRIVE  /  aft", [facility_plan("primary"), facility_plan("m_drive")], PROPOSED),
        ("09", "R1  /  isolated aft starboard D26-30", [facility_plan("r1")], HAZARD),
    ]
    for number, caption, points, color in locations:
        for x, z in points:
            assert inside_hull(x, z)
            dot(d, plan(x, z), 16, color, BG)
            text(d, plan(x, z), number, 17, BG, "mm")
    x, _, z = f["backup"]["xyz"]
    assert inside_hull(x, z)
    dot(d, plan(x, z), 5, BUILT, BG)
    text(d, (2200, 855), "PLAN KEY / SECTOR + DECK", 32, PROPOSED)
    text(d, (2200, 899), "Numbers: locations; small green dot: backup", 25, MUTED)
    for i, (number, caption, _, color) in enumerate(locations):
        y = 948+i*47
        text(d, (2200, y), number, 27, color)
        text(d, (2250, y), caption, 26)
    text(d, (390, 847), "AFT  +X", 26, PROPOSED)
    text(d, (1920, 847), "BOW  -X", 26, PROPOSED)
    text(d, (1750, 902), "PORT  -Z  ↑", 23, MUTED)
    text(d, (1680, 1320), "STARBOARD  +Z  ↓", 23, MUTED)
    # Scars are surface shorthand, intentionally outside either radiation footprint.
    for x, z in ((-310, -326), (350, 351)):
        a = plan(x, z)
        line(d, [(a[0]-25, a[1]-8), (a[0]-8, a[1]+5),
                 (a[0]+12, a[1]-4), (a[0]+28, a[1]+10)], SCAR, 5)
    text(d, (102, 1394), "OUTER PANEL SCARS (schematic surface marks) are not radiation zones.", 27, SCAR)
    text(d, (2200, 1394), "105 index bins do not imply 105 built rooms.", 25, MUTED)

    # 03 | Elevation using actual profile heights and all proposed deck floors.
    heading(d, "03", "SIDE ELEVATION", 1434, "30 DECK LEVELS  /  PROPOSED")
    text(d, (94, 1510), "2.4 km long; up to 192 m deep. These dimensions are proposed, not measured from the photo.", 30, MUTED)
    ex, ey, es = 2110, 1740, scale
    poly = polygon_profile(profile, (ex, ey), "halfheight", es)
    d.polygon(poly, fill=HULL, outline=INK, width=4)
    # Restrict floor strokes to the profile at the deck's elevation.
    def height(x):
        for lo, hi in zip(profile, profile[1:]):
            if lo["x"] <= x <= hi["x"]:
                t = (x-lo["x"])/(hi["x"]-lo["x"])
                return lo["halfheight"]*(1-t)+hi["halfheight"]*t
        return profile[-1]["halfheight"]
    for deck in range(1, 31):
        y = (14-deck)*pitch
        cuts = [x for x in range(-1200, 1201, 10) if height(x) > abs(y)+1]
        if cuts:
            x1, x2 = min(cuts), max(cuts)
            line(d, [(ex-(x1+1200)*es, ey-y*es),
                     (ex-(x2+1200)*es, ey-y*es)],
                 BUILT if deck == 14 else "#b1c5c2", 3 if deck == 14 else 1)
    bridge_x = ex-(f["bridge"]["xyz"][0]+1200)*es
    d.polygon([(bridge_x-90, ey-72), (bridge_x-64, ey-106),
               (bridge_x+45, ey-106), (bridge_x+78, ey-72)],
              fill=PROPOSED, outline=INK, width=3)
    # Drive housings are stylized beyond the stern, not a length measurement.
    stern_x = ex-(1200+1200)*es
    for offset in (-46, 0, 46):
        d.polygon([(stern_x-18, ey+offset-11), (stern_x-79, ey+offset-18),
                   (stern_x-79, ey+offset+18), (stern_x-18, ey+offset+11)],
                  fill="#a6b9bd", outline=INK, width=2)
    text(d, (177, 1856), "aft drive / stylized", 26, MUTED)
    text(d, (2005, 1856), "bow", 26, MUTED)
    text(d, (2135, 1591), "DECK PROGRAM / by vertical band", 34, PROPOSED)
    bands = [
        ("D01-04", "Fore-mid nav; aft-mid bridge"),
        ("D05-12", "Medical / civic; escape; berths"),
        ("D13-16", "Built 7-pod bay + local backup"),
        ("D17-20", "Life support; crew quarters"),
        ("D21-25", "R2 remote 2-pod / armory; crew"),
        ("D26-30", "Engineering by drives; R1 / plant"),
    ]
    for i, (decks, program) in enumerate(bands):
        y = 1653+i*55
        line(d, [(2136, y+17), (2195, y+17)],
             BUILT if i == 2 else HAZARD if i in (4, 5) else PROPOSED, 5)
        text(d, (2220, y), decks, 27)
        text(d, (2380, y), program, 27)
    text(d, (100, 1930), "D14 floor at Y=0 highlighted; floor Y=(14 - deck number) x 5.5 m.", 28, MUTED)
    text(d, (2135, 1971), "Crew + officer housing: both flanks, fore-mid to aft.", 25, MUTED)

    # 04 | Cross section is a proposed context; the inset alone is meter-true built work.
    heading(d, "04", "D14 IN CONTEXT / BUILT OPENING", 2020,
            "CROSS SECTION  +  WALKABLE ROUTE")
    text(d, (95, 2100), "Proposed hull section at X≈0", 32, PROPOSED)
    text(d, (1550, 2100), "Built opening at D14 / plan detail", 32, BUILT)
    left, right, cy, ry = 135, 1245, 2410, 244
    d.ellipse((left, cy-ry, right, cy+ry), fill=HULL, outline=INK, width=4)
    mid = (left+right)//2
    d.rectangle((mid-82, cy-ry+18, mid+82, cy+ry-18),
                fill="#c3d6d6", outline=PROPOSED, width=3)
    for z, label in [(-255, "PORT  -Z"), (235, "STARBOARD  +Z")]:
        x = mid+z*1.34
        text(d, (x, 2320), label, 26, PROPOSED, "mm")
    text(d, (mid, 2285), "CENTRAL SPINE", 26, PROPOSED, "mm")
    floor_y = cy
    line(d, [(left+90, floor_y), (right-90, floor_y)], BUILT, 5)
    d.rectangle((mid-31, floor_y-12, mid+31, floor_y+12), fill=BUILT)
    text(d, (mid+102, floor_y+21), "D14 / built bay at center", 28, BUILT)
    text(d, (190, 2700), "About 685 m wide at X≈0; ship maximum 720 m (proposed).", 29, MUTED)
    text(d, (190, 2746), "Opening drawn separately at actual built meter coordinates.", 27, MUTED)

    # X increases LEFT; negative Z is UP. 30 px is exactly one built meter.
    origin_x, origin_y, meters = 2865, 2521, 30
    def local(x, z):
        return (origin_x-(x+6)*meters, origin_y+(z+2.9)*meters)
    bay, hall, room = (f[key]["bounds"] for key in ("bay", "hall", "power_room"))
    def rect(b):
        a, c = local(b["x"][0], b["z"][0]), local(b["x"][1], b["z"][1])
        return (min(a[0], c[0]), min(a[1], c[1]),
                max(a[0], c[0]), max(a[1], c[1]))
    route_fill = "#e2f1e8"
    d.rectangle(rect(bay), fill=route_fill, outline=BUILT, width=4)
    d.rectangle(rect(hall), fill=route_fill, outline=BUILT, width=4)
    d.rectangle(rect(room), fill=route_fill, outline=BUILT, width=4)
    hatch_xy = local(f["hatch"]["xyz"][0], f["hatch"]["xyz"][2])
    hatch_half = 1.2*meters/2
    # Remove the bay and hall outlines at the only bay-to-hall threshold.
    d.rectangle((hatch_xy[0]-4, hatch_xy[1]-hatch_half,
                 hatch_xy[0]+4, hatch_xy[1]+hatch_half), fill=route_fill)
    for jamb_y in (hatch_xy[1]-hatch_half, hatch_xy[1]+hatch_half):
        line(d, [(hatch_xy[0]-7, jamb_y), (hatch_xy[0]+7, jamb_y)], BUILT, 3)
    # The room stops at Z=-1.7 and the hall at Z=-1.5; bridge both wall strokes.
    door_x = local(f["power_door"]["xyz"][0], hall["z"][0])[0]
    room_wall_y = local(0, room["z"][1])[1]
    hall_wall_y = local(0, hall["z"][0])[1]
    door_half = 1.0*meters/2
    d.rectangle((door_x-door_half, room_wall_y-4,
                 door_x+door_half, hall_wall_y+4), fill=route_fill)
    for jamb_x in (door_x-door_half, door_x+door_half):
        line(d, [(jamb_x, room_wall_y-6), (jamb_x, hall_wall_y+6)], BUILT, 3)
    line(d, [local(30, -1.5), local(30, 1.5)], INK, 8)
    # Six decorative side leaves remain solid, with no adjoining walkable space.
    for x in (9, 15, 21):
        for z in (-1.5, 1.5):
            at = local(x, z)
            line(d, [(at[0]-15, at[1]), (at[0]+15, at[1])], INK, 8)
    # A route through the bay, rod, hatch, switch, hall, real door and backup.
    route = [local(f["pod_6"]["xyz"][0], f["pod_6"]["xyz"][2]),
             local(-2.6, 0), local(f["rod"]["xyz"][0], f["rod"]["xyz"][2]),
             local(2.5, 0), hatch_xy,
             local(f["switch"]["xyz"][0], f["switch"]["xyz"][2]),
             local(18, 0), local(27, 0), (door_x, hall_wall_y),
             local(f["backup"]["xyz"][0], f["backup"]["xyz"][2])]
    line(d, route, BUILT, 4)
    for i in range(7):
        pod = f[f"pod_{i}"]
        at = local(pod["xyz"][0], pod["xyz"][2])
        dot(d, at, 17, BUILT if i == 6 else "#8baeb0", BG)
        text(d, at, str(i), 22, BG, "mm")
    for key in ("rod", "switch", "backup"):
        dot(d, local(f[key]["xyz"][0], f[key]["xyz"][2]), 10, BUILT, BG)
    text(d, (origin_x-170, 2605), "7 POD BAY", 27, BUILT, "mm")
    text(d, (1725, 2353), "POWER ROOM", 25, BUILT)
    text(d, (1725, 2386), "LOCAL BACKUP", 24, BUILT)
    text(d, (1285, 2350), "X+  ← aft", 31, PROPOSED)
    text(d, (1285, 2396), "Z-  ↑ port", 31, PROPOSED)
    text(d, (1285, 2455), "30 px = 1 m", 28, MUTED)
    text(d, (1285, 2514), "Green: built", 28, MUTED)
    text(d, (1285, 2552), "opening only", 28, MUTED)
    text(d, (1285, 2630), "X=30 solid endcap", 27, INK)
    text(d, (1285, 2672), "6 solid side leaves", 27, INK)
    text(d, (1550, 2790), "Start: pod 6 → rod → hatch → switch → hall → power door → local backup", 29, BUILT)
    text(d, (1550, 2840), "Power room is above the hall in this orientation; side leaves stay unpierced.", 27, MUTED)

    line(d, [(90, 2900), (3110, 2900)], INK, 4)
    text(d, (95, 2925), "READING KEY", 34)
    for x, color, title, detail in [
        (390, BUILT, "BUILT", "Walkable D14 opening"),
        (1270, PROPOSED, "PROPOSED", "Ship-scale layout"),
        (2220, HAZARD, "HAZARD", "Isolated radiation volumes")]:
        d.rectangle((x, 2942, x+35, 2977), fill=color)
        text(d, (x+53, 2939), title, 30, color)
        text(d, (x+53, 2992), detail, 26, MUTED)
    text(d, (95, 3100), "Source: ship_atlas.json  +  accepted exterior-concept-v2.png", 27, MUTED)
    text(d, (3100, 3100), "DESIGN MAP  /  NOT A GAME DISPLAY", 27, MUTED, "ra")
    canvas.save(OUTPUT, format="PNG", optimize=False)
    print(f"{OUTPUT}  {W}x{H}")


if __name__ == "__main__":
    build()
