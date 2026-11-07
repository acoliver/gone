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


def door_geometry(layout):
    wardrobe = next((p for p in layout["props"] if p["id"] == "wardrobe"), None)
    if not wardrobe or "door" not in wardrobe:
        return None
    door = wardrobe["door"]
    hinge = door["hinge"]
    vectors = {"-x": (-1, 0), "+x": (1, 0), "-z": (0, -1), "+z": (0, 1)}
    dx, dz = vectors[door.get("closed_toward", "-z")]
    angle = -math.radians(door["open_deg"])
    opened = (dx * math.cos(angle) - dz * math.sin(angle),
              dx * math.sin(angle) + dz * math.cos(angle))
    start, end = math.atan2(dz, dx), math.atan2(opened[1], opened[0])
    if door.get("parked"):
        return {"hinge": hinge, "radius": door["width"], "start": start,
                "end": start - math.radians(door["open_deg"]), "parked": True,
                "leaf_end": (hinge[0] + opened[0] * door["width"],
                             hinge[1] + opened[1] * door["width"])}
    while end > start:
        end -= 2 * math.pi
    return {"hinge": hinge, "radius": door["width"], "start": end, "end": start,
            "parked": False}


def point_segment_distance(x, z, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dz * dz
    t = max(0, min(1, ((x - a[0]) * dx + (z - a[1]) * dz) / length2))
    return math.hypot(x - (a[0] + t * dx), z - (a[1] + t * dz))


def distance_transform(free):
    """Euclidean distance to blocked floor cells, in metres."""
    nx, nz = len(free), len(free[0])
    inf = nx * nx + nz * nz

    def transform(values):
        sites = [i for i, value in enumerate(values) if value < inf]
        if not sites:
            return [inf] * len(values)
        vertices, boundaries = [0] * len(sites), [0.0] * (len(sites) + 1)
        k = 0
        vertices[0], boundaries[0], boundaries[1] = sites[0], -float("inf"), float("inf")
        for q in sites[1:]:
            while True:
                v = vertices[k]
                crossing = ((values[q] + q * q) - (values[v] + v * v)) / (2 * (q - v))
                if crossing > boundaries[k]:
                    break
                k -= 1
            k += 1
            vertices[k], boundaries[k], boundaries[k + 1] = q, crossing, float("inf")
        result, k = [0] * len(values), 0
        for q in range(len(values)):
            while boundaries[k + 1] < q:
                k += 1
            delta = q - vertices[k]
            result[q] = delta * delta + values[vertices[k]]
        return result

    rows = [[0 if not free[x][z] else inf for z in range(nz)] for x in range(nx)]
    vertical = [transform(rows[x]) for x in range(nx)]
    result = [[0] * nz for _ in range(nx)]
    for z in range(nz):
        column = transform([vertical[x][z] for x in range(nx)])
        for x in range(nx):
            result[x][z] = math.sqrt(column[x]) * RASTER_STEP
    return result




def reachability(layout):
    room = layout["room"]
    width, depth = room["width_x"], room["depth_z"]
    nx, nz = round(width / RASTER_STEP), round(depth / RASTER_STEP)
    radius = layout["player"]["capsule_radius"]
    door = door_geometry(layout)
    props = [p for p in layout["props"] if floor_standing(p)]
    blocked = [[False] * nz for _ in range(nx)]
    raw_blocked = [[False] * nz for _ in range(nx)]
    entrance = layout["door"]
    for ix in range(nx):
        x = (ix + 0.5) * RASTER_STEP
        for iz in range(nz):
            z = (iz + 0.5) * RASTER_STEP
            if (x <= RASTER_STEP / 2 or x >= width - RASTER_STEP / 2 or
                    z >= depth - RASTER_STEP / 2 or
                    (z <= RASTER_STEP / 2 and not entrance["x0"] <= x <= entrance["x1"])):
                raw_blocked[ix][iz] = True
            if any(p["box"][0] <= x <= p["box"][2] and p["box"][1] <= z <= p["box"][3] for p in props):
                raw_blocked[ix][iz] = True
            if door and door["parked"] and point_segment_distance(x, z, door["hinge"], door["leaf_end"]) <= 0.02:
                raw_blocked[ix][iz] = True
            elif door:
                hx, hz = door["hinge"]
                dx, dz = x - hx, z - hz
                angle = math.atan2(dz, dx)
                while angle < door["start"]:
                    angle += 2 * math.pi
                if door["start"] <= angle <= door["end"] and math.hypot(dx, dz) <= door["radius"]:
                    raw_blocked[ix][iz] = True
            if x < radius or x > width - radius or z < radius or z > depth - radius:
                blocked[ix][iz] = True
                continue
            if any(p["box"][0] - radius <= x <= p["box"][2] + radius and
                   p["box"][1] - radius <= z <= p["box"][3] + radius for p in props):
                blocked[ix][iz] = True
                continue
            if door and door["parked"]:
                if point_segment_distance(x, z, door["hinge"], door["leaf_end"]) <= radius + 0.02:
                    blocked[ix][iz] = True
            elif door:
                hx, hz = door["hinge"]
                dx, dz = x - hx, z - hz
                angle = math.atan2(dz, dx)
                while angle < door["start"]:
                    angle += 2 * math.pi
                if door["start"] <= angle <= door["end"] and math.hypot(dx, dz) <= door["radius"] + radius:
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
    free = [[not raw_blocked[ix][iz] for iz in range(nz)] for ix in range(nx)]
    clearance = distance_transform(free)
    target_results = []
    pinch_points = []
    for target in layout["reach_targets"]:
        x, z = target["point"]
        ix, iz = min(nx - 1, int(x / RASTER_STEP)), min(nz - 1, int(z / RASTER_STEP))
        ok = reachable[ix][iz]
        path = [(ix, iz)] if ok else []
        while path and path[-1] != start:
            px, pz = path[-1]
            candidates = [(distances[xx][zz], (xx, zz)) for xx, zz in
                          ((px + 1, pz), (px - 1, pz), (px, pz + 1), (px, pz - 1))
                          if 0 <= xx < nx and 0 <= zz < nz and 0 <= distances[xx][zz] < distances[px][pz]]
            if not candidates:
                break
            path.append(min(candidates)[1])
        minimum = min((2 * clearance[px][pz] for px, pz in path), default=None)
        pinch = min(path, key=lambda point: clearance[point[0]][point[1]]) if path else None
        target_results.append({"id": target["id"], "point": target["point"], "reachable": ok,
                               "path_length_m": round(distances[ix][iz] * RASTER_STEP, 3) if ok else None,
                               "minimum_corridor_width_m": round(minimum, 3) if minimum is not None else None})
        if pinch:
            px, pz = (pinch[0] + 0.5) * RASTER_STEP, (pinch[1] + 0.5) * RASTER_STEP
            nearby = []
            for prop in props:
                x0, z0, x1, z1 = prop["box"]
                qx, qz = min(max(px, x0), x1), min(max(pz, z0), z1)
                dx, dz = qx - px, qz - pz
                distance = math.hypot(dx, dz)
                if distance:
                    nearby.append((distance, dx / distance, dz / distance, prop["id"]))
            if door and door["parked"]:
                distance = max(0, point_segment_distance(px, pz, door["hinge"], door["leaf_end"]) - 0.02)
                nearby.append((distance, 0, 0, "wardrobe_door"))
            walls = [(px, "left_wall", -1, 0), (width - px, "right_wall", 1, 0),
                     (pz, "entrance_wall", 0, -1), (depth - pz, "far_wall", 0, 1)]
            nearby.extend((distance, dx, dz, name) for distance, name, dx, dz in walls)
            nearest = min(nearby)
            opposing = [entry for entry in nearby if entry[3] != nearest[3] and nearest[1] * entry[1] + nearest[2] * entry[2] < -0.5]
            pair = [nearest[3], min(opposing)[3] if opposing else min((entry for entry in nearby if entry[3] != nearest[3]), default=nearest)[3]]
            pinch_points.append({"target": target["id"], "point": [round(px, 3), round(pz, 3)],
                                 "width_m": round(minimum, 3), "bounded_by": pair})
    return reachable, {"targets": target_results, "pinch_points": pinch_points, "grid_m": RASTER_STEP}


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
    walkway_min = layout["walkway_min_m"]
    narrow_walkways = [point for point in reach_info["pinch_points"] if point["width_m"] < walkway_min]
    return [
        {"name": "footprints_inside_room", "pass": not outside, "measured": outside,
         "threshold": {"outside_tolerance_m": tolerance}, "detail": "Every footprint must remain within the interior bounds."},
        {"name": "floor_footprint_overlaps", "pass": not overlaps_found, "measured": overlaps_found,
         "threshold": "No intersecting floor-standing footprints except parent parts or vertically stacked props.", "detail": "Each reported pair has intersecting footprints and overlapping height ranges."},
        {"name": "player_reachability", "pass": targets_ok, "measured": reach_info,
         "threshold": "All reach_targets reachable on a 0.02 m grid with capsule inflation.", "detail": "Flood fill starts at the door centre, z=0.35 m."},
        {"name": "walkway_widths", "pass": not narrow_walkways, "measured": narrow_walkways,
         "threshold": {"minimum_width_m": walkway_min}, "detail": "Minimum free-floor width sampled along each target's shortest path."},
        {"name": "no_entrance_storage", "pass": not storage, "measured": storage,
         "threshold": "Storage prop z0 >= 0.2 m.", "detail": "Storage is identified by its id or zone containing 'storage'."},
        {"name": "door_opening_clear", "pass": not door_blockers, "measured": door_blockers,
         "threshold": "No floor-standing footprint in the opening for the first 1.0 m.", "detail": "The sliding opening spans the specified x interval."},
    ]


def render(layout, reachable, reach_info, output):
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
    door_shape = door_geometry(layout)
    if door_shape:
        (hx, hz), r = door_shape["hinge"], door_shape["radius"]
        start, end = door_shape["start"], door_shape["end"]
        if door_shape["parked"]:
            leaf_end = door_shape["leaf_end"]
            dx, dz = leaf_end[0] - hx, leaf_end[1] - hz
            length = math.hypot(dx, dz)
            nx, nz = -dz / length * 0.02, dx / length * 0.02
            polygon = [pt(hx + nx, hz + nz), pt(leaf_end[0] + nx, leaf_end[1] + nz),
                       pt(leaf_end[0] - nx, leaf_end[1] - nz), pt(hx - nx, hz - nz)]
            draw.polygon(polygon, fill=(157, 76, 61), outline=(105, 47, 40))
        steps = max(1, round(abs(end - start) * r * s / 12))
        for index in range(0, steps, 2):
            a0 = start + (end - start) * index / steps
            a1 = start + (end - start) * min(index + 1, steps) / steps
            draw.line((*pt(hx + r * math.cos(a0), hz + r * math.sin(a0)),
                       *pt(hx + r * math.cos(a1), hz + r * math.sin(a1))), fill=(157, 76, 61), width=3)
    for pinch in reach_info["pinch_points"]:
        px, pz = pt(*pinch["point"])
        draw.ellipse((px - 9, pz - 9, px + 9, pz + 9), fill=(215, 55, 45), outline=(255, 255, 255), width=3)
        draw.line((px - 13, pz, px + 13, pz), fill=(255, 255, 255), width=2)
        draw.line((px, pz - 13, px, pz + 13), fill=(255, 255, 255), width=2)
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
    render(layout, reachable, reach_info, args.out)
    report = {"checks": results}
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n")
    for result in results:
        print(f"{'PASS' if result['pass'] else 'FAIL'} {result['name']}: {result['measured']}")
    return 0 if all(result["pass"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
