"""Smaller residue fragments and contact-fitted fine powder below the tears."""
import argparse
import json
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import surface_tree
from powder_cards import powder_card
from sofa_decay_debris import DepositContacts, deposit, opening_sources
from sofa_decay_material import linear_to_srgb
from sofa_decay_policy import ORDER
from sofa_full_decay import ROOT, checkpoint
from sofa_pass10_material import FOAM_TAN, replace_pixels


def retain_floor(debris, baseline, record, reference):
    bm = bmesh.new()
    bm.from_mesh(debris.data)
    remove = [f for f in bm.faces if all((debris.matrix_world@v.co).z < .03 for v in f.verts)]
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    source = baseline.data
    points = [baseline.matrix_world@v.co for v in source.vertices]
    faces = [f for f in source.polygons if all(points[i].z < .03 for i in f.vertices)]
    inverse = debris.matrix_world.inverted()
    vertices = {i: bm.verts.new(inverse@points[i]) for i in sorted({i for f in faces for i in f.vertices})}
    for face in faces:
        bm.faces.new([vertices[i] for i in face.vertices])
    bm.to_mesh(debris.data)
    bm.free()
    record['placements'] = [p for p in record['placements'] if not p['floor']]+[p for p in reference['placements'] if p['floor']]
    for spill, old in zip(record['spills'], reference['spills'], strict=True):
        spill['origin_blender_m'] = old['origin_blender_m']
        spill['floor_count'] = old['floor_count']
    record['retained_floor_triangles'] = len(faces)


def grain_pixels(seed, size=1024):
    rng = np.random.default_rng(seed)
    pixels = np.ones((size, size, 4), dtype=np.float32)
    yy, xx = np.mgrid[-1:1:complex(size), -1:1:complex(size)]
    density = np.exp(-(xx*xx+yy*yy)*3)
    grain = rng.random((size, size)) < density*.45
    # Visible agglomerates sit among the sub-millimetre grains. A uniformly
    # opaque middle reads as a stain, while single texels vanish in mipmaps.
    for _ in range(110):
        x, y = rng.uniform(-.8, .8, 2)
        radius = rng.uniform(.012, .045)
        grain |= ((xx-x)**2+(yy-y)**2 < radius*radius) & (rng.random((size, size)) < .85)
    pixels[:, :, :3] = linear_to_srgb(FOAM_TAN)*(.75+.25*rng.random((size, size, 1)))
    pixels[:, :, 3] = grain
    return pixels


def finish_powder(card, contacts, seed, unsupported=frozenset()):
    points = np.array([v.co[:] for v in card.data.vertices])
    bm = bmesh.new()
    bm.from_mesh(card.data)
    bm.verts.index_update()
    remove = [face for face in bm.faces if any(v.index in unsupported for v in face.verts) or
              not contacts.clear_mesh(points, np.array([[v.index for v in face.verts]]))]
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    if not bm.faces:
        bm.free()
        bpy.data.objects.remove(card, do_unlink=True)
        return 0
    bm.to_mesh(card.data)
    bm.free()
    card.data.calc_loop_triangles()
    points = np.array([v.co[:] for v in card.data.vertices])
    faces = np.array([t.vertices[:] for t in card.data.loop_triangles])
    contacts.add_mesh(points, faces)
    shader = card.data.materials[0].node_tree.nodes['Principled BSDF']
    image = shader.inputs['Base Color'].links[0].from_node.image
    replace_pixels(image, grain_pixels(seed))
    card['aged_export'] = True
    return len(faces)


def fine_powder(out, record):
    solids = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('aged_export')]
    contacts = DepositContacts(solids)
    reports = []
    for index, name in enumerate(ORDER):
        cover = bpy.data.objects[name+'_GameContact']
        supports = [surface_tree(bpy.data.objects[name+'_Residue']), surface_tree(bpy.data.objects['Frame'])]
        lips = opening_sources(cover)
        eligible = [p for p, _ in lips if p.z > .395 and (p.y < -.08 if name.startswith('Seat') else p.y > .28)]
        anchor = min(eligible, key=lambda p: abs(p.x-cover.matrix_world.translation.x))
        y = anchor.y if name.startswith('Seat') else .35
        seed = 9710+index
        card = powder_card('FinePowder_'+name, (anchor.x, y, .42), (.055, .016), out/'textures/fine-powder', seed)
        unsupported = set()
        for vertex in card.data.vertices:
            hits = [tree.ray_cast(Vector((vertex.co.x, vertex.co.y, .9)), Vector((0, 0, -1))) for tree in supports]
            heights = [h[0].z for h in hits if h[0] is not None and h[0].z > .35]
            if heights:
                vertex.co.z = max(heights)+.0005
            else:
                unsupported.add(vertex.index)
        label = card.name
        count = finish_powder(card, contacts, seed, unsupported)
        reports.append({'part': name, 'triangles': count, 'node': label if count else None,
                        'support_clearance_m': .0005, 'contact_checked': True})
    for index, spill in enumerate(record['debris']['spills']):
        name = spill['part']
        x = spill['origin_blender_m'][0]
        seed = 9750+index
        card = powder_card('FineFloorPowder_'+name, (x, -.515, .0005), (.045, .025),
                           out/'textures/fine-powder', seed, sectors=16)
        label = card.name
        count = finish_powder(card, contacts, seed)
        reports.append({'part': name, 'triangles': count, 'node': label if count else None,
                        'floor': True, 'support_clearance_m': .0005, 'contact_checked': True})
    record['pass10']['fine_powder'] = reports
    return record


def finish(source, out, library):
    record = deposit(source, out, library, visible_deposits=True, nonfloor_median=.004)
    reference = ROOT/'tmp/age/pass9'
    with bpy.data.libraries.load(str(reference/'deposited.blend'), link=False) as (_, target):
        target.objects = ['FoamDebris']
    baseline = target.objects[0]
    old = json.loads((reference/'simulation.json').read_text())['debris']
    retain_floor(bpy.data.objects['FoamDebris'], baseline, record['debris'], old)
    bpy.data.objects.remove(baseline, do_unlink=True)
    record['debris']['floor_reference'] = str(reference/'deposited.blend')
    shader = bpy.data.materials['Foam_Debris'].node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = (*FOAM_TAN, 1)
    fine_powder(out, record)
    checkpoint(out, record, 'deposited.blend')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass10')
    parser.add_argument('--library', type=Path, default=ROOT/'tmp/age/pass4/fragments8/fragment-library.blend')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    finish(args.source, args.out, args.library)
