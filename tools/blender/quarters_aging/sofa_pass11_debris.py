"""Larger opening-led crumb deposits and wider, contact-fitted powder drifts."""
import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import surface_tree
from powder_cards import powder_card
from sofa_decay_debris import DepositContacts, deposit
from sofa_decay_policy import ORDER
from sofa_full_decay import ROOT, checkpoint
from sofa_pass10_debris import finish_powder
from sofa_pass10_material import FOAM_TAN


def powder(out, record):
    contacts = DepositContacts([o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('aged_export')])
    supports = [surface_tree(bpy.data.objects[n+'_GameContact']) for n in ORDER[:3]]
    supports += [surface_tree(bpy.data.objects[n+'_Residue']) for n in ORDER]
    supports += [surface_tree(bpy.data.objects['Frame'])]
    reports = []
    for index, name in enumerate(ORDER[:3]):
        spec = record['pass11']['parts'][name]['gash']['spec']
        x = spec['centre'][0]
        placements = [(x+dx, -.365, .42, .026, .014, False) for dx in [-.09, -.03, .03, .09]]
        placements += [(x+dx, -.235, .42, .025, .014, False) for dx in [-.06, 0., .06]]
        placements += [(x-.03, -.55, .0005, .195, .060, True),
                       (x+.04, -.70, .0005, .175, .080, True)]
        for item, (px, py, z, rx, ry, floor) in enumerate(placements):
            seed = 10010+index*37+item
            card = powder_card(f'Pass11Powder_{name}_{item}', (px, py, z), (rx, ry),
                               out/'textures/fine-powder', seed, sectors=16 if floor else 8)
            unsupported = set()
            if not floor:
                for vertex in card.data.vertices:
                    hits = [tree.ray_cast(Vector((vertex.co.x, vertex.co.y, .9)), Vector((0, 0, -1))) for tree in supports]
                    heights = [h[0].z for h in hits if h[0] is not None and h[0].z > .35]
                    if heights:
                        vertex.co.z = max(heights)+.0006
                    else:
                        unsupported.add(vertex.index)
            label = card.name
            count = finish_powder(card, contacts, seed, unsupported)
            reports.append(dict(part=name, node=label if count else None, floor=floor,
                                triangles=count, footprint_radii_m=[rx, ry], contact_checked=True))
    record['pass11']['powder'] = reports


def finish(source, out, library):
    from sofa_pass11_fragments import library as compact_library
    library = compact_library(library, out/'compact-fragments')
    record = deposit(source, out, library, seed=10011, visible_deposits=True,
                     nonfloor_median=.0075, deck_target=36, floor_counts=(3, 5, 3, 2, 1),
                     floor_radius=.30, floor_spacing=.030, floor_median=.0085, front_lip_target=16)
    shader = bpy.data.materials['Foam_Debris'].node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = (*FOAM_TAN, 1)
    record['debris']['method'] = 'target-led front/deck crumbs and wider radially decaying floor spills; all geometric contacts tested'
    powder(out, record)
    checkpoint(out, record, 'deposited.blend')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'tmp/age/pass11/throw-detailed.blend')
    parser.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass11')
    parser.add_argument('--library', type=Path, default=ROOT/'tmp/age/pass4/fragments8/fragment-library.blend')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    finish(args.source, args.out, args.library)
