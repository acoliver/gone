"""Native Z-up editable shared rail; glTF exports +Y up with length +X."""
from pathlib import Path
import json
import bpy

ROOT=Path(__file__).resolve().parents[2]
ART=ROOT/'art-source/stasis-wiring/seat-rail'
OUT=ROOT/'assets/props/stasis-wiring/seat-rail'

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
objects={}
for name in ['full','left','middle','right','study']:
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(OUT/(name+'.glb')))
    imported=[o for o in bpy.data.objects if o not in before]
    mesh=next(o for o in imported if o.type=='MESH')
    mesh.name='seat_rail_'+name
    mesh['source_cage']='art-source/stasis-wiring/seat-rail/source-cage.npz'
    mesh['profile']='36 mm flat bearing, 2.5 mm sheet, 18 mm deep returns, 3 mm returned lips'
    mesh['source_vertex_ids']='Exact indices stored in source-cage.npz; matching face and UV fields verified by build_seat_rail.py'
    objects[name]=mesh
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    bpy.context.view_layer.objects.active=mesh
    bpy.ops.export_scene.gltf(filepath=str(OUT/(name+'.glb')),export_format='GLB',use_selection=True,
        export_yup=True,export_apply=True,export_cameras=False,export_lights=False,export_materials='EXPORT')
    mesh.hide_set(name!='full')
    mesh.hide_render=name!='full'

before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(ART/'guide-aligned.glb'))
guide_collection=bpy.data.collections.new('Generated guide | aligned short 320 mm section | reference only')
bpy.context.scene.collection.children.link(guide_collection)
for obj in [o for o in bpy.data.objects if o not in before]:
    for collection in list(obj.users_collection):collection.objects.unlink(obj)
    guide_collection.objects.link(obj)
    obj.hide_render=True
    obj.hide_set(True)
    obj['source']='Full image-conditioned Hunyuan3D-2mv octree 320; see fit.json'

# Keep the actual sparse manufacturing cage editable as quads. Export meshes
# retain the original triangulation so paired source face identities stay fixed.
import numpy as np
source=np.load(ART/'source-cage.npz')
vertices=source['vertices'];uv=source['uv'];triangles=source['faces']
quads=[]
for index in range(0,len(triangles),2):
    pair=triangles[index:index+2]
    edges={}
    for tri in pair:
        for a,b in zip(tri,np.roll(tri,-1)):
            key=tuple(sorted((int(a),int(b))));edges[key]=edges.get(key,0)+1
    boundary=[edge for edge,count in edges.items() if count==1]
    ring=[boundary[0][0]]
    while len(ring)<4:
        next_vertex=next(b if a==ring[-1] else a for a,b in boundary
                         if ring[-1] in (a,b) and (b if a==ring[-1] else a) not in ring)
        ring.append(next_vertex)
    quads.append(ring)
n=int(source['profile_count'])
cap=source['cap']
faces=quads+cap.tolist()+(cap+10*n).tolist()
cage_mesh=bpy.data.meshes.new('Manufactured profile quad cage | source UV')
cage_mesh.from_pydata([(x,-z,y) for x,y,z in vertices],[],faces)
cage_mesh.update()
import bmesh
bm=bmesh.new();bm.from_mesh(cage_mesh)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(cage_mesh);bm.free()
uv_layer=cage_mesh.uv_layers.new(name='Source physical atlas UV')
for polygon in cage_mesh.polygons:
    for loop_index in polygon.loop_indices:
        uv_layer.data[loop_index].uv=uv[cage_mesh.loops[loop_index].vertex_index]
ids=cage_mesh.attributes.new('source_vertex_id','INT','POINT')
for index,value in enumerate(ids.data):value.value=index
cage=bpy.data.objects.new('EDITABLE shared folded-sheet quad cage',cage_mesh)
bpy.context.scene.collection.objects.link(cage)
cage.hide_render=True
cage.hide_set(True)
cage['rebuild']='tools/build_seat_rail.py; source-cage.npz contains original vertices, UVs, triangles, cut stations'

bpy.context.scene['coordinate_frame']='Blender native Z-up, front -Y, rail length X; export_yup=True yields glTF +Y up'
bpy.context.scene['design_fit']=json.loads((ART/'fit.json').read_text())['method']
bpy.context.scene['source_uv']='1.2 m by 0.12 m image-derived steel atlas, unchanged across cut/pose'
for image in bpy.data.images:
    if image.source=='FILE':image.pack()
bpy.ops.object.select_all(action='DESELECT')
objects['full'].hide_set(False)
objects['full'].select_set(True)
bpy.context.view_layer.objects.active=objects['full']
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'seat-rail.blend'))
