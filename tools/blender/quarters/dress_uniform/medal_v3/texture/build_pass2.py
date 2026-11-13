"""Rebuild corrected high and low from the generated fit2 subdivision surfaces."""
import json
import sys
import types
from collections import defaultdict
from itertools import product
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils.bvhtree import BVHTree

SOURCE=Path(__file__).resolve().parent
ROOT=SOURCE.parents[5]
FIT=ROOT/'tmp/issue130-v3/fit2'
OUT=ROOT/'tmp/issue130-v3/tex2/geom'
sys.path.insert(0,str(SOURCE.parent))
from export4 import export
from projection import project
from unwrap2 import unwrap

bpy.ops.wm.open_mainfile(filepath=str(FIT/'medal-fitted.blend'))
bpy.context.preferences.filepaths.save_version=0
surface=np.load(OUT/'target-surface.npz')
photo=json.loads((ROOT/'tmp/issue130-v3/tex1/projection/settings.json').read_text())
wrapper=(SOURCE.parent/'run_fit2.py').read_text()
start=wrapper.index(' reducer=types.ModuleType')
end=wrapper.index(" sys.modules['reduce_low']=reducer",start)+len(" sys.modules['reduce_low']=reducer")
namespace={'SOURCE':SOURCE.parent,'types':types,'sys':sys}
exec('''if True:
'''+wrapper[start:end],namespace)
reduction=namespace['reduction']
reduction=reduction.replace('pinned=np.zeros(len(vertices),bool)','pinned=pass2_pinned.copy()')
reduction=reduction.replace('        if not alive[a] or not alive[b] or (pinned[a] and pinned[b]):','''        if pass2_roles[a]!=pass2_roles[b]:return
        if not alive[a] or not alive[b] or (pinned[a] and pinned[b]):''')
reduction=reduction.replace('            candidates=[vertices[a],vertices[b],(vertices[a]+vertices[b])/2]', '            candidates=[vertices[a],vertices[b]] if pass2_contour[a] else [vertices[a],vertices[b],(vertices[a]+vertices[b])/2]')
reduction=reduction.replace('            if abs(np.linalg.det(q[:3,:3]))>1e-12:', '            if not pass2_contour[a] and abs(np.linalg.det(q[:3,:3]))>1e-12:')
reduction=reduction.replace('        # The enamel is a single-valued front membrane.', '''        if not pass2_winding(old,new):
            continue
        # The enamel is a single-valued front membrane.''')
module=namespace['reducer']
exec(compile(reduction,str(SOURCE.parent/'reduce_low.py'),'exec'),module.__dict__)


def smooth(x):
    x=np.clip(x,0,1)
    return x*x*(3-2*x)


def sample_grid(xy,field='depth'):
    grid=surface[field];pitch=float(surface['pitch']);lo=float(surface['lo'])
    uv=(xy-lo)/pitch-.5
    ix=np.clip(np.floor(uv[:,0]).astype(int),0,grid.shape[1]-2)
    iz=np.clip(np.floor(uv[:,1]).astype(int),0,grid.shape[0]-2)
    dx=np.clip(uv[:,0]-ix,0,1);dz=np.clip(uv[:,1]-iz,0,1)
    return (grid[iz,ix]*(1-dx)+grid[iz,ix+1]*dx)*(1-dz)+(grid[iz+1,ix]*(1-dx)+grid[iz+1,ix+1]*dx)*dz


def correct_body(mesh):
    original=np.array([v.co[:] for v in mesh.vertices])*1000
    q=original.copy();center=surface['center'];outer=float(surface['outer_radius'])
    r=np.linalg.norm(q[:,[0,2]]-center,axis=1)
    angle=np.arctan2(q[:,2]-center[1],q[:,0]-center[0])%(2*np.pi)
    source_angle=surface['source_angle'];source_radius=surface['source_radius']
    old_radius=np.interp(angle,np.r_[source_angle[-1]-2*np.pi,source_angle,source_angle[0]+2*np.pi],np.r_[source_radius[-1],source_radius,source_radius[0]])
    q[:,[0,2]]+=((q[:,[0,2]]-center)/r[:,None])*((outer-old_radius)*smooth((r-14)/1.2)*smooth((-sample_grid(original[:,[0,2]],'star_signed')-.05)/.25))[:,None]
    weight=smooth((-original[:,1]-.7)/.65)*(1-smooth((r-(outer-.65))/.6))
    q[:,1]+=(sample_grid(q[:,[0,2]])-original[:,1])*weight
    for vertex,point in zip(mesh.vertices,q/1000):
        vertex.co=point
    mesh.update()


def evaluate_low(part):
    if part=='Body':
        cage=bpy.data.objects[part+'_Cage'];modifier=cage.modifiers[0]
        modifier.levels=2
        bpy.context.view_layer.update()
        mesh=bpy.data.meshes.new_from_object(cage.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        correct_body(mesh)
    else:
        mesh=bpy.data.objects[part+'_High'].data.copy()
    bpy.data.objects[part+'_Low'].data=mesh
    return bpy.data.objects[part+'_Low']


def contour_projection(vertices,camera):
    if camera in ['studio','game']:
        return project(vertices,camera)
    angle=0. if camera=='front' else photo['photos'][camera.split('-')[0]]['oblique']['inferred_azimuth_degrees']
    yaw=np.radians(angle)
    forward=-np.array([-np.sin(yaw),-np.cos(yaw),.06 if angle else 0.]);forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0.,0.,1.]);right/=np.linalg.norm(right)
    up=np.cross(right,forward)
    high=np.array([v.co[:] for v in bpy.data.objects['Body_High'].data.vertices])
    return np.c_[vertices@right,vertices@up]*(900/np.ptp(high@right))


def curve_pins(edges,points,tolerance):
    adjacent=defaultdict(set)
    for a,b in edges:
        adjacent[a].add(b);adjacent[b].add(a)
    remaining=set(edges);chosen=set()
    while remaining:
        endpoints=[v for edge in remaining for v in edge if len(adjacent[v])!=2]
        start=min(endpoints) if endpoints else min(min(e) for e in remaining)
        sequence=[start];current=start
        while True:
            neighbors=[v for v in adjacent[current] if tuple(sorted((current,v))) in remaining]
            if not neighbors:break
            nxt=min(neighbors);remaining.remove(tuple(sorted((current,nxt))))
            sequence.append(nxt);current=nxt
            if current==start:break
        coordinates=points[sequence];stack=[(0,len(sequence)-1)];keep={0,len(sequence)-1}
        while stack:
            first,last=stack.pop()
            if last-first<2:continue
            a,b=coordinates[first],coordinates[last];direction=b-a;length=direction@direction
            middle=coordinates[first+1:last]
            if length:
                t=np.clip(((middle-a)@direction)/length,0,1)
                distances=np.linalg.norm(middle-(a+t[:,None]*direction),axis=1)
            else:
                distances=np.linalg.norm(middle-a,axis=1)
            index=int(np.argmax(distances))+first+1
            if distances.max()>tolerance:
                keep.add(index);stack.extend([(first,index),(index,last)])
        chosen.update(sequence[i] for i in keep)
    return chosen


def reduce_surface(obj,target,source_chord_tolerance_px):
    mesh=obj.data;mesh.calc_loop_triangles()
    vertices=np.array([v.co[:] for v in mesh.vertices]);tri=np.array([t.vertices[:] for t in mesh.loop_triangles])
    owners=defaultdict(list)
    for j,t in enumerate(tri):
        for a,b in zip(t,np.roll(t,-1)):
            owners[tuple(sorted((int(a),int(b))))].append(j)
    contours=set();support=set();pinned_ids=set()
    camera_roles=np.zeros(len(vertices),np.int32)
    parallel=[]
    for camera_index,camera in enumerate(['studio','game','front','remembered-oblique','present-oblique']):
        projected=contour_projection(vertices,camera);q=projected[tri]
        a=q[:,1]-q[:,0];b=q[:,2]-q[:,0];area=a[:,0]*b[:,1]-a[:,1]*b[:,0]
        sign=np.sign(np.where(np.abs(area)<np.max(np.abs(area))*1e-12,0.,area))
        edges={edge for edge,fs in owners.items() if len(fs)==2 and sign[fs[0]]!=sign[fs[1]]}
        curve={i for edge in edges for i in edge}
        camera_roles[list(curve)]|=1<<camera_index
        if camera!='game':
            basis=contour_projection(np.eye(3)*.001,camera)-contour_projection(np.zeros((3,3)),camera)
            direction=np.cross(basis[:,0],basis[:,1]);parallel.append(direction/np.linalg.norm(direction))
        pinned_ids|=curve_pins(edges,projected,source_chord_tolerance_px)
        contours|=curve
        support|={int(i) for t in tri if any(int(i) in curve for i in t) for i in t}
    field=mesh.attributes.get('enamel_field7');region=mesh.attributes.get('body_region2')
    roles=np.zeros(len(vertices),np.int32)
    for t in mesh.loop_triangles:
        label=(2*region.data[t.polygon_index].value if region else 0)+(int(field.data[t.polygon_index].value>0) if field else 0)
        roles[list(t.vertices)]|=1<<label
    if field:
        boundary=defaultdict(set)
        for edge,fs in owners.items():
            if len(fs)==2 and field.data[mesh.loop_triangles[fs[0]].polygon_index].value!=field.data[mesh.loop_triangles[fs[1]].polygon_index].value:
                contours.update(edge)
                a,b=edge;boundary[a].add(b);boundary[b].add(a)
        remaining=set(boundary);component=0
        while remaining:
            component+=1;pending=[min(remaining)];ids=set()
            while pending:
                i=pending.pop()
                if i in ids:continue
                ids.add(i);pending.extend(boundary[i]-ids)
            remaining-=ids
            roles[list(ids)]+=component*1000
        boundary_edges={tuple(sorted((a,b))) for a,neighbors in boundary.items() for b in neighbors}
        pinned_ids|=curve_pins(boundary_edges,contour_projection(vertices,'front'),source_chord_tolerance_px)
    # Simplify each camera's source curve independently. A nearby sample on
    # another camera's curve does not establish the same projected outline.
    pinned=np.zeros(len(vertices),bool)
    pinned[list(pinned_ids)]=True
    crease=mesh.attributes.get('crease_edge') or mesh.attributes.new('crease_edge','FLOAT','EDGE')
    for value in crease.data:
        value.value=0.
    def winding(old,new):
        no=np.cross(old[:,1]-old[:,0],old[:,2]-old[:,0]);nn=np.cross(new[:,1]-new[:,0],new[:,2]-new[:,0])
        if np.any((no@np.array(parallel).T)*(nn@np.array(parallel).T)<-1e-18):return False
        projected=[]
        for points in [old,new]:
            p=project(points.reshape(-1,3)/1000,'game').reshape(-1,3,2)
            a=p[:,1]-p[:,0];b=p[:,2]-p[:,0];projected.append(a[:,0]*b[:,1]-a[:,1]*b[:,0])
        return not np.any(projected[0]*projected[1]<-1e-12)
    module.pass2_pinned=pinned;module.pass2_roles=roles+camera_roles*100000
    module.pass2_contour=camera_roles!=0;module.pass2_winding=winding
    importance=np.array([10000. if any(int(i) in support for i in t) else 1. for t in tri])
    print('REDUCE_START',obj.name,len(tri),target,'fixed',int(pinned.sum()),flush=True)
    result=module.reduce_body(obj,target,importance)
    result['method']='Visibility-weighted QEM on the dense generated surface. Independent source contour/field curves simplified per camera to a fixed pixel chord tolerance; selected source positions fixed in 3D. Includes zero-area silhouette transitions. Region/cycle incidence classes cannot cross. Link, orientation, front/rear projection and aspect conditions retained from fit2.'
    result['source_chord_tolerance_px']=source_chord_tolerance_px
    return result


# The high keeps the generated fit2 mesh identities and the measured correction.
high=bpy.data.objects['Body_High'].data
corrected=np.load(OUT/'high-positions.npz')['vertices']
assert len(corrected)==len(high.vertices)
for vertex,point in zip(high.vertices,corrected):
    vertex.co=point
report={'reduction':{}}
body=evaluate_low('Body')
report['reduction']['Body']=reduce_surface(body,5400,.12)
loop=evaluate_low('Loop')
report['reduction']['Loop']=reduce_surface(loop,4000,.12)
# Bar already meets every 900px front/oblique contour gate at 1,100 triangles.
unwrap([bpy.data.objects[p+'_Low'] for p in ['Body','Loop','Bar']])
for kind in ['High','Low']:
    payload=[]
    for part in ['Body','Loop','Bar']:
        obj=bpy.data.objects[part+'_'+kind];mesh=obj.data
        for edge in mesh.edges:
            edge.use_edge_sharp=False
        if mesh.has_custom_normals:
            bpy.ops.object.select_all(action='DESELECT')
            for collection in obj.users_collection:
                collection.hide_viewport=False
            obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
        for face in mesh.polygons:
            face.use_smooth=True
        mesh.update();mesh.calc_loop_triangles()
        bm=bmesh.new();bm.from_mesh(mesh)
        assert all(e.is_manifold and e.is_contiguous for e in bm.edges),obj.name
        bm.free()
        data={'name':obj.name,'vertices':[v.co[:] for v in mesh.vertices],'triangles':[list(t.vertices) for t in mesh.loop_triangles]}
        if mesh.attributes.get('enamel_field7'):
            data['field']=[mesh.attributes['enamel_field7'].data[t.polygon_index].value for t in mesh.loop_triangles]
            data['sharp_edges']=[]
        if kind=='Low':
            data['triangle_uv']=[[mesh.uv_layers.active.data[i].uv[:] for i in t.loops] for t in mesh.loop_triangles]
        payload.append(data)
    (OUT/(kind.lower()+'-arrays.json')).write_text(json.dumps(payload,separators=(',',':')))
    export([bpy.data.objects[p+'_'+kind] for p in ['Body','Loop','Bar']],OUT/('medal-'+kind.lower()+'.glb'))
    report[kind.lower()]={'triangles':sum(len(p['triangles']) for p in payload)}
assert report['low']['triangles']<=10500
for obj in bpy.data.objects:
    obj.hide_render=not obj.name.endswith('_Low')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'medal-fitted.blend'))
decisions=json.loads((OUT/'shape-decisions.json').read_text())
decisions['low_refinement']='Body source: fit2 cage subdivision level 2 with the same generated-rim correction. Loop source: unchanged high mesh. Visibility-weighted QEM with independent per-camera source-contour pins at 0.12px chord tolerance, including edge-on transitions; region/cycle incidence restrictions preserve field boundaries. Five camera directions protected. Per-camera contour-incidence classes and projected-winding constraints prevent the suspension opening from shifting. Unpinned contour collapses retain source endpoints. Allocation Body 5400, Loop 4000, Bar 1100.'
decisions['uv_policy']='Old low topology undersampled the new rim. New continuous front/rear and intrinsic side/hardware atlas; detach remaining chart conflicts with reuv_pass2.py. Image detail transfers by closest original surface point and barycentric source UV.'
(OUT/'shape-decisions.json').write_text(json.dumps(decisions,indent=2))
(OUT/'build.json').write_text(json.dumps(report,indent=2))
print('BUILD_COMPLETE',report['high'],report['low'],flush=True)
