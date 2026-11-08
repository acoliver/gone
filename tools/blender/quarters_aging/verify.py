"""Measure aged exported GLBs with trimesh. Failed gates remain in the report."""
import argparse
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree
import trimesh

ROOT = Path(__file__).resolve().parents[3]


def load(path):
    scene = trimesh.load(path, force='scene', process=False)
    raw = path.read_bytes()
    document = json.loads(raw[20:20 + struct.unpack_from('<I', raw, 12)[0]])
    names = [n['name'] for n in document['nodes'] if 'mesh' in n]
    parts = {}
    for node in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[node]
        mesh = scene.geometry[geometry].copy()
        mesh.apply_transform(transform)
        name = next((n for n in names if node == n or node.startswith(n + '_')), node)
        parts.setdefault(name, []).append(mesh)
    combined = {}
    for name, meshes in parts.items():
        result = trimesh.util.concatenate(meshes)
        ranges, offset = [], 0
        for mesh in meshes:
            ranges.append((offset, offset + len(mesh.faces), mesh.visual.material.name))
            offset += len(mesh.faces)
        result.metadata['material_source_ranges'] = ranges
        combined[name] = result
    return combined, document


def clean(mesh):
    result = mesh.copy()
    result.merge_vertices(merge_tex=True, merge_norm=True)
    return result


def same_geometry(a, b):
    return bool(np.array_equal(a.vertices, b.vertices) and np.array_equal(a.faces, b.faces))


def geometry_buffers(path):
    raw = path.read_bytes()
    length = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20 + length])
    binary = raw[28 + length:]
    widths = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
    dimensions = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
    def accessor_bytes(index):
        accessor = doc['accessors'][index]
        if 'sparse' in accessor:
            raise ValueError('Sparse geometry is not supported by this raw-buffer check')
        view = doc['bufferViews'][accessor['bufferView']]
        width = widths[accessor['componentType']] * dimensions[accessor['type']]
        offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        stride = view.get('byteStride', width)
        return b''.join(binary[offset + i * stride:offset + i * stride + width] for i in range(accessor['count']))
    result = {}
    for node in doc['nodes']:
        if 'mesh' not in node:
            continue
        primitives = []
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            attributes = {name: accessor_bytes(index) for name, index in primitive['attributes'].items()}
            attributes['indices'] = accessor_bytes(primitive['indices'])
            primitives.append(attributes)
        result[node['name']] = primitives
    return result


def cross2(a, b):
    return a[0] * b[1] - a[1] * b[0]


def uv_loss(before, after, size=1024):
    """Weight missing pattern pixels by original world area, not by aged stretching."""
    uv = before.visual.uv
    lo, hi = uv.min(0), uv.max(0)
    scale = (size - 3) / np.maximum(hi - lo, 1e-9)
    weights = np.zeros((size, size), dtype=np.float32)
    for triangle, area in zip(uv[before.faces], before.area_faces):
        cross = cross2(triangle[1] - triangle[0], triangle[2] - triangle[0])
        uv_area = abs(float(cross)) / 2
        if uv_area < 1e-12:
            continue
        pixel = (triangle - lo) * scale + 1
        xmin, ymin = np.maximum(0, np.floor(pixel.min(0)).astype(int))
        xmax, ymax = np.minimum(size - 1, np.ceil(pixel.max(0)).astype(int))
        image = Image.new('1', (xmax - xmin + 1, ymax - ymin + 1))
        ImageDraw.Draw(image).polygon([tuple(p - [xmin, ymin]) for p in pixel], fill=1)
        patch = weights[ymin:ymax + 1, xmin:xmax + 1]
        np.maximum(patch, np.asarray(image) * area / uv_area, out=patch)
    image = Image.new('1', (size, size))
    draw = ImageDraw.Draw(image)
    for triangle in after.visual.uv[after.faces]:
        uv_area = abs(float(cross2(triangle[1] - triangle[0], triangle[2] - triangle[0]))) / 2
        if uv_area > 1e-12:
            draw.polygon([tuple(p) for p in (triangle - lo) * scale + 1], fill=1)
    retained = np.asarray(image)
    return float(weights[~retained].sum() / weights.sum())


def silhouette(before, after, size=1200):
    points = np.vstack([m.vertices[:, :2] for m in before + after])
    lo, hi = points.min(0), points.max(0)
    scale = (size - 4) / (hi - lo)
    masks = []
    for meshes in [before, after]:
        image = Image.new('1', (size, size))
        draw = ImageDraw.Draw(image)
        for mesh in meshes:
            pixels = (mesh.vertices[:, :2] - lo) * scale + 2
            for face in mesh.faces:
                draw.polygon([tuple(p) for p in pixels[face]], fill=1)
        masks.append(np.asarray(image))
    return float((masks[0] & masks[1]).sum() / (masks[0] | masks[1]).sum())


def penetration(a, b):
    """Interior vertex, edge-midpoint and triangle-centroid distances in both directions."""
    maximum = 0.0
    for source, target in [(a, b), (b, a)]:
        if not target.is_watertight:
            continue
        if np.any(source.bounds[1] < target.bounds[0]) or np.any(target.bounds[1] < source.bounds[0]):
            continue
        samples = np.vstack([source.vertices, source.triangles_center, source.vertices[source.edges_unique].mean(1)])
        inside = target.contains(samples)
        if inside.any():
            d = trimesh.proximity.closest_point(target, samples[inside])[1]
            maximum = max(maximum, float(d.max()))
    return maximum


def edge_crossings(mesh):
    edges = mesh.edges_unique
    starts, ends = mesh.vertices[edges[:, 0]], mesh.vertices[edges[:, 1]]
    delta = ends - starts
    lengths = np.linalg.norm(delta, axis=1)
    valid = lengths > 1e-8
    edges, starts, delta, lengths = edges[valid], starts[valid], delta[valid], lengths[valid]
    directions = delta / lengths[:, None]
    triangles, rays, locations = trimesh.ray.ray_triangle.ray_triangle_id(
        mesh.triangles, starts + directions * 1e-7, directions,
        tree=mesh.triangles_tree, multiple_hits=True)
    distance = np.einsum('ij,ij->i', locations - starts[rays], directions[rays])
    shared = np.any(mesh.faces[triangles, :, None] == edges[rays, None, :], axis=(1, 2))
    crossing = ~shared & (distance > 1e-6) & (distance < lengths[rays] - 1e-6)
    return int(crossing.sum())


def intersections(parts, relevant):
    meshes = {n: clean(parts[n]) for n in relevant}
    component_checks = {}
    unclosed = []
    for n, m in meshes.items():
        pieces = list(m.split(only_watertight=False))
        for i, piece in enumerate(pieces):
            if not piece.is_watertight:
                unclosed.append(f'{n}:{i}')
        # Separate crust plates and cover are checked against each other too.
        for i, left in enumerate(pieces):
            for j, right in enumerate(pieces[i + 1:], i + 1):
                if np.all(left.bounds[1] >= right.bounds[0]) and np.all(right.bounds[1] >= left.bounds[0]):
                    value = penetration(left, right)
                    if value > 1e-7:
                        component_checks[f'{n}:{i}/{j}'] = value
    for i, name in enumerate(relevant):
        for other in relevant[i + 1:]:
            component_checks[name + '/' + other] = penetration(meshes[name], meshes[other])
    maximum = max(component_checks.values(), default=0)
    return {'sampled_inward_depth_max_m': maximum, 'limit_m': .001,
            'pairs_m': component_checks, 'open_components': unclosed,
            'method': 'Bidirectional vertices, edge midpoints and triangle centres inside closed meshes. Open fray cards do not enclose volume. This is sampled penetration, not a continuous self-intersection proof.',
            'pass': maximum <= .001}


def pivots(document):
    return {n['name']: {k: n[k] for k in ['translation', 'rotation', 'scale', 'matrix'] if k in n}
            for n in document['nodes'] if 'mesh' in n}


def verify(prop, reexport, input_path=None):
    before_path = ROOT / f'assets/props/quarters/{prop}.glb'
    after_path = input_path or before_path.with_name(prop + '_aged.glb')
    before, doc_before = load(before_path)
    after, doc_after = load(after_path)
    fixed = ['Frame', 'Feet', 'Rivets'] if prop == 'sofa' else ['Hanger']
    old_buffers, new_buffers = geometry_buffers(before_path), geometry_buffers(after_path)
    record = {'prop': prop, 'unchanged_geometry': {n: same_geometry(before[n], after[n]) for n in fixed},
              'unchanged_geometry_bytes': {n: old_buffers[n] == new_buffers[n] for n in fixed}}
    old_pivots, new_pivots = pivots(doc_before), pivots(doc_after)
    record['pivots_and_origin_unchanged'] = all(new_pivots.get(n) == t for n, t in old_pivots.items())
    record['preserved_names'] = set(before) <= set(after)
    old_count = sum(len(m.faces) for m in before.values())
    new_count = sum(len(m.faces) for m in after.values())
    record['triangles'] = {'unaged': old_count, 'aged': new_count, 'ratio': new_count / old_count, 'limit_ratio': 1.5, 'pass': new_count <= 1.5 * old_count}
    record['byte_identical_reexport'] = reexport.exists() and after_path.read_bytes() == reexport.read_bytes()
    if prop == 'sofa':
        cushion_names = [n for n in before if 'Cushion' in n]
        cushions = {}
        frame = clean(after['Frame'])
        for name in cushion_names:
            m = clean(after[name])
            # Sum the oriented volumes of the closed crust and thin upholstery.
            ratio = float(m.volume / before[name].volume)
            face_mask = np.zeros(len(after[name].faces), dtype=bool)
            for start, end, material in after[name].metadata['material_source_ranges']:
                if material == 'Foam':
                    face_mask[start:end] = True
            crust = clean(after[name].submesh([face_mask], append=True))
            samples = np.vstack([crust.vertices, crust.triangles_center])
            bottom = samples[samples[:, 1] < crust.bounds[0, 1] + .002]
            below = frame.copy()
            below.update_faces(np.all(below.triangles[:, :, 1] < crust.bounds[0, 1] + .003, axis=1))
            gap = float(trimesh.proximity.closest_point(below, bottom)[1].min())
            cushions[name] = {'volume_ratio': ratio, 'volume_ratio_band': [.25, .35],
                              'support_gap_m': gap, 'support_limit_m': .003,
                              'crust_watertight': crust.is_watertight,
                              'combined_cover_and_crust_watertight': m.is_watertight,
                              'pass': .25 <= ratio <= .35 and gap <= .003 and crust.is_watertight}
        record['cushions'] = cushions
        loss = uv_loss(before['Throw'], after['Throw'])
        record['throw_tear'] = {'reference_surface_loss_fraction': loss, 'band': [.10, .30], 'pass': .10 <= loss <= .30}
        record['intersections'] = intersections(after, ['Frame', *cushion_names, 'Throw'])
    else:
        loss = uv_loss(before['TunicBody'], after['TunicBody'])
        record['cloth_holes'] = {'reference_surface_loss_fraction': loss, 'band': [.08, .25], 'pass': .08 <= loss <= .25}
        record['cloth_connected_components'] = int(clean(after['TunicBody']).body_count)
        names = [n for n in before if n != 'Hanger']
        iou = silhouette([before[n] for n in names], [after[n] for n in names])
        record['front_silhouette'] = {'iou': iou, 'band': [.6, .85], 'pass': .6 <= iou <= .85}
        construction = json.loads((ROOT / 'tools/blender/quarters/dress_uniform/construction.json').read_text())
        details = {}
        for name in names:
            if name == 'TunicBody':
                continue
            entry = construction['attachments'][name]
            p = np.asarray(entry['base_blender_m'])[:, [0, 2, 1]] * [1, 1, -1]
            m = after[name]
            anchors = m.vertices[cKDTree(m.vertices).query(p)[1]]
            maximum = float(trimesh.proximity.closest_point(after[entry['support']], anchors)[1].max())
            details[name] = {'max_attachment_gap_m': maximum, 'limit_m': .002, 'rigid_geometry_unchanged': same_geometry(before[name], after[name]), 'pass': maximum <= .002}
        record['details'] = details
        record['intersections'] = intersections(after, names + ['Hanger'])
        dust = after['FibreDust']
        params = json.loads((ROOT / 'tools/blender/quarters/dress_uniform/aging.json').read_text())
        floor = -params['debris']['drop_height_m']
        record['fibre_dust'] = {'nominal_floor_y_m': floor, 'bottom_y_m': float(dust.bounds[0, 1]), 'pass': 0 <= dust.bounds[0, 1] - floor <= .001}
    unchanged = {name for name in before if same_geometry(before[name], after[name])}
    inherited, changed = {}, {}
    for pair, depth in record['intersections']['pairs_m'].items():
        if ':' in pair:
            stationary = pair.split(':')[0] in unchanged
        else:
            stationary = all(name in unchanged for name in pair.split('/'))
        (inherited if stationary else changed)[pair] = depth
    record['intersections']['unchanged_assembly_depth_max_m'] = max(inherited.values(), default=0)
    record['intersections']['changed_geometry_depth_max_m'] = max(changed.values(), default=0)
    dynamic = ['Throw', *cushion_names] if prop == 'sofa' else ['TunicBody']
    self_checks = {}
    for name in dynamic:
        pieces = clean(after[name]).split(only_watertight=False)
        self_checks[name] = [edge_crossings(piece) for piece in pieces if len(piece.faces) > 8]
    record['intersections']['nonadjacent_self_edge_crossings_by_component'] = self_checks
    record['intersections']['self_intersection_free'] = not any(count for counts in self_checks.values() for count in counts)
    gates = [all(record['unchanged_geometry'].values()), all(record['unchanged_geometry_bytes'].values()),
             record['pivots_and_origin_unchanged'], record['preserved_names'], record['triangles']['pass'],
             record['byte_identical_reexport'], record['intersections']['pass'],
             record['intersections']['self_intersection_free']]
    if prop == 'sofa':
        gates += [all(v['pass'] for v in record['cushions'].values()), record['throw_tear']['pass']]
    else:
        gates += [record['cloth_holes']['pass'], record['front_silhouette']['pass'],
                  all(v['pass'] for v in record['details'].values()), record['fibre_dust']['pass'],
                  record['cloth_connected_components'] == 1]
    record['pass'] = bool(all(gates))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prop', choices=['sofa', 'dress_uniform'], required=True)
    parser.add_argument('--reexport', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--input', type=Path)
    args = parser.parse_args()
    record = verify(args.prop, args.reexport, args.input)
    text = json.dumps(record, indent=2, default=lambda value: value.item())
    args.report.write_text(text + '\n')
    print(text)
    if not record['pass']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
