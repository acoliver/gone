"""Replace flat 16-sided knuckles with smooth 48-sided geometry, retaining UV1."""
from pathlib import Path
import shutil
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[4]
SOURCE = Path(__file__).with_name('locker-working.blend')
OUTPUT = ROOT/'art-source/quarters/locker/faces/hinges.glb'


def main():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    old = bpy.data.objects['Hinges']
    old.data.calc_loop_triangles()
    triangles = list(old.data.loop_triangles)
    vertices = [v.co.copy() for v in old.data.vertices]
    tree = BVHTree.FromPolygons(vertices,[list(t.vertices) for t in triangles],all_triangles=True)
    uv = old.data.uv_layers.active.data
    pieces = []
    inverse = old.matrix_world.inverted()
    for z in (.350,1.250,2.150):
        bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.010,depth=.080,location=(-.260,-.301,z))
        obj = bpy.context.object
        bevel = obj.modifiers.new('Rounded knuckle rims','BEVEL')
        bevel.width = .0007
        bevel.segments = 7
        bevel.limit_method = 'ANGLE'
        bevel.angle_limit = .5
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        for face in obj.data.polygons:
            face.use_smooth = abs(face.normal.z)<.9999
        for v in obj.data.vertices:
            v.co = inverse @ (obj.matrix_world @ v.co)
        obj.matrix_world = old.matrix_world.copy()
        while obj.data.uv_layers:
            obj.data.uv_layers.remove(obj.data.uv_layers[0])
        obj.data.uv_layers.new(name='UVMap',do_init=False)
        layer = obj.data.uv_layers.active.data
        for loop in obj.data.loops:
            point = obj.data.vertices[loop.vertex_index].co
            nearest,_,index,_ = tree.find_nearest(point)
            tri = triangles[index]
            a,b,c = [vertices[i] for i in tri.vertices]
            ab,ac,ap = b-a,c-a,nearest-a
            d00,d01,d11 = ab.dot(ab),ab.dot(ac),ac.dot(ac)
            d20,d21 = ap.dot(ab),ap.dot(ac)
            den = d00*d11-d01*d01
            v,w = (d11*d20-d01*d21)/den,(d00*d21-d01*d20)/den
            layer[loop.index].uv = uv[tri.loops[0]].uv*(1-v-w)+uv[tri.loops[1]].uv*v+uv[tri.loops[2]].uv*w
        pieces.append(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in pieces: obj.select_set(True)
    bpy.context.view_layer.objects.active=pieces[0]
    bpy.ops.object.join()
    obj=bpy.context.object
    obj.name='SmoothHinges'
    obj.data.materials.append(old.data.materials[0])
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(OUTPUT),export_format='GLB',use_selection=True,
                              export_yup=True,export_apply=False,export_materials='EXPORT',
                              export_cameras=False,export_lights=False)
    shutil.copyfile(OUTPUT, ROOT/'tools/quarters_aging/locker_material/hinges.glb')
    print('HINGE: 48 sides, 0.7 mm rims with seven bevel segments, smooth sides; original UV1 transferred')


if __name__=='__main__': main()
