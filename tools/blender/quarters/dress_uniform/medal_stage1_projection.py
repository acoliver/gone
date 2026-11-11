"""Project the standalone candidate through the unchanged in-game close camera."""
import json
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion, distance_transform_edt

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def projection(out):
    registration=json.loads((out/'registration.json').read_text())
    cameras=json.loads((ROOT/'tmp/issue130-metal-finish/after/cameras.json').read_text())
    camera=cameras['remembered-medal']
    transform=np.array([float(n) for n in re.findall(r'-?\d+(?:\.\d+)?',camera['transform'])]).reshape(4,3)
    frame=registration['frame']
    focal=camera['size'][0]/(2*np.tan(np.deg2rad(camera['fov'])/2))
    projected={}
    data={name:np.load(out/f'{name}-geometry.npz') for name in ['high','low']}
    for name,d in data.items():
        authored=d['vertices']@np.array(frame['frame'])+np.array(frame['origin'])
        # Blender to glTF, then the garment's unchanged +90-degree Godot Y rotation.
        world=np.c_[-authored[:,1],authored[:,2],-authored[:,0]]+[41.32804,-9.18,5.3]
        delta=world-transform[3]
        depth=-(delta@transform[2])
        assert np.all(depth>0)
        projected[name]=np.c_[delta@transform[0],-delta@transform[1]]/depth[:,None]*focal+np.array(camera['size'])/2
    low=np.vstack(list(projected.values())).min(0)*8-8
    high=np.vstack(list(projected.values())).max(0)*8+8
    size=tuple(np.ceil(high-low).astype(int))
    boundaries={}
    masks={}
    for name,d in data.items():
        image=Image.new('1',size)
        draw=ImageDraw.Draw(image)
        for triangle in (projected[name]*8-low)[d['faces']]:
            draw.polygon([tuple(point) for point in triangle],fill=1)
        mask=np.asarray(image,dtype=bool)
        masks[name]=mask
        boundaries[name]=mask&~binary_erosion(mask)
    boundary_error=max(distance_transform_edt(~boundaries[a])[boundaries[b]].max() for a,b in [('high','low'),('low','high')])/8
    error=max(distance_transform_edt(~masks[a])[masks[b]].max() for a,b in [('high','low'),('low','high')])/8
    width={}
    for name,d in data.items():
        ids=np.unique(d['faces'][d['regions']!=d['region_names'].tolist().index('bail')])
        width[name]=np.ptp(projected[name][ids],axis=0).tolist()
    result=dict(camera_key='remembered-medal (identical to present-medal)',camera=camera,
                projected_body_width_height_px=width,complete_silhouette_error_px=float(error),
                raster_quantization_px=.125,boundary_to_boundary_distance_px=float(boundary_error),
                silhouette_metric='Symmetric Hausdorff distance between filled silhouette sets, including opening voids. Boundary-to-boundary distance is separately reported because subpixel slits at tangent crossings can open or close without moving the filled silhouette by that slit length.',
                perimeter_chord_bound_px_at_490px=.5*490*(1-np.cos(np.pi/96)),
                scope='Standalone candidate rigidly projected through the frozen registration frame and unchanged camera. Garment origin [41.32804,-9.18,5.3] is reconstructed in the read-only plan; this is not mounting or a runtime capture.')
    (out/'close-camera-projection.json').write_text(json.dumps(result,indent=2))
    assert error<=.5,result
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    projection(Path(sys.argv[1]))
