"""Small deterministic finish maps. No biological weathering or paper substrates."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[4]
COLORS = {
    'PaintedSteel': (.12,.18,.16), 'BareSteel': (.42,.47,.46), 'Brass': (.57,.34,.09),
    'Ceramic': (.77,.74,.64), 'Glaze': (.065,.11,.08), 'HardPlastic': (.12,.18,.14),
    'IvoryPlastic': (.72,.70,.58), 'BluePlastic': (.08,.18,.23), 'Display': (.007,.012,.014),
    'Rubber': (.018,.024,.021), 'Leather': (.055,.033,.023), 'Lining': (.15,.025,.035),
    'Bristle': (.39,.26,.12), 'Ribbon': (.40,.045,.035), 'RibbonIvory': (.65,.61,.45),
    'Stain': (.77,.74,.64), 'DustCeramic': (.77,.74,.64),
}


def noise(rng, size, coarse):
    source = Image.fromarray((rng.random((coarse,coarse))*255).astype('uint8'))
    return np.asarray(source.resize((size,size), Image.Resampling.BICUBIC), dtype=float)/255


def bake(item, surface=False):
    geometry=None
    if surface:
        from scipy.ndimage import distance_transform_edt
        data=np.load(ROOT/'tmp/small'/item/'surface.npz')
        nearest=distance_transform_edt(~data['valid'],return_distances=False,return_indices=True)
        geometry=(data['position'][tuple(nearest)],data['normal'][tuple(nearest)])
    folder = ROOT/'assets/props/quarters/textures'/item
    folder.mkdir(parents=True, exist_ok=True)
    used = {
        'photo_frame': ['PaintedSteel','BareSteel'],
        'mug': ['Ceramic','Glaze','Stain','DustCeramic'],
        'plate': ['Ceramic','Glaze','Stain','DustCeramic'],
        'data_tablet': ['HardPlastic','Rubber','Display','BareSteel'],
        'medal_case': ['PaintedSteel','Lining','Brass','Ribbon','RibbonIvory'],
        'jewellery_box': ['IvoryPlastic','BluePlastic','Brass'],
        'hairbrush': ['HardPlastic','Rubber','Bristle'],
        'boots': ['Leather','Rubber'],
    }[item]
    for name in used:
        color = COLORS[name]
        seed = int.from_bytes(hashlib.sha256((item+name).encode()).digest()[:4], 'little')
        rng = np.random.default_rng(seed)
        size = 512
        broad = noise(rng,size,14)
        fine = noise(rng,size,96)
        grain = rng.random((size,size))
        base = np.array(color)**(1/2.2)
        rgb = np.broadcast_to(base, (size,size,3)).copy()
        height = fine*.015
        dust = np.array([.57,.53,.43])
        if name in {'BareSteel','PaintedSteel'}:
            oxide = np.clip((broad*.75+fine*.25-.34)*3.0,0,1)
            rust = np.array([.23,.085,.025])[None,None,:]*(.7+fine[...,None]*.6)
            rgb = rgb*(1-oxide[...,None])+rust*oxide[...,None]
            height = oxide*.14+grain*.04
        elif name == 'Brass':
            patina = np.clip((broad-.33)*3,0,1)
            # Mineral verdigris on brass only; never biological growth.
            green = np.array([.17,.26,.19])*(.7+fine[...,None]*.5)
            rgb = rgb*(1-patina[...,None])*.62+green*patina[...,None]
            height = patina*.10+grain*.02
        elif name in {'HardPlastic','IvoryPlastic','BluePlastic','Display','Rubber','Leather'}:
            if 'Plastic' in name:
                rgb = rgb*np.array([1.0,.85,.54])*.78
            if name == 'Leather':
                rgb = rgb*.52+np.array([.12,.07,.03])*.20
            # Seeded irregular hairline networks, not a uniform square grid.
            spots = rng.random((180 if name=='Display' else 38,2))*size
            yy,xx = np.mgrid[:size,:size]
            nearest = np.full((size,size),np.inf)
            second = nearest.copy()
            for sx,sy in spots:
                dist = (xx-sx)**2+(yy-sy)**2
                closer = dist<nearest
                second = np.where(closer,nearest,np.minimum(second,dist))
                nearest = np.minimum(nearest,dist)
            crack_width=.28 if name=='Display' else .38 if item=='jewellery_box' else 1.15
            crack = np.sqrt(second)-np.sqrt(nearest)<crack_width
            rgb[crack] *= .60 if item=='jewellery_box' else .18
            height = np.where(crack,-.07 if item=='jewellery_box' else -.18,fine*.025)
            if name=='Display':
                rgb = rgb*.25+broad[...,None]*.008
                rgb[crack]=(.12,.13,.12)
        elif name in {'Ceramic','Glaze','Stain'}:
            rgb *= (.87+fine[...,None]*.12)
            if name=='Stain':
                stain = np.clip((broad-.38)*4,0,.90)
                rgb = rgb*(1-stain[...,None])+np.array([.21,.105,.035])*stain[...,None]
                height += fine*.025
        else:
            rgb = rgb*.56+np.array([.26,.20,.12])*.18
        if item=='jewellery_box' and name=='IvoryPlastic':
            rgb=rgb*np.array([1.12,1.16,1.37])
        if item=='jewellery_box' and name=='BluePlastic':
            rgb=rgb*np.array([.82,1.04,1.56])
        if item=='boots' and name=='Rubber':
            rgb=np.repeat(rgb.mean(axis=2,keepdims=True),3,axis=2)*.65
        if item=='boots' and name=='Leather':
            dy,dx=np.gradient(noise(rng,size,256)*.70+grain*.14)
            clean_normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1)
            clean_normal/=np.linalg.norm(clean_normal,axis=-1,keepdims=True)
            Image.fromarray(((clean_normal*.5+.5)*255+.5).astype('uint8')).save(folder/'Leather_clean_normal.png')
        surface_dust=None
        if geometry is not None and name in {'Ceramic','Glaze','Stain','DustCeramic'}:
            p,n=geometry
            x,y,z=p[...,0],p[...,1],p[...,2]
            radius=np.hypot(x,y); angle=np.arctan2(y,x)
            up=np.clip(n[...,2],0,1)
            substrate=np.array(COLORS['Glaze' if name=='Glaze' else 'Ceramic'])**(1/2.2)
            rgb=np.broadcast_to(substrate,(size,size,3)).copy()*(.95+fine[...,None]*.05)
            if item=='mug':
                inner=(n[...,0]*x+n[...,1]*y)<(-.2*radius)
                line=.077+.0025*np.sin(angle*5)+.0015*np.sin(angle*9)
                ring=np.exp(-((z-line)/.006)**2)*inner
                floor=(z<.025)*(up>.4)*(radius<.034)
                ring+=np.exp(-((radius-(.024+.0015*np.sin(angle*7)))/.003)**2)*floor
            else:
                line=.076+.0035*np.sin(angle*5)+.002*np.cos(angle*9)
                ring=np.exp(-((radius-line)/.0045)**2)*(up>.4)
            stain=np.clip(ring*(.57+.35*broad),0,.90)
            rgb=rgb*(1-stain[...,None])+np.array([.26,.115,.035])*stain[...,None]
            craze=(np.abs(fine-.5)<.010)&(up>.1)
            rgb[craze]*=.62
            height=np.where(craze,-.08,fine*.015)
            surface_dust=(.06+up*(.48+.23*fine))
        control = ROOT/'tmp/small'/item/'no_dust'
        control.mkdir(parents=True,exist_ok=True)
        no_dust_rgb=np.clip(rgb+(grain[...,None]-.5)*.018,0,1)
        Image.fromarray((no_dust_rgb*255+.5).astype('uint8')).save(control/f'{name}_aged.png')
        dust_alpha = surface_dust if surface_dust is not None else ((.52+.18*fine) if name=='DustCeramic' else (.08+.16*fine))
        if name in {'Display','Leather','Bristle'}:
            dust_alpha *= .15 if name=='Display' else .55
        if item=='jewellery_box':
            dust_alpha=.22+.25*broad
            dust=np.array([.71,.66,.55])
        rgb = rgb*(1-dust_alpha[...,None])+dust*dust_alpha[...,None]
        rgb = np.clip(rgb+(grain[...,None]-.5)*.018,0,1)
        Image.fromarray((rgb*255+.5).astype('uint8')).save(folder/f'{name}_aged.png')
        dy,dx=np.gradient(height)
        normal=np.stack((-dx*2,-dy*2,np.ones_like(dx)),axis=-1)
        normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
        Image.fromarray(((normal*.5+.5)*255+.5).astype('uint8')).save(folder/f'{name}_normal.png')
    if item=='photo_frame':
        photo=Image.open(ROOT/'docs/art/quarters/sheets/photo_frame/couple-portrait.png').convert('RGB').resize((512,384),Image.Resampling.LANCZOS)
        photo.save(folder/'print.png')
        faded=ImageEnhance.Color(photo).enhance(.15)
        rgb=np.asarray(faded,dtype=float)/255
        rgb=rgb*np.array([.62,.57,.40])+np.array([.23,.19,.13])
        Image.fromarray(np.clip(rgb*255,0,255).astype('uint8')).filter(ImageFilter.GaussianBlur(.45)).save(folder/'print_aged.png')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('item')
    parser.add_argument('--surface',action='store_true')
    args=parser.parse_args()
    bake(args.item,args.surface)
