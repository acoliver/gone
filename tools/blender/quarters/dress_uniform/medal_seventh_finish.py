"""#130 image-derived brass variation, recess oxide and low-contrast grosgrain."""
import argparse
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter


def read(path):
    return np.asarray(Image.open(path).convert('RGB'), dtype=np.float32)/255


def save(path, values):
    Image.fromarray(np.uint8(np.clip(values,0,1)*255+.5)).save(path)


def linear(values):
    return np.where(values <= .04045, values/12.92, ((values+.055)/1.055)**2.4)


def srgb(values):
    return np.where(values <= .0031308, values*12.92, 1.055*np.maximum(values,0)**(1/2.4)-.055)


def recess_oxide(concave, convex, ao):
    cavity = np.maximum(np.clip((concave-.14)/.65,0,1),np.clip((1-ao-.16)/.45,0,1))
    return np.clip((1-np.exp(-2.6*cavity))*(1-.96*np.clip(convex/.4,0,1)),0,.85)


def finish(baseline, bakes, atlas, output):
    output.mkdir(parents=True,exist_ok=True)
    for path in baseline.glob('*.png'):
        shutil.copyfile(path,output/path.name)
    brass = read(bakes/'brass-id.png')[...,0]
    concave = read(bakes/'curvature-concave.png')[...,0]
    convex = read(bakes/'curvature-convex.png')[...,0]
    ao = read(bakes/'ao.png')[...,0]
    edge = gaussian_filter(np.clip(convex/.25,0,1),.7)
    flat = brass*(1-edge)*np.clip(1-concave/.15,0,1)
    report = {}
    for state,prefix in [('working','as_built'),('pilot','aged')]:
        orm = read(baseline/f'{prefix}_orm.png')
        before = orm.copy()
        colour = linear(read(baseline/f'{prefix}_albedo.png'))
        luminance = np.mean(colour,axis=2)
        support = brass > .99
        smooth = gaussian_filter(luminance*support,4)/np.maximum(gaussian_filter(support.astype(float),4),1e-7)
        detail = np.clip((luminance-smooth)/np.maximum(smooth,.01),-.15,.15)
        if state == 'working':
            delta = (.048+.025*detail)*flat
            orm[...,1] = np.clip(orm[...,1]+delta,0,1)
            orm[...,2] = np.where(support,1,orm[...,2])
            report[state] = dict(broad_roughness_before_mean=float(before[...,1][flat>.99].mean()),broad_roughness_after_mean=float(orm[...,1][flat>.99].mean()),roughness_increment_min_max=[float(delta.min()),float(delta.max())],brass_metallic=1,edge_roughness_retained=True,albedo_normal_and_enamel_unchanged=True)
        else:
            oxide = recess_oxide(concave,convex,ao)*brass
            size = brass.shape[0]
            image = Image.new('F',(size,size)); draw = ImageDraw.Draw(image)
            data = json.loads((atlas/f'{state}-atlas.json').read_text())
            for uv,normal in zip(data['uv'],data['upward']):
                draw.polygon([(float(u*size),float((1-v)*size)) for u,v in uv],fill=float(max(0,normal)))
            up = gaussian_filter(np.asarray(image),.6)
            dust = .025*up*brass*(1-.8*edge)
            exposed = support & (oxide < .01)
            base = np.median(colour[exposed],axis=0)
            clean = base*(1+.18*detail[...,None])
            amount = .78*oxide
            new = clean*(1-amount[...,None])+np.array([.045,.020,.006])*amount[...,None]
            new = new*(1-dust[...,None])+np.array([.16,.12,.075])*dust[...,None]
            colour = colour*(1-brass[...,None])+new*brass[...,None]
            rough = .555 + .055*detail + .20*oxide + 2*dust - .018*edge
            metal = np.clip(.99-.77*oxide-1.5*dust,0,1)
            orm[...,1] = orm[...,1]*(1-brass)+rough*brass
            orm[...,2] = orm[...,2]*(1-brass)+metal*brass
            save(output/f'{prefix}_albedo.png',srgb(colour))
            save(output/'oxide-localized.png',np.repeat(oxide[...,None],3,2))
            report[state] = dict(exposed_base_linear_rgb=base.tolist(),exposed_oxide_mean=float(oxide[exposed].mean()),cavity_oxide_mean=float(oxide[support & (concave>.5)].mean()),upward_dust_max=float(dust.max()),placement='Measured concave curvature and AO, suppressed by convex curvature; upward dust from saved world face normals',broad_colour_variation='Existing image-derived high-pass only; removed broad mottling',no_green=True)
        save(output/f'{prefix}_orm.png',orm)
        installed = read(output/f'{prefix}_orm.png')
        np.testing.assert_array_equal(installed[...,0],before[...,0])
        enamel = brass == 0
        np.testing.assert_array_equal(installed[enamel],before[enamel])
    size = 512
    y,x = np.mgrid[:size,:size]/size
    source = read(baseline/'ribbon_weave_albedo.png')
    fibre = np.asarray(Image.fromarray(np.uint8(source[...,0]*255)).resize((size,size),Image.Resampling.BILINEAR),float)/255
    fibre = fibre-gaussian_filter(fibre,2,mode='wrap')
    warp = np.sin(x*32*2*np.pi)
    rib = np.sin(y*16*2*np.pi)
    crossing = np.cos(x*32*2*np.pi)*np.cos(y*16*2*np.pi)
    nx = .032*warp*(.9+.1*crossing)
    ny = .115*rib*(.92+.08*crossing)
    normal = np.stack([nx,ny,np.sqrt(1-nx*nx-ny*ny)],axis=2)
    rough = .59+.014*np.cos(y*16*2*np.pi)+.008*crossing+.18*fibre
    albedo = .975+.006*np.cos(y*16*2*np.pi)+.003*crossing+.06*fibre
    save(output/'ribbon_weave_normal.png',normal*.5+.5)
    save(output/'ribbon_weave_roughness.png',np.repeat(rough[...,None],3,2))
    save(output/'ribbon_weave_albedo.png',srgb(np.repeat(albedo[...,None],3,2)))
    report['ribbon'] = dict(rib_pitch_mm=1.066/260/16*1000,warp_pitch_mm=1.066/260/32*1000,linear_albedo_min_max=[float(albedo.min()),float(albedo.max())],roughness_min_max=[float(rough.min()),float(rough.max())],colour_stripes_and_all_uvs_preserved=True,only_medal_ribbon_material=True)
    (output.parent.parent/'finish.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['baseline','bakes','atlas','output']: p.add_argument('--'+name,type=Path,required=True)
    a = p.parse_args()
    finish(a.baseline.resolve(),a.bakes.resolve(),a.atlas.resolve(),a.output.resolve())
