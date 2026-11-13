"""Geometry and atlas checks for the manufactured-rim surface correction."""
import json
import sys
from pathlib import Path
import numpy as np
import trimesh
from scipy.ndimage import map_coordinates
from shapely.geometry import Polygon
from shapely import contains_xy

SOURCE=Path(__file__).resolve().parent
ROOT=SOURCE.parents[5]
FIT=ROOT/'tmp/issue130-v3/fit2'
OUT=ROOT/'tmp/issue130-v3/tex2/geom'
sys.path.insert(0,str(SOURCE.parent))
sys.path.insert(0,'/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d')
from mlx_hunyuan3d.rasterizer import rasterize
scope={'__file__':str(SOURCE.parent/'measure.py')}
exec((SOURCE.parent/'measure.py').read_text().split("report={'star':{}")[0],scope)
cycle=scope['cycle']
projection_scope={'__file__':str(SOURCE.parent/'silhouette12.py')}
exec((SOURCE.parent/'silhouette12.py').read_text().split("report={'scope':")[0],projection_scope)
outline=projection_scope['outline'];measure=projection_scope['measure']

def stats(x):
    return {'rms_mm':float(np.sqrt(np.mean(x*x))),'max_abs_mm':float(np.max(np.abs(x))),'p95_abs_mm':float(np.percentile(np.abs(x),95))}

arrays={k:json.loads((OUT/(k+'-arrays.json')).read_text()) for k in ['high','low']}
report={'topology':{},'star':{},'uv':{},'silhouette':{},'rim':{},'visual_assessment':False}
for kind,parts in arrays.items():
    report['topology'][kind]={}
    for part in parts:
        mesh=trimesh.Trimesh(np.array(part['vertices']),np.array(part['triangles']),process=False)
        report['topology'][kind][part['name']]={'triangles':len(mesh.faces),'watertight':bool(mesh.is_watertight),'consistent_winding':bool(mesh.is_winding_consistent),'signed_volume_m3':float(mesh.volume)}
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,part['name']
        if kind=='low':
            uv=np.array(part['triangle_uv'])
            original=next(p for p in json.loads((FIT/'low-arrays.json').read_text()) if p['name']==part['name'])
            a=uv[:,1]-uv[:,0];b=uv[:,2]-uv[:,0]
            signed=a[:,0]*b[:,1]-a[:,1]*b[:,0]
            import shapely
            polygons=shapely.polygons(uv)
            tree=shapely.STRtree(polygons)
            pairs=tree.query(polygons,predicate='intersects')
            pairs=pairs[:,pairs[0]<pairs[1]]
            areas=shapely.area(shapely.intersection(polygons[pairs[0]],polygons[pairs[1]]))
            max_overlap=float(areas.max()) if len(areas) else 0.
            report['uv'][part['name']]={'unchanged_corner_uvs':bool(np.array_equal(uv,original['triangle_uv'])),'finite':bool(np.isfinite(uv).all()),'bounds':[float(uv.min()),float(uv.max())],'minimum_absolute_triangle_area':float(np.min(np.abs(signed))/2),'maximum_overlap_area_uv2':max_overlap,'layout':'Fresh continuous front/rear and intrinsic side/hardware atlas; old UV interpolation overlapped after QEM.'}
            assert np.isfinite(uv).all() and np.min(np.abs(signed))>1e-14 and max_overlap<1e-10
    report['star'][kind]=cycle(parts[0])
    assert report['star'][kind]['peaks']==5
report['low_total_triangles']=sum(len(p['triangles']) for p in arrays['low'])
assert report['low_total_triangles']<=10500
for camera in ['studio','game']:
    shapes={k:outline(arrays[k],camera)[0] for k in arrays}
    report['silhouette'][camera]=measure(shapes['high'],shapes['low'])
    report['silhouette'][camera]['conservative_max_px']=report['silhouette'][camera]['max_px']+.025+.0003
    print('SILHOUETTE',camera,report['silhouette'][camera],flush=True)

photo_settings=json.loads((ROOT/'tmp/issue130-v3/tex1/projection/settings.json').read_text())
for view,angle in [('front-close',0.)]+[(state+'-oblique-close',photo_settings['photos'][state]['oblique']['inferred_azimuth_degrees']) for state in ['remembered','present']]:
    yaw=np.radians(angle)
    forward=-np.array([-np.sin(yaw),-np.cos(yaw),.06 if angle else 0.]);forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0.,0.,1.]);right/=np.linalg.norm(right)
    up=np.cross(right,forward)
    body=np.array(arrays['high'][0]['vertices'])
    scale=900/np.ptp(body@right)
    projection_scope['project']=lambda v,camera: np.c_[v@right,-v@up]*scale
    shapes={k:outline(arrays[k],view)[0] for k in arrays}
    report['silhouette'][view]=measure(shapes['high'],shapes['low'])
    report['silhouette'][view]['conservative_max_px']=report['silhouette'][view]['max_px']+.025+.0003
    print('SILHOUETTE',view,report['silhouette'][view],flush=True)

surface=np.load(OUT/'target-surface.npz')
center=surface['center'];radial=surface['radial'];profile=surface['profile'];border=float(surface['border_radius']);outer=float(surface['outer_radius'])
decisions=json.loads((OUT/'shape-decisions.json').read_text())
star=Polygon(decisions['star_outline_xz_mm'])
report['original_star_outline_max_xy_shift_mm']=decisions['high']['original_star_outline_max_xy_shift_mm']
assert report['original_star_outline_max_xy_shift_mm']<1e-10
# Keep clear of terminal contact blends when measuring the turned band.
aa=np.arange(1440)*2*np.pi/1440
radii=np.arange(border+.45,outer-.85,.1)
xz=center+radii[:,None,None]*np.stack([np.cos(aa),np.sin(aa)],axis=-1)[None]
excluded=contains_xy(star.buffer(.5),xz[...,0],xz[...,1])
for kind,parts in arrays.items():
    v=np.array(parts[0]['vertices'])*1000;t=np.array(parts[0]['triangles'])
    pitch=.025;lo=-18;side=1440
    fi,bary=rasterize(np.c_[(v[:,0]-lo)/pitch,(v[:,2]-lo)/pitch,v[:,1]],t,(side,side))
    depth=np.zeros((side,side));occupied=fi>0
    depth[occupied]=np.einsum('ni,ni->n',bary[occupied],v[t[fi[occupied]-1],1])
    sample=map_coordinates(depth,[(xz[...,1].ravel()-lo)/pitch-.5,(xz[...,0].ravel()-lo)/pitch-.5],order=1).reshape(xz.shape[:2])
    error=sample-np.interp(radii,radial,profile)[:,None]
    angle_variance=np.array([np.std(row[~mask]) for row,mask in zip(sample,excluded)])
    from scipy.spatial import ConvexHull
    hull=v[ConvexHull(v[:,[0,2]]).vertices][:,[0,2]]-center
    edge=np.roll(hull,-1,axis=0)-hull
    direction=np.c_[np.cos(aa),np.sin(aa)]
    cross=direction[:,0,None]*edge[None,:,1]-direction[:,1,None]*edge[None,:,0]
    numerator=hull[:,0]*edge[:,1]-hull[:,1]*edge[:,0]
    radial_hits=np.divide(numerator[None,:],cross,out=np.full_like(cross,np.inf),where=cross>1e-12).min(axis=1)
    report['rim'][kind]={'outer_circle_radial_deviation':stats(radial_hits-outer),'outer_circle_radius_peak_to_peak_mm':float(np.ptp(radial_hits)),
        'enamel_border':'Exact distance-to-circle material boundary, clipped only by generated star relief. Radius retained from generated inner-rim median.',
        'measured_radii_mm':[float(radii.min()),float(radii.max())],
        'excluded_contact_distance_mm':.5,'profile_deviation':stats(error[~excluded]),
        'angular_depth_std_rms_mm':float(np.sqrt(np.mean(angle_variance**2))),
        'angular_depth_std_max_mm':float(angle_variance.max())}
    # Measure exported glTF independently of the Blender authoring axes.
    scene=trimesh.load(OUT/('medal-'+kind+'.glb'),force='scene',process=False)
    report['topology'][kind]['exported_bounds_m']=scene.bounds.tolist()
report['silhouette_pass']=all(r['conservative_max_px']<.5 for r in report['silhouette'].values())
(OUT/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
assert report['silhouette_pass'],'High/low silhouette exceeds 0.5px'
print('GEOMETRY_VERIFIED',flush=True)
