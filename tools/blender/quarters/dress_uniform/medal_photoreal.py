"""Stage-one medal geometry and studio entry point. Never writes production assets."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import subprocess

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[1] / 'quarters_aging'))
from medal_fit import GUIDE, GUIDE_HASH, IMAGE_HASH


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def surface_tree(obj):
    obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons([v.co[:] for v in obj.data.vertices],
                               [t.vertices[:] for t in obj.data.loop_triangles], all_triangles=True)


def sample(args):
    out = args.output_directory
    out.mkdir(parents=True, exist_ok=True)
    assert digest(args.guide) == GUIDE_HASH
    assert digest(GUIDE.parent / 'c-machined-rim-seed130303.png') == IMAGE_HASH
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.guide))
    raw = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    points = np.array([raw.matrix_world @ v.co for v in raw.data.vertices])
    scale = .032 / np.ptp(points[:, 0])
    center = np.array([(points[:, 0].min() + points[:, 0].max()) / 2, 0,
                       points[:, 2].min() + .016 / scale])
    points = (points - center) * scale
    raw.matrix_world.identity()
    for v, p in zip(raw.data.vertices, points):
        v.co = p
    raw.name = 'ImmutableRegisteredGuide'
    tree = surface_tree(raw)
    angles = np.linspace(0, 2 * math.pi, 256, endpoint=False)
    radii = np.unique(np.r_[np.linspace(0, .016, 257), np.linspace(.0108, .016, 160)])
    depths = np.full((len(angles), len(radii)), np.nan)
    triangles = np.full(depths.shape, -1, dtype=int)
    for i, angle in enumerate(angles):
        for j, radius in enumerate(radii):
            hit, _, face, _ = tree.ray_cast(Vector((radius * math.cos(angle), -.04, radius * math.sin(angle))), Vector((0, 1, 0)), .08)
            if hit is not None:
                depths[i, j], triangles[i, j] = -hit.y, face
    np.savez_compressed(out / 'guide-samples.npz', vertices=points,
                        faces=np.array([t.vertices[:] for t in raw.data.loop_triangles]),
                        angles=angles, radii=radii, depths=depths, triangle_ids=triangles,
                        scale=scale, center=center)
    raw.hide_render = True
    raw.hide_set(True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'registered-guide.blend'))
    # Read the accepted assembly solely to record its unchanged ribbon and bail constraints.
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'tunic-working.blend'))
    medal = bpy.data.objects['Medal']
    frame = json.loads(medal['medal_frame'])
    origin, basis = np.array(frame['origin']), np.array(frame['frame'])
    local = (np.array([medal.matrix_world @ v.co for v in medal.data.vertices]) - origin) @ basis.T
    medal.data.calc_loop_triangles()
    ribbon_faces = [t.vertices[:] for t in medal.data.loop_triangles
                    if medal.data.materials[t.material_index].name == 'RibbonFabric']
    ids = sorted({i for f in ribbon_faces for i in f})
    remap = {v: i for i, v in enumerate(ids)}
    from medal_eyelet import ribbon_envelope
    eyelet = json.loads(medal['eyelet'])
    x, back, front = ribbon_envelope(local, ribbon_faces, eyelet['threaded_cross_section_z_m'])
    # Frozen old bail vertices retain the cloth-fitted rear return, which is not planar.
    brass_faces = [t.vertices[:] for t in medal.data.loop_triangles
                   if medal.data.materials[t.material_index].name != 'RibbonFabric']
    np.savez_compressed(out / 'ribbon-constraints.npz', vertices=local[ids],
                        faces=np.array([[remap[i] for i in f] for f in ribbon_faces]),
                        envelope_x=x, envelope_back=back, envelope_front=front,
                        metal_vertices=local, metal_faces=brass_faces)
    (out / 'registration.json').write_text(json.dumps(dict(scale=scale, center=center.tolist(),
                frame=frame, eyelet=eyelet, guide_sha256=GUIDE_HASH, concept_sha256=IMAGE_HASH), indent=2))
    print('SAMPLING COMPLETE', depths.shape, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['sample', 'geometry', 'studio'], required=True)
    parser.add_argument('--guide', type=Path, default=GUIDE)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.stage == 'sample':
        sample(args)
    elif args.stage == 'geometry':
        sample(args)
        subprocess.run(['/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python',
                        str(HERE / 'medal_stage1_fit.py'), str(args.output_directory)], check=True)
        from medal_stage1_build import build
        build(args.output_directory)
    else:
        from medal_stage1_studio import studio
        studio(args.output_directory)


if __name__ == '__main__':
    main()
