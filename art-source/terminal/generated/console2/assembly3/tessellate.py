import numpy as np

def local_tessellation(mesh,influence,rear):
 vertices=[tuple(v.co) for v in mesh.vertices]
 faces=[tuple(p.vertices) for p in mesh.polygons]
 uvs=np.array([l.uv[:] for l in mesh.uv_layers.active.data]).reshape(-1,3,2)
 for iteration in range(8):
  points=np.array(vertices);active=influence(points)>1e-10;midpoints={}
  for face in faces:
   if not active[list(face)].any():continue
   for a,b in zip(face,np.roll(face,-1)):
    edge=tuple(sorted((int(a),int(b))))
    if np.linalg.norm(points[a]-points[b])>.025 and edge not in midpoints:
     midpoints[edge]=len(vertices);vertices.append(tuple((points[a]+points[b])/2))
  if not midpoints:break
  output=[];outuv=[]
  for face,uv in zip(faces,uvs):
   mids=[midpoints.get(tuple(sorted((face[i],face[(i+1)%3])))) for i in range(3)];count=sum(m is not None for m in mids)
   if not count:output.append(face);outuv.append(uv);continue
   if count==3:
    a,b,c=face;ab,bc,ca=mids;ua,ub,uc=uv;uab=(ua+ub)/2;ubc=(ub+uc)/2;uca=(uc+ua)/2
    output.extend([(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]);outuv.extend([(ua,uab,uca),(uab,ub,ubc),(uca,ubc,uc),(uab,ubc,uca)]);continue
   # Rotate the face so its split edges have an explicit local pattern.
   start=next(i for i in range(3) if mids[i] is not None and (count==1 or mids[(i+1)%3] is not None))
   ids=[(start+i)%3 for i in range(3)];a,b,c=[face[i] for i in ids];ua,ub,uc=uv[ids];ab=mids[start];uab=(ua+ub)/2
   if count==1:
    output.extend([(a,ab,c),(ab,b,c)]);outuv.extend([(ua,uab,uc),(uab,ub,uc)])
   else:
    bc=mids[(start+1)%3];ubc=(ub+uc)/2
    output.extend([(a,ab,c),(ab,bc,c),(ab,b,bc)]);outuv.extend([(ua,uab,uc),(uab,ubc,uc),(uab,ub,ubc)])
  faces=output;uvs=np.array(outuv)
 # Split triangles exactly at the protected rear boundary. The cut is shared
 # across adjacent triangles, and UV interpolation remains local to each face.
 points=np.array(vertices);weights=influence(points);crossings={};output=[];outuv=[]
 for face,uv in zip(faces,uvs):
  y=points[list(face),1]-rear
  if not (y.min()<-1e-8 and y.max()>1e-8):output.append(face);outuv.append(uv);continue
  for sign in [-1,1]:
   poly=[]
   for i in range(3):
    j=(i+1)%3;a,b=face[i],face[j];ya,yb=y[i],y[j]
    if sign*ya>=-1e-8:poly.append((a,uv[i]))
    if ya*yb<0 and abs(ya)>1e-8 and abs(yb)>1e-8:
     edge=tuple(sorted((a,b)));t=-ya/(yb-ya)
     if edge not in crossings:
      q=points[a]+t*(points[b]-points[a]);q[1]=rear;crossings[edge]=len(vertices);vertices.append(tuple(q))
     poly.append((crossings[edge],uv[i]+t*(uv[j]-uv[i])))
   for i in range(1,len(poly)-1):
    tri=[poly[0],poly[i],poly[i+1]];output.append(tuple(p[0] for p in tri));outuv.append([p[1] for p in tri])
 coordinates=np.array(vertices,dtype=np.float32);faces=np.array(output);uvs=np.array(outuv)
 area=np.linalg.norm(np.cross(coordinates[faces[:,1]]-coordinates[faces[:,0]],coordinates[faces[:,2]]-coordinates[faces[:,0]]),axis=1)
 assert area.min()>0,'Tessellation produced a degenerate face'
 mesh.clear_geometry();mesh.from_pydata(coordinates.tolist(),[],faces.tolist());mesh.update()
 layer=mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap')
 for l,uv in zip(layer.data,uvs.reshape(-1,2)):l.uv=uv
 return len(coordinates),len(faces)
