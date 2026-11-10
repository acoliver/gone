"""Measure generated-face colour, exported knuckles, and actual Godot captures."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion
import trimesh

from locker_faces import ROOT, SOURCE, SCRATCH, FACES, scores, pack
from locker_gates import rgb, hsv, rust_pixels, newly_green, project
from colour import linear, luminance, lab, delta_e_2000
from visibility_gates import trail_metrics, boundary_orientation, longest_straight_boundary, secondary_correlation
from atlas_gates import uv_metrics, measure_atlases


def hinge_metrics():
    scene = trimesh.load(SOURCE/'hinges.glb',force='scene',process=False)
    angles = []
    smooth = []
    for mesh in scene.geometry.values():
        normals = mesh.vertex_normals.copy()
        vertices = mesh.vertices.copy()
        mesh = mesh.copy()
        mesh.merge_vertices(merge_tex=True,merge_norm=True)
        angles.extend(np.degrees(mesh.face_adjacency_angles).tolist())
        for point in np.unique(np.round(vertices,6),axis=0):
            at = np.all(abs(vertices-point)<1e-6,axis=1)
            ns = normals[at]
            if len(ns)>1:
                smooth.extend(np.degrees(np.arccos(np.clip(ns@ns.T,-1,1))).ravel().tolist())
    return dict(knuckle_adjacent_face_angle_max_deg=max(angles),knuckle_split_normal_jump_max_deg=max(smooth,default=0))


def hardware_metrics(selection, fields=SCRATCH/'geometry.npz'):
    from scipy.ndimage import map_coordinates
    arrays=np.load(fields)
    occupied=arrays['occupied']
    p=arrays['position'][occupied][:,[0,2,1]].copy();p[:,2]*=-1
    names=arrays['part_names'][arrays['part_index'][occupied]]
    scene=trimesh.load(ROOT/'assets/props/quarters/storage_locker_module.glb',force='scene',process=False)
    atlas=np.asarray(Image.open(SOURCE/'aged-face-normal.png'))[...,:2]/255*2-1
    results={}
    for part in ('Rivets','Hinges','DoorVents','Handle','KickPlate'):
        points=p[names==part]
        name='kick' if part=='KickPlate' else 'hardware'
        image=Image.open(SOURCE/selection[name]['chosen']).convert('RGB')
        colour=np.asarray(image)/255
        face=FACES[name]
        if part=='Hinges':
            u=np.arctan2(points[:,2]-.301,points[:,0]+.260)*.010/.20+.5
            centre=np.floor((points[:,1]-.350)/.9+.5)*.9+.350
            v=.5-(points[:,1]-centre)/.20
        elif part=='KickPlate':
            u=(points[:,0]+.260)/.520;v=1-points[:,1]/.105
        else:
            bounds=[]
            for node in scene.graph.nodes_geometry:
                if node==part or node.startswith(part+'_'):
                    transform,mesh_name=scene.graph[node]
                    mesh=scene.geometry[mesh_name].copy();mesh.apply_transform(transform)
                    bounds.extend(mesh.bounds.tolist())
            bounds=np.array(bounds);lo,hi=bounds.min(0),bounds.max(0)
            u=((points[:,0]-lo[0]+.1)/.2)%1
            v=1-((points[:,1]-lo[1]+.1)/.2)%1
        uv=np.array([np.clip(v,0,1)*(image.height-1),np.clip(u,0,1)*(image.width-1)])
        samples=np.stack([map_coordinates(colour[...,c],uv,order=1,mode='nearest') for c in range(3)],-1)
        from locker_faces import paint_fields
        chroma=paint_fields(Image.fromarray(np.uint8(np.round(samples[None]*255))))[1][0]<.5
        x0,y0,x1,y1=face['rect']
        normal=atlas[y0:y1,x0:x1]
        pits=np.stack([map_coordinates(normal[...,c],uv,order=1,mode='nearest') for c in range(2)],-1)
        results[part]=dict(rust_fraction=float(rust_pixels(samples).mean()),chroma_rust_fraction=float(chroma.mean()),
                           pit_normal_rms=float(np.sqrt(np.mean(np.sum(pits*pits,axis=-1)))))
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fields',type=Path,default=SCRATCH/'geometry.npz')
    args=parser.parse_args()
    values,gates,thresholds = {},{},{}
    def record(name,value,threshold,passed):
        values[name],thresholds[name],gates[name] = value,threshold,bool(passed)
    selection = json.loads((SOURCE/'selection.json').read_text())
    for name,face in FACES.items():
        row = selection[name]
        result = scores(Image.open(SOURCE/row['chosen']),Image.open(SOURCE/f'{name}-source.png'),face)
        for metric,value in result.items():
            identity = f'face_{name}_{metric}'
            if metric.endswith('delta_e'): record(identity,value,'<=8 D65 Lab',value<=8)
            elif metric=='planar_light_gradient': record(identity,value,'<0.06 linear luminance across full image',value<.06)
            elif metric=='secondary_autocorrelation': record(identity,value,'<=0.5 at secondary peaks beyond 50 mm',value<=.5)
            elif metric=='edge_broad_ratio' and name!='hardware': record(identity,value,'>=1.8, outer 10% against broad interior',value>=1.8)
            else: values[identity]=value
        width,height = Image.open(SOURCE/row['chosen']).size
        density = min(width/face['size'][0],height/face['size'][1])
        minimum = 600 if name=='door' else 300
        record(f'face_{name}_pixels_per_metre',density,f'>={minimum}',density>=minimum)
    for name,value in hinge_metrics().items():
        record(name,value,'<=15 degrees, all exported knuckle adjacency including rounded end rims',value<=15)
    control=SCRATCH/'repeat'
    control.mkdir(exist_ok=True)
    pack(selection,control)
    identical = all((SOURCE/(name+'.png')).read_bytes()==(control/(name+'.png')).read_bytes()
                    for name in ('aged-face-albedo','aged-face-normal','aged-face-orm'))
    record('byte_identical_bakes',identical,True,identical)
    # A changed material must not rewrite the delivered clean assets.
    paths=[f'assets/props/quarters/storage_locker_module/as_built_{kind}.png' for kind in ('albedo','normal','orm')]
    clean_unchanged=all(subprocess.check_output(['git','show','2fecbce:'+p],cwd=ROOT)==(ROOT/p).read_bytes() for p in paths)
    record('as_built_atlases_unchanged',clean_unchanged,True,clean_unchanged)
    uv=uv_metrics(ROOT/'assets/props/quarters/storage_locker_module.glb')
    record('as_built_exported_uv_density',[uv['density_min'],uv['density_max']],'304.6 +/-15% px/m',uv['density_min']>=304.6*.85 and uv['density_max']<=304.6*1.15)
    record('as_built_exported_uv_no_stretch',uv['max_stretch'],'<=1.015',uv['max_stretch']<=1.015)
    original=ROOT/'assets/props/quarters/storage_locker_module'
    fields=args.fields
    clean=measure_atlases(original,fields)
    lo,hi=clean['paint_roughness_range']
    record('paint_roughness_range',[lo,hi],'.34 <= minimum; maximum <= .56; span >= .12',lo>=.34 and hi<=.56 and hi-lo>=.12)
    preview=json.loads((SCRATCH/'preview.json').read_text())
    masks=json.loads((original/'masks.json').read_text())
    finish=json.loads((original/'finishes.json').read_text())
    painted_count=aged_rust=clean_rust=up_count=dust_count=0
    green=[]
    for angle in ('hero','front','detail','top'):
        a=rgb(SCRATCH/f'as_built-albedo-{angle}.png')
        b=rgb(SCRATCH/f'aged-albedo-{angle}.png')
        ids=rgb(SCRATCH/f'aged-ids-{angle}.png')
        prop=ids[...,2]>.95
        painted=prop & (ids[...,0]>.95)
        green.append(newly_green(a,b,prop)[1])
        if angle in ('hero','front'):
            painted_count+=int(painted.sum())
            aged_rust+=int((rust_pixels(b)&painted).sum())
            clean_rust+=int((rust_pixels(a)&painted).sum())
        if angle=='top':
            up=prop & (ids[...,1]>.95)
            h,s,v=hsv(b)
            dust=(h>=20)&(h<=55)&(s>=.06)&(s<=.25)&(v>.25)&(np.linalg.norm(a-b,axis=-1)>.035)
            up_count+=int(up.sum()); dust_count+=int((dust&up).sum())
    record('as_built_rust',clean_rust/painted_count,'<0.01',clean_rust/painted_count<.01)
    record('aged_painted_rust',aged_rust/painted_count,'[.25,.60]',.25<=aged_rust/painted_count<=.60)
    record('no_new_green',max(green),'<0.005',max(green)<.005)
    record('up_face_dust',dust_count/up_count,'>=0.70',dust_count/up_count>=.7)
    record('identical_geometry',all(preview[n] for n in ('same_mesh','same_pivots','same_part_names','same_footprint')),True,
           all(preview[n] for n in ('same_mesh','same_pivots','same_part_names','same_footprint')))
    ids=rgb(SCRATCH/'aged-ids-front.png')
    painted=(ids[...,0]>.95)&(ids[...,2]>.95)
    regions=rgb(SCRATCH/'aged-regions-front.png')
    edge=painted&(regions[...,0]>.95); broad=painted&(regions[...,1]>.95)
    camera=preview['cameras']['front']; ppm=camera['image_size'][1]/camera['size']
    distributions=[]
    for lane in ('albedo','neutral','present'):
        colour=rgb(SCRATCH/f'aged-{lane}-front.png')
        rust=rust_pixels(colour)
        fraction=float(rust[broad].mean()); ratio=float(rust[edge].mean())/max(fraction,1e-8)
        record('broad_face_rust_'+lane,fraction,'[.08,.25]',.08<=fraction<=.25)
        record('edge_broad_ratio_'+lane,ratio,'>=1.8, replaces procedural-path >=2.5',ratio>=1.8)
        measurements=[]
        from streak_sources import outlet_position
        for source in masks['sources']:
            if source['part'] not in ('Rivets','Hinges'): continue
            x,y,z=outlet_position(source)
            if source['part']!='Hinges' and z<1.2: continue
            cx,cy=project([x,z,-y],camera)
            row=trail_metrics(colour,painted,cx,cy,ppm)
            row['source']=source; measurements.append(row)
        fraction=sum(r['passed'] for r in measurements)/len(measurements)
        values['legacy_visible_fastener_streaks_'+lane]=fraction
        distributions.append(dict(lane=lane,measurements=measurements))
        top=rgb(SCRATCH/f'aged-{lane}-top.png')
        ids_top=rgb(SCRATCH/'aged-ids-top.png')
        up=binary_erosion((ids_top[...,1]>.95)&(ids_top[...,2]>.95))
        h,s,v=hsv(top)
        fraction=float(((h[up]>=20)&(h[up]<=55)&(s[up]>=.06)&(s[up]<=.25)).mean())
        record('dust_warm_low_saturation_'+lane,fraction,'>=0.70',fraction>=.7)
        from visibility_gates import dust_visibility
        control=rgb(SCRATCH/f'aged-nodust-{lane}-top.png')
        difference=dust_visibility(top,control,up)
        values['illustrative_dust_control_difference_'+lane]=difference
    bare_count=rust_count=0; clean_luma=[]; roughness=[]
    for angle in ('front','detail','hero','streaks'):
        region=rgb(SCRATCH/f'aged-regions-{angle}.png')
        bare=binary_erosion(region[...,2]>.95)
        if not bare.any(): continue
        bare_count+=int(bare.sum()); rust_count+=int((rust_pixels(rgb(SCRATCH/f'aged-albedo-{angle}.png'))&bare).sum())
        clean_luma.extend(luminance(rgb(SCRATCH/f'as_built-albedo-{angle}.png'))[bare].tolist())
        roughness.extend(linear(rgb(SCRATCH/f'as_built-orm-{angle}.png'))[...,0][bare].tolist())
    record('aged_bare_steel_rust',rust_count/bare_count,'>=0.30',rust_count/bare_count>=.3)
    record('as_built_bare_steel_linear_luminance',float(np.mean(clean_luma)),'>=0.35',np.mean(clean_luma)>=.35)
    record('as_built_bare_steel_roughness_max',float(max(roughness)),'<=0.45',max(roughness)<=.45)
    observed=np.median(rgb(SCRATCH/'as_built-albedo-front.png')[broad],axis=0)
    delta=float(delta_e_2000(lab(observed),lab(np.array(finish['as_built_paint_srgb']))))
    record('as_built_design_delta_e_2000',delta,'<=6',delta<=6)
    # Keep visible boundary checks independent of the source-image measurements.
    close=rgb(SCRATCH/'streaks-closeup.png')[:,1024:]
    close_ids=rgb(SCRATCH/'aged-ids-streaks.png')
    valid=(close_ids[...,0]>.95)&(close_ids[...,2]>.95)
    from locker_swatches import paint_field
    axis_ratio,_,samples=boundary_orientation(1-paint_field(close),valid)
    record('closeup_atlas_axis_peak_ratio',axis_ratio,'<=2.0',axis_ratio<=2.)
    a=project([-.245,2.29,.274],camera);b=project([.245,.14,.274],camera)
    left,top=np.ceil(a).astype(int);right,bottom=np.floor(b).astype(int)
    door=rgb(SCRATCH/'aged-albedo-front.png')[top:bottom,left:right]
    valid=rgb(SCRATCH/'aged-doorface-front.png')[top:bottom,left:right,0]>.95
    peak=secondary_correlation(door,ppm,valid)
    record('door_secondary_autocorrelation',peak,'<=0.5 beyond 50 mm, actual rendered door',peak<=.5)
    straight=longest_straight_boundary(rust_pixels(door),valid,ppm)
    record('longest_straight_rust_boundary_m',straight,'<=0.040 at <=1 mm chord deviation',straight<=.04)
    hardware=hardware_metrics(selection,fields)
    values['hardware']=hardware
    for part,row in hardware.items():
        record('hardware_'+part+'_rust',row['rust_fraction'],'>=0.30',row['rust_fraction']>=.3)
        record('hardware_'+part+'_chroma_rust',row['chroma_rust_fraction'],'>=0.30',row['chroma_rust_fraction']>=.3)
        record('hardware_'+part+'_pit_normal_rms',row['pit_normal_rms'],'>=0.01',row['pit_normal_rms']>=.01)
    hardware_ids=rgb(SCRATCH/'closeup-hardware-ids.png')
    for part,channel,width_mm in [('hinge',0,20.),('handle',1,110.)]:
        mask=(hardware_ids[...,channel]>.95)&(hardware_ids[...,(channel+1)%3]<.05)
        widths=[]
        for row in mask:
            pixels=np.flatnonzero(row)
            if len(pixels): widths.append(int(pixels[-1]-pixels[0]+1))
        value=max(widths)/width_mm
        record(part+'_screen_px_per_mm',value,'>=5 at 0.3 m, ID-pass horizontal silhouette pixels / physical width in mm',value>=5)
    opacity=max(row.get('supplemental_max_opacity',0) for row in selection.values())
    record('supplemental_runoff_max_opacity',opacity,'<=0.30',opacity<=.30)
    retired={
        'dust_grain_std_ratio': 'Compared a procedural dust-density field with its smoothed control. Dust is now in the complete generated top image.',
        'broad_face_island_max_m': 'Measured placed blister instances; there are no placed islands in the image-owned layout.',
        'unattached_runoff_max': 'Measured the removed analytic runoff control texture; new supplementary stains are baked at bounded opacity.',
        'streak_width_median_m': 'Measured half-opacity contours of the removed full-opacity analytic generator.',
        'streak_source_length_range_m': 'Preset source lengths no longer decide the corrosion layout.',
        'streak_reduced_opacity_max': 'Replaced the old less-than-one generator opacity by the explicit <=0.30 limit.',
        'panel_edge_rust_cv_min': 'Measured variability of the old procedural edge band, replaced by independently measured image edge/broad rust ratios.',
        'fasteners_with_streaks, visible_fastener_streaks_{albedo,neutral,present}': 'The old >=50% population of strong 40 mm generated trails required a stamped fixture distribution and >=0.03 contrast. Image-owned trails and optional <=30% stains replace that generator contract; connected-run measurements remain diagnostics, not passes.',
        'dust_linear_difference_{albedo,neutral,present}': 'The old control disabled a separate dust mask while retaining identical substrate. Dust is now part of the top image. A generated dust-removal edit is illustrative and is not a numerically matched effect-disabled control; differences remain diagnostics, not visibility passes.'}
    report=dict(passed=all(gates.values()),values=values,gates=gates,thresholds=thresholds,
                retired_gates=retired,fasteners=distributions,
                replaced_gates={'swatch colour and correlation': 'Same thresholds, measured on every complete face image against its own saved crop',
                                'edge/broad >=2.5': 'Replaced by the requested >=1.8 on every painted face and all lighting lanes'})
    (SCRATCH/'gates.json').write_text(json.dumps(report,indent=2)+'\n')
    for name,passed in gates.items(): print('PASS' if passed else 'FAIL',name,values[name],'threshold',thresholds[name])
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__': main()
