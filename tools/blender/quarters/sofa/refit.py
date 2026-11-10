"""Fit the larger cloth pads and connect the feet to the existing side rails."""
import argparse
import math
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import assemble
from cloth import SCRATCH
from assemble import uv, join, components
from build import export, name_meshes


def mount_plates():
    frame = bpy.data.objects['Frame']
    plates = []
    feet=bpy.data.objects['Feet']
    tops=[]
    for ids in components(feet.data):
        points=np.array([feet.matrix_world @ feet.data.vertices[i].co for i in ids])
        tops.append((points.mean(axis=0),points[:,2].max()))
    for x in (-.995, .995):
        for y in (-.34, .34):
            foot_top=min(tops,key=lambda p:abs(p[0][0]-x)+abs(p[0][1]-y))[1]
            bottom=foot_top+.00015
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x,y,(bottom+.131)/2))
            obj = bpy.context.object
            obj.name = 'Foot mounting plate'
            obj.dimensions = (.19,.11,.131-bottom)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            mod = obj.modifiers.new('Plate edge', 'BEVEL')
            mod.width = .003
            mod.segments = 2
            bpy.ops.object.modifier_apply(modifier=mod.name)
            obj.data.materials.append(frame.data.materials[0])
            uv(obj)
            plates.append(obj)
    join(frame, plates)


def rivet_material():
    material=bpy.data.materials.get('BareSteel') or bpy.data.materials.new('BareSteel')
    material.use_nodes=True
    shader=material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(.48,.52,.54,1)
    shader.inputs['Metallic'].default_value=.85
    shader.inputs['Roughness'].default_value=.32
    return material


def domed_rivets():
    old = bpy.data.objects['Rivets']
    material = rivet_material()
    bpy.data.objects.remove(old, do_unlink=True)
    verts, faces = [], []
    for sign in (-1,1):
        for y in (-.395,-.285,.285,.395):
            for z in (.385,.455):
                start = len(verts)
                for ring in range(3):
                    angle = ring*math.pi/6
                    for i in range(8):
                        a = i*math.tau/8
                        verts.append((sign*(1.0975+.003*math.sin(angle)),
                                      y+.006*math.cos(angle)*math.cos(a),
                                      z+.006*math.cos(angle)*math.sin(a)))
                tip = len(verts)
                verts.append((sign*1.1005,y,z))
                base = len(verts)
                verts.append((sign*1.0975,y,z))
                for i in range(8):
                    j = (i+1)%8
                    faces.append((base,start+j,start+i))
                    for ring in range(2):
                        a,b = start+ring*8+i,start+ring*8+j
                        faces.append((a,b,b+8,a+8))
                    faces.append((start+16+i,start+16+j,tip))
                if sign < 0:
                    faces[-32:] = [tuple(reversed(f)) for f in faces[-32:]]
    mesh = bpy.data.meshes.new('Rivets')
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new('Rivets', mesh)
    bpy.context.collection.objects.link(obj)
    for face in mesh.polygons:
        face.use_smooth = True
    uv(obj)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', required=True)
    ap.add_argument('--source', type=Path, default=SCRATCH/'baseline.blend')
    ap.add_argument('--out', type=Path, default=SCRATCH/'assembly.blend')
    ap.add_argument('--throw-source', type=Path)
    ap.add_argument('--export', type=Path)
    args = ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    bpy.ops.wm.open_mainfile(filepath=str(SCRATCH/args.template/'cushion.blend'))
    obj = bpy.data.objects['SeatCushion_C']
    vertices = np.array([v.co[:] for v in obj.data.vertices])
    assemble.TEMPLATE_FACES = [tuple(p.vertices) for p in obj.data.polygons]
    bpy.ops.wm.open_mainfile(filepath=str(args.source))
    assemble.setup_cushions(vertices)
    mount_plates()
    domed_rivets()
    for obj in bpy.data.objects:
        for mod in list(obj.modifiers):
            obj.modifiers.remove(mod)
        if obj.type == 'MESH':
            obj.data.name = obj.name
    if args.throw_source:
        with bpy.data.libraries.load(str(args.throw_source)) as (available,loaded):
            loaded.objects=['Throw']
        obj=loaded.objects[0]
        bpy.context.collection.objects.link(obj)
        obj.data.materials.clear()
        obj.data.materials.append(bpy.data.materials['OatmealWool'])
    name_meshes()
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out))
    if args.export:
        export(args.export)


if __name__ == '__main__':
    main()
