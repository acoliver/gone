"""Blender fixtures for mask geometry, independent of the locker asset.

Run with Blender --background --factory-startup --python-exit-code 1 --python
 tools/blender/quarters_aging/test_bake_masks.py. Fixtures are not exported.
"""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bake_masks as bake


def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    material = bpy.data.materials.new("PaintedSteel")
    material.use_nodes = True
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, .5))
    body = bpy.context.object
    body.name = "MirroredBody"
    body.scale.x = -1
    body.data.materials.append(material)
    bpy.ops.mesh.primitive_cube_add(size=.1, location=(0, -.55, .8))
    rivet = bpy.context.object
    rivet.name = "Rivet"
    rivet.data.materials.append(material)
    bpy.context.view_layer.update()
    objects = [body, rivet]
    bake.planar_atlas(objects, 128)
    position, normal, edge, contact, _, occupied, _, density = bake.rasterize(objects, 128)
    assert np.isfinite(position).all() and np.isfinite(edge).all()
    assert np.ptp(density) / np.median(density) < .015
    top = occupied & (position[:, :, 2] > .999)
    assert top.any() and (normal[:, :, 2][top] > .99).all(), "mirrored top still faces up"
    assert contact.max() > .3, "touching parts produce contact"
    ao_without = bake.bake_ao(objects, 128, 9501)
    bpy.ops.mesh.primitive_cube_add(size=4, location=(0, 0, .5))
    guide = bpy.context.object
    guide.name = "ExcludedGuide"
    ao_with = bake.bake_ao(objects, 128, 9501)
    assert np.array_equal(ao_without, ao_with), "unselected guide cannot affect prop AO"
    assert not guide.hide_render, "guide visibility restored"
    assert not body.hide_render and not body.hide_get(), "body visibility restored"
    print("BAKER FIXTURES PASS: density, reflected exposure, contact, isolated AO, visibility", flush=True)


if __name__ == "__main__":
    main()
