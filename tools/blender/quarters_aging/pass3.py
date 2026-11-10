"""Run one recorded cut-first physics trial; publish only explicitly selected bakes."""
import argparse
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import collision, export, save

ROOT=Path(__file__).resolve().parents[3]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prop',choices=['sofa','dress_uniform'],required=True)
    parser.add_argument('--trial',required=True)
    parser.add_argument('--frames',type=int,default=240)
    parser.add_argument('--publish',action='store_true')
    parser.add_argument('--finish-tunic',type=Path)
    parser.add_argument('--resume-sofa',type=Path)
    parser.add_argument('--parts',nargs='+')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    folder=ROOT/'tools/blender/quarters'/args.prop
    out=ROOT/'tmp/age/pass3'/args.trial; out.mkdir(parents=True,exist_ok=True)
    stem='sofa' if args.prop=='sofa' else 'tunic'
    params=json.loads((folder/'aging.json').read_text())
    record={'trial':args.trial,'seed':params['seed'],'prop':args.prop,'frames':args.frames,'status':'started'}
    trials_path=folder/'cloth-trials.json'
    trials=json.loads(trials_path.read_text()); trials.setdefault('pass3',[]).append(record)
    trials_path.write_text(json.dumps(trials,indent=2)+'\n')
    if args.resume_sofa:
        if args.prop!='sofa' or not args.parts:raise ValueError('--resume-sofa requires sofa and --parts')
        from sofa_pass3 import restore_parts
        restore_parts(args.resume_sofa,folder/f'{stem}-working.blend',args.parts)
        record['reused_bake']=str(args.resume_sofa);record['resimulated_parts']=args.parts
    else:
        if args.parts:raise ValueError('--parts requires --resume-sofa')
        bpy.ops.wm.open_mainfile(filepath=str(folder/f'{stem}-working.blend'))
    retained=set(params['parts'])|({'FoamDebris','ThrowDetachedPiece'} if args.resume_sofa else set())
    for obj in list(bpy.context.scene.objects):
        if obj.type=='MESH' and obj.name not in retained:
            bpy.data.objects.remove(obj,do_unlink=True)
    for name in sorted(retained&set(bpy.data.objects.keys())):
        obj=bpy.data.objects[name]; obj.hide_set(False); obj.hide_render=False
        obj.modifiers.clear(); obj['aged_export']=True
    bpy.context.scene.render.fps=24
    bpy.context.scene.gravity=(0,0,-9.81)
    bpy.ops.mesh.primitive_plane_add(size=8,location=(0,0,0 if args.prop=='sofa' else -.95))
    ground=bpy.context.object;ground.name='AgingFloorCollider'; ground.hide_render=True
    collision(ground,.001)
    if args.prop=='sofa':
        from sofa_pass3 import build
    else:
        from tunic_pass3 import build
    bpy.context.scene['pass3_trial_dir']=str(out)
    try:
        if args.finish_tunic:
            if args.prop!='dress_uniform':raise ValueError('--finish-tunic requires dress_uniform')
            bpy.ops.wm.open_mainfile(filepath=str(args.finish_tunic.resolve()))
            from tunic_pass3 import finish
            record['reused_simulation']=str(args.finish_tunic)
            record['construction']=finish(json.loads(bpy.context.scene['tunic_simulated_state']))
        else:
            if args.resume_sofa:
                record['construction']=build(params['seed'],args.frames,args.parts)
            else:
                record['construction']=build(params['seed'],args.frames)
        bpy.data.objects.remove(bpy.data.objects['AgingFloorCollider'],do_unlink=True)
        record['status']='baked'
        save(out/f'{stem}-aged.blend',record)
        export(out/f'{args.prop}_aged.glb')
        (out/f'{args.prop}-trial.json').write_text(json.dumps(record,indent=2)+'\n')
        if args.publish:
            save(folder/f'{stem}-aged.blend',record)
            export(ROOT/params['asset'])
            (folder/f'{stem}-aged.json').write_text(json.dumps(record,indent=2)+'\n')
    except Exception as error:
        record['status']='failed';record['error']=str(error)
        raise
    finally:
        trials=json.loads(trials_path.read_text())
        index=next(i for i,value in enumerate(trials['pass3']) if value['trial']==args.trial)
        trials['pass3'][index]=record
        trials_path.write_text(json.dumps(trials,indent=2)+'\n')
        (out/f'{args.prop}-trial.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':
    main()
