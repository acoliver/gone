"""Separate point-touching cover panels before giving the brittle cloth thickness."""
import json
from pathlib import Path
import sys

import bmesh
import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build import ASSETS, mesh_points, unwrap
from common import activate, export, midsurface, recalc, save, solidify
from stress_cut import cut_faces


def retain_material(obj, predicate):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    remove = [face for face in bm.faces if not predicate(obj.data.materials[face.material_index].name)]
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()


def repair_cover(mattress):
    cover = mattress.copy()
    cover.data = mattress.data.copy()
    bpy.context.collection.objects.link(cover)
    cover.name = 'MattressCoverWork'
    retain_material(cover, lambda name: name.startswith('CottonTicking'))
    cotton = next(mat for mat in cover.data.materials if mat.name.startswith('CottonTicking'))
    cover.data.materials.clear()
    cover.data.materials.append(cotton)
    for face in cover.data.polygons:
        face.material_index = 0
    midsurface(cover)
    # The Voronoi face mask can leave panels sharing a single point. Those
    # contacts must be separate fans before Solidify, not welded thin solids.
    cut_faces(cover, lambda point: False, 95250, refine=False, fan_clearance=.001)
    solidify(cover, .0018)
    shift = .501 - float(mesh_points(cover)[:, 2].min())
    for vertex in cover.data.vertices:
        vertex.co.z += shift
    retain_material(mattress, lambda name: name == 'Foam')
    activate(mattress)
    cover.select_set(True)
    bpy.ops.object.join()
    mattress.name = 'Mattress'
    recalc(mattress)
    unwrap(mattress)
    return {'point_fans_separated_before_thickness': True, 'cover_support_translation_m': shift}


def main():
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'bed-soft-aged.blend'))
    record = json.loads((HERE / 'aging.json').read_text())
    record['Mattress']['cover_finish'] = repair_cover(bpy.data.objects['Mattress'])
    (HERE / 'aging.json').write_text(json.dumps(record, indent=2) + '\n')
    save(HERE / 'bed-soft-aged.blend', record)
    export(ASSETS / 'bed_soft_aged.glb')


if __name__ == '__main__':
    main()
