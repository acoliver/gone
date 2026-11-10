import bpy, json
from pathlib import Path
root=Path('art-source/terminal/generated/console2')
bpy.ops.import_scene.gltf(filepath=str(root/'fit/console-a.glb'))
for obj in list(bpy.context.scene.objects):
    if obj.type != 'MESH' or obj.name != 'ConsoleBody':
        bpy.data.objects.remove(obj, do_unlink=True)
body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
body.name='ConsoleBody'
body.data.calc_loop_triangles()
verts=[body.matrix_world @ v.co for v in body.data.vertices]
lo=[min(v[i] for v in verts) for i in range(3)]
hi=[max(v[i] for v in verts) for i in range(3)]
centroid=[(lo[i]+hi[i])/2 for i in range(3)]
scale=max(max(abs((v[i]-centroid[i])) for v in verts) for i in range(3))
report={'name':body.name,'vertices':len(body.data.vertices),'triangles':len(body.data.loop_triangles),'bounds_min':lo,'bounds_max':hi,'centroid':centroid,'paint_scale':scale,'front_is_negative_y':True}
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.gltf(filepath=str(root/'paint/console-body-fit.glb'),export_format='GLB',use_selection=True,export_apply=True)
(root/'paint/fit-transform.json').write_text(json.dumps(report,indent=2)+'\n')
print('PREPARED',json.dumps(report),flush=True)
