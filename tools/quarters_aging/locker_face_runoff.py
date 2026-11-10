"""Optional translucent fixture stains, coloured only from the receiving image."""
import json

import numpy as np
from PIL import Image

from colour import linear, srgb
from locker_faces import ROOT, FACES, paint_fields


def attached_runs(image, name):
    if name not in ('door','stile-left','stile-right','header'):
        return image,[]
    face=FACES[name]
    colour=np.asarray(image.convert('RGB'),float)/255
    paint=paint_fields(image)[1]
    rust=paint<.5
    from locker_gates import hsv
    hue,saturation,_=hsv(colour)
    existing=rust|((hue>=5)&(hue<=50)&(saturation>=.18))
    if not rust.any():
        raise ValueError('fixture stain needs rust colour in its own receiving image')
    energy=linear(colour)
    pigments=energy[rust]
    luma=pigments@[.2126,.7152,.0722]
    score= pigments[:,0]-pigments[:,2]-np.maximum(luma-.06,0)*20
    pigment=pigments[np.argmax(score)]
    sources=json.loads((ROOT/'assets/props/quarters/storage_locker_module/masks.json').read_text())['sources']
    h,w=paint.shape
    yy,xx=np.mgrid[:h,:w]
    x=face['low'][0]+xx/(w-1)*face['size'][0]
    y=face['low'][1]+(1-yy/(h-1))*face['size'][1]
    opacity=np.zeros((h,w))
    records=[]
    for source in sources:
        if source['part'] not in ('Rivets','Hinges'): continue
        sx,_,sy=source['position_blender']
        if source['part']=='Hinges': sx+=.015
        if not (face['low'][0]<=sx<=face['low'][0]+face['size'][0] and
                face['low'][1]<sy<=face['low'][1]+face['size'][1]): continue
        if name=='door' and source['part']!='Hinges': continue
        if name!='door' and source['part']=='Hinges': continue
        signature=int(abs(sx*13747+sy*3209))
        length=.085+(signature%79)/1000
        paired=any(other is not source and abs(other['position_blender'][2]-sy)<.004
                   and .001<abs(other['position_blender'][0]-sx)<.020 for other in sources)
        width=.0045 if paired else .008
        drop=sy-y
        t=np.clip(drop/length,0,1)
        drift=.0012*np.sin(t*np.pi)*(1 if signature%2 else -1)
        radius=width*.5*(1-t)**.65
        lateral=abs(x-sx-drift)
        coverage=np.clip((radius-lateral)/.0015+.5,0,1)
        coverage*=.30*np.clip((length-drop)/.030,0,1)
        coverage*=(drop>=.002)&(drop<=length)
        # Existing image corrosion remains untouched; this is a stain on paint.
        coverage*=~existing
        opacity=np.maximum(opacity,coverage)
        records.append(dict(part=source['part'],outlet_prop=[sx,sy],length_m=length,width_m=width,max_opacity=.30))
    result=energy*(1-opacity[...,None])+pigment*opacity[...,None]
    return Image.fromarray(np.uint8(np.round(np.clip(srgb(result),0,1)*255))),records
