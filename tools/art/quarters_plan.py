#!/usr/bin/env python3
"""Render and validate a top-down quarters layout plan."""

import argparse
import json
import math
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ZONE_COLORS = {
    "far wall": (195, 160, 118),
    "left wall": (133, 174, 194),
    "right wall": (160, 166, 193),
    "living": (137, 181, 151),
    "centre": (211, 190, 124),
}
PIXELS_PER_METRE = 300
RASTER_STEP = 0.02


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def floor_standing(prop):
    return prop.get("h_from", 0) < 1.5


def in_parent_relation(a, b):
    return a.get("part_of") == b["id"] or b.get("part_of") == a["id"]


def vertical_overlap(a, b):
    a0, b0 = a.get("h_from", 0), b.get("h_from", 0)
    return not (a0 >= b0 + b["h"] or b0 >= a0 + a["h"])


def door_sector(layout):
    wardrobe = next((p for p in layout["props"] if p["id"] == "wardrobe"), None)
    if not wardrobe or "door" not in wardrobe:
        return None
    door = wardrobe["door"]
    hinge = door["hinge"]
    # Closed, the leaf runs toward -z (270 degrees) and swings toward -x.
    end = 3 * math.pi / 2
    start = end - math.radians(door["open_deg"])
    return hinge, door["width"], start, end


def in_sector(x, z, sector):
    if not sector:
        return False
    (hx, hz), radius, start, end = sector
    dx, dz = x - hx, z - hz
    distance = math.hypot(dx, dz)
    angle = math.atan2(dz, dx)
    while angle < start:
        angle += 2 * math.pi
    return distance <= radius and start <= angle <= end


def reachability(layout):
    room = layout["room"]
    width, depth = room["width_x"], room["depth_z"]
    nx, nz = round(width / RASTER_STEP), round(depth / RASTER_STEP)
    radius = layout["player"]["capsule_radius"]
    sector = door_sector(layout)
    props = [p for p in layout["props"] if floor_standing(p)]
    blocked = [[False] * nz for _ in range(nx)]
    for ix in range(nx):
        x = (ix + 0.5) * RASTER_STEP
        for iz in range(nz):
            z = (iz + 0.5) * RASTER_STEP
            if x < radius or x > width - radius or z < radius or z > depth - radius:
                blocked[ix][iz] = True
                continue
            if any(p["box"][0] - radius <= x <= p["box"][2] + radius and
                   p["box"][1] - radius <= z <= p["box"][3] + radius for p in props):
                blocked[ix][iz] = True
                continue
            if sector:
                (hx, hz), r, start, end = sector
                # Inflate the swept door sector by the capsule radius.
                dx, dz = x - hx, z - hz
                distance = math.hypot(dx, dz)
                angle = math.atan2(dz, dx)
                while angle < start:
                    angle += 2 * math.pi
                if start <= angle <= end and distance <= r + radius:
                    blocked[ix][iz] = True
    start = (int(4.0 / RASTER_STEP), int(0.35 / RASTER_STEP))
    start = (min(nx - 1, start[0]), min(nz - 1, start[1]))
    distances = [[-1] * nz for _ in range(nx)]
    reachable = [[False] * nz for _ in range(nx)]
    if not blocked[start[0]][start[1]]:
        queue = deque([start])
        distances[start[0]][start[1]] = 0
        reachable[start[0]][start[1]] = True
        while queue:
            x, z = queue.popleft()
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, zz = x + dx, z + dz
                if 0 <= xx < nx and 0 <= zz < nz and not blocked[xx][zz] and distances[xx][zz] < 0:
                    distances[xx][zz] = distances[x][z] + 1
                    reachable[xx][zz] = True
                    queue.append((xx, zz))
    target_results = []
    for target in layout["reach_targets"]:
        x, z = target["point"]
        ix, iz = min(nx - 1, int(x / RASTER_STEP)), min(nz - 1, int(z / RASTER_STEP))
        ok = reachable[ix][iz]
        target_results.append({"id": target["id"], "point": target["point"], "reachable": ok,
                               "path_length_m": round(distances[ix][iz] * RASTER_STEP, 3) if ok else None})
    bed_target = next((r for r in target_results if r["id"] == "bed_foot"), None)
    narrowest = None
    if bed_target and bed_target["reachable"]:
        # Measure local free width along the shortest-path tree to bed_foot.
        goal = (int(layout["reach_targets"][0]["point"][0] / RASTER_STEP),
                int(layout["reach_targets"][0]["point"][1] / RASTER_STEP))
        path = [goal]
        while path[-1] != start:
            x, z = path[-1]
            candidates = [(distances[xx][zz], (xx, zz)) for xx, zz in
                          ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1))
                          if 0 <= xx < nx and 0 <= zz < nz and distances[xx][zz] >= 0 and distances[xx][zz] < distances[x][z]]
            if not candidates:
                break
            path.append(min(candidates)[1])
        # Clearance is twice the nearest obstacle/wall distance, sampled on route.
        clearances = []
        for x, z in path:
            nearest = radius
            for xx in range(max(0, x - 80), min(nx, x + 81)):
                for zz in range(max(0, z - 80), min(nz, z + 81)):
                    if blocked[xx][zz]:
                        nearest = min(nearest, math.hypot(xx - x, zz - z) * RASTER_STEP)
            clearances.append(2 * nearest)
        narrowest = round(min(clearances), 3) if clearances else None
    return reachable, {"targets": target_results, "narrowest_clearance_m": narrowest, "grid_m": RASTER_STEP}


def checks(layout, reach_info):
    room, props = layout["room"], layout["props"]
    width, depth = room["width_x"], room["depth_z"]
    tolerance = 0.001
    outside = []
    overlaps_found = []
    for p in props:
        x0, z0, x1, z1 = p["box"]
        violation = max(0, -x0, -z0, x1 - width, z1 - depth)
        if violation > tolerance:
            outside.append({"id": p["id"], "max_outside_m": round(violation, 4)})
    standing = [p for p in props if floor_standing(p)]
    for i, a in enumerate(standing):
        for b in standing[i + 1:]:
            if overlaps(a["box"], b["box"]) and not in_parent_relation(a, b) and vertical_overlap(a, b):
                overlaps_found.append({"a": a["id"], "b": b["id"]})
    storage = [{"id": p["id"], "z0": p["box"][1]} for p in props
               if ("storage" in p.get("zone", "").lower() or "storage" in p["id"].lower()) and p["box"][1] < 0.2]
    door = layout["door"]
    door_blockers = [p["id"] for p in standing if overlaps(p["box"], [door["x0"], 0, door["x1"], 1.0])]
    targets_ok = all(t["reachable"] for t in reach_info["targets"])
    return [
        {"name": "footprints_inside_room", "pass": not outside, "measured": outside,
         "threshold": {"outside_tolerance_m": tolerance}, "detail": "Every footprint must remain within the interior bounds."},
        {"name": "floor_footprint_overlaps", "pass": not overlaps_found, "measured": overlaps_found,
         "threshold": "No intersecting floor-standing footprints except parent parts or vertically stacked props.", "detail": "Each reported pair has intersecting footprints and overlapping height ranges."},
        {"name": "player_reachability", "pass": targets_ok, "measured": reach_info,
         "threshold": "All reach_targets reachable on a 0.02 m grid with capsule inflation.", "detail": "Flood fill starts at the door centre, z=0.35 m."},
        {"name": "no_entrance_storage", "pass": not storage, "measured": storage,
         "threshold": "Storage prop z0 >= 0.2 m.", "detail": "Storage is identified by its id or zone containing 'storage'."},
        {"name": "door_opening_clear", "pass": not door_blockers, "measured": door_blockers,
         "threshold": "No floor-standing footprint in the opening for the first 1.0 m.", "detail": "The sliding opening spans the specified x interval."},
    ]


def render(layout, reachable, output):
    room, door = layout["room"], layout["door"]
    s, margin = PIXELS_PER_METRE, 180
    width, depth = room["width_x"], room["depth_z"]
    wall = room["wall_thickness"]
    image = Image.new("RGB", (round((width + 2 * wall) * s + margin * 2), round((depth + 2 * wall) * s + margin * 2)), (250, 249, 245))
    draw = ImageDraw.Draw(image)
    def pt(x, z):
        return (round(margin + (x + wall) * s), round(margin + (depth + wall - z) * s))
    def rect(box):
        x0, z0, x1, z1 = box
        return (pt(x0, z1)[0], pt(x0, z1)[1], pt(x1, z0)[0], pt(x1, z0)[1])
    # Reachable tint underneath all plan symbols.
    for ix, col in enumerate(reachable):
        for iz, value in enumerate(col):
            if value:
                x0, z0 = pt(ix * RASTER_STEP, (iz + 1) * RASTER_STEP)
                x1, z1 = pt((ix + 1) * RASTER_STEP, iz * RASTER_STEP)
                draw.rectangle((x0, z0, x1, z1), fill=(234, 245, 231))
    # Half-metre grid, with metre lines slightly stronger.
    for i in range(round(width * 2) + 1):
        x = i * 0.5
        a, b = pt(x, 0), pt(x, depth)
        color, line = ((215, 218, 214), 2) if i % 2 == 0 else ((233, 234, 231), 1)
        draw.line((a, b), fill=color, width=line)
    for i in range(round(depth * 2) + 1):
        z = i * 0.5
        draw.line((*pt(0, z), *pt(width, z)), fill=((215, 218, 214) if i % 2 == 0 else (233, 234, 231)), width=2 if i % 2 == 0 else 1)
    # Walls surround the interior; leave the entrance aperture open.
    x0, z0, x1, z1 = -wall, -wall, width + wall, depth + wall
    def world_rect(x0, z0, x1, z1, fill):
        draw.rectangle((pt(x0, z1), pt(x1, z0)), fill=fill, outline=(48, 57, 61), width=3)
    world_rect(x0, -wall, door["x0"], 0, (75, 83, 88))
    world_rect(door["x1"], -wall, x1, 0, (75, 83, 88))
    world_rect(-wall, 0, 0, depth, (75, 83, 88))
    world_rect(width, 0, width + wall, depth, (75, 83, 88))
    world_rect(-wall, depth, width + wall, depth + wall, (75, 83, 88))
    small = font(15)
    draw.text(pt((door["x0"] + door["x1"]) / 2, -0.34), "DOOR", fill=(37, 44, 47), font=font(20), anchor="mm")
    # Props and faces.
    label_font = font(15)
    for prop in layout["props"]:
        box = prop["box"]
        color = ZONE_COLORS.get(prop.get("zone"), (177, 175, 163))
        outline = tuple(max(0, c - 65) for c in color)
        bounds = rect(box)
        if prop.get("h_from", 0) >= 1.5:
            x0, y0, x1, y1 = bounds
            dash = 12
            for x in range(x0, x1, dash * 2):
                draw.line((x, y0, min(x + dash, x1), y0), fill=outline, width=3)
                draw.line((x, y1, min(x + dash, x1), y1), fill=outline, width=3)
            for y in range(y0, y1, dash * 2):
                draw.line((x0, y, x0, min(y + dash, y1)), fill=outline, width=3)
                draw.line((x1, y, x1, min(y + dash, y1)), fill=outline, width=3)
        else:
            if prop.get("shape") == "round":
                draw.ellipse(bounds, fill=color, outline=outline, width=3)
            else:
                draw.rectangle(bounds, fill=color, outline=outline, width=3)
        cx, cz = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        draw.text(pt(cx, cz), prop["id"], fill=(31, 38, 40), font=label_font, anchor="mm")
        face = prop.get("faces")
        if face:
            vectors = {"-x": (-0.22, 0), "+x": (0.22, 0), "-z": (0, -0.22), "+z": (0, 0.22)}
            dx, dz = vectors[face]
            start, end = pt(cx, cz), pt(cx + dx, cz + dz)
            draw.line((*start, *end), fill=(35, 45, 48), width=3)
            angle = math.atan2(end[1] - start[1], end[0] - start[0])
            for offset in (-2.5, 2.5):
                draw.line((*end, end[0] - 9 * math.cos(angle + offset), end[1] - 9 * math.sin(angle + offset)), fill=(35, 45, 48), width=2)
    sector = door_sector(layout)
    if sector:
        (hx, hz), r, start, end = sector
        center = pt(hx, hz)
        bbox = (center[0] - r * s, center[1] - r * s, center[0] + r * s, center[1] + r * s)
        draw.arc(bbox, start=math.degrees(-end), end=math.degrees(-start), fill=(157, 76, 61), width=4)
        endpoint = (hx + r * math.cos(end), hz + r * math.sin(end))
        draw.line((*center, *pt(*endpoint)), fill=(157, 76, 61), width=5)
    # Camera rays at the floor projection of the doorway camera.
    camera = layout["camera"]
    cx, cz = camera["position"][0], camera["position"][2]
    yaw = math.atan2(camera["look_at"][0] - cx, camera["look_at"][2] - cz)
    half = math.radians(camera["horizontal_fov_deg"]) / 2
    for direction in (yaw - half, yaw + half):
        draw.line((*pt(cx, cz), *pt(cx + 8 * math.sin(direction), cz + 8 * math.cos(direction))), fill=(90, 111, 150), width=2)
    draw.ellipse((pt(cx, cz)[0] - 7, pt(cx, cz)[1] - 7, pt(cx, cz)[0] + 7, pt(cx, cz)[1] + 7), fill=(64, 86, 132))
    # Scale bar and metre labels.
    for i in range(9):
        x = i
        draw.text(pt(x, -0.62), str(x), fill=(55, 61, 64), font=small, anchor="mm")
    scale_y = -0.88
    draw.line((*pt(0, scale_y), *pt(1, scale_y)), fill=(35, 41, 43), width=6)
    draw.line((*pt(0, scale_y - 0.05), *pt(0, scale_y + 0.05)), fill=(35, 41, 43), width=3)
    draw.line((*pt(1, scale_y - 0.05), *pt(1, scale_y + 0.05)), fill=(35, 41, 43), width=3)
    draw.text(pt(0.5, scale_y - 0.12), "1 m", fill=(35, 41, 43), font=small, anchor="mm")
    # Zone legend.
    lx, ly = margin + 20, image.height - 115
    draw.rounded_rectangle((lx - 10, ly - 12, lx + 740, ly + 92), radius=8, fill=(255, 255, 252), outline=(180, 184, 179), width=2)
    for index, (zone, color) in enumerate(ZONE_COLORS.items()):
        x = lx + index * 145
        draw.rectangle((x, ly, x + 20, ly + 20), fill=color, outline=tuple(max(0, c - 65) for c in color))
        draw.text((x + 27, ly + 2), zone, fill=(40, 46, 48), font=small)
    image.save(output, format="PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    layout = json.loads(Path(args.layout).read_text())
    reachable, reach_info = reachability(layout)
    results = checks(layout, reach_info)
    render(layout, reachable, args.out)
    report = {"checks": results}
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n")
    for result in results:
        print(f"{'PASS' if result['pass'] else 'FAIL'} {result['name']}: {result['measured']}")
    return 0 if all(result["pass"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
