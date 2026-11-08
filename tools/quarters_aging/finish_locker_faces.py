"""Select measured final images, with bounded image-coloured fixture stains."""
import copy
import json

import numpy as np
from PIL import Image, ImageDraw

from locker_faces import ROOT, SOURCE, SCRATCH, FACES, scores, eligible, pack
from locker_gates import hsv
from locker_face_runoff import attached_runs


def finish(image,name, right_hue=50., door_muted=.34):
    colour=np.asarray(image.convert('RGB'),float)/255
    hue,saturation,value=hsv(colour)
    # A spatially uniform hue/saturation operation keeps generated green paint
    # in the muted source gamut. It cannot introduce a new wear layout.
    green=(hue>=70)&(hue<=170)&(saturation>.23)
    ratio=np.minimum(1.,.23/np.maximum(saturation,1e-6))
    colour[green]=(value[...,None]-(value[...,None]-colour)*ratio[...,None])[green]
    if name!='hardware':
        hue,saturation,value=hsv(colour)
        muted=saturation<(.39 if name=='top' else (door_muted if name=='door' else (.30 if name=='stile-left' else .36)))
        saturation[muted]=np.clip(saturation[muted]*.65+.035,.07,.20) if name=='top' else np.clip(saturation[muted]*.45+.03,.06,.17)
        hue[muted]=np.clip(hue[muted]+8,25,50) if name=='top' else (35. if name=='door' else (right_hue if name=='stile-right' else 65.))
        chroma=value*saturation
        sector=hue/60.
        second=chroma*(1-abs(sector%2-1))
        zero=np.zeros_like(chroma)
        channels=[(chroma,second,zero),(second,chroma,zero),(zero,chroma,second),
                  (zero,second,chroma),(second,zero,chroma),(chroma,zero,second)]
        converted=np.zeros_like(colour)
        for index,values in enumerate(channels):
            selected=(sector>=index)&(sector<index+1)
            converted[selected]=np.stack(values,-1)[selected]
        colour=converted+(value-chroma)[...,None]
    image=Image.fromarray(np.uint8(np.round(colour*255)))
    return attached_runs(image,name)


def main():
    candidates=json.loads((SOURCE/'candidate-scores.json').read_text())
    selection={}; finished={}
    for name,face in FACES.items():
        reference=Image.open(SOURCE/f'{name}-source.png').convert('RGB')
        rows=[]
        for original in candidates[name]:
            row=copy.deepcopy(original)
            image,runs=finish(Image.open(SOURCE/row['chosen']),name)
            destination=row['chosen'].removesuffix('.png')+'-finish.png'
            image.save(SOURCE/destination)
            row['calibrated']=row['chosen'];row['chosen']=destination
            row['supplemental_runs']=runs
            row['global_colour_grade']=dict(method='Spatially uniform HSV operation; no spatial wear mask',
                muted_threshold=.39 if name=='top' else (.34 if name=='door' else (.30 if name=='stile-left' else .36)),
                muted_hue_degrees='clip(input+8,25,50)' if name=='top' else (35 if name=='door' else (50 if name=='stile-right' else 65)),
                muted_saturation='clip(input*.65+.035,.07,.20)' if name=='top' else 'clip(input*.45+.03,.06,.17)',
                original_high_chroma_oxide_retained=True)
            row['supplemental_max_opacity']=.30 if runs else 0.
            row['scores']=scores(image,reference,face)
            row['eligible']=eligible(row['scores'],name=='hardware')
            row['rank_score']=(sum(v for k,v in row['scores'].items() if k.endswith('delta_e'))
                               +row['scores']['secondary_autocorrelation']*8
                               +abs(row['scores']['broad_rust']-.15)*(50 if name=='door' else 10))
            if name=='door' and row['seed']<96000:
                row['eligible']=False
                row['visual_rejection']='Straight, near-continuous margins; replaced with a full door-like reference edit'
            if name=='top' and row['seed']!=96130:
                row['eligible']=False
                row['visual_rejection']='Image-comparer selected 96130 for fine soft dust; other candidates contain cloudy patches, branching streaks or strong dark margins'
            rows.append(row)
        valid=[row for row in rows if row['eligible']]
        if not valid:
            # Keep measured failures available for inspection, never mark them
            # accepted or substitute a supposedly safe generated material.
            valid=rows
        chosen=min(valid,key=lambda r:(sum(max(0,v-8) for k,v in r['scores'].items() if k.endswith('delta_e'))
                   +max(0,1.8-r['scores']['edge_broad_ratio'])*10
                   +max(0,r['scores']['secondary_autocorrelation']-.5)*20,r['rank_score']))
        selection[name]=chosen;finished[name]=rows
        print(name,chosen['seed'],chosen['eligible'],chosen['scores'],flush=True)
    (SOURCE/'finish-scores.json').write_text(json.dumps(finished,indent=2)+'\n')
    if not all(row['eligible'] for row in selection.values()):
        failed=[name for name,row in selection.items() if not row['eligible']]
        raise SystemExit('No eligible final image for: '+', '.join(failed)+'; see finish-scores.json')
    (SOURCE/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
    pack(selection)
    sheet=Image.new('RGB',(1024,len(FACES)*390),'#24282a');draw=ImageDraw.Draw(sheet)
    for index,(name,row) in enumerate(selection.items()):
        for column,path in enumerate([f'{name}-source.png',row['chosen']]):
            image=Image.open(SOURCE/path).convert('RGB');image.thumbnail((490,340))
            sheet.paste(image,(column*512+(512-image.width)//2,index*390+32))
        draw.text((12,index*390+8),f'{name}: source | seed {row["seed"]}; measured rank {row["rank_score"]:.3f}',fill='white')
    sheet.save(SCRATCH/'faces.png')
    swatch_sheet(selection)
    pattern_comparison(selection)


def swatch_sheet(selection):
    sheet=Image.new('RGB',(1200,1320),'#24282a');draw=ImageDraw.Draw(sheet)
    for index,(name,row) in enumerate(selection.items()):
        image=Image.open(SOURCE/row['chosen']).convert('RGB')
        metres=FACES[name]['size']
        width=min(image.width,round(.2/metres[0]*image.width))
        height=min(image.height,round(.2/metres[1]*image.height))
        left=(image.width-width)//2;top=(image.height-height)//2
        image=image.crop((left,top,left+width,top+height))
        image.thumbnail((384,384))
        x=index%3*400;y=index//3*440
        sheet.paste(image,(x+(400-image.width)//2,y+40))
        draw.text((x+8,y+8),f'{name}: seed {row["seed"]}; central <=0.20 m',fill='white')
    sheet.save(SCRATCH/'swatches.png')


def pattern_comparison(selection):
    density=400
    door=Image.open(SOURCE/selection['door']['chosen']).convert('RGB')
    door=door.resize(tuple(round(value*density) for value in FACES['door']['size']),Image.Resampling.LANCZOS)
    crop=Image.open(ROOT/'docs/art/quarters/concept-now.png').convert('RGB').crop((448,310,534,460))
    # The concept has no metric annotation. Register its full locker height to
    # the fitted 2.4 m carcass, preserving its original aspect ratio.
    crop=crop.resize((round(crop.width/crop.height*2.4*density),round(2.4*density)),Image.Resampling.LANCZOS)
    comparison=Image.new('RGB',(door.width+crop.width+48,crop.height+48),'#24282a')
    comparison.paste(door,(16,32+round((2.4-2.330)*density)))
    comparison.paste(crop,(door.width+32,32))
    draw=ImageDraw.Draw(comparison)
    draw.text((16,8),'Door | concept locker; 400 px/m by registered height',fill='white')
    comparison.save(SCRATCH/'pattern-compare.png')


if __name__=='__main__': main()
