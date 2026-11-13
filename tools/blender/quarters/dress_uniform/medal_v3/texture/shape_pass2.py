"""Derive a revolved rim from fit2 and soften the generated relief in millimetres."""
import json
import sys
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates, distance_transform_edt
from scipy.interpolate import interp1d
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon
from shapely import contains_xy

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[5]
FIT = ROOT / 'tmp/issue130-v3/fit2'
OUT = ROOT / 'tmp/issue130-v3/tex2/geom'
OUT.mkdir(parents=True, exist_ok=True)
HY = Path('/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d')
sys.path.insert(0, str(HY))
from mlx_hunyuan3d.rasterizer import rasterize


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x*x*(3-2*x)


def main():
    arrays = {k: json.loads((FIT / (k+'-arrays.json')).read_text()) for k in ['high', 'low']}
    features = json.loads((FIT / 'features.json').read_text())
    paths = {x['name']: np.array(x['points_mm']) for x in features['features']}
    star = Polygon(paths['star_outline'][:, [0, 2]])
    body = arrays['high'][0]
    v = np.array(body['vertices'])*1000
    t = np.array(body['triangles'])
    # Read the fitted source's actual field-boundary cycles. The smaller one
    # is the generated star, including its unequal tips and fitted joins.
    from collections import defaultdict
    edges=np.sort(np.concatenate([t[:,[0,1]],t[:,[1,2]],t[:,[2,0]]]),axis=1)
    labels=np.tile(np.array(body['field']),3)
    order=np.lexsort((edges[:,1],edges[:,0]));edges=edges[order];labels=labels[order]
    assert np.array_equal(edges[::2],edges[1::2])
    border_edges=edges[::2][labels[::2]!=labels[1::2]]
    adjacent=defaultdict(list)
    for a,b in border_edges:
        adjacent[int(a)].append(int(b));adjacent[int(b)].append(int(a))
    assert all(len(ns)==2 for ns in adjacent.values())
    remaining=set(adjacent);cycles=[]
    while remaining:
        ids=[min(remaining)];previous=None
        while True:
            nxt=next(i for i in adjacent[ids[-1]] if i!=previous);previous=ids[-1]
            if nxt==ids[0]:break
            ids.append(nxt)
        remaining-=set(ids);cycles.append(ids)
    assert len(cycles)==2
    star_ids=min(cycles,key=lambda ids:Polygon(v[ids][:,[0,2]]).area)
    star=Polygon(v[star_ids][:,[0,2]]).simplify(.005,preserve_topology=True)
    # Fit the evaluated source disk, rather than the pre-subdivision controls.
    hull_points = v[ConvexHull(v[:,[0,2]]).vertices][:,[0,2]]
    circle_points = hull_points[hull_points[:,1]<9]
    result = least_squares(lambda p: np.linalg.norm(circle_points-p[:2],axis=1)-p[2], [0,0,16])
    center = result.x[:2]
    angle = np.arange(2880)*2*np.pi/2880
    direction = np.c_[np.cos(angle),np.sin(angle)]
    a = hull_points-center
    e = np.roll(a,-1,axis=0)-a
    cross = direction[:,0,None]*e[None,:,1]-direction[:,1,None]*e[None,:,0]
    numerator = a[:,0]*e[:,1]-a[:,1]*e[:,0]
    ray_radius = np.divide(numerator[None,:],cross,out=np.full_like(cross,np.inf),where=cross>1e-12)
    radii = ray_radius.min(axis=1)
    assert np.isfinite(radii).all() and np.min(radii)>14
    outer_radius = float(np.median(radii))
    outer_at = interp1d(np.r_[angle[-1]-2*np.pi,angle,angle[0]+2*np.pi],np.r_[radii[-1],radii,radii[0]])
    border_radius = float(np.median(np.linalg.norm(paths['rim_step_0'][:,[0,2]]-center,axis=1)))
    pitch = .025
    lo = -18.
    side = 1440
    screen = np.c_[(v[:,0]-lo)/pitch,(v[:,2]-lo)/pitch,v[:,1]]
    fi, bary = rasterize(screen,t,(side,side))
    occupied = fi>0
    depth = np.zeros((side,side))
    depth[occupied] = np.einsum('ni,ni->n',bary[occupied],v[t[fi[occupied]-1],1])
    index = distance_transform_edt(~occupied,return_distances=False,return_indices=True)
    depth = depth[tuple(index)]
    def sample(image, xz):
        return map_coordinates(image,[(xz[:,1]-lo)/pitch-.5,(xz[:,0]-lo)/pitch-.5],order=1,mode='nearest')
    # Every radius has 1,440 equal-angle first-hit samples. No ideal profile,
    # profile spline or hand-specified stepped cross-section is substituted.
    radial = np.arange(10.2, outer_radius-.03, .025)
    aa = np.arange(1440)*2*np.pi/1440
    xz = center+radial[:,None,None]*np.stack([np.cos(aa),np.sin(aa)],axis=-1)[None]
    raw_profile = np.median(sample(depth,xz.reshape(-1,2)).reshape(len(radial),-1),axis=1)
    profile = interp1d(radial,raw_profile,bounds_error=False,fill_value=(raw_profile[0],raw_profile[-1]))
    np.savetxt(OUT/'generated-median-rim-profile.csv',np.c_[radial,raw_profile],delimiter=',',header='radius_mm,front_y_mm',comments='')
    yy,xx = np.mgrid[:side,:side]
    gx = lo+(xx+.5)*pitch
    gz = lo+(yy+.5)*pitch
    rr = np.hypot(gx-center[0],gz-center[1])
    star_inside = contains_xy(star,gx,gz)
    inside_distance = distance_transform_edt(star_inside)*pitch
    outside_distance = distance_transform_edt(~star_inside)*pitch
    signed = inside_distance-outside_distance
    # A 0.075 mm Gaussian footprint rounds existing ridges rather than
    # introducing analytic facets. The asymmetric source star XY is untouched.
    soft_depth = gaussian_filter(depth,.075/pitch)
    field_depth = float(np.median(depth[(rr>9)&(rr<10.5)&(~star_inside)]))
    rim_weight = smoothstep((rr-(border_radius-.45))/.6)
    manufactured_base = field_depth*(1-rim_weight)+profile(rr)*rim_weight
    # Terminate relief at its shared substrate over a short contact band.
    # The high ridge stays generated; the previous terminal hump cannot remain
    # as a separate raised tab at either the field or the turned rim.
    star_weight = smoothstep((signed+.10)/.38)
    target = manufactured_base*(1-star_weight)+soft_depth*star_weight
    # Retain field's broad fitted depth inside the star-free central annulus,
    # but remove the undulating border by joining it to the circular substrate.
    local_field = gaussian_filter(depth,.25/pitch)
    field_blend = smoothstep((rr-(border_radius-1.0))/.65)
    outside_target = local_field*(1-field_blend)+manufactured_base*field_blend
    target = outside_target*(1-star_weight)+soft_depth*star_weight
    changes = {}
    for kind, parts in arrays.items():
        src = np.array(parts[0]['vertices'])*1000
        q = src.copy()
        r = np.linalg.norm(q[:,[0,2]]-center,axis=1)
        a = np.arctan2(q[:,2]-center[1],q[:,0]-center[0])%(2*np.pi)
        radial_shift = outer_radius-outer_at(a)
        # Use only the physical sidewall, never the suspension/neck cap.
        w = smoothstep((r-14.0)/1.2)*smoothstep((-sample(signed,src[:,[0,2]])-.05)/.25)
        q[:,[0,2]] += ((q[:,[0,2]]-center)/r[:,None])*radial_shift[:,None]*w[:,None]
        region_front = src[:,1]<-.7
        # Keep the round sidewall shoulder connected to the unchanged back.
        front_weight = smoothstep((-src[:,1]-.7)/.65)
        new_depth = sample(target,q[:,[0,2]])
        side_blend = 1-smoothstep((r-(outer_radius-.65))/.6)
        weight = front_weight*side_blend
        q[:,1] += (new_depth-src[:,1])*weight
        changes[kind] = {'body_max_vertex_shift_mm':float(np.linalg.norm(q-src,axis=1).max()),'body_rms_vertex_shift_mm':float(np.sqrt(np.mean(np.sum((q-src)**2,axis=1))))}
        if kind=='high':
            changes[kind]['original_star_outline_max_xy_shift_mm']=float(np.linalg.norm((q-src)[star_ids][:,[0,2]],axis=1).max())
            assert changes[kind]['original_star_outline_max_xy_shift_mm']<1e-10
        np.savez_compressed(OUT/(kind+'-positions.npz'),vertices=q/1000)
    # Numerical profile comparison uses the same unmodified sample definition.
    new_sample = sample(target,xz.reshape(-1,2)).reshape(len(radial),-1)
    star_support = contains_xy(star,xz[...,0],xz[...,1])
    errors = new_sample-raw_profile[:,None]
    core = (radial>border_radius+.22)&(radial<outer_radius-.7)
    usable = core[:,None]&(~star_support)
    changes.update({'circle_center_xz_mm':center.tolist(),'outer_radius_mm':outer_radius,'enamel_border_radius_mm':border_radius,
        'median_profile_source':str(FIT/'medal-high.glb'),'profile_samples_per_radius':1440,'profile_radial_pitch_mm':.025,
        'profile_deviation_target_rms_mm':float(np.sqrt(np.mean(errors[usable]**2))),
        'profile_deviation_target_max_mm':float(np.max(np.abs(errors[usable]))),
        'star_outline_xz_mm':list(star.exterior.coords)[:-1],
        'bevel_footprint_mm':.075,'star_outline_xy':'Unchanged generated asymmetric five-point outline; only relief depths and terminal joins changed.',
        'uv_policy':'All vertex identities, triangles, and corner UVs retained; material IDs reclassified against original star and circular enamel boundary.',
        'method':'Median equal-angle first-hit fit2 front height at each rim radius, revolved without radial smoothing; 0.6 mm field transition, 0.6 mm shoulder transition; generated star height Gaussian rounded at 0.075 mm, contact flattened to its substrate over 0.38 mm.'})
    np.savez_compressed(OUT/'target-surface.npz',depth=target,original=depth,star_signed=signed,pitch=pitch,lo=lo,center=center,radial=radial,profile=raw_profile,border_radius=border_radius,outer_radius=outer_radius,source_angle=angle,source_radius=radii)
    (OUT/'shape-decisions.json').write_text(json.dumps(changes,indent=2))
    print(json.dumps(changes,indent=2),flush=True)

if __name__=='__main__':
    main()
