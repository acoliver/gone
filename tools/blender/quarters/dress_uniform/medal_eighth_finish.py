"""Medal-local detail maps derived from the four selected reference PNGs."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, distance_transform_cdt, map_coordinates

from medal_photo_measure import reference_masks, REFERENCES
from medal_seventh_finish import linear, srgb, recess_oxide, read, save


def delight(photo, sigma):
    blur=gaussian_filter(photo,(sigma,sigma,0) if photo.ndim==3 else sigma,mode='reflect')
    return photo/np.maximum(blur,1e-9)-1


def tileable(detail):
    result=detail.copy()
    y=np.linspace(0,1,len(result))[:,None]
    x=np.linspace(0,1,result.shape[1])[None,:]
    result-=y*(result[-1:]-result[:1])
    result-=x*(result[:,-1:]-result[:,:1])
    return result-result.mean()


def normal_from_height(height, strength):
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.5
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.5
    normal=np.stack([-dx*strength,dy*strength,np.ones_like(height)],axis=2)
    return normal/np.linalg.norm(normal,axis=2)[...,None]


def patch(rgb,mask):
    distance=distance_transform_cdt(mask,metric='chessboard')
    y,x=np.unravel_index(distance.argmax(),mask.shape)
    half=int(distance[y,x])-1
    assert half>=4,('Reference crop too small',half)
    rect=[int(x-half),int(y-half),int(x+half),int(y+half)]
    return rgb[rect[1]:rect[3],rect[0]:rect[2]],rect


def resized(values,size):
    return np.asarray(Image.fromarray(values.astype(np.float32),'F').resize((size,size),Image.Resampling.BICUBIC),float)


def extract(references,output):
    output.mkdir(parents=True,exist_ok=True)
    provenance=[];details={}
    for state,views in REFERENCES.items():
        for view,filename in views.items():
            rgb=read(references/filename); masks,scale,geometry=reference_masks(rgb)
            red=(rgb[...,0]>rgb[...,1]*1.35)&(rgb[...,0]>rgb[...,2]*1.35)
            for name,mask in [('brass',masks['faces']),('enamel',masks['enamel']),('ribbon',masks['ribbon']&red)]:
                crop,rect=patch(rgb,mask)
                h,w=crop.shape[:2];sigma=min(h,w)/5
                detail=delight(linear(crop),sigma).mean(2)
                size=512
                detail=tileable(resized(detail,size))
                detail=np.clip(detail,-.35,.35)
                # Reapply boundary correction after clipping rather than hiding a seam at repeat.
                detail=tileable(detail)
                stem=f'{state}-{view}-{name}'
                np.save(output/f'{stem}.npy',detail)
                save(output/f'{stem}-crop.png',crop)
                save(output/f'{stem}-detail.png',np.repeat((.5+detail)[...,None],3,2))
                details[(state,view,name)]=detail
                spectrum=np.abs(np.fft.rfft(delight(linear(crop).mean(2),sigma).mean(1)))
                frequency=int(np.argmax(spectrum[2:max(3,h//3)])+2)
                provenance.append(dict(map=stem,source=str((references/filename).resolve()),crop_xyxy_exclusive=rect,crop_size_px=[w,h],reference_pixels_per_mm=scale,dominant_row_cycles=frequency,estimated_rib_pitch_mm=h/frequency/scale if name=='ribbon' else None,processing=f'sRGB decode; divide by Gaussian sigma={sigma:g}px; subtract one; mean RGB; bicubic 512px; boundary-ramp periodic correction; clamp +/-0.35; periodic correction and zero mean',reference_segmentation=geometry))
    (output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    return details,provenance


def finish(baseline,bakes,references,output,detail_output,config,occupied_path):
    output.mkdir(parents=True,exist_ok=True)
    details,provenance=extract(references,detail_output)
    brass=read(bakes/'brass-id.png')[...,0]
    enamel=read(bakes/'enamel-id.png')[...,0]
    concave=read(bakes/'curvature-concave.png')[...,0]
    convex=read(bakes/'curvature-convex.png')[...,0]
    ao=read(bakes/'ao.png')[...,0]
    size=brass.shape[0]
    yy,xx=np.indices(brass.shape)
    tile=lambda a:map_coordinates(a,[yy/size*512*8,xx/size*512*8],order=1,mode='grid-wrap')
    occupied=read(occupied_path)[...,0]>.5
    report={'config':config,'provenance':provenance,'occupied_uv_mask':str(occupied_path),'brass_enamel_detail_atlas_repeats':8,'enamel_inherited_normal_slope_factor':.25,'enamel_photo_normal_strength':.15,'enamel_photo_albedo_strength':.12,'enamel_photo_roughness_strength':.045,'states':{}}
    for state,prefix in [('remembered','as_built'),('present','aged')]:
        cfg=config[state]
        original=read(baseline/f'{prefix}_albedo.png')
        blue=(original[...,2]>original[...,0]*1.5)&(original[...,2]>.1)
        assert np.mean(enamel[blue]>.99)>.99, 'Bake masks do not address the saved atlas UV generation'
        colour=linear(original)
        orm=read(baseline/f'{prefix}_orm.png')
        normal=read(baseline/f'{prefix}_normal.png')
        bd=tile((details[state,'medal','brass']+details[state,'oblique-context','brass'])*.5)
        ed=tile((details[state,'medal','enamel']+details[state,'oblique-context','enamel'])*.5)
        oxide=recess_oxide(concave,convex,ao)*brass
        edge=np.clip((convex-.20)/.4,0,1)*(1-oxide)
        broad=occupied&(brass>.99)&(concave<.14)&(convex<.12)
        base=np.median(colour[broad],axis=0)*np.array(cfg['brass_gain'])
        new=base*(1+cfg['albedo_detail']*bd[...,None])
        new*=1+cfg['edge_gain']*edge[...,None]
        amount=oxide*cfg['oxide_strength']*np.clip(1+2*bd,.6,1.4)
        new=new*(1-amount[...,None])+np.array([.045,.020,.006])*amount[...,None]
        colour=colour*(1-brass[...,None])+new*brass[...,None]
        colour*=1-enamel[...,None]+enamel[...,None]*np.array(cfg['enamel_gain'])*(1+.12*ed[...,None])
        rough=cfg['roughness']+cfg['rough_detail']*bd+.16*oxide-.035*edge
        orm[...,1]=orm[...,1]*(1-brass)+np.clip(rough,0,1)*brass
        orm[...,1]=orm[...,1]*(1-enamel)+(cfg['enamel_roughness']+.045*ed)*enamel
        orm[...,2]=orm[...,2]*(1-brass)+np.clip(1-.78*amount,0,1)*brass
        micro=normal_from_height(bd,cfg['normal_detail'])
        xy=normal[...,:2]*2-1
        xy*=1-.75*enamel[...,None]
        xy+=micro[...,:2]*brass[...,None]+normal_from_height(ed,.15)[...,:2]*enamel[...,None]
        xy=np.clip(xy,-.95,.95)
        length=np.linalg.norm(xy,axis=2);xy/=np.maximum(length/.95,1)[...,None]
        normal=np.dstack([xy,np.sqrt(1-np.sum(xy*xy,axis=2))])*.5+.5
        save(output/f'{prefix}_albedo.png',srgb(colour))
        save(output/f'{prefix}_orm.png',orm)
        save(output/f'{prefix}_normal.png',normal)
        coat=read(baseline/f'{prefix}_coat.png')*cfg['coat_gain']
        save(output/f'{prefix}_coat.png',coat)
        report['states'][state]=dict(base_linear_rgb=base.tolist(),broad_roughness_mean=float(rough[broad].mean()),recess_oxide_mean=float(amount[(brass>.99)&(concave>.5)].mean()),exposed_oxide_mean=float(amount[broad].mean()),ao_byte_preserved=True,no_green=True)
        np.testing.assert_array_equal(read(output/f'{prefix}_orm.png')[...,0],read(baseline/f'{prefix}_orm.png')[...,0])
    rib=details['remembered','medal','ribbon']
    rib=.80*rib.mean(axis=1,keepdims=True)+.20*rib
    crop=next(p for p in provenance if p['map']=='remembered-medal-ribbon')
    # Quantize to whole photographic ribs so the existing UV tile remains periodic.
    cycles=crop['dominant_row_cycles']
    tile_span_mm=1.066/260*1000
    tile_cycles=round(tile_span_mm/crop['estimated_rib_pitch_mm'])
    y,x=np.indices((512,512))
    ribbon=map_coordinates(rib,[y*tile_cycles/cycles,x],order=1,mode='grid-wrap')
    ribbon=tileable(ribbon)
    ribbon/=max(float(ribbon.std()),1e-6)
    ribbon=np.clip(ribbon,-3,3)
    ribbon=tileable(ribbon)
    save(output/'ribbon_weave_albedo.png',srgb(np.repeat(np.clip(.35+.32*ribbon,.02,1)[...,None],3,2)))
    save(output/'ribbon_weave_normal.png',normal_from_height(ribbon,3.0)*.5+.5)
    save(output/'ribbon_weave_roughness.png',np.repeat(np.clip(.86+.06*ribbon,.68,1)[...,None],3,2))
    report['ribbon']=dict(source='remembered-medal-ribbon',rib_cycles_per_tile=tile_cycles,uv_scale=260,tile_span_mm=tile_span_mm,rib_pitch_mm=tile_span_mm/tile_cycles,photographic_transverse_profile_weight=.80,photographic_fibre_weight=.20,linear_albedo_base=.35,albedo_detail=.32,normal_height_strength=3.0,roughness_base=.86,roughness_detail=.06,shader_and_stripe_colours_unchanged=True)
    (detail_output/'finish.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['baseline','bakes','references','output','detail-output','config','occupied']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    finish(a.baseline,a.bakes,a.references,a.output,a.detail_output,json.loads(a.config.read_text()),a.occupied)
