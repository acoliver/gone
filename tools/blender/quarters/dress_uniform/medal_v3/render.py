"""Matched neutral clay cameras for frozen raw, fitted high, and game low."""
from pathlib import Path
import json
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path(__file__).resolve().parent
OUT = (Path(sys.argv[sys.argv.index('--output')+1]) if '--output' in sys.argv
       else ROOT/'tmp/issue130-v3/fit1')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'
scene.render.threads = 8
scene.render.resolution_x = scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'JPEG'
scene.render.image_settings.quality = 92
scene.view_settings.view_transform = 'AgX'
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.32,.32,.32,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .65
clay = bpy.data.materials.new('Neutral_Clay')
clay.use_nodes = True
bsdf = clay.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (.45,.45,.45,1)
bsdf.inputs['Metallic'].default_value = 0
bsdf.inputs['Roughness'].default_value = .73
for name,pos,power,size in [('Key',(-3,-4,6),650,4),('Fill',(4,-2,2),300,5),('Rear',(0,4,5),500,3)]:
    data=bpy.data.lights.new(name,'AREA')
    data.energy=power
    data.shape='DISK'
    data.size=size
    obj=bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    obj.location=pos
    obj.rotation_euler=(Vector((0,0,.5))-obj.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Matched_Orthographic')
camdata.type='ORTHO'
camdata.clip_start=.01
camdata.clip_end=100
camera=bpy.data.objects.new('Matched_Orthographic',camdata)
scene.collection.objects.link(camera)
scene.camera=camera
assets={}
normal_clays={}
for prefix,image_name in [('low-normalmapped','medal-low-normal.png')]:
    material=clay.copy()
    material.name=prefix+'_Clay'
    texture=material.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image=bpy.data.images.load(str(OUT/image_name))
    texture.image.colorspace_settings.name='Non-Color'
    normal=material.node_tree.nodes.new('ShaderNodeNormalMap')
    normal.space='TANGENT'
    material.node_tree.links.new(texture.outputs['Color'],normal.inputs['Color'])
    material.node_tree.links.new(normal.outputs['Normal'],material.node_tree.nodes['Principled BSDF'].inputs['Normal'])
    normal_clays[prefix]=material
for label,path in [('raw',OUT/'raw-oriented.glb'),('high',OUT/'medal-high.glb'),
                   ('low',OUT/'medal-low.glb'),('low-normalmapped',OUT/'medal-low-normalmapped.glb')]:
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects=[o for o in bpy.context.selected_objects if o.type=='MESH']
    for obj in objects:
        # Render-only scale improves camera/light numerical conditioning.
        for v in obj.data.vertices:
            v.co *= 100
        obj.data.materials.clear()
        obj.data.materials.append(normal_clays.get(label,clay))
        for p in obj.data.polygons:
            p.use_smooth=True
        obj.hide_render=True
    assets[label]=objects
match=json.loads((OUT/'camera-match.json').read_text())
views={
 'front':((0,-9,.5),(0,0,.5),5.05),
 'three-quarter':(match['position'],match['target'],5.05),
 'edge':((9,0,.5),(0,0,.5),5.05),
 'rear':((0,9,.5),(0,0,.5),5.05),
 'star-close':((-1,-9,1),(0,-.3,0),2.3),
 'ring-bar-close':((-3,-9,4.1),(0,0,2.35),3.8),
}
outputs=[]
for label,objects in assets.items():
    for obj in objects:
        obj.hide_render=False
    for name,(pos,target,scale) in views.items():
        camera.location=pos
        camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
        camdata.ortho_scale=scale
        path=OUT/(label+'-'+name+'.jpg')
        outputs.append(str(path))
        if '--reuse-unchanged' in sys.argv and label=='raw':
            assert path.exists()
            continue
        if '--only-three-quarter' in sys.argv and name!='three-quarter':
            assert path.exists()
            continue
        scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        print('RENDER_DONE',path,flush=True)
    for obj in objects:
        obj.hide_render=True
(OUT/'render-manifest.json').write_text(json.dumps({'images':outputs,'size':[900,900],
    'comparison_camera':match,
    'raw_shading':'Same smooth neutral clay as high and low; vertex positions unchanged.'},indent=2))
print('RENDER_COMPLETE',flush=True)
