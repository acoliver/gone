#!/usr/bin/env python3
"""Render and validate a top-down quarters layout plan."""

import argparse
import heapq
import json
import math
from collections import deque
from pathlib import Path



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
        from PIL import ImageFont
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




def widest_path(free, clearance, start, target, target_point):
    """Return the maximin path, ignoring the final 0.35 m at the target."""
    nx, nz = len(free), len(free[0])
    capacity = [[-1.0] * nz for _ in range(nx)]
    previous = {}
    start_x, start_z = (start[0] + 0.5) * RASTER_STEP, (start[1] + 0.5) * RASTER_STEP
    start_capacity = (float("inf") if math.hypot(start_x - target_point[0], start_z - target_point[1]) <= 0.35
                      else 2 * clearance[start[0]][start[1]])
    capacity[start[0]][start[1]] = start_capacity
    queue = [(-start_capacity, start)]
    while queue:
        negative, (x, z) = heapq.heappop(queue)
        score = -negative
        if score < capacity[x][z]:
            continue
        if (x, z) == target:
            break
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            xx, zz = x + dx, z + dz
            if not (0 <= xx < nx and 0 <= zz < nz and free[xx][zz]):
                continue
            wx, wz = (xx + 0.5) * RASTER_STEP, (zz + 0.5) * RASTER_STEP
            cell_capacity = (float("inf") if math.hypot(wx - target_point[0], wz - target_point[1]) <= 0.35
                             else 2 * clearance[xx][zz])
            candidate = min(score, cell_capacity)
            if candidate > capacity[xx][zz]:
                capacity[xx][zz] = candidate
                previous[(xx, zz)] = (x, z)
                heapq.heappush(queue, (-candidate, (xx, zz)))
    if capacity[target[0]][target[1]] < 0:
        return [], None
    path = [target]
    while path[-1] != start:
        path.append(previous[path[-1]])
    path.reverse()
    measured = [(point, 2 * clearance[point[0]][point[1]]) for point in path
                if math.hypot((point[0] + 0.5) * RASTER_STEP - target_point[0],
                              (point[1] + 0.5) * RASTER_STEP - target_point[1]) > 0.35]
    bottleneck = min(measured, key=lambda item: item[1]) if measured else (path[-1], None)
    return path, bottleneck


def self_test():
    size = round(4 / RASTER_STEP)
    free = [[True] * size for _ in range(size)]
    for i in range(size):
        free[0][i] = free[-1][i] = False
        free[i][0] = free[i][-1] = False
    for ix in range(round(0.5 / RASTER_STEP), round(3.5 / RASTER_STEP)):
        free[ix][0] = True
    for ix in range(round(1.5 / RASTER_STEP), round(2.5 / RASTER_STEP)):
        for iz in range(round(1.5 / RASTER_STEP), round(2.5 / RASTER_STEP)):
            free[ix][iz] = False
    clearance = distance_transform(free)
    _, bottleneck = widest_path(free, clearance, (size // 2, 5),
                                (size // 2, round(3.5 / RASTER_STEP)), (2.0, 3.5))
    width = bottleneck[1]
    passed = abs(width - 1.5) <= 0.05
    print(f"{'PASS' if passed else 'FAIL'} self-test: bottleneck_width_m={width:.3f}, expected=1.500±0.050")
    return passed


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
    widest_paths = []
    bottleneck_points = []
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
        widest, bottleneck = widest_path(free, clearance, start, (ix, iz), (x, z)) if ok else ([], None)
        minimum = bottleneck[1] if bottleneck else None
        target_results.append({"id": target["id"], "point": target["point"], "reachable": ok,
                               "path_length_m": round(distances[ix][iz] * RASTER_STEP, 3) if ok else None,
                               "widest_path_bottleneck_width_m": round(minimum, 3) if minimum is not None else None})
        if bottleneck:
            (bx, bz), _ = bottleneck
            px, pz = (bx + 0.5) * RASTER_STEP, (bz + 0.5) * RASTER_STEP
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
            bottleneck_points.append({"target": target["id"], "point": [round(px, 3), round(pz, 3)],
                                      "width_m": round(minimum, 3), "bounded_by": pair})
            sampled_path = widest[::10]
            if sampled_path[-1] != widest[-1]:
                sampled_path.append(widest[-1])
            widest_paths.append({"target": target["id"], "points": [[round((a + 0.5) * RASTER_STEP, 3),
                                                                         round((b + 0.5) * RASTER_STEP, 3)]
                                                                        for a, b in sampled_path]})
    return reachable, {"targets": target_results, "bottleneck_points": bottleneck_points,
                       "widest_paths": widest_paths, "grid_m": RASTER_STEP}


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
    narrow_walkways = [point for point in reach_info["bottleneck_points"] if point["width_m"] < walkway_min]
    return [
        {"name": "footprints_inside_room", "pass": not outside, "measured": outside,
         "threshold": {"outside_tolerance_m": tolerance}, "detail": "Every footprint must remain within the interior bounds."},
        {"name": "floor_footprint_overlaps", "pass": not overlaps_found, "measured": overlaps_found,
         "threshold": "No intersecting floor-standing footprints except parent parts or vertically stacked props.", "detail": "Each reported pair has intersecting footprints and overlapping height ranges."},
        {"name": "player_reachability", "pass": targets_ok,
         "measured": {key: value for key, value in reach_info.items() if key != "widest_paths"},
         "threshold": "All reach_targets reachable on a 0.02 m grid with capsule inflation.", "detail": "Flood fill starts at the door centre, z=0.35 m."},
        {"name": "walkway_widths", "pass": not narrow_walkways, "measured": narrow_walkways,
         "threshold": {"minimum_width_m": walkway_min}, "detail": "Widest-path bottleneck width from the uninflated obstacle map, excluding the final 0.35 m at each target."},
        {"name": "no_entrance_storage", "pass": not storage, "measured": storage,
         "threshold": "Storage prop z0 >= 0.2 m.", "detail": "Storage is identified by its id or zone containing 'storage'."},
        {"name": "door_opening_clear", "pass": not door_blockers, "measured": door_blockers,
         "threshold": "No floor-standing footprint in the opening for the first 1.0 m.", "detail": "The sliding opening spans the specified x interval."},
    ]


def render(layout, reachable, reach_info, output):
    from PIL import Image, ImageDraw
    room, door = layout["room"], layout["door"]
    s, margin, top, footer = PIXELS_PER_METRE, 210, 150, 620
    width, depth = room["width_x"], room["depth_z"]
    wall = room["wall_thickness"]
    image = Image.new("RGB", (round((width + 2 * wall) * s + margin * 2),
                               round((depth + 2 * wall) * s + margin * 2 + top + footer)), (250, 249, 245))
    draw = ImageDraw.Draw(image)

    def pt(x, z):
        return round(margin + (x + wall) * s), round(top + margin + (depth + wall - z) * s)

    def rect(box):
        x0, z0, x1, z1 = box
        return (*pt(x0, z1), *pt(x1, z0))

    for ix, col in enumerate(reachable):
        for iz, value in enumerate(col):
            if value:
                draw.rectangle((*pt(ix * RASTER_STEP, (iz + 1) * RASTER_STEP),
                                *pt((ix + 1) * RASTER_STEP, iz * RASTER_STEP)), fill=(234, 245, 231))
    for i in range(round(width * 2) + 1):
        x = i * 0.5
        draw.line((*pt(x, 0), *pt(x, depth)), fill=(215, 218, 214) if i % 2 == 0 else (233, 234, 231),
                  width=2 if i % 2 == 0 else 1)
    for i in range(round(depth * 2) + 1):
        z = i * 0.5
        draw.line((*pt(0, z), *pt(width, z)), fill=(215, 218, 214) if i % 2 == 0 else (233, 234, 231),
                  width=2 if i % 2 == 0 else 1)

    def world_rect(x0, z0, x1, z1, fill):
        draw.rectangle((*pt(x0, z1), *pt(x1, z0)), fill=fill, outline=(48, 57, 61), width=3)

    world_rect(-wall, -wall, door["x0"], 0, (75, 83, 88))
    world_rect(door["x1"], -wall, width + wall, 0, (75, 83, 88))
    world_rect(-wall, 0, 0, depth, (75, 83, 88))
    world_rect(width, 0, width + wall, depth, (75, 83, 88))
    world_rect(-wall, depth, width + wall, depth + wall, (75, 83, 88))
    labels = {"bed": "Double bed", "bedside_l": "Bedside", "bedside_r": "Bedside",
              "headboard": "Double bed", "lockers_over_bed": "Lockers above bed",
              "wardrobe_door": "Wardrobe door (open)",
              "storage_far_l": "Storage", "storage_far_r": "Storage", "storage_left_near": "Storage",
              "storage_left_far": "Storage", "storage_right_near": "Storage", "storage_right_far": "Storage",
              "view_screen": "View screen (wall)", "media_cabinet": "Media cabinet", "sofa": "Sofa",
              "dining_table": "Table", "dining_chair_1": "Chair", "dining_chair_2": "Chair",
              "desk": "Desk", "console": "Console", "desk_chair": "Desk chair", "wardrobe": "Wardrobe"}
    title_font, label_font = font(40), font(36)
    draw.text((margin, 25), "Protagonist's quarters, plan view (8.0 x 6.0 m, 3.2 m ceiling). Entrance at bottom.",
              fill=(31, 38, 40), font=title_font)
    narrowest = min((item["widest_path_bottleneck_width_m"], item["id"]) for item in reach_info["targets"]
                    if item["widest_path_bottleneck_width_m"] is not None)
    draw.text((margin, 80), f"Narrowest walkway {narrowest[0]:.2f} m (to the {narrowest[1]})",
              fill=(67, 75, 77), font=font(30))

    prop_pixels = {prop["id"]: rect(prop["box"]) for prop in layout["props"]}
    door_shape = door_geometry(layout)
    label_props = list(layout["props"])
    if door_shape and door_shape["parked"]:
        hx, hz = door_shape["hinge"]
        ex, ez = door_shape["leaf_end"]
        label_props.append({"id": "wardrobe_door", "box": [min(hx, ex), min(hz, ez), max(hx, ex), max(hz, ez)]})
        prop_pixels["wardrobe_door"] = rect(label_props[-1]["box"])
    for prop in layout["props"]:
        box = prop["box"]
        color = ZONE_COLORS.get(prop.get("zone"), (177, 175, 163))
        outline = tuple(max(0, c - 65) for c in color)
        bounds = prop_pixels[prop["id"]]
        if prop.get("h_from", 0) >= 1.5:
            x0, y0, x1, y1 = bounds
            for x in range(x0, x1, 24):
                draw.line((x, y0, min(x + 12, x1), y0), fill=outline, width=3)
                draw.line((x, y1, min(x + 12, x1), y1), fill=outline, width=3)
            for y in range(y0, y1, 24):
                draw.line((x0, y, x0, min(y + 12, y1)), fill=outline, width=3)
                draw.line((x1, y, x1, min(y + 12, y1)), fill=outline, width=3)
        elif prop.get("shape") == "round":
            draw.ellipse(bounds, fill=color, outline=outline, width=3)
        else:
            draw.rectangle(bounds, fill=color, outline=outline, width=3)
        cx, cz = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        face = prop.get("faces")
        if face:
            dx, dz = {"-x": (-0.22, 0), "+x": (0.22, 0), "-z": (0, -0.22), "+z": (0, 0.22)}[face]
            start, end = pt(cx, cz), pt(cx + dx, cz + dz)
            draw.line((*start, *end), fill=(35, 45, 48), width=3)

    occupied = []
    label_bounds = []
    for prop in label_props:
        name = labels[prop["id"]]
        box = prop_pixels[prop["id"]]
        bbox = draw.textbbox((0, 0), name, font=label_font, stroke_width=5)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        assert th >= 28, f"Label font is too small for {prop['id']}: {th}px"
        x0, y0, x1, y1 = box
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        candidates = []
        if x1 - x0 >= tw + 16 and y1 - y0 >= th + 16:
            candidates.append((cx, cy, True))
        for d in range(8, 601, 24):
            for offset in (0, -80, 80, -160, 160, -240, 240):
                candidates.extend(((cx + offset, y0 - d - th / 2, False),
                                   (cx + offset, y1 + d + th / 2, False),
                                   (x0 - d - tw / 2, cy + offset, False),
                                   (x1 + d + tw / 2, cy + offset, False)))
        chosen = None
        for lx, ly, inside in candidates:
            bound = (round(lx - tw / 2 - 5), round(ly - th / 2 - 5),
                     round(lx + tw / 2 + 5), round(ly + th / 2 + 5))
            if not inside and not (margin < bound[0] and bound[2] < margin + width * s and
                                   top + margin < bound[1] and bound[3] < top + margin + depth * s):
                continue
            if any(overlaps(bound, other) for other in occupied):
                continue
            if not inside:
                if abs(ly - cy) > abs(lx - cx):
                    anchor = (min(max(lx, x0), x1), y0 if ly < y0 else y1)
                else:
                    anchor = (x0 if lx < x0 else x1, min(max(ly, y0), y1))
                blocked = False
                for step_index in range(1, 10):
                    t = step_index / 10
                    sx, sy = anchor[0] + (lx - anchor[0]) * t, anchor[1] + (ly - anchor[1]) * t
                    if any(other_id != prop["id"] and
                           not (prop["id"] == "view_screen" and other_id == "media_cabinet") and
                           other[0] <= sx <= other[2] and other[1] <= sy <= other[3]
                           for other_id, other in prop_pixels.items()):
                        blocked = True
                        break
                    if any(other[0] <= sx <= other[2] and other[1] <= sy <= other[3] for other in occupied):
                        blocked = True
                        break
                if blocked:
                    continue
            chosen = lx, ly, bound, inside
            break
        assert chosen is not None, f"No clear label location for {prop['id']} ({name})"
        lx, ly, bound, inside = chosen
        if not inside:
            if abs(ly - cy) > abs(lx - cx):
                anchor = (min(max(lx, x0), x1), y0 if ly < y0 else y1)
            else:
                anchor = (x0 if lx < x0 else x1, min(max(ly, y0), y1))
            draw.line((*anchor, lx, ly), fill=(55, 63, 65), width=2)
        draw.text((lx, ly), name, fill=(31, 38, 40), font=label_font, anchor="mm",
                  stroke_width=5, stroke_fill=(255, 255, 252))
        occupied.append(bound)
        label_bounds.append((prop["id"], bound))
    assert all(not overlaps(a[1], b[1]) for i, a in enumerate(label_bounds) for b in label_bounds[i + 1:]), \
        "Object label bounding boxes overlap"

    door_shape = door_geometry(layout)
    if door_shape:
        (hx, hz), r = door_shape["hinge"], door_shape["radius"]
        if door_shape["parked"]:
            ex, ez = door_shape["leaf_end"]
            dx, dz = ex - hx, ez - hz
            length = math.hypot(dx, dz)
            nx, nz = -dz / length * 0.02, dx / length * 0.02
            draw.polygon([pt(hx + nx, hz + nz), pt(ex + nx, ez + nz), pt(ex - nx, ez - nz), pt(hx - nx, hz - nz)],
                         fill=(157, 76, 61), outline=(105, 47, 40))
        for i in range(max(1, round(abs(door_shape["end"] - door_shape["start"]) * r * s / 12))):
            if i % 2:
                continue
            a0 = door_shape["start"] + (door_shape["end"] - door_shape["start"]) * i / max(1, round(abs(door_shape["end"] - door_shape["start"]) * r * s / 12))
            a1 = door_shape["start"] + (door_shape["end"] - door_shape["start"]) * (i + 1) / max(1, round(abs(door_shape["end"] - door_shape["start"]) * r * s / 12))
            draw.line((*pt(hx + r * math.cos(a0), hz + r * math.sin(a0)),
                       *pt(hx + r * math.cos(a1), hz + r * math.sin(a1))), fill=(157, 76, 61), width=3)

    distinct = {}
    for point in reach_info["bottleneck_points"]:
        distinct.setdefault(tuple(point["point"]), point)
    paths = {}
    for route in reach_info["widest_paths"]:
        marker = next((item for item in reach_info["bottleneck_points"] if item["target"] == route["target"]), None)
        if marker:
            paths.setdefault(tuple(marker["point"]), route)
    for route in paths.values():
        points = [pt(*point) for point in route["points"]]
        if len(points) > 1:
            draw.line(points, fill=(44, 110, 194), width=5)
    for bottleneck in distinct.values():
        px, py = pt(*bottleneck["point"])
        draw.ellipse((px - 9, py - 9, px + 9, py + 9), fill=(215, 55, 45), outline=(255, 255, 255), width=3)
        draw.text((px + 18, py - 20), f"{bottleneck['width_m']:.2f} m", fill=(31, 38, 40), font=font(26),
                  stroke_width=5, stroke_fill=(255, 255, 252))

    camera = layout["camera"]
    cx, cz = camera["position"][0], camera["position"][2]
    yaw = math.atan2(camera["look_at"][0] - cx, camera["look_at"][2] - cz)
    half = math.radians(camera["horizontal_fov_deg"]) / 2
    for direction in (yaw - half, yaw + half):
        dx, dz = math.sin(direction), math.cos(direction)
        scale = min((width - cx) / dx if dx > 0 else -cx / dx if dx < 0 else float("inf"),
                    (depth - cz) / dz if dz > 0 else -cz / dz if dz < 0 else float("inf"))
        draw.line((*pt(cx, cz), *pt(cx + scale * dx, cz + scale * dz)), fill=(90, 111, 150), width=3)
    draw.ellipse((pt(cx, cz)[0] - 7, pt(cx, cz)[1] - 7, pt(cx, cz)[0] + 7, pt(cx, cz)[1] + 7), fill=(64, 86, 132))

    def dimension(start, end, label, text_font):
        draw.line((*start, *end), fill=(43, 51, 54), width=3)
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        for point, direction in ((start, angle), (end, angle + math.pi)):
            for side in (-0.55, 0.55):
                draw.line((*point, point[0] + 14 * math.cos(direction + side),
                           point[1] + 14 * math.sin(direction + side)), fill=(43, 51, 54), width=3)
        if label:
            draw.text(((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 - 20), label,
                      fill=(31, 38, 40), font=text_font, anchor="mm", stroke_width=5, stroke_fill=(255, 255, 252))

    left, right = pt(-wall, 0), pt(width + wall, 0)
    dimension((left[0], left[1] + 100), (right[0], right[1] + 100), "8.0 m", font(28))
    top_left, bottom_left = pt(0, depth + wall), pt(0, -wall)
    dimension((top_left[0] - 105, top_left[1]), (bottom_left[0] - 105, bottom_left[1]), "6.0 m", font(28))
    door_y = pt(0, -wall)[1] + 35
    dimension((pt(door["x0"], 0)[0], door_y), (pt(door["x1"], 0)[0], door_y), "1.2 m door", font(24))

    sx, sy = margin + 35, image.height - footer + 40
    step = round(0.5 * s)
    for i in range(4):
        x = sx + i * step
        draw.line((x, sy, x + step, sy), fill=(35, 41, 43), width=7)
        draw.line((x, sy - 11, x, sy + 11), fill=(35, 41, 43), width=3)
    for x, text in ((sx, "0"), (sx + 2 * step, "1 m"), (sx + 4 * step, "2 m")):
        draw.line((x, sy - 11, x, sy + 11), fill=(35, 41, 43), width=3)
        draw.text((x, sy + 18), text, fill=(35, 41, 43), font=font(26), anchor="mt")
    lx, ly = margin + 700, image.height - footer + 20
    legend = [(f"zone_{zone}", zone) for zone in ZONE_COLORS]
    legend.extend((("dash", "Dashed outline: wall-mounted, floor free below"),
                   ("floor", "Walkable floor (player 0.6 m wide)"),
                   ("route", "Widest route from door"),
                   ("bottle", "Narrowest point on route, with width"),
                   ("camera", "Doorway camera view (100°)")))
    draw.rounded_rectangle((lx - 15, ly - 10, image.width - margin + 5, image.height - 15), radius=8,
                           fill=(255, 255, 252), outline=(180, 184, 179), width=2)
    for index, (kind, text) in enumerate(legend):
        x, y = lx + (index % 2) * 1010, ly + (index // 2) * 78
        if kind.startswith("zone_"):
            color = ZONE_COLORS[text]
            draw.rectangle((x, y + 3, x + 22, y + 25), fill=color,
                           outline=tuple(max(0, channel - 65) for channel in color))
        elif kind == "dash":
            for dx in range(0, 56, 18):
                draw.line((x + dx, y + 12, x + dx + 10, y + 12), fill=(55, 63, 65), width=3)
        elif kind == "floor":
            draw.rectangle((x, y + 2, x + 38, y + 26), fill=(234, 245, 231), outline=(140, 160, 138))
        elif kind == "route":
            draw.line((x, y + 14, x + 45, y + 14), fill=(44, 110, 194), width=5)
        elif kind == "bottle":
            draw.ellipse((x + 10, y + 5, x + 26, y + 21), fill=(215, 55, 45))
        elif kind == "camera":
            draw.line((x, y + 23, x + 19, y + 2, x + 38, y + 23), fill=(90, 111, 150), width=3)
        draw.text((x + 65, y), text, fill=(40, 46, 48), font=font(26))
    image.save(output, format="PNG", optimize=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout")
    parser.add_argument("--out")
    parser.add_argument("--report")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return 0 if self_test() else 1
    if not args.layout or not args.out or not args.report:
        parser.error("--layout, --out, and --report are required unless --self-test is used")
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
