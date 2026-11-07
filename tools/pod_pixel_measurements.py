"""Measure pod captures without visual judgments (requires NumPy and Pillow).

Run after pod_captures.gd and Blender's pod_v4/diagnose_views.py:
python tools/pod_pixel_measurements.py --captures tmp/pods/fix5/captures
All luminance is linear Rec.709; geometry IDs exclude glass and particle smoke.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from PIL import Image


def rgb(path):
    return np.asarray(Image.open(path).convert('RGB'),dtype=float)/255


def luminance(image):
    linear = np.where(image<=.04045,image/12.92,((image+.055)/1.055)**2.4)
    return linear @ np.array([.2126,.7152,.0722])


def erode(mask, distance):
    result = mask.copy()
    for axis in [0,1]:
        for offset in [-distance,distance]:
            result &= np.roll(mask,offset,axis)
    result[:distance] = result[-distance:] = False
    result[:,:distance] = result[:,-distance:] = False
    return result


def interior(directory):
    result = {}
    for power in ['red','white']:
        glass = luminance(rgb(directory/f'sealed-close-{power}.png'))
        hidden = luminance(rgb(directory/f'sealed-close-{power}-pane-hidden.png'))
        aperture = erode(rgb(directory/f'pane-mask-{power}.png').min(2)>.95,2)
        for part in ['couch','pillow']:
            mask = rgb(directory/f'{part}-mask-{power}.png').min(2)>.95
            inside = erode(mask,5)&aperture
            edges = []
            for dy,dx in [(0,5),(0,-5),(5,0),(-5,0)]:
                paired = mask & ~np.roll(mask,(-dy,-dx),(0,1)) & aperture & np.roll(aperture,(-dy,-dx),(0,1))
                paired[:7] = paired[-7:] = False
                paired[:,:7] = paired[:,-7:] = False
                edges.append((paired,dy,dx))
            row = {'pixels':int(inside.sum()),'hidden_mean':float(hidden[inside].mean()),'glass_mean':float(glass[inside].mean()),'glass_p10_p50_p90':np.quantile(glass[inside],[.1,.5,.9]).tolist(),'pixelwise_mean_delta':float((glass-hidden)[inside].mean())}
            for name,image in [('hidden',hidden),('glass',glass)]:
                differences,contrasts=[],[]
                for paired,dy,dx in edges:
                    a=image[paired]; b=np.roll(image,(-dy,-dx),(0,1))[paired]
                    differences.extend(np.abs(a-b))
                    contrasts.extend(np.abs(a-b)/np.maximum(a+b,1e-9))
                row[name+'_edge_delta']=float(np.mean(differences))
                row[name+'_edge_michelson']=float(np.mean(contrasts))
            for control in ['pane-hidden','lid-hidden']:
                witness=luminance(rgb(directory/f'white-fabric-{power}-{control}.png'))
                row['white_fabric_'+control]=float(witness[inside].mean())
            result[part+'_'+power]=row
    return result


def surface_summary(directory,label,roi):
    rays=np.load(directory/f'{label}-rays.npy')
    surfaces=json.loads((directory/'ray-surfaces.json').read_text())['mirror' if 'mirror' in label else 'scene']
    lum=luminance(rgb(directory/(label+'.png')))
    x,y=rays[:,:2].astype(int).T
    values=lum[y,x]
    selected=(x>=roi[0])&(y>=roi[1])&(x<roi[2])&(y<roi[3])
    result={'roi':roi,'sample_stride':int(rays[1,0]-rays[0,0]),'samples':int(selected.sum()),'dark_first_hits':{},'surfaces':{}}
    dark=selected&(values<.01)
    for index,count in Counter(rays[dark,2].astype(int)).most_common():
        name='background/void' if index<0 else surfaces[index]['path']+':'+surfaces[index]['material']
        result['dark_first_hits'][name]=count
    for index in np.unique(rays[selected,2].astype(int)):
        if index<0:
            continue
        name=surfaces[index]['path']+':'+surfaces[index]['material']
        mask=selected&(rays[:,2]==index)
        if 'Pod' not in name:
            continue
        result['surfaces'][name]={'samples':int(mask.sum()),'mean_luminance':float(values[mask].mean()),'dark_samples':int((mask&dark).sum()),'backfacing_normals':int((rays[mask,9]<0).sum()),'mean_normal':rays[mask,6:9].mean(0).tolist()}
    return result


def strips(directory):
    rows={}; profiles=[]
    for side in ['left','right']:
        image=rgb(directory/f'flank-mirror-{side}.png')
        mask=(image[:,:,0]>.4)&(image[:,:,0]>2*image[:,:,1])&(image[:,:,0]>2*image[:,:,2])
        ys,xs=np.where(mask)
        rows[side]={'pixels':len(ys),'row_min_median_max':np.quantile(ys,[0,.5,1]).tolist()}
        if side=='right':mask=mask[:,::-1]
        counts=mask.sum(0)
        profiles.append(np.divide((mask*np.arange(648)[:,None]).sum(0),counts,out=np.full(1152,np.nan),where=counts>0))
    delta=np.abs(profiles[0]-profiles[1]); common=np.isfinite(delta)
    rows['mirrored_column_row_delta']={'columns':int(common.sum()),'mean':float(delta[common].mean()),'maximum':float(delta[common].max()),'median':float(np.median(delta[common]))}
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures',type=Path,required=True)
    args=parser.parse_args()
    result={'interior':interior(args.captures),'strips':strips(args.captures),'hinge':surface_summary(args.captures,'open-head-hinge-contact',[400,180,800,420])}
    result['flanks']={label:surface_summary(args.captures,label,[100,120,1050,420]) for label in ['flank-row-a-left','flank-row-a-right','flank-row-b-left','flank-row-b-right','flank-mirror-left','flank-mirror-right']}
    (args.captures/'surface-measurements.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
