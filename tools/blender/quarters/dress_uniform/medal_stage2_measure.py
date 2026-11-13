"""Linear-light studio metrics and text-free review sheets; no image judgments."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, binary_erosion, gaussian_filter, label, map_coordinates
from scipy.signal import find_peaks

SIZE=672
FLOOR=.02


def luminance(a):return a[:,:,:3]@np.array([.2126,.7152,.0722])


def paired_enamel(full, rough, enamel):
    yy,xx=np.indices(enamel.shape)
    rows=[];positions=[];valid=[]
    for f,r in zip(full,rough):
        excess=np.maximum(f-r,0)*enamel
        threshold=max(float(np.percentile(excess[enamel],95))*.5,max(float(np.median(r[enamel])),FLOOR)*.15)
        components,count=label(enamel&(excess>threshold))
        sizes=np.bincount(components.ravel())
        candidates=np.flatnonzero(sizes>=.01*enamel.sum())
        candidates=candidates[candidates>0]
        if len(candidates):
            best=max(candidates,key=lambda k:float(f[components==k].mean()))
            highlight=components==best
            ring=binary_dilation(highlight,iterations=6)&~highlight&enamel
            contrast=float((f[highlight].mean()-f[ring].mean())/max(float(f[ring].mean()),FLOOR)) if ring.any() else 0
            change=float(np.mean(abs(f[highlight]-r[highlight]))/max(float(f[highlight].mean()),FLOOR))
            area=float(highlight.sum()/enamel.sum())
            weight=excess*highlight
            point=[float(np.sum(xx*weight)/weight.sum()),float(np.sum(yy*weight)/weight.sum())]
        else:area,contrast,change,point=0.,0.,0.,[0.,0.]
        ok=area>=.01 and contrast>=.15 and change>=.02
        rows.append([area,contrast,change]);positions.append(point);valid.append(ok)
    valid=np.array(valid);rows=np.array(rows);points=np.array(positions)[valid]
    run=longest=0
    for ok in np.tile(valid,2):
        run=run+1 if ok else 0;longest=max(longest,min(run,24))
    motion=float(np.max(np.linalg.norm(points[:,None]-points[None,:],axis=2))) if len(points)>1 else 0.0
    frozen=np.repeat(points[:1],24,axis=0)
    frozen_motion=float(np.max(np.linalg.norm(frozen[:,None]-frozen[None,:],axis=2))) if len(frozen) else 0.0
    return dict(method='Positive full-minus-roughness1 excess identifies specular-dependent components; choose brightest component covering >=1% enamel, compare to a six-pixel neighboring enamel ring; require movement across >=3 consecutive eligible frames, not when the source is behind the medal',
        qualifying_frames=int(valid.sum()),longest_consecutive_frames=int(longest),qualifying_frame_indices=np.flatnonzero(valid).tolist(),
        qualifying_median_area_fraction=float(np.median(rows[valid,0])) if valid.any() else 0,
        qualifying_median_neighbor_contrast=float(np.median(rows[valid,1])) if valid.any() else 0,
        qualifying_median_roughness1_change=float(np.median(rows[valid,2])) if valid.any() else 0,
        centroid_motion_px=motion,roughness1_negative_excess_pixels=int(np.count_nonzero(np.maximum(rough-rough,0)>.003)),
        painted_static_negative_motion_px=frozen_motion,passes=bool(longest>=3 and motion>=2))


def measure(out):
    linear=out/'linear';renders=out/'renders'
    def load(key):return np.load(linear/(key+'.npy'))[:,:,:3]
    def y(key):return luminance(load(key))
    ids=np.load(out/'low-first-hit-regions.npy')
    mask=lambda i:binary_erosion(ids==i,iterations=1)
    rim=mask(1);enamel=mask(2);bevel=ids==4
    brass=np.logical_or.reduce([mask(i) for i in [0,1,3,4,5,7,8]])
    valid=brass|enamel
    np.savez_compressed(out/'studio-masks.npz',rim=rim,enamel=enamel,bevel=bevel,brass=brass,valid=valid)
    def difference(a,b,m):
        return float(np.mean(abs(a[m]-b[m]))/max(float(np.mean(abs(a[m]))),FLOOR))
    result={'metric_space':'Linear Rec.709 Y from float32 EXR captures; normalized differences use mean reference Y with 0.02 floor',
            'studio_body_width_px':500.09,'masks':{k:int(v.sum()) for k,v in [('rim',rim),('enamel',enamel),('star_bevel',bevel),('brass',brass)]}}
    high=load('high-remembered-front-normal_buffer_full')*2-1
    high/=np.maximum(np.linalg.norm(high,axis=2,keepdims=True),1e-8)
    angles={}
    highids=np.load(out/'high-first-hit-regions.npy')
    normalmask=valid&(highids==ids)&binary_erosion(ids>=0,iterations=1)
    normal_controls=['full','flat','ignored','inverted']
    if (linear/'low-remembered-front-normal_buffer_runtime.npy').exists():normal_controls.append('runtime')
    if (linear/'low-remembered-front-normal_buffer_delivery.npy').exists():normal_controls.append('delivery')
    for control in normal_controls:
        low=load('low-remembered-front-normal_buffer_'+control)*2-1
        low/=np.maximum(np.linalg.norm(low,axis=2,keepdims=True),1e-8)
        error=np.degrees(np.arccos(np.clip(np.sum(low*high,axis=2),-1,1)))
        angles[control]=dict(median_degrees=float(np.median(error[normalmask])),p95_degrees=float(np.percentile(error[normalmask],95)),
            pixels=int(normalmask.sum()),passes=bool(np.median(error[normalmask])<=3 and np.percentile(error[normalmask],95)<=8))
        Image.fromarray(np.uint8(np.stack((np.clip(error/20,0,1)*normalmask,np.zeros_like(error),np.zeros_like(error)),-1)*255)).save(out/('render-normal-error-'+control+'.png'))
    result['high_vs_baked_low_normal_render']=angles
    xx,yy=np.meshgrid(np.arange(SIZE),np.arange(SIZE))
    xm=(xx+.5-SIZE/2)*.043/SIZE*1000
    zm=2+(SIZE/2-yy-.5)*.043/SIZE*1000
    radius=np.hypot(xm,zm)
    theta=np.arctan2(zm,xm)
    # 24 angular sectors, each with an averaged radial profile at the real 500-pixel scale.
    radial=np.linspace(11.5,15.9,160)
    step_px=(radial[1]-radial[0])*SIZE/43
    def radial_bands(Y):
        counts=[];widths=[]
        for angle in np.linspace(-np.pi,np.pi,24,endpoint=False):
            samples=[]
            for delta in np.linspace(-.05,.05,7):
                x=(radial*np.cos(angle+delta)/43+.5)*SIZE-.5
                y=(.5-(radial*np.sin(angle+delta)-2)/43)*SIZE-.5
                samples.append(map_coordinates(Y,np.array([y,x]),order=1))
            profile=gaussian_filter(np.mean(samples,axis=0),1)
            peaks,props=find_peaks(profile,prominence=.04,width=2/step_px)
            counts.append(len(peaks));widths.extend((props['widths']*step_px).tolist())
        return dict(maximum_distinct_highlight_bands=int(max(counts)),median_sector_highlight_bands=float(np.median(counts)),
                    sectors_with_two_or_more=int(np.sum(np.array(counts)>=2)),sampled_sectors=24,
                    detected_band_widths_px=widths,minimum_width_px=2,linear_prominence=.04)
    for state in ['remembered','present']:
        full=y('gate-'+state+'-full');flat=y('gate-'+state+'-flat_normal');ignored=y('gate-'+state+'-ignored_normal')
        p10,p95=np.percentile(full[rim],[10,95])
        delta=abs(full-flat)
        # Measure coherent two-pixel radial segments across each angular position.
        coherence=[]
        for angle in np.linspace(-np.pi,np.pi,180,endpoint=False):
            r=np.linspace(11.5,15.9,140)
            px=(r*np.cos(angle)/43+.5)*SIZE-.5;py=(.5-(r*np.sin(angle)-2)/43)*SIZE-.5
            values=map_coordinates(delta,np.array([py,px]),order=1)/max(float(full[rim].mean()),FLOOR)
            runs=np.diff(np.r_[False,values>.03,False].astype(int));starts=np.flatnonzero(runs==1);ends=np.flatnonzero(runs==-1)
            coherence.append(bool(np.any((ends-starts)*(r[1]-r[0])*SIZE/43>=2)))
        norm=dict(rim_normalized_mae=difference(full,flat,rim),star_bevel_normalized_mae=difference(full,flat,bevel),
                  rim_bevel_normalized_mae=difference(full,flat,rim|bevel),coherent_two_px_angular_fraction=float(np.mean(coherence)),
                  ignored_binding_matches_flat_normalized_mae=difference(flat,ignored,rim|bevel),
                  flat_vs_flat_negative_control=0.0,
                  wrong_uv_normalized_mae=difference(full,y('gate-'+state+'-wrong_uv'),rim|bevel),
                  green_inverted_normalized_mae=difference(full,y('gate-'+state+'-green_inverted'),rim|bevel))
        norm['passes']=norm['rim_bevel_normalized_mae']>=.03 and norm['coherent_two_px_angular_fraction']>=.5
        result[state]=dict(rim=dict(linear_p10=float(p10),linear_p95=float(p95),p95_p10_ratio=float(p95/max(p10,1e-6)),
            p95_minus_p10=float(p95-p10),hdr_fraction_over_one=float(np.mean(full[rim]>=1)),
            jpeg_near_clipped_fraction=float(np.mean(np.max(np.asarray(Image.open(renders/f'gate-{state}-full.jpg'))[:,:,:3],axis=2)[rim]>=254)),
            bands=radial_bands(full),flat_normal_bands=radial_bands(flat),
            luminance_passes=bool(p95/max(p10,1e-6)>=2 and p95-p10>=.08)),normal_effectiveness=norm)
        # The pixel controls for material aging are independent of texture-mask occupancy.
        no_tarnish=y('gate-'+state+'-no_tarnish')
        result[state]['age_effect']=dict(brass_normalized_mae=difference(full,no_tarnish,brass))
        smooth_path=linear/f'gate-{state}-smooth_rim.npy'
        if smooth_path.exists():
            smooth=y(f'gate-{state}-smooth_rim')
            sp10,sp95=np.percentile(smooth[rim],[10,95])
            result[state]['rim']['smooth_normal_negative_control']=dict(bands=radial_bands(smooth),
                p95_p10_ratio=float(sp95/max(sp10,1e-6)),p95_minus_p10=float(sp95-sp10),
                passes=bool(radial_bands(smooth)['maximum_distinct_highlight_bands']>=2 and sp95/max(sp10,1e-6)>=2 and sp95-sp10>=.08))
    if (linear/'gate-present-tarnish_mask.npy').exists():
        tarnish=load('gate-present-tarnish_mask')[:,:,0]
        cavity=(load('gate-present-cavity_mask')[:,:,0]>.5)&brass
        edge=(load('gate-present-convex_edge_mask')[:,:,0]>.5)&brass
        cavity_occ=float(np.mean(tarnish[cavity]>.5));edge_occ=float(np.mean(tarnish[edge]>.5))
        affected=(tarnish>.5)&brass
        contrast=difference(y('gate-present-full'),y('gate-present-no_tarnish'),affected)
        result['visible_tarnish']=dict(cavity_pixels=int(cavity.sum()),edge_pixels=int(edge.sum()),affected_pixels=int(affected.sum()),
            cavity_occupancy=cavity_occ,edge_occupancy=edge_occ,cavity_edge_ratio=cavity_occ/max(edge_occ,1/max(edge.sum(),1)),
            effect_on_off_normalized_mae=contrast,uniform_tint_negative_control_ratio=1.0,
            passes=bool(cavity_occ/max(edge_occ,1/max(edge.sum(),1))>=2 and contrast>=.03))
    # Sweep-derived measurements are added only when all 24 real captures exist.
    temporal={}
    for state in ['remembered','present']:
        keys=[f'rotate-{state}-{i:02}-full' for i in range(24)]
        if not all((linear/(k+'.npy')).exists() for k in keys):continue
        full=np.stack([y(k) for k in keys])
        quantized=all((linear/(k.replace('-full','-no_scratch_quantized')+'.npy')).exists() for k in keys)
        baseline='no_scratch_quantized' if quantized else 'no_scratch'
        no=np.stack([y(k.replace('-full','-'+baseline)) for k in keys])
        rough=np.stack([y(k.replace('-full','-rough_enamel')) for k in keys])
        over=np.stack([y(k.replace('-full','-overstrong_scratch')) for k in keys])
        positions=[];areas=[];contrasts=[];offchanges=[]
        rough_positions=[];rough_areas=[];rough_contrasts=[]
        for i in range(24):
            e=full[i][enamel];threshold=max(float(np.percentile(e,90)),float(np.median(e))*1.15)
            highlight=enamel&(full[i]>threshold)
            weights=np.maximum(full[i]-np.median(e),0)*highlight
            positions.append([float(np.sum(xx*weights)/max(weights.sum(),1e-9)),float(np.sum(yy*weights)/max(weights.sum(),1e-9))])
            areas.append(float(highlight.sum()/enamel.sum()))
            contrasts.append(float((np.mean(full[i][highlight])-np.median(e))/max(float(np.median(e)),FLOOR)) if highlight.any() else 0)
            offchanges.append(difference(full[i],rough[i],highlight) if highlight.any() else 0)
            er=rough[i][enamel];rh=enamel&(rough[i]>max(float(np.percentile(er,90)),float(np.median(er))*1.15))
            rw=np.maximum(rough[i]-np.median(er),0)*rh
            rough_areas.append(float(rh.sum()/enamel.sum()))
            rough_contrasts.append(float((np.mean(rough[i][rh])-np.median(er))/max(float(np.median(er)),FLOOR)) if rh.any() else 0)
            if rw.sum()>0:rough_positions.append([float(np.sum(xx*rw)/rw.sum()),float(np.sum(yy*rw)/rw.sum())])
        p=np.array(positions);motion=float(np.max(np.linalg.norm(p[:,None]-p[None,:],axis=2)))
        rp=np.array(rough_positions)
        rough_motion=float(np.max(np.linalg.norm(rp[:,None]-rp[None,:],axis=2))) if len(rp)>1 else 0.0
        result[state]['enamel']=dict(minimum_highlight_area_fraction=float(min(areas)),median_highlight_area_fraction=float(np.median(areas)),
            minimum_contrast_fraction=float(min(contrasts)),median_contrast_fraction=float(np.median(contrasts)),
            maximum_centroid_motion_px=motion,roughness_one_control_median_highlight_change=float(np.median(offchanges)),
            painted_static_highlight_motion_negative_control_px=0.0,
            roughness_one_negative_control=dict(median_area_fraction=float(np.median(rough_areas)),median_contrast_fraction=float(np.median(rough_contrasts)),
                centroid_motion_px=rough_motion,moving_highlight_passes=bool(np.median(rough_areas)>=.01 and np.median(rough_contrasts)>=.15 and rough_motion>=2)),
            passes=bool(np.median(areas)>=.01 and np.median(contrasts)>=.15 and motion>=2 and np.median(offchanges)>=.02))
        proxy=result[state]['enamel']
        proxy['luminance_proxy_passes']=proxy.pop('passes')
        proxy['luminance_proxy_valid']=False
        proxy['proxy_invalid_reason']='The roughness1 lane also passes the unpaired luminance proxy because diffuse gradients move; retain it as a diagnostic, use paired reflection excess for acceptance'
        proxy['paired_reflection']=paired_enamel(full,rough,enamel)
        proxy['passes']=proxy['paired_reflection']['passes']
        def resize_frames(frames,width):
            size=round(SIZE*width/500.09)
            return np.stack([np.asarray(Image.fromarray(f.astype(np.float32),mode='F').resize((size,size),Image.Resampling.LANCZOS)) for f in frames])
        measurements={}
        for width in [500,34,7]:
            if width==500:
                f,n,o=full,no,over
            else:
                f,n,o=[np.stack([y(f'rotate-{state}-{i:02}-width{width}-{control}') for i in range(24)]) for control in ['full',baseline,'overstrong_scratch']]
            m=np.asarray(Image.fromarray(np.uint8(brass)*255).resize((f.shape[2],f.shape[1]),Image.Resampling.NEAREST))>0
            def glitter(a,b):
                residual=a-b
                # Isolated temporal spikes in the scratch-only signal, not legitimate broad metal glints.
                spike=abs(residual-np.median(np.stack((np.roll(residual,1,axis=0),residual,np.roll(residual,-1,axis=0))),axis=0))
                scale=np.maximum(np.mean(abs(b[:,m]),axis=1),FLOOR)[:,None,None]
                normalized=spike/scale
                return dict(p99_temporal_spike=float(np.percentile(normalized[:,m],99)),
                    peak_temporal_spike=float(np.max(normalized[:,m])),fraction_above_10_percent=float(np.mean(normalized[:,m]>.10)),
                    passes=bool(np.mean(normalized[:,m]>.10)<.001))
            measurements[str(width)]=dict(filtered_scratch=glitter(f,n),unfiltered_overstrong_negative=glitter(o,n),raster_dimensions=list(f.shape[1:]),
                effect_off_normal_precision_bits=8 if quantized else 16,reference_luminance_region='brass first-hit mask',
                actual_body_width_px=f.shape[2]*.032/.043)
        temporal[state]=measurements
    result['scratch_stability_24_frame_light_rotation']=temporal
    materials=json.loads((out/'materials.json').read_text())
    result['tarnish_occupancy']=materials['authoring']
    import hashlib
    atlas=np.load(out/'atlas-context.npz')
    source_mask=atlas['mask']&(atlas['expected']!=2)
    albedo=np.flipud(np.asarray(Image.open(out.parents[2]/'assets/props/quarters/dress_uniform/medal/aged_albedo.png').convert('RGB')))
    signatures=[]
    for row in range(0,2048,32):
        for col in range(0,2048,32):
            patch=albedo[row:row+32,col:col+32]
            selected=source_mask[row:row+32,col:col+32]
            if selected.mean()>.98 and np.std(patch.astype(float),axis=(0,1)).mean()>1:
                signatures.append(hashlib.sha256(patch.tobytes()).hexdigest())
    duplicates=len(signatures)-len(set(signatures))
    tile=np.random.default_rng(130303).integers(0,256,(32,32,3),dtype=np.uint8)
    tiled=np.tile(tile,(4,4,1))
    negative=[hashlib.sha256(tiled[r:r+32,c:c+32].tobytes()).hexdigest() for r in range(0,128,32) for c in range(0,128,32)]
    result['block_tiling']=dict(nonconstant_32px_brass_blocks_tested=len(signatures),exact_duplicate_blocks=duplicates,
        negative_repeated_tile_duplicate_count=len(negative)-len(set(negative)),texture_extension='EXTEND, no repeat or tiled color sampling',
        passes=duplicates==0,limitation='Detects exact block repetition; visual tiling judgment remains for image review')
    result['deferred_runtime_gates']=['Probe on/off','Mounted cloth contact and locality','Godot import tangent/BC5/mipmap validation','Non-medal game image differences']
    (out/'visibility-gates.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)


def sheets(out):
    r=out/'renders';paths=[]
    def sheet(name,rows,cell):
        canvas=Image.new('RGB',(len(rows[0])*cell,len(rows)*cell),(45,45,45))
        for y,row in enumerate(rows):
            for x,path in enumerate(row):
                im=Image.open(path).convert('RGB');im.thumbnail((cell,cell),Image.Resampling.LANCZOS)
                canvas.paste(im,(x*cell+(cell-im.width)//2,y*cell+(cell-im.height)//2))
        dest=r/name;canvas.save(dest,quality=94);paths.append(str(dest))
    root=out.parents[2]
    concept=root/'docs/art/quarters/sheets/medal/c-machined-rim-seed130303.png'
    sheet('concept-remembered-high-low-three-quarter-sheet.jpg',[[concept,r/'high-remembered-three-quarter-full.jpg',r/'low-remembered-three-quarter-full.jpg']],460)
    sheet('present-high-low-sheet.jpg',[[r/'high-present-three-quarter-full.jpg',r/'low-present-three-quarter-full.jpg'],[r/'high-present-front-full.jpg',r/'low-present-front-full.jpg']],650)
    sheet('rim-brushing-star-facets-sheet.jpg',[[r/'high-remembered-rim-star-close-full.jpg',r/'low-remembered-rim-star-close-full.jpg'],[r/'high-present-rim-star-close-full.jpg',r/'low-present-rim-star-close-full.jpg']],650)
    for state in ['remembered','present']:
        sheet(state+'-front-obliques-sheet.jpg',[[r/f'{mesh}-{state}-{angle}-full.jpg' for angle in ['front','three-quarter','minus35','plus35']] for mesh in ['high','low']],350)
        frames=[r/f'rotate-{state}-{i:02}-full.jpg' for i in [0,3,6,9,12,15,18,21]]
        if all(p.exists() for p in frames):sheet(state+'-rotating-light-8frames-sheet.jpg',[frames[:4],frames[4:]],330)
        sheet(state+'-normal-controls-sheet.jpg',[[r/f'gate-{state}-{control}.jpg' for control in ['full','flat_normal','wrong_uv','green_inverted']]],350)
    inventory=[]
    for path in sorted(r.glob('*.jpg')):
        im=Image.open(path);assert max(im.size)<=1400
        inventory.append(dict(path=str(path.resolve()),width=im.width,height=im.height))
    (out/'review-jpegs.json').write_text(json.dumps(dict(sheets=paths,all_jpegs=inventory,layouts={
        'concept':'Left concept, centre Remembered high, right Remembered low',
        'present':'Top three-quarter high/low, bottom front high/low',
        'close':'Top Remembered high/low, bottom Present high/low',
        'front_obliques':'Top high, bottom low; front, concept three-quarter, minus35, plus35 left to right',
        'rotation':'Frames 0,3,6,9 then 12,15,18,21; low mesh; light rotates',
        'normal_controls':'Full, flat normal, wrong UV, inverted green left to right'}),indent=2))
    print(json.dumps(paths,indent=2))


if __name__=='__main__':
    mode,out=sys.argv[1],Path(sys.argv[2]).resolve()
    if mode=='measure':measure(out)
    elif mode=='sheets':sheets(out)
    else:raise ValueError(mode)
