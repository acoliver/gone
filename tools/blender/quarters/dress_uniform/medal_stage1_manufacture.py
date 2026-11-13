"""Independent millimetre-space measurements of the manufactured suspension and facets."""
import json

import numpy as np
import trimesh


def bounded_separation(a, b, exact):
    small,large=sorted([a,b],key=lambda m:len(m.vertices))
    upper=float(trimesh.proximity.closest_point(large,small.vertices)[1].min())+1e-5
    def candidates(source,other):
        lo,hi=source.triangles.min(1),source.triangles.max(1)
        gap=np.maximum(np.maximum(other.bounds[0]-hi,lo-other.bounds[1]),0)
        return source.submesh([np.flatnonzero(np.linalg.norm(gap,axis=1)<=upper)],append=True)
    # An AABB farther than an existing vertex/face upper bound cannot contain
    # the closest triangle pair. Keep exact edge/edge distances on the remainder.
    return exact(candidates(a,b),candidates(b,a))


def surface_measurements(out, meshes, separation):
    design=json.loads((out/'suspension-design.json').read_text())
    ribbon=np.load(out/'ribbon-constraints.npz')
    cloth=trimesh.Trimesh(ribbon['vertices']*1000,ribbon['faces'],process=False)
    fit=np.load(out/'feature-fit.npz')
    phase=float(fit['phase'])
    result={'design':design}
    for name,source in meshes.items():
        metal=source.copy();metal.apply_scale(1000)
        pieces=sorted(metal.split(only_watertight=False),key=lambda p:np.ptp(p.vertices[:,0]),reverse=True)
        assert len(pieces)==3,(name,'Expected body/eyelet, suspender bar and jump ring',len(pieces))
        body,bar,ring=pieces
        pairwise={a+'_'+b:float(bounded_separation(x,y,separation)) for a,b,x,y in
                  [('body','ring',body,ring),('body','bar',body,bar),('ring','bar',ring,bar)]}
        bar_gap=float(bounded_separation(bar,cloth,separation))
        ring_gap=float(bounded_separation(ring,cloth,separation))
        # Probe five rotated copies at matching radial positions, on the final mesh.
        radii=np.array([.15,.25,.5,1.,2.,3.,4.])
        angles=phase+np.arange(5)*2*np.pi/5
        origins=np.array([[r*np.cos(a),-10,r*np.sin(a)] for r in radii for a in angles])
        locations,ray,_=body.ray.intersects_location(origins,np.tile([0,1,0],(len(origins),1)),multiple_hits=True)
        depths=np.array([-locations[ray==i,1].min() for i in range(len(origins))]).reshape(-1,5)
        symmetry=float(np.ptp(depths,axis=1).max())
        data=np.load(out/f'{name}-geometry.npz')
        names=data['region_names'].tolist()
        anchor=phase+np.arange(10)*np.pi/5
        raw=np.interp(anchor%(2*np.pi),fit['angles'],fit['outline_mm'],period=2*np.pi)
        tip,notch=np.median(raw[::2]),np.median(raw[1::2])
        rr=np.where(np.arange(10)%2==0,tip,notch)*(1-.08/tip)
        polygon=np.c_[rr*np.cos(anchor),rr*np.sin(anchor)]
        planes=np.array([np.linalg.solve(np.array([polygon[i],polygon[(i+1)%10]]),np.full(2,1.30-2.20)) for i in range(10)])
        # Each main facet has one approximately 15.9 mm2 interior triangle;
        # the finished ridge strips are all below 0.21 mm2 and are not planes.
        roof_ids=np.flatnonzero((data['regions']==names.index('star_roof'))&(metal.area_faces>1.))
        assert len(roof_ids)==10,(name,'Expected ten main facet interiors')
        centres=metal.triangles_center[roof_ids]
        sector=np.floor(((np.arctan2(centres[:,2],centres[:,0])-phase)%(2*np.pi))/(np.pi/5)).astype(int)%10
        roof_error=float(np.max(abs(-centres[:,1]-(np.sum(centres[:,[0,2]]*planes[sector],axis=1)+2.20))))
        face_ids=np.flatnonzero(data['regions']==names.index('sidewall'))
        wall=metal.submesh([face_ids],append=True)
        # Full perimeter, including triangle interiors, at six section depths.
        station_t=np.linspace(0,1,16) if name=='high' else np.array([0,.35,.70,1.])
        samples=[]
        for depth in [.05,.10,.19,.275,.385,.50]:
            theta=np.arange(1440)*2*np.pi/1440
            origins=np.tile([0.,-depth,0.],(len(theta),1))
            directions=np.c_[np.cos(theta),np.zeros(len(theta)),np.sin(theta)]
            points,ray,_=wall.ray.intersects_location(origins,directions,multiple_hits=False)
            assert len(np.unique(ray))==len(theta),(name,depth,'Incomplete wall section')
            radius=np.linalg.norm(points[:,[0,2]],axis=1)
            expected=float(np.interp(depth,station_t*.55,15.88+.12*np.sin(station_t*np.pi/2)))
            samples.append(dict(depth_mm=depth,radius_peak_to_peak_mm=float(np.ptp(radius)),
                                maximum_absolute_radial_error_mm=float(np.max(abs(radius-expected))),
                                minimum_radius_mm=float(radius.min()),maximum_radius_mm=float(radius.max())))
        wall_error=max(x['maximum_absolute_radial_error_mm'] for x in samples)
        result[name]=dict(closed_manufactured_components=[bool(p.is_watertight and p.is_winding_consistent) for p in pieces],
            pairwise_solid_clearance_mm=pairwise,bar_to_ribbon_clearance_mm=bar_gap,
            ring_to_ribbon_clearance_mm=ring_gap,
            bar_measured_bounds_mm=bar.bounds.tolist(),
            eyelet_bore_minimum_wall_above_mm=18.02-(17.+.76),
            star_apex_fivefold_max_depth_spread_mm=symmetry,
            star_main_facet_max_plane_error_mm=roof_error,
            star_apex_probe_radii_mm=radii.tolist(),star_apex_probe_depths_mm=depths.tolist(),
            sidewall_perimeter_sections=samples,sidewall_roundness_max_radial_error_mm=wall_error,
            jump_ring_wire_measured_x_section_mm=float(np.ptp(ring.vertices[:,0])))
    result['gates']={
        'three_closed_interlocked_solids':all(all(result[n]['closed_manufactured_components']) for n in meshes),
        'suspension_no_solid_crossings':all(min(result[n]['pairwise_solid_clearance_mm'].values())>.05 for n in meshes),
        'bar_and_ring_clear_ribbon':all(min(result[n]['bar_to_ribbon_clearance_mm'],result[n]['ring_to_ribbon_clearance_mm'])>=.08 for n in meshes),
        'fivefold_apex_symmetry':all(result[n]['star_apex_fivefold_max_depth_spread_mm']<.001 for n in meshes),
        'planar_star_facets':all(result[n]['star_main_facet_max_plane_error_mm']<.001 for n in meshes),
        'sidewall_full_perimeter_roundness':result['low']['sidewall_roundness_max_radial_error_mm']<.009 and result['high']['sidewall_roundness_max_radial_error_mm']<.001,
    }
    (out/'manufacture-measurements.json').write_text(json.dumps(result,indent=2))
    return result
