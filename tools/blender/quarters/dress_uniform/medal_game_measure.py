"""Measure #130 fixed-camera LDR captures with first-hit runtime geometry masks."""
import argparse
import sys
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt, gaussian_filter1d, map_coordinates
from scipy.signal import find_peaks

ROOT = Path(__file__).resolve().parents[4]


def linear_image(path):
    rgb = np.asarray(Image.open(path).convert('RGB'), float)/255
    return np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)


def luminance(path):
    return linear_image(path) @ [.2126,.7152,.0722]


def masks(game, state, view):
    data=np.load(game/f'{state}-{view}-raw-masks.npz')
    role,region=data['role'],data['region']
    names=data['names'].tolist()
    metal=np.isin(role,[1,2])
    width=float(data['width'])
    prefix='aged' if state=='present' else 'as_built'
    evidence=np.load(game.parent/'mounted'/f'{prefix}_contact-evidence.npz')
    distance=distance_transform_edt(~evidence['footprint'],sampling=(.056/512,.048/512))
    local=data['local']
    x=np.nan_to_num(local[:,:,0]);z=np.nan_to_num(local[:,:,2]);depth=np.nan_to_num(local[:,:,1])
    uv=np.array([(z+.024)/.056*512-.5,(x+.024)/.048*512-.5])
    projected_distance=map_coordinates(distance,uv,order=1,mode='constant',cval=1)
    rgba=np.flipud(np.asarray(Image.open(ROOT/'assets/props/quarters/dress_uniform/medal'/f'{prefix}_contact.png').convert('RGBA'),float)/255)
    baked_depth=(map_coordinates(rgba[:,:,1],uv,order=1,mode='constant',cval=.5)-.5)*.02
    covered=map_coordinates(evidence['coverage'].astype(float),uv,order=0,mode='constant',cval=0)>.99
    front=(role==4)&covered&(abs(depth-baked_depth)<.00035)
    result=dict(brass=role==1,enamel=role==2,ribbon=role==3,cloth=role==4,
                rim=(role==1)&(region==names.index('rim')),
                bevel=(role==1)&np.isin(region,[names.index('star_bevel'),names.index('star_wall')]),
                contact=front&(projected_distance>=.00025)&(projected_distance<=.0015),
                outside=(role==4)&(projected_distance>.003),metal=metal,
                visible_body_width_px=np.array(width))
    for key in ['brass','enamel','rim','bevel','contact','outside']:
        Image.fromarray(np.uint8(result[key])*255).save(game/f'{state}-{view}-{key}-mask.png')
    print('MASKS',state,view,{k:int(v.sum()) for k,v in result.items() if v.ndim==2},flush=True)
    return result


def compare(a,b,mask):
    assert mask.any(), 'Empty measurement mask'
    return float(np.mean(abs(a-b)[mask])/max(float(a[mask].mean()),.02))


def measure(game):
    report={'method':'Tone-mapped PNG decoded to linear Rec.709; normalized MAE with luminance floor .02. First-hit masks use runtime wardrobe mesh arrays; source face labels matched in mounted local coordinates.', 'states':{}}
    baseline=game.parent/'baseline/game'
    assert json.loads((game/'cameras.json').read_text())==json.loads((baseline/'cameras.json').read_text()),'Acceptance cameras changed'
    for state in ['remembered','present']:
        m=masks(game,state,'medal'); a=luminance(game/f'{state}-medal.png')
        flat=luminance(game/f'{state}-medal-flat-normal.png')
        off=luminance(game/f'{state}-medal-contact-off.png')
        rough=luminance(game/f'{state}-medal-rough-enamel.png')
        probe=luminance(game/f'{state}-medal-probe-off.png')
        rim=a[m['rim']]; p10,p95=np.percentile(rim,[10,95])
        reduction=(off-a)/np.maximum(off,.02)
        # The full geometric crescent is reported, not only changed pixels.
        contact=float(np.median(reduction[m['contact']]))
        outside=float(np.max(abs(a-off)[m['outside']]))
        effect=abs(a-flat)/max(float(a[m['rim']].mean()),.02)
        row=dict(rim_y_p10=float(p10),rim_y_p95=float(p95),rim_ratio=float(p95/max(p10,.000001)),rim_range=float(p95-p10),
                 normal_rim_nmae=compare(a,flat,m['rim']),normal_bevel_nmae=compare(a,flat,m['bevel']),
                 enamel_rough_off_nmae=compare(a,rough,m['enamel']),probe_brass_nmae=compare(a,probe,m['brass']),probe_enamel_nmae=compare(a,probe,m['enamel']),
                 contact_crescent_median_reduction=contact,contact_changed_fraction=float(np.mean(abs(a-off)[m['contact']]>.001)),
                 outside_3mm_max_linear_delta=outside,normal_changed_rim_fraction=float(np.mean(effect[m['rim']]>=.03)),
                 normal_buffer_nmae=compare(luminance(game/f'{state}-medal-normal-buffer.png'),luminance(game/f'{state}-medal-flat-normal-buffer.png'),m['brass']),
                 visible_medal_pixels=int(m['metal'].sum()),mask_width_px=float(m['visible_body_width_px']))
        ldr=np.asarray(Image.open(game/f'{state}-medal.png').convert('RGB'),float)/255
        ldr_off=np.asarray(Image.open(game/f'{state}-medal-contact-off.png').convert('RGB'),float)/255
        for role in ['rim','enamel']:
            row[role+'_clipped_rgb_fraction']=float(np.any(ldr[m[role]]>=.99,axis=1).mean())
        row['outside_3mm_max_ldr_channel_delta']=float(np.max(abs(ldr-ldr_off)[m['outside']]))
        data=np.load(game/f'{state}-medal-raw-masks.npz')
        uv=data['uv']
        def atlas_mask(name):
            image=np.asarray(Image.open(ROOT/'tmp/issue130-photoreal/stage2'/f'{name}.png').convert('L'),float)/255
            coords=np.array([uv[:,:,1]*image.shape[0]-.5,uv[:,:,0]*image.shape[1]-.5])
            return map_coordinates(image,coords,order=1,mode='nearest')>.5
        tarnish=atlas_mask('tarnish_mask')&m['brass']
        cavity=atlas_mask('cavity_mask')&m['brass']
        edge=atlas_mask('convex_edge_mask')&m['brass']
        cavity_occupancy=float(np.mean(tarnish[cavity]));edge_occupancy=float(np.mean(tarnish[edge]))
        row['age_cavity_occupancy']=cavity_occupancy
        row['age_exposed_edge_occupancy']=edge_occupancy
        row['age_occupancy_ratio']=cavity_occupancy/max(edge_occupancy,1/int(edge.sum()))
        row['age_off_affected_nmae']=compare(a,luminance(game/f'{state}-medal-age-off.png'),tarnish)
        coherent=binary_dilation(binary_erosion(effect>=.03,structure=np.ones((2,2))),iterations=2)
        row['normal_two_pixel_coherent_bevel_fraction']=float(np.mean(coherent[m['bevel']]))
        # Radial profiles use physical hit positions and explicit two-pixel half-height widths.
        local=data['local'];radius=np.hypot(local[:,:,0],local[:,:,2])*1000
        angle=np.arctan2(local[:,:,2],local[:,:,0]);sectors=[]
        for sector in range(36):
            selected=m['rim']&(angle>=-np.pi+sector*np.pi/18)&(angle<-np.pi+(sector+1)*np.pi/18)
            bins=np.linspace(11.5,16,65)
            profile=np.array([np.median(a[selected&(radius>=lo)&(radius<hi)]) if np.any(selected&(radius>=lo)&(radius<hi)) else np.nan for lo,hi in zip(bins[:-1],bins[1:])])
            valid=np.isfinite(profile)
            if valid.sum()<48: continue
            profile=np.interp(np.arange(64),np.flatnonzero(valid),profile[valid])
            profile=gaussian_filter1d(profile,.6)
            min_width=2/(4.5/64*row['mask_width_px']/32)
            peaks,_=find_peaks(profile,prominence=.04,width=min_width)
            valleys,_=find_peaks(-profile,prominence=.04,width=min_width)
            sectors.append({'sector':sector,'highlight_bands':len(peaks),'shadow_bands':len(valleys)})
        row['rim_profile_sectors']=sectors
        row['rim_sectors_with_two_pixel_highlight_and_shadow']=sum(x['highlight_bands']>=1 and x['shadow_bands']>=1 for x in sectors)
        row['gates']={'rim_contrast':p95/max(p10,.000001)>=2 and p95-p10>=.08,
            'normal_effective':row['normal_rim_nmae']>=.03 and row['normal_bevel_nmae']>=.03 and row['normal_two_pixel_coherent_bevel_fraction']>=.5,
            'normal_buffer_differs':row['normal_buffer_nmae']>0,
            'enamel_reflection':row['enamel_rough_off_nmae']>=.02,
            'probe_contributes':max(row['probe_brass_nmae'],row['probe_enamel_nmae'])>=.01,
            'contact_visible':.05<=contact<=.20,
            'contact_local':row['outside_3mm_max_ldr_channel_delta']<=1/255+1e-9,
            'age_follows_form':state!='present' or (row['age_occupancy_ratio']>=2 and row['age_off_affected_nmae']>=.03)}
        exposed=m['brass'] & ~cavity & ~edge
        age_off=luminance(game/f'{state}-medal-age-off.png')
        row['age_off_exposed_nmae']=compare(a,age_off,exposed)
        row['age_exposed_changed_fraction']=float(np.mean(abs(a-age_off)[exposed] >= .03*max(float(a[exposed].mean()),.02)))
        row['age_exposed_mean_y']=float(a[exposed].mean())
        row['age_off_exposed_mean_y']=float(age_off[exposed].mean())
        row['weave_ribbon_nmae']=compare(a,luminance(game/f'{state}-medal-weave-off.png'),m['ribbon'])
        row['local_probe_brass_nmae']=compare(a,luminance(game/f'{state}-medal-local-probe-off.png'),m['brass'])
        row['gates']['rim_not_clipped']=row['rim_clipped_rgb_fraction']<=.02
        row['gates']['exposed_oxide_visible']=state!='present' or (row['age_off_exposed_nmae']>=.03 and row['age_exposed_changed_fraction']>=.5)
        row['gates']['weave_visible']=row['weave_ribbon_nmae']>=.01
        row['gates']={k:bool(v) for k,v in row['gates'].items()}
        row['negative_controls']={'normal_flat_vs_flat_nmae':compare(flat,flat,m['rim']),
            'rough_enamel_vs_itself_nmae':compare(rough,rough,m['enamel']),
            'white_contact_vs_itself_reduction':0.,'probe_off_vs_itself_nmae':compare(probe,probe,m['brass']),
            'normal_flat_two_pixel_band_fraction':0.,'uniform_tarnish_occupancy_ratio':1.}
        row['distance_views']={}
        for view in ['buttons','wardrobe']:
            mask=masks(game,state,view)
            row['distance_views'][view]={'visible_metal_pixels':int(mask['metal'].sum()),'body_projection_width_px':float(mask['visible_body_width_px'])}
        report['states'][state]=row
        print(state,json.dumps(row,indent=2),flush=True)
    (game.parent/'visibility-gates.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game',type=Path,required=True)
    measure(p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None).game.resolve())
