"""Repeat the rail arrangement and dry finish from retained fitted cloth inputs."""
import argparse
import json
from pathlib import Path
import sys

import bpy

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/'her_jacket')]
import arrange
from cloth_tools import retain_pattern,save_state


def restore_inputs():
    originals=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('aged_export') and not o.get('finish_generated')]
    for obj in originals:
        name=obj.name+'_FinishInput'
        source=bpy.data.objects.get(name)
        if source is None:
            source=retain_pattern(obj);source.name=name;source.data.name=name
    for obj in list(bpy.context.scene.objects):
        if obj.get('finish_generated'):bpy.data.objects.remove(obj,do_unlink=True)
    for source in list(bpy.context.scene.objects):
        if not source.name.endswith('_FinishInput'):continue
        name=source.name.removesuffix('_FinishInput')
        obj=bpy.data.objects.get(name)
        if obj is None:
            obj=source.copy();obj.name=name;bpy.context.collection.objects.link(obj)
        obj.data=source.data.copy()
        obj['aged_export']=True;obj.hide_render=False;obj.hide_set(False)
    bpy.data.orphans_purge(do_recursive=True)


def finish(state,arrangement_only=False):
    bpy.ops.wm.open_mainfile(filepath=str(HERE/f'her_dresses-{state}.blend'))
    record=json.loads((HERE/f'{state}.json').read_text())
    restore_inputs()
    for name in arrange.POSITIONS:
        for suffix in ('','_Hanger','_FrayedYarns'):
            obj=bpy.data.objects.get(name+suffix)
            if obj is not None:
                placement=arrange.apply(obj,name)
        record['dresses'][name]['arrangement']=placement
    if state=='aged' and not arrangement_only:
        import refine
        record['dry_finish']=refine.apply()
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH' and obj.get('aged_export'):
            for mat in obj.data.materials:mat.use_backface_culling=True
    record['sidedness']='Single-sided materials for the reflected room; cloth retains both sewn plies and fringe has explicit opposite faces'
    record['finish_input']='Retained *_FinishInput mesh per exported component; all finishes restart from these fitted inputs'
    save_state(HERE,'her_dresses',state,record)
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',choices=['remembered','aged'],required=True)
    p.add_argument('--arrangement-only',action='store_true')
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    finish(a.state,a.arrangement_only)
