"""Pass-10 finishing of the retained pass-9 solve; never publish a failed trial."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_down import boundary_hausdorff
from cloth_metrics import lip_lift, save_surface, surface_metrics
from sofa_decay_finish import detail, throw_detail
from sofa_decay_policy import ORDER
from sofa_full_decay import ROOT, checkpoint
from sofa_pass8_finish import clearance, save_lip_classes
from sofa_pass9_finish import carry_clearance, points
from sofa_pass10_material import replace_pixels, tan_residue
from sofa_pass10_mesh import break_planar_patches, fair_interior, restore_hold_patch, roughen_residue


def geometry(source, prepared, out, cover_limit=.006, throw_limit=.006):
    bpy.ops.wm.open_mainfile(filepath=str(prepared))
    rest = points(bpy.data.objects['Throw'])
    bpy.ops.wm.open_mainfile(filepath=str(source))
    record = json.loads(bpy.context.scene['sofa_decay_record'])
    record['pass10'] = {'source': str(source), 'method': 'retained pass-9 cloth solve, bounded reduction fairing and local pinned-fold repair'}
    throw = bpy.data.objects['Throw']
    record['pass10']['hold_repair'] = restore_hold_patch(throw, rest)
    from bake_down import decimate
    bpy.data.objects.remove(bpy.data.objects['Throw_GameContact'], do_unlink=True)
    low, reduction = decimate(throw, 3200, protect=.002, keep_factor=4)
    low.name = 'Throw_GameContact'
    low.hide_render = True
    low['aged_export'] = False
    record['throw']['reduction'] = reduction
    dense_right = bpy.data.objects['BackCushion_R']
    bpy.data.objects.remove(bpy.data.objects['BackCushion_R_GameContact'], do_unlink=True)
    low_right, reduction = decimate(dense_right, 2300, protect=.002, keep_factor=4)
    low_right.name = 'BackCushion_R_GameContact'
    low_right.hide_render = True
    low_right['aged_export'] = False
    record['cushions']['BackCushion_R']['cover_decimation'] = reduction
    for name in [*ORDER, 'Throw']:
        dense, low = bpy.data.objects[name], bpy.data.objects[name+'_GameContact']
        original = points(low)
        if name in {'BackCushion_C', 'BackCushion_R'}:
            fairing = fair_interior(low, maximum=cover_limit, iterations=5, nonshrinking=True)
        else:
            maximum = .008 if name == 'BackCushion_L' else throw_limit if name == 'Throw' else cover_limit
            fairing = fair_interior(low, maximum=maximum)
        transfer = carry_clearance(dense, low, original)
        item = record['throw'] if name == 'Throw' else record['cushions'][name]
        item['pass10_fairing'] = fairing
        item['pass10_dense_transfer'] = transfer
    for name in ORDER[:3]:
        for suffix in ['DenseResidue', 'Residue']:
            residue = bpy.data.objects[name+'_'+suffix]
            report = roughen_residue(residue, record['cushions'][name]['plan']['seed'])
            record['cushions'][name]['pass10_residue_detail'] = report
        record['cushions'][name]['pass10_crust_relief'] = break_planar_patches(bpy.data.objects[name+'_Residue'])
    supports = [bpy.data.objects[n] for n in ['Frame', 'Feet', 'Rivets', 'DecayFloor']]
    supports += [bpy.data.objects[n+'_Residue'] for n in ORDER]
    covers = [bpy.data.objects[n+'_GameContact'] for n in [*ORDER, 'Throw']]
    originals = {o.name: points(o) for o in covers}
    record['pass10']['clearance'] = clearance(supports+covers, {o.name for o in covers})
    for name in [*ORDER, 'Throw']:
        dense, low = bpy.data.objects[name], bpy.data.objects[name+'_GameContact']
        item = record['throw'] if name == 'Throw' else record['cushions'][name]
        item['pass10_clearance_transfer'] = carry_clearance(dense, low, originals[low.name])
        item.update(dense_metrics=surface_metrics(dense), game_metrics=surface_metrics(low))
        reduction = item['reduction' if name == 'Throw' else 'cover_decimation']
        reduction['boundary_hausdorff_upper_m'] = boundary_hausdorff(dense, low)
        stem = 'throw' if name == 'Throw' else name
        save_surface(dense, out/(stem+'-dense.npz'))
        save_surface(low, out/(stem+'-game.npz'))
        if name == 'Throw':
            continue
        item['G5'] = lip_lift(dense)
        save_lip_classes(dense, out/(name+'-lip-classes.npz'))
        for suffix, label in [('DenseResidue', 'dense'), ('Residue', 'game')]:
            residue = bpy.data.objects[name+'_'+suffix]
            save_surface(residue, out/(name+'-'+label+'-residue.npz'))
    checkpoint(out, record, 'geometry.blend')


def apply_opacity(record, out):
    from sofa_pass10_opacity import opacity
    for name in [*ORDER, 'Throw']:
        low = bpy.data.objects[name+'_GameContact']
        seed = 9699 if name == 'Throw' else record['cushions'][name]['plan']['seed']
        alpha, report = opacity(low, out/'textures'/name.lower()/'pass10_opacity.png', seed)
        shader = low.data.materials[0].node_tree.nodes['Principled BSDF']
        image = shader.inputs['Base Color'].links[0].from_node.image
        pixels = np.array(image.pixels[:], dtype=np.float32).reshape(image.size[1], image.size[0], 4)
        pixels[:, :, 3] = np.array(alpha.pixels[:], dtype=np.float32).reshape(image.size[1], image.size[0], 4)[:, :, 0]
        replace_pixels(image, pixels)
        if name == 'Throw':
            record['throw']['materials']['opacity'] = report
        else:
            record['materials'][name]['cover']['opacity'] = report


def materials(source, out):
    detail(source, out)
    throw_detail(out/'detailed.blend', out)
    record = json.loads(bpy.context.scene['sofa_decay_record'])
    apply_opacity(record, out)
    for name in ORDER:
        dense = bpy.data.objects[name+'_DenseResidue']
        low = bpy.data.objects[name+'_Residue']
        maps = tan_residue(dense, low, out/'textures'/name.lower()/'residue')
        record['materials'][name]['residue'] = maps
    checkpoint(out, record, 'throw-detailed.blend')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['geometry', 'materials'], required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--prepared', type=Path, default=ROOT/'tmp/age/pass9/throw-prepared.blend')
    parser.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass10')
    parser.add_argument('--cover-limit', type=float, default=.006)
    parser.add_argument('--throw-limit', type=float, default=.006)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.out.mkdir(parents=True, exist_ok=True)
    if args.stage == 'geometry':
        geometry(args.source, args.prepared, args.out, args.cover_limit, args.throw_limit)
    else:
        materials(args.source, args.out)
