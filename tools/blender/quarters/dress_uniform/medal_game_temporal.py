"""Measure isolated temporal finish spikes in the additional, non-acceptance view sweep."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion, label


def luminance(path):
    rgb=np.asarray(Image.open(path).convert('RGB'),np.float32)/255
    linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    return linear@np.array([.2126,.7152,.0722],np.float32)


def measure(game):
    report={'method':'Additional +/-0.8 degree 24-frame view arc. Second temporal difference of full-minus-geometry-normal signal; isolated connected components of at most four pixels, above 10% of reference mean luminance. Uncompressed ImageTexture normals; full and geometry controls are mipmapped, while the overstrong negative has no mipmaps. Production uses imported compression.', 'states':{}}
    for state in ['remembered','present']:
        role=np.load(game/f'{state}-medal-raw-masks.npz')['role']
        mask=binary_erosion(role==1,iterations=8)
        values={lane:np.stack([luminance(game/f'{state}-sweep-{frame:02d}-{lane}.png') for frame in range(24)]) for lane in ['full','fine-off','strong']}
        floor=max(float(values['full'][:,mask].mean()),.02)
        row={}
        for lane in ['full','strong']:
            signal=values[lane]-values['fine-off']
            curvature=abs(signal[1:-1]-(signal[:-2]+signal[2:])*.5)/floor
            spikes=[]
            for frame in curvature:
                components,count=label((frame>.10)&mask)
                sizes=np.bincount(components.ravel());sizes[0]=0
                spikes.append(int(sizes[(sizes>0)&(sizes<=4)].sum()))
            row[lane]={'isolated_spike_pixels_total':sum(spikes),'maximum_in_one_frame':max(spikes), 'sample_fraction':sum(spikes)/(22*int(mask.sum())), 'normalized_second_difference_p999':float(np.quantile(curvature[:,mask],.999))}
        row['mask_pixels']=int(mask.sum())
        row['threshold_10_percent_exposes_overstrong_control']=row['strong']['isolated_spike_pixels_total']>row['full']['isolated_spike_pixels_total']
        report['states'][state]=row
    (game.parent/'temporal-gates.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game',type=Path,required=True)
    measure(p.parse_args().game.resolve())
