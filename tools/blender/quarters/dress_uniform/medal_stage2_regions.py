"""Region-isolated selected-to-active projection with explicit patch-normal cages."""
import json
from pathlib import Path
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from medal_stage2_bake import SIZE, pixels, image_from, create_material


def subset(source, region, name):
    faces=[p for p in source.data.polygons if source.data.attributes['FeatureRegion'].data[p.index].value==region]
    ids=sorted({v for p in faces for v in p.vertices});remap={v:i for i,v in enumerate(ids)}
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata([source.data.vertices[v].co[:] for v in ids],[],[[remap[v] for v in p.vertices] for p in faces]);mesh.update()
    for dst,src in zip(mesh.polygons,faces):dst.use_smooth=src.use_smooth
    loops=[i for p in faces for i in p.loop_indices]
    mesh.normals_split_custom_set([source.data.corner_normals[i].vector[:] for i in loops])
    if source.data.uv_layers:
        layer=mesh.uv_layers.new(name='MedalUV')
        for dst,i in zip(layer.data,loops):dst.uv=source.data.uv_layers.active.data[i].uv
    for key in ['Medal_convex','Medal_concave']:
        if key in source.data.attributes:
            attr=mesh.attributes.new(key,'FLOAT_VECTOR','POINT')
            for dst,i in zip(attr.data,ids):dst.vector=source.data.attributes[key].data[i].vector
    attr=mesh.attributes.new('MedalRegionID','FLOAT_VECTOR','FACE')
    for dst in attr.data:dst.vector=((region+1)/16,)*3
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    return obj


def regions(out, maps=None):
    bpy.ops.wm.open_mainfile(filepath=str(out/'medal-bake.blend'))
    high,low=bpy.data.objects['MedalHigh'],bpy.data.objects['MedalLow']
    for obj in bpy.context.scene.objects:obj.hide_render=True;obj.hide_set(True)
    names=json.loads(low['feature_names'])
    pairs=[]
    for i,name in enumerate(names):
        h=subset(high,i,'BakeHigh_'+name);l=subset(low,i,'BakeLow_'+name)
        # Cage normals are computed on each geometric patch, not averaged through adjacent enamel/metal walls.
        cage=bpy.data.objects.new('Cage_'+name,l.data.copy());bpy.context.scene.collection.objects.link(cage)
        cage.data.free_normals_split() if hasattr(cage.data,'free_normals_split') else None
        cage.data.normals_split_custom_set([(0,0,0)]*len(cage.data.loops))
        directions=[v.normal.copy() for v in cage.data.vertices]
        for v,n in zip(cage.data.vertices,directions):v.co+=n*.00015
        cage.hide_render=True
        sm,emit=create_material('Source_'+name);h.data.materials.append(sm)
        tm,_=create_material('Target_'+name);l.data.materials.append(tm)
        tex=tm.node_tree.nodes.new('ShaderNodeTexImage');tm.node_tree.nodes.active=tex
        pairs.append((name,h,l,cage,sm,emit,tex))
        h.hide_render=False;l.hide_render=True
    scene=bpy.context.scene;scene.cycles.device='CPU';scene.cycles.seed=130303
    scene.render.threads_mode='FIXED';scene.render.threads=10
    scene.render.bake.use_cage=True;scene.render.bake.use_selected_to_active=True
    scene.render.bake.max_ray_distance=.00030;scene.render.bake.margin=16;scene.render.bake.margin_type='EXTEND'
    scene.render.bake.normal_space='TANGENT';scene.render.bake.normal_r='POS_X';scene.render.bake.normal_g='POS_Y';scene.render.bake.normal_b='POS_Z'
    atlas=np.load(out/'atlas-context.npz')
    ownership=atlas['expected'];occupied=atlas['mask']
    def execute(key,kind='EMIT',samples=64):
        combined=np.zeros((SIZE,SIZE,4),np.float32)
        start=time.time()
        # Feature boundaries can share one chart. Dilate only after merging ownership,
        # otherwise a later feature's gutter overwrites an earlier feature's interior.
        scene.render.bake.margin=0
        scene.render.bake.normal_space='OBJECT' if key=='high_shading_normal' else 'TANGENT'
        for index,(name,h,l,cage,sm,emit,tex) in enumerate(pairs):
            im=bpy.data.images.new(key+'_'+name,SIZE,SIZE,alpha=True,float_buffer=True)
            im.colorspace_settings.name='Non-Color'
            tex.image=im
            nt=sm.node_tree
            socket=None
            if key=='projected_regions':
                a=nt.nodes.new('ShaderNodeAttribute');a.attribute_name='MedalRegionID';socket=a.outputs['Vector']
            elif key.startswith('curvature_'):
                a=nt.nodes.new('ShaderNodeAttribute');a.attribute_name='Medal_'+key.removeprefix('curvature_');socket=a.outputs['Vector']
            elif key.startswith('ao_'):
                a=nt.nodes.new('ShaderNodeAmbientOcclusion');a.samples=1;a.only_local=False
                a.inputs['Distance'].default_value=.0003 if key=='ao_near' else .002;socket=a.outputs['AO']
            elif key in ['surface_position','high_shading_normal']:
                g=nt.nodes.new('ShaderNodeNewGeometry');a=nt.nodes.new('ShaderNodeVectorMath');a.operation='MULTIPLY_ADD'
                nt.links.new(g.outputs['Position' if key=='surface_position' else 'Normal'],a.inputs[0])
                a.inputs[1].default_value=(20,20,20) if key=='surface_position' else (.5,.5,.5)
                a.inputs[2].default_value=(.5,.5,.5);socket=a.outputs[0]
            if socket is not None:nt.links.new(socket,emit.inputs['Color'])
            bpy.ops.object.select_all(action='DESELECT')
            h.select_set(True);l.hide_render=False;l.select_set(True);bpy.context.view_layer.objects.active=l
            scene.render.bake.cage_object=cage
            scene.render.bake.use_clear=True;scene.cycles.samples=samples
            print('REGION BAKE',key,name,flush=True)
            bpy.ops.object.bake(type=kind,uv_layer='MedalUV')
            l.hide_render=True
            values=pixels(im)
            use=occupied&(ownership==index)
            combined[use]=values[use]
            tex.image=None
            bpy.data.images.remove(im)
        np.save(out/(key+'_raw.npy'),combined)
        np.save(out/(key+'.npy'),combined)
        image_from(key,combined,out)
        print('REGION MAP DONE',key,round(time.time()-start,2),flush=True)
    for key in maps or ['projected_regions','geometry_normal','curvature_convex','curvature_concave','surface_position','high_shading_normal','ao_near','ao_local']:
        execute(key,'NORMAL' if key in ['geometry_normal','high_shading_normal'] else 'EMIT',128 if key.startswith('ao_') else 64)
    # Only the original, unchanged geometry is retained in the editable bake source.
    for name,h,l,cage,sm,emit,tex in pairs:
        for o in [h,l,cage]:bpy.data.objects.remove(o,do_unlink=True)
    low.hide_set(False);low.hide_render=False
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'medal-bake.blend'))
    settings=json.loads((out/'bake-settings.json').read_text())
    settings.update(projection='Explicit region-normal cages on feature-isolated copies; original coordinates and corner shading normals retained',
        cage_regions=names,ao_node_samples=1,ao_path_samples=128,assembled_high_for_ao=True,
        preliminary_unisolated_wrong_region_texels=14615,regional_cage_extrusion_mm=.15)
    (out/'bake-settings.json').write_text(json.dumps(settings,indent=2))
    print('REGIONAL BAKES COMPLETE',flush=True)


if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    regions(Path(args[0]),args[1:] or None)
