"""Triangulate a scratch copy before the shared geometry-mask bake.

The fitted door has valid concave polygons with collinear first corners.
The shared planar projector assumes its first three corners define a plane;
triangulating a copy removes that assumption without changing the game mesh.
"""
import importlib.util
from pathlib import Path
import sys

import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[4]
SCRATCH = ROOT / 'tmp/mat1/wardrobe'
SOURCE = ROOT / 'tools/blender/quarters/wardrobe/wardrobe-working.blend'


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    root = bpy.data.objects['Wardrobe']
    meshes = [obj for obj in root.children_recursive if obj.type == 'MESH']
    for obj in meshes:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        bm.free()
    bpy.context.preferences.filepaths.save_version = 0
    copy = SCRATCH / 'triangulated.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(copy))
    spec = importlib.util.spec_from_file_location('wardrobe_mask_bake', ROOT / 'tools/blender/quarters_aging/bake_masks.py')
    bake = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bake)
    sys.argv = ['blender', '--', '--blend', str(copy), '--objects', 'Wardrobe',
                '--output', str(SCRATCH / 'masks'), '--seed', '97001', '--resolution', '2048',
                '--fields', str(SCRATCH / 'geometry.npz'), '--export', str(SCRATCH / 'masked.glb')]
    bake.main()


if __name__ == '__main__':
    main()
