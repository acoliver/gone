"""Quadric reduction with immutable detected feature vertices and edges."""
import heapq
import numpy as np


def reduce_body(obj, target, importance=None):
    mesh=obj.data
    mesh.calc_loop_triangles()
    vertices=np.array([v.co[:] for v in mesh.vertices])*1000
    faces=np.array([t.vertices[:] for t in mesh.loop_triangles],dtype=int)
    field_attribute=mesh.attributes.get('enamel_field7')
    field_flags=np.array([field_attribute.data[t.polygon_index].value for t in mesh.loop_triangles]) if field_attribute else np.zeros(len(faces),int)
    feature_weights={tuple(sorted(e.vertices)):mesh.attributes['crease_edge'].data[e.index].value for e in mesh.edges}
    feature_edges=[tuple(e.vertices) for e in mesh.edges
                   if mesh.attributes['crease_edge'].data[e.index].value>0]
    pinned=np.zeros(len(vertices),bool)
    pinned[np.array(feature_edges,dtype=int).ravel()]=True
    quadrics=np.zeros((len(vertices),4,4))
    incident=[set() for _ in vertices]
    valid=np.ones(len(faces),bool)
    alive=np.ones(len(vertices),bool)
    versions=np.zeros(len(vertices),int)
    for i,tri in enumerate(faces):
        a,b,c=vertices[tri]
        normal=np.cross(b-a,c-a)
        area=np.linalg.norm(normal)
        normal/=area
        plane=np.r_[normal,-normal@a]
        # The rear gets less error weight; front relief and side views get more.
        weight=.35 if normal[1]>.5 else 4. if normal[1]<-.25 else 3.
        if importance is not None:weight*=importance[i]
        q=np.outer(plane,plane)*area*weight
        for vertex in tri:
            quadrics[vertex]+=q
            incident[vertex].add(i)
    queue=[]

    def neighbours(i):
        return set(int(v) for f in incident[i] for v in faces[f] if v!=i)

    def candidate(a,b):
        if not alive[a] or not alive[b] or (pinned[a] and pinned[b]):
            return
        if pinned[b]:
            a,b=b,a
        q=quadrics[a]+quadrics[b]
        if pinned[a]:
            point=vertices[a].copy()
        else:
            candidates=[vertices[a],vertices[b],(vertices[a]+vertices[b])/2]
            if abs(np.linalg.det(q[:3,:3]))>1e-12:
                solution=np.linalg.solve(q[:3,:3],-q[:3,3])
                if np.linalg.norm(solution-(vertices[a]+vertices[b])/2)<np.linalg.norm(vertices[a]-vertices[b]):
                    candidates.append(solution)
            point=min(candidates,key=lambda x:np.r_[x,1]@q@np.r_[x,1]).copy()
        cost=max(0.,float(np.r_[point,1]@q@np.r_[point,1]))
        heapq.heappush(queue,(cost,a,b,int(versions[a]),int(versions[b]),tuple(point)))

    edges=set(tuple(sorted((int(a),int(b)))) for tri in faces
              for a,b in zip(tri,np.roll(tri,-1)))
    for a,b in edges:
        candidate(a,b)
    count=len(faces)
    collapsed=0
    while count>target and queue:
        _,a,b,va,vb,point=heapq.heappop(queue)
        if not alive[a] or not alive[b] or versions[a]!=va or versions[b]!=vb:
            continue
        common=incident[a]&incident[b]
        if len(common)!=2:
            continue
        shared=set(int(v) for f in common for v in faces[f])-{a,b}
        if neighbours(a)&neighbours(b)!=shared:
            continue
        point=np.array(point)
        affected=incident[a]|incident[b]
        remaining=sorted(affected-common)
        old=vertices[faces[remaining]]
        new=old.copy()
        new[(faces[remaining]==a)|(faces[remaining]==b)]=point
        normal_old=np.cross(old[:,1]-old[:,0],old[:,2]-old[:,0])
        normal_new=np.cross(new[:,1]-new[:,0],new[:,2]-new[:,0])
        lengths=np.linalg.norm(normal_new,axis=1)
        if np.any(lengths<1e-8) or np.any(np.einsum('ij,ij->i',normal_old,normal_new)
                <.2*np.linalg.norm(normal_old,axis=1)*lengths):
            continue
        # The enamel is a single-valued front membrane. A 3D normal test can
        # accept a projected fold on a steep narrow field triangle.
        if np.any(normal_new[field_flags[remaining]>0,1]>=-1e-12):
            continue
        local=neighbours(a)|neighbours(b)
        for f in affected:
            for v in faces[f]:
                incident[v].discard(f)
        for f in common:
            valid[f]=False
        for f in remaining:
            faces[f][faces[f]==b]=a
            for v in faces[f]:
                incident[v].add(f)
        vertices[a]=point
        quadrics[a]+=quadrics[b]
        alive[b]=False
        versions[a]+=1
        versions[b]+=1
        count-=2
        collapsed+=1
        # Invalid candidates may become legal after a neighbouring collapse.
        refreshed=set()
        for v in local|{a}:
            if alive[v]:
                for n in neighbours(v):
                    refreshed.add(tuple(sorted((v,n))))
        for x,y in refreshed:
            candidate(x,y)
    assert count<=target, ('constrained reduction cannot meet budget',count,target)
    retained=sorted(set(faces[valid].ravel()))
    index={v:i for i,v in enumerate(retained)}
    protected=set(tuple(sorted(e)) for e in feature_edges)
    final_edges=set(tuple(sorted((int(a),int(b)))) for tri in faces[valid]
                    for a,b in zip(tri,np.roll(tri,-1)))
    assert protected<=final_edges
    assert all(alive[v] for edge in feature_edges for v in edge)
    mesh.clear_geometry()
    mesh.from_pydata((vertices[retained]/1000).tolist(),[],
                     [[index[int(v)] for v in tri] for tri in faces[valid]])
    mesh.update()
    field=mesh.attributes.get('enamel_field7') or mesh.attributes.new('enamel_field7','INT','FACE')
    for face,flag in zip(mesh.polygons,field_flags[valid]):
        face.use_smooth=True
        field.data[face.index].value=int(flag)
    crease=mesh.attributes.get('crease_edge') or mesh.attributes.new('crease_edge','FLOAT','EDGE')
    for edge in mesh.edges:
        w=feature_weights.get(tuple(sorted(retained[i] for i in edge.vertices)),0.)
        crease.data[edge.index].value=w
        edge.use_edge_sharp=w>=.99
    stats={'input_triangles':len(faces),'output_triangles':count,
           'protected_feature_edges':len(protected),'retained_feature_edges':len(protected&final_edges),
           'fixed_feature_vertices':int(pinned.sum()),'collapsed_edges':collapsed,
           'method':'Visibility-weighted QEM on clean level-two cage subdivision; detected star branches/outline, rim steps, rear steps and silhouette edges cannot collapse or move. Link condition and normal orientation checked at every collapse.'}
    print('CONSTRAINED_REDUCTION',stats,flush=True)
    return stats
