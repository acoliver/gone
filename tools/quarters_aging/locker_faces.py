"""Face-sized locker images: colour owns the layout; chroma only derives relief."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'art-source/quarters/locker/faces'
SCRATCH = ROOT / 'tmp/mat/locker/pass5'
RUNTIME = ROOT / 'tools/quarters_aging/locker_material'
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_hatch_paint import paint_fields
from colour import lab, linear, srgb, delta_e_2000
from visibility_gates import secondary_correlation

ATLAS = (2048, 4096)
# Rectangles are image-space pixels, exclusive right/bottom. Axes use game +Y up.
FACES = {
    'door': dict(part='Door', size=[.514, 2.220], axes=[0, 1], low=[-.257, .110], rect=[8, 8, 520, 2248], crop=[817, 119, 890, 352], concept='docs/art/corridors/hatch-concept-rusted.png'),
    'left': dict(part='SidePanel_L', size=[.560, 2.295], axes=[2, 1], low=[-.280, .105], rect=[696, 8, 888, 776], crop=[445, 338, 535, 411]),
    'right': dict(part='SidePanel_R', size=[.560, 2.295], axes=[2, 1], low=[-.280, .105], rect=[904, 8, 1096, 776], crop=[704, 273, 831, 319]),
    'top': dict(part='TopPanel', size=[.556, .580], axes=[0, 2], low=[-.278, -.290], rect=[1112, 8, 1624, 552], crop=[656, 272, 720, 304]),
    'stile-left': dict(part='SurroundStile_L', size=[.040, 2.180], axes=[0, 1], low=[-.300, .210], rect=[536, 8, 600, 3496], crop=[438, 259, 459, 319]),
    'stile-right': dict(part='SurroundStile_R', size=[.040, 2.180], axes=[0, 1], low=[.260, .210], rect=[616, 8, 680, 3496], crop=[810, 259, 831, 319]),
    'header': dict(part='SurroundHead', size=[.520, .055], axes=[0, 1], low=[-.260, 2.335], rect=[696, 792, 1656, 904], crop=[438, 259, 841, 274]),
    'kick': dict(part='KickPlate', size=[.520, .105], axes=[0, 1], low=[-.260, 0], rect=[696, 920, 1336, 1048], crop=[604, 563, 735, 624]),
    'hardware': dict(part='Hinges,Handle,DoorVents,Rivets,HandlePocket', size=[.2, .2], axes=[0, 1], low=[0, 0], rect=[696, 1064, 1720, 2088], crop=[550, 814, 806, 1032], concept='docs/art/corridors/hatch-concept-rusted.png'),
}


def image_size(face):
    x0, y0, x1, y1 = face['rect']
    return x1-x0, y1-y0


def scores(image, reference, face):
    colour = np.asarray(image.convert('RGB'), float) / 255
    target = np.asarray(reference.convert('RGB'), float) / 255
    paint = paint_fields(image)[1]
    h, w = paint.shape
    # Relative bands also work on the narrow frame. No mask modifies colour.
    yy, xx = np.mgrid[:h, :w]
    edge = (xx < w*.10) | (xx >= w*.90) | (yy < h*.10) | (yy >= h*.90)
    broad = ~edge
    rust = paint < .5
    lum = linear(colour) @ [.2126, .7152, .0722]
    design = np.stack([xx.ravel()/w-.5, yy.ravel()/h-.5, np.ones(w*h)], -1)
    gradient = np.linalg.lstsq(design, lum.ravel(), rcond=None)[0]
    # Downsample only the measurement, retaining the physical 50 mm exclusion.
    measure = image.copy()
    measure.thumbnail((384, 768))
    density = min(measure.width/face['size'][0], measure.height/face['size'][1])
    result = dict(delta_e=float(delta_e_2000(lab(colour).mean((0,1)), lab(target).mean((0,1)))),
                  planar_light_gradient=float(np.linalg.norm(gradient[:2])),
                  secondary_autocorrelation=secondary_correlation(np.asarray(measure)/255, density),
                  edge_rust=float(rust[edge].mean()), broad_rust=float(rust[broad].mean()),
                  edge_broad_ratio=float(rust[edge].mean()/max(rust[broad].mean(), 1e-8)))
    # Keep the previous per-class mean and standard-deviation colour gates.
    for name, selected, expected in [('paint', paint >= .5, paint_fields(reference)[1] >= .5),
                                     ('rust', paint < .5, paint_fields(reference)[1] < .5)]:
        if selected.any() and expected.any():
            a, b = lab(colour[selected]), lab(target[expected])
            result[name+'_mean_delta_e'] = float(np.linalg.norm(a.mean(0)-b.mean(0)))
            result[name+'_std_delta_e'] = float(np.linalg.norm(a.std(0)-b.std(0)))
        else:
            result[name+'_mean_delta_e'] = 100.
            result[name+'_std_delta_e'] = 100.
    return result


def eligible(row, hardware=False):
    return (all(v <= 8 for k,v in row.items() if k.endswith('delta_e'))
            and row['planar_light_gradient'] < .06
            and row['secondary_autocorrelation'] <= .5
            and (hardware or row['edge_broad_ratio'] >= 1.8))


def pack(selection, output=SOURCE):
    atlas = np.zeros((ATLAS[1], ATLAS[0], 4), np.uint8)
    normal = np.zeros_like(atlas)
    normal[:] = [128,128,255,255]
    orm = np.zeros_like(atlas)
    orm[:] = [255,230,0,0]
    for name, face in FACES.items():
        image = Image.open(SOURCE / selection[name]['chosen']).convert('RGB')
        if image.size != image_size(face):
            raise ValueError(f'wrong face size: {name}')
        colour, paint = paint_fields(image)
        width, height = image.size
        density = [width/face['size'][0], height/face['size'][1]]
        relief = paint * .0015
        if name == 'hardware':
            lum = linear(colour) @ [.2126, .7152, .0722]
            relief = (lum-lum.mean())*.0003
        dy, dx = np.gradient(relief)
        n = np.dstack([-dx*density[0], dy*density[1], np.ones_like(dx)])
        n /= np.linalg.norm(n,axis=2,keepdims=True)
        x0,y0,x1,y1 = face['rect']
        atlas[y0:y1,x0:x1,:3] = np.round(colour*255).astype('uint8')
        atlas[y0:y1,x0:x1,3] = np.round((1-paint)*255).astype('uint8')
        normal[y0:y1,x0:x1,:3] = np.round((n*.5+.5)*255).astype('uint8')
        orm[y0:y1,x0:x1,1] = np.round((.91*(1-paint)+.69*paint)*255).astype('uint8')
        orm[y0:y1,x0:x1,3] = 255 if name == 'top' else 0
        # Four-pixel extrusion prevents neighbouring cells bleeding into mip 0.
        for data in (atlas,normal,orm):
            data[y0-4:y1+4,x0-4:x1+4] = np.pad(data[y0:y1,x0:x1],((4,4),(4,4),(0,0)),mode='edge')
    for name,data in [('aged-face-albedo',atlas),('aged-face-normal',normal),('aged-face-orm',orm)]:
        Image.fromarray(data).save(output/(name+'.png'))
        if output == SOURCE:
            RUNTIME.mkdir(exist_ok=True)
            Image.fromarray(data).save(RUNTIME/(name+'.png'))
    if output == SOURCE:
        (RUNTIME/'face-layout.json').write_text(json.dumps(manifest(),indent=2)+'\n')


def manifest():
    rows = {}
    for name, face in FACES.items():
        x0,y0,x1,y1 = face['rect']
        rows[name] = dict(face, uv_rectangle=[x0/ATLAS[0], y0/ATLAS[1], x1/ATLAS[0], y1/ATLAS[1]],
                          pixels_per_metre=[(x1-x0)/face['size'][0],(y1-y0)/face['size'][1]])
    return dict(atlas=list(ATLAS), faces=rows, paint_height_m=.0015,
                mapping='one full image per face, clamped direct physical projection; hardware cylindrical/dominant planar projection',
                procedural_islands=False, procedural_streaks=False, supplemental_runoff_opacity=0)
