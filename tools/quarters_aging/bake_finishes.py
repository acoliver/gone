"""Bake the unchanged clean finish and pack direct generated aged face images."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

from colour import linear, srgb
from finish_fields import noise
from locker_faces import SOURCE, pack

ROOT = Path(__file__).resolve().parents[2]
DESIGN_ROI = (460, 440, 550, 600)


def design_paint():
    image = Image.open(ROOT/'docs/art/quarters/sheets/storage_locker_module/hero.png').convert('RGB')
    region = np.asarray(image.crop(DESIGN_ROI),np.float32)/255
    return srgb(np.median(linear(region),axis=(0,1)))


def write_atlas(path, data, nearest):
    data = data[tuple(nearest)]
    Image.fromarray(np.uint8(np.round(np.clip(data,0,1)*255))).save(path)


def bake(directory, fields):
    metadata = json.loads((directory/'masks.json').read_text())
    geometry = np.asarray(Image.open(directory/'geometry_masks.png'),np.float32)/255
    arrays = np.load(fields)
    occupied,ownership = arrays['occupied'],arrays['ownership']
    p = arrays['position'][occupied]
    owner = ownership[occupied]
    grain = noise(p,430,metadata['seed']+2)
    flakes = noise(p,84,metadata['seed']+1)
    paint = design_paint()
    colour = np.where((owner==1)[:,None],paint,
                      np.where((owner==2)[:,None],[.72,.75,.77],[.23,.265,.26]))
    roughness = np.where(owner==2,.30+grain*.10,np.where(owner==1,.35+flakes*.20,.52))
    metallic = np.where(owner==1,.02,.45)
    height = (owner==1)*(grain-.5)*.00045
    height -= (owner==2)*np.maximum(grain-.55,0)*.00005
    nearest = distance_transform_edt(~occupied,return_distances=False,return_indices=True)
    atlas_height = np.zeros_like(occupied,np.float32)
    atlas_height[occupied] = height
    dy,dx = np.gradient(atlas_height[tuple(nearest)])
    density = metadata['texels_per_metre']
    normals = np.stack([-dx*density,dy*density,np.ones_like(dx)],-1)
    normals /= np.linalg.norm(normals,axis=-1,keepdims=True)
    albedo = np.zeros((*occupied.shape,4),np.float32)
    albedo[occupied] = np.column_stack([colour,np.zeros(len(p))])
    orm = np.zeros_like(albedo)
    orm[occupied] = np.column_stack([geometry[...,0][occupied],roughness,metallic,np.zeros(len(p))])
    write_atlas(directory/'as_built_albedo.png',albedo,nearest)
    write_atlas(directory/'as_built_normal.png',np.dstack([normals*.5+.5,np.ones_like(dx)]),nearest)
    write_atlas(directory/'as_built_orm.png',orm,nearest)
    selection = json.loads((SOURCE/'selection.json').read_text())
    pack(selection)
    print('Clean finish unchanged; aged atlas packed from complete generated face images',flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--fields',type=Path,required=True)
    args = parser.parse_args()
    bake(args.directory,args.fields)


if __name__=='__main__': main()
