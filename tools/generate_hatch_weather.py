from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, zoom, maximum_filter

import argparse

parser = argparse.ArgumentParser(description="Generate the original round-7 hatch weather mask")
parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "assets/surfaces/hatch/leaf-weather.png")
args = parser.parse_args()
args.output.parent.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(73041)
h, w = 2048, 1024
y, x = np.mgrid[:h, :w].astype(np.float32)
x *= 1.08 / (w - 1)
y *= 2.4 / (h - 1)

def field(rows, cols):
    small = rng.random((rows, cols), dtype=np.float32)
    return zoom(small, (h / rows, w / cols), order=3)[:h, :w]

edge = np.minimum.reduce([x, 1.08-x, np.maximum(y-.08, 0), np.maximum(2.4-y, 0)])
cluster = np.exp(-edge*8.5)
for sx, sy in [(.215,.48),(.215,2.0),(.87,.40),(.87,1.17),(.87,2.07),(.54,1.2)]:
    cluster = np.maximum(cluster, .9*np.exp(-np.square((x-sx)/.18)-np.square((y-sy)/.20)))
patches = field(31, 17)
flakes = field(127, 61)*.53 + field(281, 139)*.31 + field(611, 307)*.16
threshold = .68 - .14*cluster + .075*(patches-.5)
paint = np.clip((flakes-threshold)*32+.45, 0, 1)
paint *= np.clip((patches-.30)*5, 0, 1)
paint *= np.clip(edge/.018, 0, 1)
bleed = np.clip(maximum_filter(paint, size=13)-paint,0,1)
bleed = gaussian_filter(bleed, 1.5)
drips = np.zeros_like(paint)
sources = [(a,b,.014,.88) for b in [.48,2.0] for a in [.09,.19,.35]]
sources += [(a,b,.013,.74) for b in [.40,1.17,2.07] for a in [.87,1.01]]
sources += [(.54,1.20,.040,.97),(.515,1.16,.009,.78),(.58,1.16,.009,.65)]
sources += [(a,b,.004,.23) for a in [.0525,1.0275] for b in np.arange(.32,2.22,.16)]
sources += [(a,2.345,.004,.33) for a in np.arange(.23,.88,.14)]
for i,(sx,sy,width,length) in enumerate(sources):
    width *= rng.uniform(.65,1.20)
    length *= rng.uniform(.75,1.2)
    dy = sy-y
    wander = .0025*np.sin(y*rng.uniform(8,19)+i)
    trail = np.exp(-np.square((x-sx+wander)/width))*np.clip(1-dy/length,0,1)**.65
    trail *= (dy>=0)*(.72+.28*field(37,9))
    drips = np.maximum(drips,trail)
grain = gaussian_filter(rng.random((h,w),dtype=np.float32),.65)
channels = np.stack([paint,np.clip((grain-.3)*2.5,0,1),drips,bleed],axis=-1)
Image.fromarray(np.uint8(np.clip(channels,0,1)*255)).save(args.output)
print('Unique 1024x2048 RGBA weather: paint/grain/runoff/flake-edge bleed; paint coverage',float((paint>.5).mean()))
