"""Bake sofa detail, pack its cover atlas and assemble a non-published preview."""
import argparse
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_down import bake
from common import export
from fabric_mesh import join
from fringe_cards import cards
from opacity_bake import opacity_bake
from sofa_decay_material import exportable_material, fabric_fringe, pack_covers, upholstery_fringe
from sofa_decay_policy import FOAM, ORDER, UPHOLSTERY
from sofa_full_decay import ROOT, checkpoint


def game_surfaces():
    return [o for o in bpy.context.scene.objects if o.type == 'MESH' and
            (o.name in {'Frame', 'Feet', 'Rivets', 'DecayFloor'} or
             o.name.endswith(('_GameContact', '_Residue', '_Fringe')))]


def detail(source, out, size=2048):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    record = json.loads(bpy.context.scene['sofa_decay_record'])
    for obj in bpy.context.scene.objects:
        for mod in list(obj.modifiers):
            if mod.type == 'COLLISION':
                obj.modifiers.remove(mod)
    fringe_mat = upholstery_fringe(out/'textures/fringe', 9601)
    record.setdefault('materials', {})
    for name in ORDER:
        dense = bpy.data.objects[name]
        low = bpy.data.objects[name+'_GameContact']
        texture_dir = out/'textures'/name.lower()
        low.hide_render = False
        mat, paths = bake(dense, low, texture_dir, size=size, samples=8)
        mat.name = 'CharcoalUpholstery_'+name
        alpha, alpha_report = opacity_bake(low, texture_dir/'opacity.png', size=size,
                                          seed=record['cushions'][name]['plan']['seed'], gain=4.5)
        maps = exportable_material(mat, UPHOLSTERY, texture_dir, alpha)
        maps.update(opacity=alpha_report, baked=paths)
        dense.hide_render = True
        low.hide_render = False
        dense['aged_export'] = False
        low['aged_export'] = True
        residue = bpy.data.objects[name+'_Residue']
        dense_residue = bpy.data.objects[name+'_DenseResidue']
        residue.hide_render = False
        mat_residue, residue_paths = bake(dense_residue, residue, texture_dir/'residue', size=min(1024, size), samples=8)
        mat_residue.name = 'Foam_'+name
        residue_maps = exportable_material(mat_residue, FOAM, texture_dir/'residue')
        dense_residue.hide_render = True
        residue.hide_render = False
        residue['aged_export'] = True
        fringe, report = cards(low, fringe_mat, record['cushions'][name]['plan']['seed'],
                               spacing=.005, boundary_group='Lip shrink', blockers=game_surfaces())
        fringe.name = name+'_Fringe'
        record['materials'][name] = {'cover': maps, 'residue': residue_maps,
                                     'residue_baked': residue_paths, 'fringe': report}
        checkpoint(out, record, name+'-detailed.blend')
    checkpoint(out, record, 'detailed.blend')
    return record


def throw_detail(source, out, size=2048):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    record = json.loads(bpy.context.scene['sofa_decay_record'])
    for obj in bpy.context.scene.objects:
        for mod in list(obj.modifiers):
            if mod.type == 'COLLISION':
                obj.modifiers.remove(mod)
    obj = bpy.data.objects['Throw']
    low = bpy.data.objects['Throw_GameContact']
    low.hide_render = False
    mat, paths = bake(obj, low, out/'textures/throw', size=size, samples=8)
    mat.name = 'OatmealWool_Decay'
    alpha, alpha_report = opacity_bake(low, out/'textures/throw/opacity.png', size=size, seed=9699)
    maps = exportable_material(mat, (.56, .48, .35), out/'textures/throw', alpha)
    obj.hide_render = True
    obj['aged_export'] = False
    low.hide_render = False
    low['aged_export'] = True
    fringe, fringe_report = cards(low, fabric_fringe(out/'textures/wool-fringe', 9699, (.56, .48, .35), wool=True),
                                  9699, wool=True, spacing=.009, boundary_group='Lip shrink', blockers=game_surfaces())
    fringe.name = 'Throw_Fringe'
    record['throw']['materials'] = {'maps': maps, 'baked': paths, 'opacity': alpha_report, 'fringe': fringe_report}
    checkpoint(out, record, 'throw-detailed.blend')
    return record


def preview(source, out):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    record = json.loads(bpy.context.scene['sofa_decay_record'])
    for obj in bpy.context.scene.objects:
        for mod in list(obj.modifiers):
            if mod.type == 'COLLISION':
                obj.modifiers.remove(mod)
    covers = [bpy.data.objects[n+'_GameContact'] for n in ORDER]
    record['cover_atlas'] = pack_covers(covers, out/'textures/atlas')
    for name in ORDER:
        dense = bpy.data.objects[name]
        dense.name = name+'_DenseCover'
        low = bpy.data.objects[name+'_GameContact']
        low.name = name
        join(low, [bpy.data.objects[name+'_Residue']])
        low['aged_export'] = True
    if 'Throw_GameContact' in bpy.data.objects:
        bpy.data.objects['Throw'].name = 'Throw_DenseCover'
        bpy.data.objects['Throw_GameContact'].name = 'Throw'
    for obj in list(bpy.context.scene.objects):
        if obj.type == 'MESH' and not obj.get('aged_export'):
            bpy.data.objects.remove(obj, do_unlink=True)
    record['publication'] = 'preview only; required gates must pass before replacing the game asset'
    checkpoint(out, record, 'sofa-preview.blend')
    export(out/'sofa-preview.glb')
    bpy.ops.wm.open_mainfile(filepath=str(out/'sofa-preview.blend'))
    export(out/'sofa-preview-repeat.glb')
    return record


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', choices=['detail', 'throw-detail', 'preview'], required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass6')
    p.add_argument('--size', type=int, default=2048)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.out.mkdir(parents=True, exist_ok=True)
    if a.stage == 'detail':
        detail(a.source, a.out, a.size)
    elif a.stage == 'throw-detail':
        throw_detail(a.source, a.out, a.size)
    else:
        preview(a.source, a.out)
