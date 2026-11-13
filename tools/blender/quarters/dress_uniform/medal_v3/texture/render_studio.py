"""Cycles comparison renders of the unchanged game mesh at measured display scales."""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import FIT, OUT

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=64
scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED'
scene.render.threads=8
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=0
# Soft directional world gradient gives metal a reflection outside the area cards.
world=scene.world or bpy.data.worlds.new('Neutral_Gradient_World')
scene.world=world
world.use_nodes=True
nodes,links=world.node_tree.nodes,world.node_tree.links
nodes.clear()
tex=nodes.new('ShaderNodeTexCoord')
separate=nodes.new('ShaderNodeSeparateXYZ')
ramp=nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position=.0
ramp.color_ramp.elements[0].color=(.055,.065,.08,1)
ramp.color_ramp.elements[1].position=1.
ramp.color_ramp.elements[1].color=(.7,.72,.75,1)
maprange=nodes.new('ShaderNodeMapRange')
maprange.inputs['From Min'].default_value=-1
maprange.inputs['From Max'].default_value=1
background=nodes.new('ShaderNodeBackground')
background.inputs['Strength'].default_value=.8
output=nodes.new('ShaderNodeOutputWorld')
links.new(tex.outputs['Normal'],separate.inputs[0])
links.new(separate.outputs['Z'],maprange.inputs['Value'])
links.new(maprange.outputs['Result'],ramp.inputs[0])
links.new(ramp.outputs['Color'],background.inputs['Color'])
links.new(background.outputs[0],output.inputs['Surface'])

bpy.ops.import_scene.gltf(filepath=str(FIT/'medal-low-normalmapped.glb'))
objects=[o for o in bpy.context.selected_objects if o.type=='MESH']
for obj in objects:
    # Transform objects only for studio conditioning; exported source never changes.
    obj.scale=(100,100,100)
    obj.hide_render=False
body=next(o for o in objects if o.name.startswith('Body'))
allpoints=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
bpy.context.view_layer.update()
allpoints=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
center=(min(p.z for p in allpoints)+max(p.z for p in allpoints))/2
light_settings=[]
for name,pos,power,size,shape in [
    ('Softbox_Key',(-4,-6,6),420,4,'RECTANGLE'),
    ('Softbox_Fill',(5,-4,1),180,5,'RECTANGLE'),
    ('Rim_Card',(-3,1,3),240,3,'RECTANGLE'),
]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape=shape;data.size=size;data.size_y=size*1.4
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=pos
    obj.rotation_euler=(Vector((0,0,.6))-obj.location).to_track_quat('-Z','Y').to_euler()
    light_settings.append({'name':name,'position':pos,'watts':power,'size':size,'size_y':size*1.4})
# Broad white and dark reflection cards, outside the camera and away from the medal.
for name,pos,scale,color in [('White_Reflection',(-4,-2,1),(1.5,1.5,3),(.8,.8,.8,1)),
                              ('Dark_Reflection',(4,1,1),(1.5,1.5,3),(.025,.025,.025,1))]:
    bpy.ops.mesh.primitive_plane_add(size=2,location=pos)
    obj=bpy.context.object;obj.name=name;obj.scale=scale
    obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('Z','Y').to_euler()
    obj.visible_camera=False
    material=bpy.data.materials.new(name);material.diffuse_color=color;material.use_nodes=True
    bsdf=material.node_tree.nodes['Principled BSDF'];bsdf.inputs['Base Color'].default_value=color;bsdf.inputs['Roughness'].default_value=.85
    obj.data.materials.append(material)
camdata=bpy.data.cameras.new('Measured_Orthographic');camdata.type='ORTHO';camdata.clip_start=.01
camera=bpy.data.objects.new('Measured_Orthographic',camdata);scene.collection.objects.link(camera);scene.camera=camera
textures=json.loads((OUT/'textures.json').read_text())
projection=json.loads((OUT/'projection/settings.json').read_text())
rows=[]
for route,states in textures.items():
    for state,maps in states.items():
        material=bpy.data.materials.new(f'{route}_{state}_ImageDerived')
        material.use_nodes=True
        nodes,links=material.node_tree.nodes,material.node_tree.links
        bsdf=nodes.get('Principled BSDF')
        for name,socket,noncolor in [('basecolor','Base Color',False),('roughness','Roughness',True),('metallic','Metallic',True)]:
            tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(maps[name],check_existing=True)
            tex.image.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
            links.new(tex.outputs['Color'],bsdf.inputs[socket])
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(maps['normal'],check_existing=True);tex.image.colorspace_settings.name='Non-Color'
        nm=nodes.new('ShaderNodeNormalMap');nm.space='TANGENT'
        links.new(tex.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bsdf.inputs['Normal'])
        # The enamel gloss is represented by dielectric roughness; metallic map
        # makes the same BSDF brass on geometry-owned metal, enamel elsewhere.
        bsdf.inputs['IOR'].default_value=1.5
        for obj in objects:
            obj.data.materials.clear();obj.data.materials.append(material)
        for view in ['front','oblique']:
            angle=0. if view=='front' else projection['photos'][state]['oblique']['inferred_azimuth_degrees']
            yaw=math.radians(angle)
            target=Vector((0,0,center))
            direction=Vector((-math.sin(yaw),-math.cos(yaw),.06 if view=='oblique' else 0))
            camera.location=target+direction*12
            camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
            for scale,resolution,width in [('game',(900,1100),480),('close',(1400,1800),900)]:
                scene.render.resolution_x,scene.render.resolution_y=resolution
                camdata.ortho_scale=6.
                bpy.context.view_layer.update()
                coords=[world_to_camera_view(scene,camera,body.matrix_world@v.co) for v in body.data.vertices]
                current=(max(p.x for p in coords)-min(p.x for p in coords))*resolution[0]
                camdata.ortho_scale*=current/width
                bpy.context.view_layer.update()
                coords=[world_to_camera_view(scene,camera,body.matrix_world@v.co) for v in body.data.vertices]
                bbox=[min(p.x for p in coords)*resolution[0],(1-max(p.y for p in coords))*resolution[1],
                      max(p.x for p in coords)*resolution[0],(1-min(p.y for p in coords))*resolution[1]]
                path=OUT/'renders'/f'{route}-{state}-{view}-{scale}.png'
                scene.render.filepath=str(path)
                bpy.ops.render.render(write_still=True)
                rows.append({'route':route,'state':state,'view':view,'scale':scale,'path':str(path),
                    'resolution':resolution,'medal_body_width_px':bbox[2]-bbox[0],'body_bbox_px':bbox,
                    'camera_position':list(camera.location),'camera_target':list(target),
                    'azimuth_degrees':angle,'ortho_scale':camdata.ortho_scale})
                (OUT/'renders/progress.json').write_text(json.dumps(rows,indent=2))
                print('RENDER_DONE',path,flush=True)
        for image in bpy.data.images:
            if image.source=='FILE':
                image.pack()
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/route/state/'studio.blend'))
(OUT/'renders/settings.json').write_text(json.dumps({'renders':rows,'engine':'Cycles','device':'CPU','samples':64,
    'denoising':True,'view_transform':'AgX','look':'AgX - Medium High Contrast','exposure':0,
    'world':'Linear Z-direction gradient .055/.065/.08 to .7/.72/.75, strength .8; no noise',
    'area_lights':light_settings,'reflection_cards':'White and dark diffuse rectangles, camera invisible, glossy visible',
    'body_display_width_px':{'game':480,'close':900},'geometry':str(FIT/'medal-low-normalmapped.glb'),
    'render_only_uniform_object_scale':100,'ao':'AO is a weather placement mask and ORM channel, not multiplied into Cycles base colour.',
    'comparison_limit':'Isolated neutral studio, no tunic or ribbon. Photographs include those contexts. Camera estimated numerically from blue-field ellipse, not calibrated from an actual camera.'},indent=2))
print('STUDIO_COMPLETE',flush=True)
