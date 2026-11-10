from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from PIL import Image
O=Path(__file__).resolve().parent
positions=np.load(O/'surface-positions.npy');features=np.load(O/'convex-features.npy');coverage=np.load(O/'surface-coverage.npy')>.5
points=positions[coverage]*1.6-np.array([.6,.8,.01]);assert np.isfinite(points).all()
distances=cKDTree(features).query(points,workers=4)[0]
from scipy.ndimage import map_coordinates
lattice=np.random.default_rng(410).random((48,48,56)).astype(np.float32);coordinates=(points+np.array([.65,.85,.05]))/.04
assert np.all(coordinates>=0) and np.all(coordinates<np.array(lattice.shape)-1)
coherent=map_coordinates(lattice,coordinates.T,order=1,mode='nearest');broken=np.clip((coherent-.46)/.14,0,1);broken=broken*broken*(3-2*broken)
mask=np.zeros(coverage.shape,np.float32);mask[coverage]=np.clip((.014-distances)/.010,0,1)*broken
Image.fromarray(np.uint8(np.clip(mask[::-1],0,1)*255)).convert('RGB').save(O/'convex-edge-mask.png')
print('CONVEX_FIELD',len(features),'samples',int(coverage.sum()),'covered texels','band',int(np.count_nonzero(mask)),flush=True)
