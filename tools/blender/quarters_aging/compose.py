"""Compose unaged-left comparisons and four-view turntables without system fonts."""
import argparse
from pathlib import Path

from PIL import Image


def compose(out, props=('sofa', 'dress_uniform')):
    for prop in props:
        label = 'sofa' if prop == 'sofa' else 'tunic'
        before = Image.open(out / f'{prop}-before.png').convert('RGB')
        after = Image.open(out / f'{prop}-after.png').convert('RGB')
        if before.size != after.size:
            raise ValueError('Comparison cameras must have matching image dimensions')
        width, height = before.size
        sheet = Image.new('RGB', (width * 2, height))
        sheet.paste(before, (0, 0))
        sheet.paste(after, (width, 0))
        sheet.save(out / f'{label}-before-after.png')
        turntable = Image.new('RGB', (width * 2, height * 2))
        for index, angle in enumerate([30, 120, 210, 300]):
            image = Image.open(out / f'{prop}-turn-{angle}.png').convert('RGB')
            turntable.paste(image, ((index % 2) * width, (index // 2) * height))
        turntable.save(out / f'{label}-turntable.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--prop', choices=['sofa', 'dress_uniform'], action='append')
    args = parser.parse_args()
    compose(args.out, args.prop or ('sofa', 'dress_uniform'))
