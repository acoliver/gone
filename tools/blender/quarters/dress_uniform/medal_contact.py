"""Bake incremental mounted-medal occlusion, never cloth fold shading or albedo."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tunic_details import points
from build import tree
from mathutils.bvhtree import BVHTree

SIZE = 512
SAMPLES = 128
PATCH = (.048, .056)


def bake(sources, out):
    out.mkdir(parents=True, exist_ok=True)
    frames = {}
    for name, state in [('working', 'as_built'), ('pilot', 'aged')]:
        bpy.ops.wm.open_mainfile(filepath=str(sources/f'tunic-{name}.blend'))
        medal, body = bpy.data.objects['Medal'], bpy.data.objects['TunicBody']
        record = json.loads(medal['medal_frame'])
        origin, frame = np.array(record['origin']), np.array(record['frame'])
        normal = -frame[1]
        cloth = tree(body)
        medal.data.calc_loop_triangles()
        fs = [t.vertices[:] for t in medal.data.loop_triangles if t.material_index < 2]
        metal = BVHTree.FromPolygons(points(medal).tolist(), fs, all_triangles=True)
        coverage = np.zeros((SIZE, SIZE), bool)
        footprint = np.zeros_like(coverage)
        position = np.zeros((SIZE, SIZE, 3))
        normals = np.zeros_like(position)
        depth = np.zeros((SIZE, SIZE))
        for row in range(SIZE):
            z = (row+.5)/SIZE*PATCH[1]-.024
            for col in range(SIZE):
                x = (col+.5)/SIZE*PATCH[0]-.024
                start = Vector(origin+np.array([x, -.02, z])@frame)
                hit, n, _, _ = cloth.ray_cast(start, Vector(-normal), .04)
                if hit is None or np.dot(n, normal) < .2: continue
                coverage[row,col] = True
                position[row,col] = hit
                normals[row,col] = n
                depth[row,col] = np.dot(np.array(hit)-origin, frame[1])
                footprint[row,col] = metal.ray_cast(start, Vector(-normal), .04)[0] is not None
        # A 3 mm projection dilation is an explicit bound, not a black disc.
        bounded = footprint.copy()
        steps = int(np.floor(.003/max(PATCH)*SIZE))
        for _ in range(steps):
            previous = bounded.copy()
            bounded[1:] |= previous[:-1]; bounded[:-1] |= previous[1:]
            bounded[:,1:] |= previous[:,:-1]; bounded[:,:-1] |= previous[:,1:]
        ao = np.ones((SIZE,SIZE))
        without = np.ones_like(ao)
        with_medal = np.ones_like(ao)
        phi = np.arange(SAMPLES)*np.pi*(3-np.sqrt(5))
        radius = np.sqrt((np.arange(SAMPLES)+.5)/SAMPLES)
        hemisphere = np.c_[radius*np.cos(phi), radius*np.sin(phi), np.sqrt(1-radius*radius)]
        for row,col in np.argwhere(bounded & coverage):
            p = position[row,col]; n = normals[row,col]
            tx = np.cross(n, [0,0,1]); tx /= np.linalg.norm(tx)
            ty = np.cross(n,tx)
            directions = hemisphere@np.array([tx,ty,n])
            baseline = combined = 0
            start = Vector(p+n*.00001)
            for d in directions:
                direction = Vector(d)
                cloth_hit = cloth.ray_cast(start,direction,.003)[0] is not None
                medal_hit = metal.ray_cast(start,direction,.003)[0] is not None
                baseline += not cloth_hit
                combined += not (cloth_hit or medal_hit)
            without[row,col] = baseline/SAMPLES
            with_medal[row,col] = combined/SAMPLES
            # A fully occluded cloth sample carries no incremental visible signal.
            ao[row,col] = combined/baseline if baseline else 1.
        rgba = np.ones((SIZE,SIZE,4),np.float32)
        rgba[:,:,0] = ao
        rgba[:,:,1] = np.clip(.5+depth/.02,0,1)
        rgba[:,:,2] = coverage
        image = bpy.data.images.new('MedalContact_'+state, width=SIZE, height=SIZE, alpha=True)
        image.colorspace_settings.name = 'Non-Color'
        image.pixels.foreach_set(rgba.ravel())
        image.filepath_raw = str(out/(state+'_contact.png'))
        image.file_format = 'PNG'; image.save()
        axes = {}
        for key,i in [('x',0),('depth',1),('height',2)]:
            axis = frame[i]
            axes[key] = [float(axis[0]),float(axis[2]),float(-axis[1]),float(-origin@axis)]
        frames[state] = dict(axes=axes, patch_m=list(PATCH), z_low_m=-.024,
            samples=SAMPLES, radius_m=.003, covered_texels=int(coverage.sum()),
            footprint_texels=int(footprint.sum()), changed_texels=int((ao<1).sum()),
            outside_bound_max_delta=float(np.max(abs(1-ao[~bounded]))),
            construction='AO(cloth + final medal)/AO(cloth alone), cosine-weighted deterministic hemisphere; R ratio, G cloth depth (.5+y/.02), B front coverage; linear data',
            source_frame=record)
        np.savez_compressed(sources/(state+'_contact-evidence.npz'), ao=ao, baseline=without, mounted=with_medal,
                            footprint=footprint, coverage=coverage, bounded=bounded)
        print(state,frames[state],flush=True)
    (out/'contact-frames.json').write_text(json.dumps(frames,indent=2)+'\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    bake(args.sources.resolve(),args.output.resolve())
