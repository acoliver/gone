import bpy, json
from pathlib import Path
from mathutils import Vector
root=Path('art-source/terminal/generated/console2')
fit=json.loads((root/'paint/fit-transform.json').read_text())
for obj in list(bpy.context.scene.objects):
    bpy.data.objects.remove(obj,do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(root/'fit/console-a.glb'))
original={o.name:o for o in bpy.context.scene.objects}
body=original['ConsoleBody']
assert all(name in original for name in ('ScreenSocket','DisplayPlane','KeyboardSocket'))
existing=set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=str(root/'paint/console-painted-normalized.glb'))
painted=next(o for o in bpy.context.scene.objects if o not in existing and o.type=='MESH')
painted.data.name='ConsoleBody_PaintedMesh'
centroid=fit['centroid']; scale=fit['paint_scale']
for vertex in painted.data.vertices:
    vertex.co.x=vertex.co.x*scale+centroid[0]
    vertex.co.y=vertex.co.y*scale+centroid[1]
    vertex.co.z=vertex.co.z*scale+centroid[2]
body.data=painted.data
bpy.data.objects.remove(painted,do_unlink=True)
body.name='ConsoleBody'
body.data.name='ConsoleBody_Painted'
body.data.materials[0].name='Hunyuan3D-2 Painted Steel'
for mat in body.data.materials:
    if mat and mat.use_nodes:
        bs=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
        if bs:
            bs.inputs['Metallic'].default_value=.2
            bs.inputs['Roughness'].default_value=.6
# Scene render configuration.
scene=bpy.context.scene
scene.render.engine='CYCLES'; scene.cycles.samples=64; scene.cycles.use_denoising=True
scene.render.resolution_x=1600; scene.render.resolution_y=900; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX'; scene.world.color=(.08,.08,.08)
# Drop any imported lighting/cameras and establish a neutral studio.
for obj in list(scene.objects):
    if obj.type in {'LIGHT','CAMERA'}: bpy.data.objects.remove(obj,do_unlink=True)
target=Vector((0,-.35,.637)); z=1.275

def area(name,loc,power,color,size):
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.color=color; data.shape='DISK'; data.size=size
    obj=bpy.data.objects.new(name,data); scene.collection.objects.link(obj); obj.location=loc
    obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler(); return obj
lights=[area('StudioKey',(-2,-3,3),500,(1.0,.96,.9),3),area('StudioFill',(2,-2,1.8),300,(.88,.93,1.0),2.5),area('StudioRim',(0,1,2.8),380,(1.0,.88,.78),2.2)]
def camera(name,loc):
    data=bpy.data.cameras.new(name); data.type='ORTHO'; data.ortho_scale=1.8
    obj=bpy.data.objects.new(name,data); scene.collection.objects.link(obj); obj.location=loc
    obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler(); return obj
cams={'front':camera('Front',(0,-3.2,.67)),'three-quarter':camera('ThreeQuarter',(-2.2,-3.2,.67)),'side':camera('Side',(-3.3,0,.67)),'back':camera('Back',(0,3.2,.67))}
for name in ('front','three-quarter','side','back'):
    scene.camera=cams[name]; scene.render.filepath=str(root/f'paint/renders/{name}.png'); bpy.ops.render.render(write_still=True)
# Dim red-lit version of the 3/4 camera.
for light in lights:
    light.data.energy=45 if light.name=='StudioKey' else (8 if light.name=='StudioFill' else 14)
    light.data.color=(1.0,.025,.018)
scene.camera=cams['three-quarter']; scene.render.filepath=str(root/'paint/renders/three-quarter-red.png'); bpy.ops.render.render(write_still=True)
# Export only the console and the three fitted accessories, preserving their transforms.
for obj in bpy.context.scene.objects: obj.select_set(False)
keep=[original['ConsoleBody'],original['DisplayPlane'],original['ScreenSocket'],original['KeyboardSocket']]
for obj in keep: obj.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.gltf(filepath=str(root/'fit/console-painted.glb'),export_format='GLB',use_selection=True,export_apply=True,export_image_format='AUTO')
report={'objects':[(o.name,o.type) for o in keep],'body_triangles':sum(len(p.vertices)-2 for p in body.data.polygons),'body_bounds_min':[min((body.matrix_world@v.co)[i] for v in body.data.vertices) for i in range(3)],'body_bounds_max':[max((body.matrix_world@v.co)[i] for v in body.data.vertices) for i in range(3)],'texture_materials':[m.name for m in body.data.materials]}
(root/'paint/assembly-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('ASSEMBLED',json.dumps(report),flush=True)
