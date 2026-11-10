from pathlib import Path
O=Path(__file__).resolve().parent
s=(O/'geometry.py').read_text();start=s.index('# Remove scan ripples');end=s.index("rem=body.modifiers.new",start)
s=s[:start]+'''# Reconstruct clean side/underside panels from the fitted raw silhouette and front ray depths.
# A remesh of the thin torn scan alone seals its skin but retains deep closed creases.
from mathutils.bvhtree import BVHTree
raw=np.array([v.co[:] for v in body.data.vertices]);bvh=BVHTree.FromPolygons([v.co for v in body.data.vertices],[p.vertices[:] for p in body.data.polygons])
zgrid=np.linspace(raw[:,2].min(),raw[:,2].max(),320);lefts=[];rights=[];fronts=[]
for z in zgrid:
 row=raw[np.abs(raw[:,2]-z)<.003]
 lefts.append(float(row[:,0].min()) if len(row) else np.nan);rights.append(float(row[:,0].max()) if len(row) else np.nan);fronts.append(float(row[:,1].min()) if len(row) else np.nan)
lefts=np.array(lefts);rights=np.array(rights);fronts=np.array(fronts)
for values in (lefts,rights,fronts):
 valid=np.isfinite(values);values[:]=np.interp(zgrid,zgrid[valid],values[valid])
newleft=lefts.copy();newright=rights.copy()
for z0,z1 in [(.025,.465),(.555,.625),(.700,1.245)]:
 region=(zgrid>=z0)&(zgrid<=z1)
 for original,new in [(lefts,newleft),(rights,newright)]:
  coefficients=np.polyfit(zgrid[region],original[region],1);fit=np.polyval(coefficients,zgrid[region]);weights=np.minimum(1.,np.minimum((zgrid[region]-z0)/.012,(z1-zgrid[region])/.012));new[region]=original[region]*(1-weights)+fit*weights
# Suppress single-row scan notches while retaining the head, deck and pedestal corners.
for values in (newleft,newright,fronts):
 values[1:-1]=values[:-2]*.2+values[1:-1]*.6+values[2:]*.2
vertices=[];faces=[];columns=65;stride=columns+2
for row,z in enumerate(zgrid):
 l,r=newleft[row],newright[row];oldl,oldr=lefts[row],rights[row];front=fronts[row]
 for col,t in enumerate(np.linspace(0,1,columns)):
  x=l+t*(r-l);samplex=oldl+t*(oldr-oldl);hit,n,f,d=bvh.ray_cast(Vector((samplex,-2,z)),Vector((0,1,0)));y=front if hit is None else min(front+.035,max(front,hit.y))
  if t<.06 or t>.94:y=front
  vertices.append((float(x),float(y),float(z)))
 vertices.extend([(float(l),0,float(z)),(float(r),0,float(z))])
 if row:
  a=(row-1)*stride;b=row*stride
  for col in range(columns-1):faces.append((a+col,a+col+1,b+col+1,b+col))
  faces.extend([(a+columns,b+columns,b,a),(a+columns-1,b+columns-1,b+columns+1,a+columns+1),(a+columns+1,b+columns+1,b+columns,a+columns)])
faces.append(tuple(list(range(columns))+[columns+1,columns]));a=(len(zgrid)-1)*stride;faces.append(tuple([a+columns,a+columns+1]+[a+c for c in reversed(range(columns))]))
clean=bpy.data.meshes.new('Clean fitted console shell');clean.from_pydata(vertices,[],faces);clean.update();body.data=clean
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free();body.data.materials.append(emitmat())
report['local_repairs']=['Closed side and underside panels reconstructed from the raw fitted silhouette, retaining the ray-sampled front depth and screen recess.','Side-panel outline straightened with 12 mm feathering; single-row scan notches filtered before voxel rebuilding.','Deck-to-body joint is a continuous solid shell with no retained scan sliver.']
''' +s[end:]
(O/'geometry.py').write_text(s)
