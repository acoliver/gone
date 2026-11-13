"""Bake paired high-to-low tangent normals into the existing 2048 low UVs."""
from pathlib import Path
import json
import sys
import bpy

SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE))
from glb_normals import preserve_normals
OUT=(Path(sys.argv[sys.argv.index('--output')+1]) if '--output' in sys.argv
     else SOURCE.parents[4]/'tmp/issue130-v3/fit1')
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=1
scene.render.threads_mode='FIXED'
scene.render.threads=8
scene.render.bake.use_selected_to_active=True
scene.render.bake.normal_space='TANGENT'
scene.render.bake.cage_extrusion=.0005
scene.render.bake.max_ray_distance=.001
scene.render.bake.margin=8
scene.render.bake.use_clear=False
reports=[]
body_extrusion=(float(sys.argv[sys.argv.index('--body-extrusion')+1])
                if '--body-extrusion' in sys.argv else .0005)
body_ray_distance=(float(sys.argv[sys.argv.index('--body-ray-distance')+1])
                   if '--body-ray-distance' in sys.argv else .001)
pairs=[('pass'+OUT.name.removeprefix('fit'),OUT,'')]
for label,folder,prefix in pairs:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    assets={}
    for kind in ['high','low']:
        bpy.ops.import_scene.gltf(filepath=str(folder/('medal-'+kind+'.glb')))
        assets[kind]={o.name.split('_')[0]:o for o in bpy.context.selected_objects if o.type=='MESH'}
    image=bpy.data.images.new(label+'_Tangent_Normal_2048',width=2048,height=2048,alpha=False)
    image.generated_color=(.5,.5,1,1)
    image.colorspace_settings.name='Non-Color'
    image.filepath_raw=str(OUT/(prefix+'medal-low-normal.png'))
    image.file_format='PNG'
    for part,low in assets['low'].items():
        material=bpy.data.materials.new(label+'_'+part+'_Bake')
        material.use_nodes=True
        texture=material.node_tree.nodes.new('ShaderNodeTexImage')
        texture.image=image
        material.node_tree.nodes.active=texture
        low.data.materials.clear()
        low.data.materials.append(material)
        for face in low.data.polygons:
            face.use_smooth=True
        high=assets['high'][part]
        bpy.ops.object.select_all(action='DESELECT')
        high.select_set(True)
        low.select_set(True)
        bpy.context.view_layer.objects.active=low
        # The old body cage starts beyond the lower inner wall and bakes that
        # wall onto the field. Local ray diagnostics establish 0.1 mm clearance.
        corrected=folder==OUT and part=='Body'
        scene.render.bake.cage_extrusion=body_extrusion if corrected else .0005
        scene.render.bake.max_ray_distance=body_ray_distance if corrected else .001
        bpy.ops.object.bake(type='NORMAL')
        normal=material.node_tree.nodes.new('ShaderNodeNormalMap')
        normal.space='TANGENT'
        material.node_tree.links.new(texture.outputs['Color'],normal.inputs['Color'])
        material.node_tree.links.new(normal.outputs['Normal'],material.node_tree.nodes['Principled BSDF'].inputs['Normal'])
        print('BAKED_PART',label,part,flush=True)
    image.save()
    if folder==OUT:
        bpy.ops.object.select_all(action='DESELECT')
        for low in assets['low'].values():
            low.select_set(True)
        bpy.context.view_layer.objects.active=next(iter(assets['low'].values()))
        bpy.ops.export_scene.gltf(filepath=str(OUT/'medal-low-normalmapped.glb'),use_selection=True,
            export_format='GLB',export_yup=True,export_normals=True,export_texcoords=True,
            export_tangents=True,export_materials='EXPORT')
        changes=preserve_normals(OUT/'medal-low.glb',OUT/'medal-low-normalmapped.glb')
        (OUT/'normal-export-roundtrip.json').write_text(json.dumps(changes,indent=2))
    reports.append({'pass':label,'image':image.filepath_raw,'size':[2048,2048],
        'parts':sorted(assets['low']),'method':'Cycles selected-to-active tangent normal bake, matching high/low parts, existing exported low TEXCOORD_0; smooth low normals.',
        'cage_extrusion_m':{p:body_extrusion if p=='Body' and folder==OUT else .0005 for p in assets['low']},
        'max_ray_distance_m':{p:body_ray_distance if p=='Body' and folder==OUT else .001 for p in assets['low']},
        'margin_pixels':8})
(OUT/'normal-bake.json').write_text(json.dumps(reports,indent=2))
print('BAKE_COMPLETE',flush=True)
