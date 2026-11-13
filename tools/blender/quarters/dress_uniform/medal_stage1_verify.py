"""Measure stage-one geometry independently of Blender and its saved metadata."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import ConvexHull, cKDTree
from shapely.geometry import Polygon
from shapely.strtree import STRtree
import trimesh


def stats(a):
    a=np.asarray(a)
    return dict(zip(['p50','p95','max'],np.quantile(a,[.5,.95,1]).tolist()))


def nearest(target,points):
    # Trimesh's absolute triangle tolerances misclassify submillimetre
    # triangles in metre space. Solve distances in millimetres throughout.
    scaled=trimesh.Trimesh(vertices=target.vertices*1000,faces=target.faces,process=False)
    return np.concatenate([trimesh.proximity.closest_point(scaled,points[i:i+1024]*1000)[1]
                           for i in range(0,len(points),1024)])

def hull_distance(a,b):
    a=a[ConvexHull(a).vertices]
    b=b[ConvexHull(b).vertices]
    def directed(p,q):
        end=np.roll(q,-1,axis=0)
        v=end-q
        t=np.clip(np.sum((p[:,None]-q[None])*v[None],axis=2)/np.sum(v*v,axis=1),0,1)
        return np.linalg.norm(p[:,None]-(q[None]+t[:,:,None]*v[None]),axis=2).min(1).max()
    return max(directed(a,b),directed(b,a))


def verify(out):
    result={}
    budget=json.loads((out/'budget.json').read_text())
    meshes={}
    for name in ['high','low']:
        d=np.load(out/f'{name}-geometry.npz')
        mesh=trimesh.Trimesh(vertices=d['vertices'],faces=d['faces'],process=False)
        meshes[name]=mesh
        v=mesh.vertices*1000
        radius=np.linalg.norm(v[:,[0,2]],axis=1)
        body_ids=np.unique(d['faces'][d['regions']!=d['region_names'].tolist().index('bail')])
        body=v[body_ids]
        mat=d['materials']
        enamel=mesh.triangles[mat==1]*1000
        peak=float(-v[radius<1,1].min())
        bed=float(np.median(-enamel[:,:,1]))
        side=v[radius>15.95]
        exported=trimesh.load(out/f'medal-{name}.glb',force='mesh',process=True)
        exported.merge_vertices(merge_tex=True,merge_norm=True)
        sys.path.append(str(Path(__file__).resolve().parents[2]/'quarters_aging'))
        from triangle_contacts import intersect
        crossings=[]
        tree=mesh.triangles_tree
        for i,triangle in enumerate(mesh.triangles):
            bounds=np.r_[triangle.min(0),triangle.max(0)]
            for j in tree.intersection(bounds):
                if j<=i:continue
                other=mesh.triangles[j]
                if np.any(np.linalg.norm(triangle[:,None]-other[None,:],axis=2)<1e-7):continue
                if intersect(triangle*1000,other*1000,tolerance=1e-6):crossings.append([i,int(j)])
        result[name]=dict(triangles=len(mesh.faces),vertices=len(mesh.vertices),
                          strict_self_contacts=len(crossings),self_contact_examples=crossings[:10],
                          watertight=bool(mesh.is_watertight),winding_consistent=bool(mesh.is_winding_consistent),
                          components=len(mesh.split(only_watertight=False)),
                          body_diameter_mm=float(2*np.max(radius[body_ids])),
                          body_depth_mm=float(np.ptp(body[:,1])),
                          star_peak_front_mm=peak,enamel_bed_front_mm=bed,star_rise_mm=peak-bed,
                          degenerate_3d_triangles=int(np.sum(mesh.area_faces<1e-16)),
                          exported_bounds_yup_m=exported.bounds.tolist(),exported_watertight=bool(exported.is_watertight))
        if name=='low':
            uv=d['uv']
            a,b=uv[:,1]-uv[:,0],uv[:,2]-uv[:,0]
            area=abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])*.5
            polys=[Polygon(t) for t in uv]
            tree=STRtree(polys)
            overlaps=[]
            for i,p in enumerate(polys):
                for j in tree.query(p,predicate='intersects'):
                    if j>i and p.intersection(polys[j]).area>1e-12:
                        overlaps.append([i,int(j)])
            parent=list(range(len(uv)))
            def root(i):
                while parent[i]!=i:
                    parent[i]=parent[parent[i]];i=parent[i]
                return i
            edges={}
            for i,triangle in enumerate(uv):
                for a,b in zip(triangle,np.roll(triangle,-1,axis=0)):
                    key=tuple(sorted([tuple(np.round(a,7)),tuple(np.round(b,7))]))
                    if key in edges:parent[root(i)]=root(edges[key])
                    else:edges[key]=i
            from shapely.ops import unary_union
            groups={}
            for i,p in enumerate(polys):groups.setdefault(root(i),[]).append(p)
            islands=[unary_union(group) for group in groups.values()]
            gutter=min(a.distance(b) for i,a in enumerate(islands) for b in islands[i+1:])*2048
            front=(mesh.face_normals[:,1]<-.5)&(mesh.triangles_center[:,2]<.0155)
            density=float(np.sqrt(np.sum(area[front])/np.sum(mesh.area_faces[front]))*.032*2048)
            result[name].update(uv_zero_area=int(np.sum(area<1e-12)),uv_min_area=float(area.min()),
                                equivalent_visible_front_diameter_texels_at_2048=density,
                                uv_overlapping_triangle_pairs=len(overlaps),uv_overlap_examples=overlaps[:10],
                                uv_islands=len(islands),uv_min_gutter_texels_at_2048=float(gutter),
                                uv_bounds=[uv.min((0,1)).tolist(),uv.max((0,1)).tolist()])
    fit=np.load(out/'feature-fit.npz')
    source=np.load(out/'guide-samples.npz')
    report=json.loads((out/'feature-fit.json').read_text())
    reg=json.loads((out/'registration.json').read_text())
    ribbon=np.load(out/'ribbon-constraints.npz')
    # Actual guide-triangle barycentric correspondence for every supported angular/radial hit.
    aa,rr=np.meshgrid(source['angles'],source['radii'],indexing='ij')
    valid=source['triangle_ids']>=0
    points=np.stack([rr*np.cos(aa),-source['depths'],rr*np.sin(aa)],axis=-1)[valid]
    triangle_ids=source['triangle_ids'][valid]
    triangles=source['vertices'][source['faces'][triangle_ids]]
    bary=trimesh.triangles.points_to_barycentric(triangles,points)
    reconstructed=np.sum(triangles*bary[:,:,None],axis=1)
    np.savez_compressed(out/'guide-correspondence.npz',triangle_ids=triangle_ids,barycentric=bary,
                        sampled_points_m=points)
    result['correspondence']=dict(samples=len(points),max_reconstruction_error_mm=float(np.linalg.norm(points-reconstructed,axis=1).max()*1000),
                                  minimum_barycentric_weight=float(bary.min()))
    # GuideFaired displacement is indexed one-to-one against all original triangles.
    noise=np.linalg.norm(fit['clean_vertices']-fit['raw_vertices'],axis=1)*1000
    result['noise_only_deviation_mm']=report['noise_only_displacement_mm']
    result['pinned_curve_deviation_mm']=report['pinned_displacement_mm']
    matched_clean=np.sum(fit['clean_vertices'][source['faces'][triangle_ids]]*bary[:,:,None],axis=1)
    sample_angles=aa[valid]
    sample_radius=rr[valid]*1000
    result['sixteen_radial_cut_noise_mm']=[]
    for angle in source['angles'][::16]:
        mask=np.abs(np.angle(np.exp(1j*(sample_angles-angle))))<.001
        result['sixteen_radial_cut_noise_mm'].append(dict(angle_degrees=float(np.rad2deg(angle)),
                  displacement_mm=stats(np.linalg.norm(matched_clean[mask]-points[mask],axis=1)*1000)))
    result['five_star_arms']=[]
    for arm in range(5):
        angle=float(fit['phase'])+arm*2*np.pi/5
        mask=(np.abs(np.angle(np.exp(1j*(sample_angles-angle))))<.035)&(sample_radius<11)
        result['five_star_arms'].append(dict(arm=arm,tip_radius_mm=float(np.interp(angle%(2*np.pi),fit['angles'],fit['outline_mm'],period=2*np.pi)),
                  raw_peak_depth_mm=float(-points[mask,1].min()*1000),
                  faired_peak_depth_mm=float(-matched_clean[mask,1].min()*1000),
                  noise_displacement_mm=stats(np.linalg.norm(matched_clean[mask]-points[mask],axis=1)*1000)))
    result['guide_feature_regions']={str(label):stats(noise[fit['labels']==label]) for label in np.unique(fit['labels'])}
    high=meshes['high']
    raw_vertices=fit['raw_vertices']
    raw_radius=np.linalg.norm(raw_vertices[:,[0,2]],axis=1)*1000
    feature_masks={
        'field':fit['labels']==3,
        'star':fit['labels']==6,
        'rim':fit['labels']==4,
        'suspension':fit['labels']==5,
    }
    for landmark in report['landmarks']:
        feature_masks[landmark['name']]=(fit['labels']==4)&(abs(raw_radius-landmark['radius_mm'])<.15)
    result['raw_to_corrected_high_feature_deviation_mm']={
        'direction':'Raw guide vertices to nearest corrected high surface; deterministic every-eighth vertex within each feature.',
        'regions':{},
    }
    for name,mask in feature_masks.items():
        ids=np.flatnonzero(mask)[::8]
        distance=nearest(high,raw_vertices[ids])/1000
        result['raw_to_corrected_high_feature_deviation_mm']['regions'][name]=dict(samples=len(ids),**stats(distance*1000))
    # Report deliberate manufacturing corrections separately from denoising; they are not a fidelity pass.
    for label in [3,4,6]:
        ids=np.flatnonzero(fit['labels']==label)[::8]
        distance=nearest(high,fit['clean_vertices'][ids])/1000
        result.setdefault('intentional_manufacturing_correction_mm',{})[str(label)]=stats(distance*1000)
    # Include vertices, triangle interiors and edge midpoints in both directions.
    # Sampling only low vertices misses omitted high-poly terraces entirely.
    low=meshes['low']
    result['bidirectional_surface_residual_mm']={}
    for name,target_name in [('low','high'),('high','low')]:
        m=meshes[name]
        points=np.vstack([m.vertices,m.triangles_center,m.vertices[m.edges_unique].mean(1)])
        distance=nearest(meshes[target_name],points)
        result['bidirectional_surface_residual_mm'][name+'_to_'+target_name]=stats(distance)
        if name=='low':
            samples=points
            result['low_to_high_surface_residual_mm']=stats(distance)
        d=np.load(out/f'{name}-geometry.npz')
        names=d['region_names'].tolist()
        centers=m.triangles_center
        dd=nearest(meshes[target_name],centers)
        for region in names:
            mask=d['regions']==names.index(region)
            if mask.any():
                result.setdefault('surface_residual_by_feature_mm',{}).setdefault(name+'_to_'+target_name,{})[region]=dict(samples=int(mask.sum()),**stats(dd[mask]))
    result['normal_bake_only_regions']={
        'scope':'Fine rounding and the 0.065 mm enamel meniscus only. Steps, groove valleys, silhouette and bail are geometry. No residual is excluded from the 0.10 mm maximum gate.',
        'measured_regions':['star_bevel','enamel','star_center'],
    }
    silhouettes={}
    for degrees in [0,-35,35,90]:
        a=np.deg2rad(degrees)
        project=lambda p:np.c_[p[:,0]*np.cos(a)+p[:,1]*np.sin(a),p[:,2]]*1000
        silhouettes[str(degrees)]=float(hull_distance(project(low.vertices),project(high.vertices)))
    result['projected_convex_silhouette_departure_mm']=silhouettes
    # Rasterize the complete projected solid, including the nonconvex bail hole,
    # at 8x the 490 px close-camera body width. This is a matched scale diagnostic,
    # not a mounted in-game capture. Quantization uncertainty is 0.125 px.
    from PIL import Image, ImageDraw
    from scipy.ndimage import distance_transform_edt
    raster={}
    for degrees in [0,-35,35,90]:
        a=np.deg2rad(degrees)
        scale=490/32*8
        projected={n:np.c_[m.vertices[:,0]*np.cos(a)+m.vertices[:,1]*np.sin(a),m.vertices[:,2]]*1000*scale for n,m in meshes.items()}
        lo=np.vstack(list(projected.values())).min(0)-8
        hi=np.vstack(list(projected.values())).max(0)+8
        size=tuple(np.ceil(hi-lo).astype(int))
        masks={}
        for n,m in meshes.items():
            image=Image.new('1',size)
            draw=ImageDraw.Draw(image)
            xy=projected[n]-lo
            for triangle in xy[m.faces]:draw.polygon([tuple(p) for p in triangle],fill=1)
            masks[n]=np.asarray(image,dtype=bool)
        raster[str(degrees)]=float(max(distance_transform_edt(~masks['high'])[masks['low']].max(),distance_transform_edt(~masks['low'])[masks['high']].max())/8)
    result['complete_silhouette_error_px_at_490px_body']=raster
    result['silhouette_quantization_px']=.125
    result['budget']=budget
    if (out/'close-camera-projection.json').exists():
        result['close_camera_projection']=json.loads((out/'close-camera-projection.json').read_text())
    # Sample actual ribbon triangles densely against the complete solid, without moving either surface.
    rv,rf=ribbon['vertices'],ribbon['faces']
    ribbon_points=np.vstack([rv,rv[rf].mean(1), (rv[rf[:,0]]+rv[rf[:,1]])/2,
                             (rv[rf[:,1]]+rv[rf[:,2]])/2,(rv[rf[:,2]]+rv[rf[:,0]])/2])
    from export_detail_metrics import separation
    ribbon_mesh=trimesh.Trimesh(vertices=rv,faces=rf,process=False)
    for name,metal in meshes.items():
        distance=nearest(metal,ribbon_points)/1000
        result[name]['sampled_ribbon_clearance_mm']=float(distance.min()*1000)
        near=metal.submesh([np.flatnonzero(metal.triangles[:,:,2].max(1)>.0162)],append=True)
        scaled_near=near.copy();scaled_near.apply_scale(1000)
        scaled_ribbon=ribbon_mesh.copy();scaled_ribbon.apply_scale(1000)
        result[name]['exact_disjoint_ribbon_clearance_mm']=separation(scaled_near,scaled_ribbon)
        crossings=0
        for target,edges in [(near,ribbon_mesh.vertices[ribbon_mesh.edges_unique]),(ribbon_mesh,near.vertices[near.edges_unique])]:
            directions=edges[:,1]-edges[:,0]
            lengths=np.linalg.norm(directions,axis=1)
            unit=directions/lengths[:,None]
            locations,index_ray,_=target.ray.intersects_location(edges[:,0],unit,multiple_hits=True)
            if len(locations):
                travel=np.linalg.norm(locations-edges[index_ray,0],axis=1)
                crossings+=int(np.sum((travel>1e-9)&(travel<lengths[index_ray]-1e-9)))
        result[name]['ribbon_strict_edge_face_crossings']=crossings
    from medal_stage1_manufacture import surface_measurements
    result['manufacture']=surface_measurements(out,meshes,separation)
    result['bail']=dict(design=result['manufacture']['design'],
                        sewn_ribbon_width_mm=float(np.ptp(rv[:,0])*1000),
                        ribbon_bottom_height_mm=float(rv[:,2].min()*1000),
                        note='Frozen ribbon used as a measurement reference only. Not mounted to either production tunic in stage one.')
    knots=report['rim_correction_knots_radius_depth_mm']
    result['rim']=dict(measured_guide_landmarks=[{k:v for k,v in l.items() if k!='angular_extrema'} for l in report['landmarks']],
                        correction_profile_radius_depth_mm=knots,
                        retained_step_depths_mm=[knots[1][1],knots[3][1],knots[7][1]],
                        enamel_recess_below_inner_lip_mm=knots[1][1]-1.,
                        deliberate_grooves=[dict(radius_mm=13.58,width_fwhm_mm=.259,depth_mm=.16),dict(radius_mm=15.35,width_fwhm_mm=.259,depth_mm=.16)])
    result['source_hashes']={}
    for name,filename,expected in [('guide','c-machined-rim-seed130303-hunyuan-full-seed0-oct320-guide.glb',reg['guide_sha256']),('concept','c-machined-rim-seed130303.png',reg['concept_sha256'])]:
        path=Path(__file__).resolve().parents[4]/'docs/art/quarters/sheets/medal'/filename
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual==expected,(name,actual,expected)
        result['source_hashes'][name]=actual
    result['gates']={
        'solid_budget':result['low']['triangles']<=budget['candidate_solid_ceiling'],
        'star_relief':all(1.0<=result[n]['star_rise_mm']<=1.3 for n in meshes),
        'body_diameter':all(abs(result[n]['body_diameter_mm']-32)<.001 for n in meshes),
        'body_depth_under_4mm':all(result[n]['body_depth_mm']<=4 for n in meshes),
        'watertight_manufactured_components':all(result[n]['watertight'] and result[n]['winding_consistent'] and result[n]['exported_watertight'] and result[n]['components']==3 for n in meshes),
        'zero_strict_self_contacts':all(result[n]['strict_self_contacts']==0 for n in meshes),
        'uv_noncollapsed_nonoverlapping':result['low']['uv_zero_area']==0 and result['low']['uv_overlapping_triangle_pairs']==0,
        'noise_p95':result['noise_only_deviation_mm']['p95']<=.1,
        'pins_p95':result['pinned_curve_deviation_mm']['p95']<=.05,
        'silhouette_0_pm35':max(silhouettes[str(d)] for d in [0,-35,35])<=.05,
        'complete_silhouette_under_half_pixel':max(raster[str(d)] for d in [0,-35,35])<=.5,
        'surface_residual_p95':result['low_to_high_surface_residual_mm']['p95']<=.10,
        'strict_unexcluded_surface_residual_max':max(v['max'] for v in result['bidirectional_surface_residual_mm'].values())<=.10,
        'uv_gutter_16_texels':result['low']['uv_min_gutter_texels_at_2048']>=16,
        'uv_front_density_1000_texels':result['low']['equivalent_visible_front_diameter_texels_at_2048']>=1000,
        'ribbon_triangle_clearance':min(result[n]['exact_disjoint_ribbon_clearance_mm'] for n in meshes)>=.08,
        'ribbon_no_crossings':all(result[n]['ribbon_strict_edge_face_crossings']==0 for n in meshes),
    }
    result['deferred']=[
        'Mounted body envelope and cloth support/clearance require mount-stage verification. Ribbon measurements use the frozen local frame without mounting.',
        'No normal bake yet; fine rounding and enamel meniscus remain for baking. No region is excluded from the geometric maximum residual.',
        'Image judgment is delegated to the parent. Numeric gates do not establish visual acceptance.',
        'Only the authored asset triangle allocation is updated in the two garment verifiers, via medal-budget.json. Production garment geometry, tests and frame-time policy remain unchanged.'
    ]
    (out/'measurements.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    required=['solid_budget','star_relief','body_diameter','body_depth_under_4mm',
              'watertight_manufactured_components','zero_strict_self_contacts','uv_noncollapsed_nonoverlapping',
              'noise_p95','pins_p95','silhouette_0_pm35','uv_gutter_16_texels',
              'uv_front_density_1000_texels','ribbon_triangle_clearance','ribbon_no_crossings',
              'strict_unexcluded_surface_residual_max','complete_silhouette_under_half_pixel']
    failed=[name for name in required if not result['gates'][name]]
    failed += [name for name,passed in result['manufacture']['gates'].items() if not passed]
    assert not failed, failed


if __name__=='__main__':
    verify(Path(sys.argv[1]))
