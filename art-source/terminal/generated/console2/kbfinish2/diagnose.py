import bpy,numpy as np
from pathlib import Path
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'source.blend'));ob=bpy.data.objects['Keyboard'];m=ob.data
v=np.array([v.co[:] for v in m.vertices]);n=np.array([p.normal[:] for p in m.polygons]);c=np.array([p.center[:] for p in m.polygons]);print('normals',np.percentile(n[:,2],[0,10,50,90,100]));print('coords',np.percentile(c[:,2],[0,10,50,90,100]));print('up',sum(n[:,2]>.4),'down',sum(n[:,2]<-.4))
z=np.load(OUT/'segmentation.npz');xs=z['xs'];ys=z['ys'];xx=np.clip(np.round((c[:,0]-xs[0])/(xs[-1]-xs[0])*800).astype(int),0,800);yy=np.clip(np.round((c[:,1]-ys[0])/(ys[-1]-ys[0])*308).astype(int),0,308);h=z['height'][yy,xx];base=z['base'][yy,xx];labels=z['labels'][yy,xx]
for normal in [n[:,2]>.4,n[:,2]<-.4]:
 print('near visible',sum(normal&(abs(c[:,2]-h)<.003)),'key',sum(normal&(labels>0)&(abs(c[:,2]-h)<.003)),'residual',np.percentile((c[:,2]-base)[normal],[0,25,50,75,100]))
print('positions sample',c[:3],n[:3]);print('threshold',z['threshold'])
