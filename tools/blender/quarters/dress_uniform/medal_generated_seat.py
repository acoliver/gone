"""Seat the generated reverse on frozen wool and remove intersecting interior caps."""
import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from build import activate
from reduced_clearance import crossing_pairs

def reverse_anchors(obj, source_points, source_faces):
    """Keep the entire rear cap and every source rear-envelope bearing point."""
    region=obj.data.attributes['body_region2']
    selected={i for face in obj.data.polygons if region.data[face.index].value==2 for i in face.vertices}
    source=BVHTree.FromPolygons(source_points.tolist(),source_faces,all_triangles=True)
    for i,value in enumerate(obj.data.attributes['GeneratedNative'].data):
        q=value.vector
        if q.y<0:
            continue
        hit,normal,_,_=source.ray_cast(Vector((q.x,.02,q.z)),Vector((0.,-1.,0.)),.04)
        if hit is not None and abs(hit.y-q.y)<=1e-6 and normal.y>.25:
            selected.add(i)
    return np.array(sorted(selected))


def fit_reverse(obj, origin, frame, support):
    mesh=obj.data
    bm=bmesh.new()
    bm.from_mesh(mesh)
    region=bm.faces.layers.int['body_region2']
    for _ in range(5):
        edges=[e for e in bm.edges if e.calc_length()>.0045 and any(f[region]!=1 for f in e.link_faces)]
        if not edges:
            break
        bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.calc_loop_triangles()
    original=np.array([v.co[:] for v in mesh.vertices])
    source=BVHTree.FromPolygons(original.tolist(),[t.vertices[:] for t in mesh.loop_triangles],
                                all_triangles=True,epsilon=1e-8)
    attribute=mesh.attributes.new(name='GeneratedNative',type='FLOAT_VECTOR',domain='POINT')
    for item,point in zip(attribute.data,original):
        item.vector=point
    positions=original.copy()
    region=mesh.attributes['body_region2']
    front={i for f in mesh.polygons if region.data[f.index].value==1 for i in f.vertices}
    normal=-frame[1]
    for i,point in enumerate(original):
        if i in front:
            continue
        world=origin+point@frame
        hit=support.ray_cast(Vector(world+normal*.02),Vector(-normal),.04)[0]
        assert hit is not None
        depth=np.dot(np.array(hit)-origin,frame[1])
        x,y,z=point
        a=source.ray_cast(Vector((x,-.02,z)),Vector((0,1,0)),.04)[0]
        b=source.ray_cast(Vector((x,.02,z)),Vector((0,-1,0)),.04)[0]
        assert a is not None and b is not None
        span=b.y-a.y
        if span<1e-7 or y-a.y<2e-6:
            continue
        target=min(.00130,np.clip(b.y,depth-.0017,depth-.00026))
        assert target>a.y, ('Cloth reaches generated front',i,a.y,target)
        positions[i,1]=a.y+np.clip((y-a.y)/span,0,1)*(target-a.y)
    for vertex,point in zip(mesh.vertices,positions):
        vertex.co=point
    mesh.update()
    pairs=crossing_pairs(obj)
    print('REVERSE_FIT','vertices',len(positions),'interior_cap_crossings',len(pairs),flush=True)
    region=mesh.attributes['body_region2']
    reverse=sorted({i for face in mesh.polygons if region.data[face.index].value==2 for i in face.vertices})
    return np.array([v.co[:] for v in mesh.vertices]),np.array(reverse)


def clean_world_cap(obj):
    mesh=obj.data
    pairs=crossing_pairs(obj)
    if pairs:
        activate(obj)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.intersect_boolean(operation='UNION',use_self=True,solver='EXACT')
        bpy.ops.object.mode_set(mode='OBJECT')
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    region=bm.faces.layers.int['body_region2']
    front={v for face in bm.faces if face[region]==1 for v in face.verts}
    targets=bmesh.ops.find_doubles(bm,verts=list(bm.verts),keep_verts=list(front),dist=1e-7)['targetmap']
    bmesh.ops.weld_verts(bm,targetmap=targets)
    edges=[e for e in bm.edges if all(face[region]!=1 for face in e.link_faces)]
    bmesh.ops.dissolve_degenerate(bm,edges=edges,dist=1e-7)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    remaining=set(bm.faces)
    groups=[]
    while remaining:
        pending=[remaining.pop()]
        group=set(pending)
        while pending:
            face=pending.pop()
            for edge in face.edges:
                if len(edge.link_faces)!=2:
                    continue
                for other in edge.link_faces:
                    if other in remaining:
                        remaining.remove(other)
                        group.add(other)
                        pending.append(other)
        groups.append(group)
    groups.sort(key=len,reverse=True)
    print('CAP_GROUPS',[len(group) for group in groups],flush=True)
    fragments={face for group in groups[1:] for face in group}
    if fragments:
        assert all(face[region]!=1 for face in fragments), 'Generated front fragment must not be removed'
        for group in groups[1:]:
            vertices=np.array([v.co[:] for face in group for v in face.verts])
            center=vertices.mean(0)
            centered=vertices-center
            _,_,axes=np.linalg.svd(centered,full_matrices=False)
            width=np.ptp(centered@axes.T,axis=0).min()
            triangles=np.array([[face.verts[0].co[:],face.verts[i].co[:],face.verts[i+1].co[:]]
                                for face in group for i in range(1,len(face.verts)-1)])-center
            volume=abs(np.einsum('ij,ij->i',triangles[:,0],np.cross(triangles[:,1],triangles[:,2])).sum()/6)
            assert width<.00002 and volume<1e-12, 'Unexpected substantial disconnected body surface'
        bmesh.ops.delete(bm,geom=list(fragments),context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    assert all(len(e.link_faces)==2 for e in bm.edges), 'Cleaned body must be watertight'
    assert bm.calc_volume(signed=True)>0
    print('CAP_CLEANUP','welded',len(targets),'interior_fragment_faces',len(fragments),'triangles',len(bm.faces),flush=True)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    assert not crossing_pairs(obj), 'World-quantized body must have no cap crossings'
