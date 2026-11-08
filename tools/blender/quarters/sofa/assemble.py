"""Bake independently settled upholstery into the pilot's editable source."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cloth import ROOT, SCRATCH, activate, collider, cloth, bake, measurements, ray

SOURCE = Path(__file__).with_name('sofa-working.blend')


def components(mesh):
    adjacent = [set() for v in mesh.vertices]
    for e in mesh.edges:
        a,b=e.vertices; adjacent[a].add(b); adjacent[b].add(a)
    unseen=set(range(len(adjacent)))
    while unseen:
        stack=[unseen.pop()]; found=[]
        while stack:
            i=stack.pop(); found.append(i)
            todo=adjacent[i]&unseen; unseen.difference_update(todo); stack.extend(todo)
        yield found


def decimate(obj, ratio):
    activate(obj)
    mod=obj.modifiers.new('Runtime triangle budget','DECIMATE'); mod.ratio=ratio
    bpy.ops.object.modifier_apply(modifier=mod.name)


def uv(obj):
    activate(obj); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(island_margin=.015); bpy.ops.object.mode_set(mode='OBJECT')


def join(obj, others):
    activate(obj)
    for other in others: other.select_set(True)
    bpy.ops.object.join()


def fit_frame():
    frame=bpy.data.objects['Frame']; activate(frame)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    changes=[]
    for ids in components(frame.data):
        vs=[frame.data.vertices[i] for i in ids]
        points=np.array([v.co[:] for v in vs]); lo=points.min(axis=0); hi=points.max(axis=0); c=(lo+hi)/2
        if abs(c[0])>.9 and hi[1]-lo[1]>.9:
            # Keep the external arm and hardware positions; clear the 2 m upholstery bay.
            outer=hi[0] if c[0]>0 else lo[0]
            width=.075 if hi[2]-lo[2]>.2 else .080
            inner=outer-math.copysign(width,c[0])
            for v in vs:
                t=(v.co.x-lo[0])/(hi[0]-lo[0]); v.co.x=min(inner,outer)+t*width
            changes.append({'part':'arm','old_bounds':[lo.tolist(),hi.tolist()],'width_m':width})
        elif hi[0]-lo[0]>1.8 and c[1]<-.3:
            for v in vs: v.co.z-=.018
            changes.append({'part':'front rail','vertical_shift_m':-.018})
        elif hi[0]-lo[0]>1.8 and c[1]>.3:
            for v in vs: v.co.y+=.025
            changes.append({'part':'back rail','rear_shift_m':.025})
        elif abs(c[0])>.9 and hi[2]-lo[2]>.4 and hi[1]-lo[1]<.1:
            for v in vs: v.co.x+=math.copysign(.06,c[0]); v.co.y+=.025
            changes.append({'part':'back upright','outward_shift_m':.06,'rear_shift_m':.025})
        elif hi[0]-lo[0]>1.8 and abs(c[1])<.1:
            for v in vs: v.co.y*=20; v.co.z+=.015
            changes.append({'part':'seat support deck','depth_m':.70,'top_m':.39})
    for name,ratio in [('Frame',.52),('Feet',.35),('Rivets',.32)]:
        decimate(bpy.data.objects[name],ratio)
    (SCRATCH/'frame-fit.json').write_text(json.dumps(changes,indent=2)+'\n')


def welt(obj, material, vertical_step=None):
    # Closed upper seam, including both the front and rear perimeter edges.
    lo,hi=np.array([v.co[:] for v in obj.data.vertices]).min(axis=0),np.array([v.co[:] for v in obj.data.vertices]).max(axis=0)
    points=[]; normals=[]
    # A rounded rectangular seam follows the top surface rather than a flat curve.
    rx=(hi[0]-lo[0])/2-.019; ry=(hi[1]-lo[1])/2-.019
    cx,cy=(lo[:2]+hi[:2])/2; corner=.025
    corners=[(cx+rx-corner,cy+ry-corner,0),(cx-rx+corner,cy+ry-corner,90),(cx-rx+corner,cy-ry+corner,180),(cx+rx-corner,cy-ry+corner,270)]
    path=[]
    for k,(x,y,start) in enumerate(corners):
        for j in range(4):
            a=math.radians(start+j*30);path.append((x+corner*math.cos(a),y+corner*math.sin(a)))
        nx,ny,na=corners[(k+1)%4];a=math.radians(na);end=np.array([nx+corner*math.cos(a),ny+corner*math.sin(a)])
        begin=np.array(path[-1])
        for j in range(1,8):path.append(tuple(begin+(end-begin)*j/8))
    if vertical_step:
        dense=[]
        for i,p in enumerate(path):
            end=path[(i+1)%len(path)]
            steps=max(1,math.ceil(abs(end[1]-p[1])/vertical_step))
            for j in range(steps):dense.append(tuple(np.array(p)+(np.array(end)-p)*j/steps))
        path=dense
    for px,py in path:
        hit,loc,n,idx=obj.ray_cast(Vector((px,py,hi[2]+1)),Vector((0,0,-1)))
        if not hit:raise ValueError('Welt missed upholstery surface')
        points.append(loc+n*(.00458 if vertical_step else .0047));normals.append(n)
    verts=[]; faces=[]; count=len(points)
    for i,(p,n) in enumerate(zip(points,normals)):
        tangent=(points[(i+1)%count]-points[(i-1)%count]).normalized()
        across=tangent.cross(n).normalized(); normal=across.cross(tangent).normalized()
        for j in range(6):
            angle=math.tau*j/6
            verts.append(p+.004*(normal*math.cos(angle)+across*math.sin(angle)))
    for i in range(count):
        for j in range(6):
            faces.append((i*6+(j+1)%6,((i+1)%count)*6+(j+1)%6,((i+1)%count)*6+j,i*6+j))
    mesh=bpy.data.meshes.new(obj.name+'_Welt');mesh.from_pydata(verts,[],faces);mesh.materials.append(material)
    w=bpy.data.objects.new(obj.name+'_Welt',mesh);bpy.context.collection.objects.link(w);w.matrix_world=obj.matrix_world.copy()
    for p in mesh.polygons:p.use_smooth=True
    return w


def setup_cushions(template):
    material=bpy.data.materials['CharcoalUpholstery']; piping=material
    for name in list(bpy.data.objects.keys()):
        if name.startswith(('SeatCushion','BackCushion')) or name=='Throw':bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    v=template.copy();lo=v.min(axis=0);hi=v.max(axis=0); normalized=(v-lo)/(hi-lo)
    records={}
    for tag,x in zip('LCR',(-.67,0,.67)):
        p=normalized*np.array([.66,.70,.18])+np.array([-.33,-.35,-.09])
        mesh=bpy.data.meshes.new('Settled upholstery');mesh.from_pydata(p.tolist(),[],TEMPLATE_FACES);mesh.materials.append(material)
        o=bpy.data.objects.new('SeatCushion_'+tag,mesh);bpy.context.collection.objects.link(o);o.location=(x,-.035,.480)
        for f in mesh.polygons:f.use_smooth=True
        triangles=sum(len(f.vertices)-2 for f in o.data.polygons)
        if triangles>1440:decimate(o,1440/triangles)
        records[o.name]=measurements(o);uv(o);collider(o)
    # A back pad's lower return compresses behind the seat rather than occupying it.
    for tag,x in zip('LCR',(-.67,0,.67)):
        h=normalized[:,1]; q=normalized[:,2]
        t=np.clip((h-.38)/.20,0,1);t=t*t*(3-2*t)
        depth=.04+.16*t; rear=.37+.005*t
        p=np.column_stack(((normalized[:,0]-.5)*.66,rear-q*depth,.415+h*.42))
        mesh=bpy.data.meshes.new('Settled back upholstery');mesh.from_pydata(p.tolist(),[],TEMPLATE_FACES);mesh.materials.append(material)
        o=bpy.data.objects.new('BackCushion_'+tag,mesh);bpy.context.collection.objects.link(o);o.location.x=x
        for f in mesh.polygons:f.use_smooth=True
        triangles=sum(len(f.vertices)-2 for f in o.data.polygons)
        decimate(o,min(.88,1210/triangles))
        uv(o)
    (SCRATCH/'cushion-fit.json').write_text(json.dumps(records,indent=2)+'\n')
    # Seam coordinates are found on the simulated shell before orientation.
    for o in list(bpy.data.objects):
        if o.name.startswith('SeatCushion'):
            w=welt(o,piping);uv(w);join(o,[w])
        elif o.name.startswith('BackCushion'):
            # Rotate the front to a temporary up-facing surface, without scaling the tube.
            dummy=bpy.data.objects.new('Back seam guide',bpy.data.meshes.new('Guide'))
            rotated=[(p.co.x,p.co.z,-p.co.y) for p in o.data.vertices]
            dummy.data.from_pydata(rotated,[],[tuple(p.vertices) for p in o.data.polygons]);bpy.context.collection.objects.link(dummy)
            w=welt(dummy,piping,vertical_step=.018)
            for vert in w.data.vertices:
                x,y,z=vert.co;vert.co=(x,-z,y)
            w.location.x=o.location.x
            bpy.data.objects.remove(dummy,do_unlink=True);uv(w);join(o,[w])


def main():
    global TEMPLATE_FACES
    ap=argparse.ArgumentParser();ap.add_argument('--template',default='seat-k');ap.add_argument('--out',default='assembly.blend');ap.add_argument('--frame-source',type=Path,required=True)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    bpy.ops.wm.open_mainfile(filepath=str(SCRATCH/args.template/'cushion.blend'))
    obj=bpy.data.objects['SeatCushion_C'];template=np.array([v.co[:] for v in obj.data.vertices]);TEMPLATE_FACES=[tuple(p.vertices) for p in obj.data.polygons]
    bpy.ops.wm.open_mainfile(filepath=str(args.frame_source.resolve()))
    fit_frame();setup_cushions(template)
    bpy.context.scene.frame_set(1)
    # Collision modifiers are simulation scaffolding, not part of the baked export.
    for o in bpy.data.objects:
        for m in list(o.modifiers):o.modifiers.remove(m)
    bpy.ops.wm.save_as_mainfile(filepath=str(SCRATCH/args.out))

if __name__=='__main__':main()
