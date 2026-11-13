"""Physical-scale photo brass, planar star normals, fine grosgrain and cavity oxide."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates

from medal_eighth_finish import delight, tileable, normal_from_height
from medal_seventh_finish import read, save, linear, srgb


def fine_rib_cycles(detail):
    """Separate the resolved 2.5..6px fibre/rib band from broader photographed bands."""
    profile=detail.mean(1)
    spectrum=np.abs(np.fft.rfft(profile-profile.mean()))**2
    cycles=np.arange(len(spectrum)); valid=(cycles>=len(profile)/6)&(cycles<=len(profile)/2.5)
    return int(cycles[valid][np.argmax(spectrum[valid])])


def cavity_oxide(concave,convex,ao,photo):
    cavity=np.maximum(np.clip((concave-.20)/.65,0,1),np.clip((.78-ao)/.50,0,1))
    exposed=1-np.clip(convex/.35,0,1)
    photographic=np.clip(.80+2.5*photo,.15,1)
    return cavity**1.5*exposed**2*photographic


def restrict_facet_detail(current,flat,mask):
    return np.where(mask[...,None],flat,current)


def finish(baseline,bakes,reference_maps,features,output,config,report_path):
    provenance=json.loads((reference_maps/'provenance.json').read_text())
    brass=read(bakes/'brass-id.png')[...,0];enamel=read(bakes/'enamel-id.png')[...,0]
    concave=read(bakes/'curvature-concave.png')[...,0];convex=read(bakes/'curvature-convex.png')[...,0];ao=read(bakes/'ao.png')[...,0]
    report={'config':config,'states':{},'photo_source':'ingame8 extracted original PNG crops; no generated noise'}
    for state,prefix in [('remembered','as_built'),('present','aged')]:
        cfg=config[state];feature=np.load(features/f'{state}-features.npz');loc=feature['local'];star=feature['star']
        crop=next(p for p in provenance if p['map']==f'{state}-medal-brass')
        source=read(reference_maps/f'{state}-medal-brass-crop.png')
        detail=tileable(delight(linear(source),min(source.shape[:2])/5).mean(2))
        pitch_mm=source.shape[0]/crop['reference_pixels_per_mm']
        coords=[loc[...,2]*1000/pitch_mm*detail.shape[0],loc[...,0]*1000/pitch_mm*detail.shape[1]]
        bd=map_coordinates(detail,coords,order=1,mode='grid-wrap')
        orm=read(baseline/f'{prefix}_orm.png');colour=linear(read(baseline/f'{prefix}_albedo.png'));normal=read(baseline/f'{prefix}_normal.png')*2-1
        broad=(brass>.99)&(concave<.14)&(convex<.12)&(np.linalg.norm(loc,axis=2)>0)
        base=np.median(colour[broad],axis=0)*cfg['brass_gain']
        amount=cavity_oxide(concave,convex,ao,bd)*brass*cfg['oxide_strength']
        # Replace only brass color. Its face mean is calibrated in the fixed room after capture.
        new=base*(1+.12*bd[...,None])
        new*=1+.035*np.clip((convex-.20)/.4,0,1)[...,None]
        new=new*(1-amount[...,None])+np.array([.045,.020,.006])*amount[...,None]
        colour=np.where((brass>.99)[...,None],new,colour)
        rough=cfg['roughness']+cfg['rough_detail']*bd+.12*amount
        rough=np.where(star,cfg['star_roughness']+.10*amount,rough)
        orm[...,1]=np.where(brass>.99,np.clip(rough,cfg['minimum_roughness'],1),orm[...,1])
        orm[...,2]=np.where(brass>.99,1-.78*amount,orm[...,2])
        orm[...,1]=np.where(enamel>.99,cfg['enamel_roughness'],orm[...,1])
        micro=normal_from_height(bd,cfg['normal_detail'])
        normal[...,:2]=np.where((brass>.99)[...,None],normal[...,:2]*.18+micro[...,:2],normal[...,:2])
        normal[...,:2]=np.where((enamel>.99)[...,None],normal[...,:2]*cfg['enamel_normal_slope_factor'],normal[...,:2])
        normal[...,2]=np.sqrt(np.maximum(1-np.sum(normal[...,:2]**2,axis=2),0))
        normal=restrict_facet_detail(normal,feature['normal'],star)
        save(output/f'{prefix}_albedo.png',srgb(colour));save(output/f'{prefix}_orm.png',orm);save(output/f'{prefix}_normal.png',normal*.5+.5)
        save(output/f'{prefix}_coat.png',read(baseline/f'{prefix}_coat.png')*cfg['coat_weight_gain'])
        save(report_path.parent/f'{prefix}-oxide-mask.png',np.repeat(amount[...,None],3,2))
        report['states'][state]={'photo_crop_span_mm':pitch_mm,'reference_pixels_per_mm':crop['reference_pixels_per_mm'],'brass_photo_detail_std':float(bd[broad].std()),'broad_bake_roughness_before_clamp_mean_std':[float(rough[broad].mean()),float(rough[broad].std())],'star_roughness':cfg['star_roughness'],'facet_source':'Least-squares planes fitted to ten angular sectors of the unchanged generated star surface, transferred through its exported tangent frame; no photo detail on planes','oxide_exposed_mean':float(amount[broad].mean()),'oxide_recess_mean':float(amount[(brass>.99)&(concave>.5)].mean()),'oxide_recess_std':float(amount[(brass>.99)&(concave>.5)].std()),'brass_albedo_detail_strength':.12,'enamel_albedo_unchanged':True,'enamel_coat_weight_gain':cfg['coat_weight_gain'],'enamel_normal_slope_factor':cfg['enamel_normal_slope_factor']}
        np.testing.assert_array_equal(read(output/f'{prefix}_orm.png')[...,0],read(baseline/f'{prefix}_orm.png')[...,0])
    crop=next(p for p in provenance if p['map']=='remembered-medal-ribbon')
    raw=linear(read(reference_maps/'remembered-medal-ribbon-crop.png')).mean(2)
    detail=delight(raw,min(raw.shape)/5);cycles=fine_rib_cycles(detail)
    spectrum=np.fft.rfft(detail,axis=0);freq=np.arange(len(spectrum));spectrum[(freq<cycles*.70)|(freq>cycles*1.4)]=0
    rib=np.fft.irfft(spectrum,n=len(detail),axis=0)
    rib=.35*rib.mean(1,keepdims=True)+.65*rib
    rib=tileable(rib);rib/=rib.std()
    geometric=json.loads((features.parent/'feature-report.json').read_text())['remembered']
    reference_width_px=crop['reference_segmentation']['ellipse_cx_cy_rx_ry_shear'][2]*1.4
    ratio=len(raw)/cycles/reference_width_px
    pitch_mm=ratio*geometric['ribbon_width_m']*1000
    tile_span_mm=geometric['ribbon_m_per_uv_xy_median'][1]/260*1000
    tile_cycles=round(tile_span_mm/pitch_mm)
    y,x=np.indices((512,512));ribbon=map_coordinates(rib,[y/512*len(rib)*tile_cycles/cycles,x/512*rib.shape[1]],order=1,mode='grid-wrap')
    ribbon=tileable(ribbon);ribbon/=ribbon.std();ribbon=np.clip(ribbon,-3,3)
    save(output/'ribbon_weave_albedo.png',srgb(np.repeat(np.clip(.35+.045*ribbon,.15,.60)[...,None],3,2)))
    save(output/'ribbon_weave_normal.png',normal_from_height(ribbon,.70)*.5+.5)
    save(output/'ribbon_weave_roughness.png',np.repeat(np.clip(.86+.025*ribbon,.68,1)[...,None],3,2))
    report['ribbon']={'reference_fine_cycles_in_crop':cycles,'reference_crop_height_px':len(raw),'reference_ribbon_mask_width_px':reference_width_px,'reference_pitch_over_width':ratio,'physical_pitch_target_mm':pitch_mm,'physical_tile_span_mm':tile_span_mm,'tile_cycles':tile_cycles,'installed_pitch_mm':tile_span_mm/tile_cycles,'uv_scale':260,'row_profile_weight':.35,'photo_2d_weight':.65,'linear_albedo_amplitude':.045,'normal_height_strength':.70,'selection':'Strongest resolved 2.5..6px row-frequency band in original reference crop; ingame8 selected broad 8.8px bands instead','albedo_stripes_geometry_uv_and_shader_unchanged':True}
    report_path.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['baseline','bakes','reference-maps','features','output','config','report']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();finish(a.baseline,a.bakes,a.reference_maps,a.features,a.output,json.loads(a.config.read_text()),a.report)
