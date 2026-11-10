"""Run the wardrobe's auxiliary mask bake on triangulated scratch copies.

These masks measure geometry and exposure only. Runtime library atlases keep
fitted UVs; the auxiliary isometric pack is never exported to the game assets.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prop', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    prop = args.prop
    scratch = ROOT / f'tmp/mat2/{prop}/mask-bake'
    scratch.mkdir(parents=True, exist_ok=True)
    source = ROOT / f'tools/blender/quarters/{prop}/{prop}-working.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH'
              and not obj.hide_render and not obj.name.startswith('Guide_')]
    for obj in meshes:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        bm.free()
    names = sorted(obj.name for obj in meshes)
    bpy.context.preferences.filepaths.save_version = 0
    copy = scratch / 'triangulated.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(copy))
    spec = importlib.util.spec_from_file_location('auxiliary_bake', ROOT / 'tools/blender/quarters_aging/bake_masks.py')
    bake = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bake)
    sys.argv = ['blender', '--', '--blend', str(copy), '--objects', *names,
                '--output', str(scratch / 'masks'), '--seed', '9502', '--resolution', '2048',
                '--fields', str(scratch / 'geometry.npz'), '--export', str(scratch / 'masked.glb')]
    bake.main()
    print('AUXILIARY MASKS COMPLETE', prop, flush=True)


if __name__ == '__main__':
    main()
