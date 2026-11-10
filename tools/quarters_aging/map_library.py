"""Bake seeded whole-face library images into a prop's unchanged fitted UV atlas.

Run with the installed Hunyuan Python, --blend source.blend --prop desk.
Blender only reads the source; neither fitted geometry nor its UVs are rewritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, map_coordinates

from steel_library import ROOT, LIBRARY
from locker_faces import paint_fields
from colour import linear
from library_projection import cylinders, cylindrical_frame

BLENDER = '/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'
PROPS = ['wardrobe', 'desk', 'console', 'bed', 'lockers_over_bed', 'bedside', 'media_cabinet',
         'dining_table', 'dining_chair', 'desk_chair', 'view_screen']
PRESERVED = {'Display', 'Glass', 'ScreenGlass', 'Screen', 'DisplayGlass'}


def classify_face(normal, size, area):
    if normal[2] > .7:
        return 'top'
    aspect = max(size) / min(size)
    return 'strip' if aspect >= 4 or area < .004 else 'broad'


def choose_face(rows, kind, size, seed, identity, neighbors):
    candidates = [row for row in rows if row['kind'] == kind]
    if not candidates:
        raise ValueError(f'library lacks {kind} faces')
    candidates = [row for row in candidates if min(np.array(row['pixels'])/size) >= 600]
    if not candidates:
        raise ValueError(f'library lacks {kind} source density >=600 pixels/metre for {size}')
    aspect = size[0] / size[1]
    distance = {row['id']: abs(np.log((row['pixels'][0]/row['pixels'][1])/aspect)) for row in candidates}
    closest = min(distance.values())
    tolerance = .8 if kind == 'strip' else .45
    suitable = [row for row in candidates if distance[row['id']] <= closest + tolerance]
    varied = [row for row in suitable if row['id'] not in neighbors]
    suitable = varied or suitable
    return min(suitable, key=lambda row: hashlib.sha256(f"{seed}/{identity}/{row['id']}".encode()).digest())


def projection_frame(points, normal):
    normal = np.array(normal, float)
    normal /= np.linalg.norm(normal)
    vertical = np.array([0., 0., 1.]) if abs(normal[2]) < .7 else np.array([0., 1., 0.])
    vertical -= normal*np.dot(vertical, normal)
    vertical /= np.linalg.norm(vertical)
    horizontal = np.cross(vertical, normal)
    coordinates = points @ np.stack([horizontal, vertical], axis=1)
    low, high = coordinates.min(0), coordinates.max(0)
    size = high-low
    if np.any(size < 1e-9):
        raise ValueError('collapsed physical face')
    return (coordinates-low)/size, size


def triangle_samples(uv, resolution):
    if not np.isfinite(uv).all() or np.any(uv < -1e-6) or np.any(uv > 1+1e-6):
        raise ValueError('invalid fitted UVs')
    tex = uv * resolution
    tex[:, 1] = resolution-tex[:, 1]
    denominator = np.linalg.det(np.stack([tex[1]-tex[0], tex[2]-tex[0]]))
    if abs(denominator) < 1e-10:
        raise ValueError('collapsed UV triangle')
    low = np.maximum(np.floor(tex.min(0)).astype(int), 0)
    high = np.minimum(np.ceil(tex.max(0)).astype(int), resolution-1)
    yy, xx = np.mgrid[low[1]:high[1]+1, low[0]:high[0]+1]
    delta = np.stack([xx+.5, yy+.5], axis=-1)-tex[0]
    a = (delta[..., 0]*(tex[2, 1]-tex[0, 1])-delta[..., 1]*(tex[2, 0]-tex[0, 0]))/denominator
    b = ((tex[1, 0]-tex[0, 0])*delta[..., 1]-(tex[1, 1]-tex[0, 1])*delta[..., 0])/denominator
    inside = (a >= -1e-9) & (b >= -1e-9) & (a+b <= 1+1e-9)
    return xx[inside], yy[inside], np.stack([1-a[inside]-b[inside], a[inside], b[inside]], -1)


def material_role(name):
    if name in PRESERVED or 'glass' in name.lower() or 'display' in name.lower():
        return 'preserved'
    if name == 'PaintedSteel':
        return 'paint'
    if name in {'BareSteel', 'DarkSteel'}:
        return 'hardware'
    if any(word in name.lower() for word in ('fabric', 'pad', 'cloth', 'cushion')):
        return 'fabric'
    raise ValueError(f'unknown fitted material role: {name}')


def sample_image(image, coordinates):
    h, w = image.shape[:2]
    coords = [np.clip(1-coordinates[:, 1], 0, 1)*(h-1), np.clip(coordinates[:, 0], 0, 1)*(w-1)]
    return np.stack([map_coordinates(image[..., i], coords, order=1, mode='nearest') for i in range(image.shape[2])], -1)


def map_prop(document, prop, output, resolution, seed):
    manifest = json.loads((LIBRARY / 'manifest.json').read_text())
    if not all(row['passed'] for row in manifest['faces']):
        raise ValueError('cannot map failed library images')
    images = {row['id']: np.asarray(Image.open(LIBRARY / row['image']).convert('RGB'), float)/255 for row in manifest['faces']}
    for kind in ('hardware', 'fabric', 'clean'):
        images[kind] = np.asarray(Image.open(LIBRARY / manifest[kind]).convert('RGB'), float)/255
    shape = (resolution, resolution)
    owner = np.full(shape, -1, np.int32)
    interior_owner = np.zeros(shape, bool)
    region = np.zeros((*shape, 3), np.uint8)
    albedo = np.zeros((*shape, 3), np.float32)
    clean = np.zeros_like(albedo)
    relief = np.zeros(shape, np.float32)
    roughness = np.zeros(shape, np.float32)
    clean_roughness = np.zeros(shape, np.float32)
    clean_metallic = np.zeros(shape, np.float32)
    records, densities = [], []
    fields = {}
    recent = {}
    round_parts = cylinders(document['faces'])
    round_images = {}
    for index, face in enumerate(document['faces']):
        role = material_role(face['material'])
        if role == 'preserved':
            records.append(dict(id=face['id'], role=role))
            continue
        triangles = np.array(face['triangles'], float)
        points = triangles.reshape(-1, 3)
        cylinder = round_parts.get(face['part'])
        cylindrical = cylinder is not None and abs(np.dot(face['normal'], cylinder['axis'])) < .7
        if cylindrical:
            coordinates, size = cylindrical_frame(points, cylinder)
        else:
            coordinates, size = projection_frame(points, face['normal'])
            coordinates = coordinates.reshape(-1, 3, 2)
        areas = np.linalg.norm(np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]), axis=-1)/2
        area = float(areas.sum())
        kind = classify_face(face['normal'], size, area if not cylindrical else float(np.prod(size)))
        if role == 'paint':
            identity = face['part']+'/tube/'+kind if cylindrical else face['id']
            if cylindrical and identity in round_images:
                chosen = round_images[identity]
            else:
                chosen = choose_face(manifest['faces'], kind, size, seed, identity, set(recent.get(kind, [])))
                if cylindrical: round_images[identity] = chosen
                recent[kind] = [chosen['id']]
            image_id = chosen['id']
        else:
            image_id = role
        if image_id not in fields:
            image = images[image_id]
            source_image = Image.fromarray(np.uint8(np.round(image*255)))
            _, paint = paint_fields(source_image)
            if role == 'hardware':
                height = (linear(image) @ [.2126, .7152, .0722])*.0003
            elif role == 'fabric':
                height = image.mean(-1)*.0002
            else:
                height = paint*.0015
            fields[image_id] = np.dstack([image, height, .91*(1-paint)+.69*paint])
        field = fields[image_id]
        record = dict(id=face['id'], part=face['part'], material=face['material'], role=role,
                      kind=kind, image=image_id, size_m=size.tolist(), area_m2=area,
                      upward=bool(face['normal'][2] > .7), projection='cylindrical' if cylindrical else 'planar')
        if role in ('hardware', 'fabric'):
            record['pitch_m'] = .2 if role == 'hardware' else .1
            record['source_pixels_per_metre'] = min(images[image_id].shape[:2])/record['pitch_m']
        else:
            record['source_pixels_per_metre'] = float(np.min(np.array(images[image_id].shape[:2][::-1])/size))
        records.append(record)
        for ti, uv in enumerate(np.array(face['uv'], float)):
            x, y, weights = triangle_samples(uv, resolution)
            if len(x) == 0:
                continue
            interior = np.min(weights, axis=1) > 1e-8
            overlap = (owner[y, x] >= 0) & (owner[y, x] != index) & interior & interior_owner[y, x]
            if overlap.any():
                prior = np.unique(owner[y[overlap], x[overlap]])
                raise ValueError(f'UV overlap {face["id"]} with {prior.tolist()}')
            # A pixel centre exactly on a shared UV edge belongs to either
            # face. Preserve interior samples over boundary-only ownership.
            keep = (owner[y, x] < 0) | interior | ~interior_owner[y, x]
            x, y, weights, interior = x[keep], y[keep], weights[keep], interior[keep]
            owner[y, x] = index
            interior_owner[y, x] = interior
            local = weights @ coordinates[ti]
            if cylindrical: local[:, 0] %= 1
            texture_coordinates = np.mod(local*size/record['pitch_m'], 1) if role in ('hardware', 'fabric') else local
            sampled = sample_image(field, texture_coordinates)
            albedo[y, x] = sampled[:, :3]
            relief[y, x] = sampled[:, 3]
            roughness[y, x] = sampled[:, 4] if role != 'fabric' else .94
            pigment = images['clean'][0, 0]
            if role == 'hardware':
                pigment = np.array([.60, .63, .65]) if face['material'] == 'BareSteel' else np.array([.17, .20, .19])
            if role == 'fabric':
                pigment = sampled[:, :3] * np.array([.24, .29, .25]) / [.43, .45, .41]
            clean[y, x] = pigment
            clean_roughness[y, x] = .45 if role == 'paint' else (.87 if role == 'fabric' else .35)
            clean_metallic[y, x] = .45 if role == 'hardware' else .02
            if role == 'paint':
                edge = ((local < .1) | (local > .9)).any(-1)
                region[y, x, 0] = edge*255
                region[y, x, 1] = (~edge)*255
                region[y, x, 2] = (face['normal'][2] > .7)*255
            physical = triangles[ti]
            uv_area = abs(np.linalg.det(np.stack([uv[1]-uv[0], uv[2]-uv[0]])))*resolution**2
            densities.append(float(np.sqrt(uv_area/(2*areas[ti]))))
        print('MAP', prop, face['id'], role, image_id, flush=True) if area > .1 else None
    occupied = owner >= 0
    if not occupied.any():
        raise ValueError('empty atlas')
    # Extend each island into unused atlas space for stable anisotropic mipmaps.
    _, nearest = distance_transform_edt(~occupied, return_indices=True)
    y, x = nearest
    density = float(np.median(densities))
    filled_height = relief[y, x]
    dy, dx = np.gradient(filled_height)
    normal = np.dstack([-dx*density, dy*density, np.ones(shape)])
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    output.mkdir(parents=True, exist_ok=True)
    for state in ('as_built', 'aged'):
        rgb = clean if state == 'as_built' else albedo
        orm = np.dstack([np.ones(shape), clean_roughness if state == 'as_built' else roughness,
                         clean_metallic if state == 'as_built' else np.zeros(shape)])
        normals = np.zeros((*shape, 3), np.float32)+[.5, .5, 1] if state == 'as_built' else normal*.5+.5
        for name, field in [('albedo', rgb[y, x]), ('normal', normals), ('orm', orm[y, x])]:
            Image.fromarray(np.uint8(np.round(np.clip(field, 0, 1)*255))).save(output / f'{state}_{name}.png')
    Image.fromarray(region).save(output / 'regions.png')
    metadata = dict(prop=prop, seed=seed, atlas_size=resolution, uv_method='original fitted UVs; no repack',
                    texels_per_metre=density, density_range=[min(densities), max(densities)],
                    uv_overlap_texels=0, occupied_texels=int(occupied.sum()), faces=records,
                    source_blend=document['blend'], preserved_materials=[m for m in document['materials'] if material_role(m) == 'preserved'])
    (output / 'mapping.json').write_text(json.dumps(metadata, indent=2)+'\n')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blend', type=Path, required=True)
    parser.add_argument('--prop', required=True)
    parser.add_argument('--seed', type=int, default=9502)
    parser.add_argument('--resolution', type=int, default=2048)
    parser.add_argument('--reuse-faces', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    scratch = ROOT / 'tmp/mat2' / args.prop
    scratch.mkdir(parents=True, exist_ok=True)
    faces = scratch / 'faces.json'
    if not args.reuse_faces:
        command = [BLENDER, '--background', '--factory-startup', '--python-exit-code', '1',
                   '--python', str(ROOT / 'tools/blender/quarters_aging/library_faces.py'), '--',
                   '--blend', str(args.blend.resolve()), '--output', str(faces)]
        subprocess.run(command, check=True, cwd=ROOT)
    document = json.loads(faces.read_text())
    output = args.output or ROOT / f'assets/props/quarters/steel/{args.prop}'
    map_prop(document, args.prop, output, args.resolution, args.seed)
    from library_imports import configure
    for path in sorted(output.glob('*.png')):
        configure(path)


if __name__ == '__main__':
    main()
