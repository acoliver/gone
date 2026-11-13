"""Paths and fixed inputs for the image-derived medal material comparison."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
FIT = ROOT / 'tmp/issue130-v3/fit2'
OUT = ROOT / 'tmp/issue130-v3/tex1'
HY = Path('/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d')
INPUT = ROOT / 'tmp/issue130-regen2/inputs/c01-seed1306201.png'
REFDIR = ROOT / 'tmp/issue130-reference/photo-20261111-01'
REFS = {
    'remembered': {'front': REFDIR / 'remembered-front-seed1304102.png',
                   'oblique': REFDIR / 'remembered-oblique-seed1304201.png'},
    'present': {'front': REFDIR / 'present-front-seed1304101.png',
                'oblique': REFDIR / 'present-oblique-seed1304201.png'},
}
SIZE = 2048
for directory in [OUT, OUT / 'paint', OUT / 'bakes', OUT / 'projection', OUT / 'renders', OUT / 'sheets']:
    directory.mkdir(parents=True, exist_ok=True)
