"""Package fixed-camera #130 PNGs as <=1400-pixel JPEGs without judging images."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parents[4]
FONT=ImageFont.load_default(size=18)


def sheet(panels, destination, columns=2):
    width=1400//columns
    height=round(width*824/1536)
    rows=(len(panels)+columns-1)//columns
    result=Image.new('RGB',(width*columns,(height+32)*rows),(28,28,28))
    draw=ImageDraw.Draw(result)
    for index,(path,title) in enumerate(panels):
        image=ImageOps.contain(Image.open(path).convert('RGB'),(width,height),Image.Resampling.LANCZOS)
        x,y=index%columns*width,index//columns*(height+32)
        draw.text((x+10,y+6),title,font=FONT,fill='white')
        result.paste(image,(x+(width-image.width)//2,y+32+(height-image.height)//2))
    assert max(result.size)<=1400
    result.save(destination,quality=94,subsampling=0)


def make(game,baseline,original,output):
    output.mkdir(parents=True,exist_ok=True)
    paths=[]
    def save(name,panels,columns=2):
        path=output/(name+'.jpg');sheet(panels,path,columns);paths.append(str(path))
    for state in ['remembered','present']:
        for view in ['medal','buttons','wardrobe']:
            name=f'{state}-{view}'
            save(name,[(game/(name+'.png'),f'{state.title()} | {view} | production')],1)
            save(name+'-before-after',[(baseline/(name+'.png'),'Before | 6987fce'),(game/(name+'.png'),'After | physical brass and ribbon')])
            save(name+'-original-before-after',[(original/(name+'.png'),'Before | ef57c29'),(game/(name+'.png'),'After | physical brass and ribbon')])
        save(state+'-oblique-context',[(game/f'{state}-oblique-context-full.png','Additional evidence | oblique wool, loop and contact')],1)
        save(state+'-oblique-context-controls',[(game/f'{state}-oblique-context-{control}.png',title) for control,title in [('full','Additional evidence | full'),('contact-off','Contact AO off'),('weave-off','Ribbon weave off')]],3)
        save(state+'-probe-viewpoints',[(game.parent/f'{state}-probe-face-{i}.png',f'Additional evidence | local probe direction {i}') for i in range(6)],3)
        def lane(suffix):return game/(f'{state}-medal'+('-'+suffix if suffix else '')+'.png')
        save(state+'-ribbon-controls',[(lane(''),'Woven ribbon'),(lane('weave-off'),'Weave off')])
        save(state+'-reflection-controls',[(lane(''),'Full'),(lane('local-probe-off'),'Local probe off'),(lane('probe-off'),'All quarters probes off')],3)
        save(state+'-probe-cause-controls',[(lane(''),'Full'),(lane('capture-no-lights'),'Local capture excludes light layer 1'),(lane('capture-disabled-ambient'),'Local capture ambient disabled')],3)
        save(state+'-controls',[(lane(''),'Full'),(lane('flat-normal'),'Flat normal'),(lane('contact-off'),'Contact AO off'),(lane('probe-off'),'Quarters probes off')])
        save(state+'-finish-controls',[(lane(''),'Full'),(lane('rough-enamel'),'Rough enamel'),(lane('age-off'),'Untarnished atlas'),(lane('normal-buffer'),'Tangent normal buffer')])
        save(state+'-power-controls',[(lane(''),'Normal power state'),(lane('fade'),'Existing power fade'),(lane('off'),'Existing power off')])
        save(state+'-sweep',[(game/f'{state}-sweep-{frame:02d}-{control}.png',f'Additional view {frame:02d} | '+('full' if control=='full' else 'overstrong, no mips')) for frame in [0,12,23] for control in ['full','strong']])
        studio=game.parents[1]/'stage2/renders'
        save(state+'-concept-studio-game',[(ROOT/'docs/art/quarters/sheets/medal/c-machined-rim-seed130303.png','Concept reference'),(studio/f'low-{state}-three-quarter-full.jpg','Stage 2 low | studio reference'),(studio/f'high-{state}-three-quarter-full.jpg','Stage 2 high | studio reference'),(lane(''),'Game | unchanged acceptance camera')])
    (game.parent/'jpeg-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
    print(json.dumps(paths,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',type=Path,required=True);p.add_argument('--game',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();make(a.game.resolve(),a.baseline.resolve(),a.original.resolve(),a.output.resolve())
