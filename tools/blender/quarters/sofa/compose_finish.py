"""Compose matched sofa finish and material-control captures."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'tmp/mat/sofa2'
FONT = ImageFont.load_default(size=24)


def pair(left, right, name, labels, crop=None):
    sheet = Image.new('RGB', (2048, 1072), '#202020')
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate([left, right]):
        image = Image.open(path).convert('RGB')
        if crop:
            image = image.crop(crop)
        image = image.resize((1024, 1024), Image.Resampling.LANCZOS)
        sheet.paste(image, (index * 1024, 48))
        draw.text((index * 1024 + 18, 12), labels[index], font=FONT, fill='white')
    sheet.save(OUT / name)


def main():
    pair(OUT / 'aged-present-hero.png', ROOT / 'docs/art/quarters/sheets/sofa/aged-target.png', 'target-compare.png', ['Godot present light', 'Approved aged target'])
    pair(OUT / 'as_built-neutral-hero.png', ROOT / 'docs/art/quarters/sheets/sofa/hero.png', 'design-compare.png', ['Godot neutral light', 'Approved as-built design'])
    pair(OUT / 'baseline/aged-neutral-rail.png', OUT / 'aged-neutral-rail.png', 'rail-closeup.png', ['Before: stacked rail charts', 'After: separate near-isotropic charts'])
    pair(OUT / 'debris-off.png', OUT / 'debris-on.png', 'debris-on-off.png', ['Floor debris disabled', 'Floor debris enabled'])
    pair(OUT / 'baseline/aged-present-hero.png', OUT / 'aged-present-hero.png', 'material-before-after.png', ['Previous materials, matched stage', 'Calibrated materials, matched stage'])
    closeup = Image.new('RGB', (2048, 2144), '#202020')
    draw = ImageDraw.Draw(closeup)
    for row, angle in enumerate(['detail', 'streaks']):
        for col, state in enumerate(['as_built', 'aged']):
            closeup.paste(Image.open(OUT / ('%s-neutral-%s.png' % (state, angle))).convert('RGB'), (col * 1024, row * 1072 + 48))
            draw.text((col * 1024 + 16, row * 1072 + 12), '%s, neutral, 0.6 m: %s' % (state, 'upholstery' if row == 0 else 'throw'), font=FONT, fill='white')
    closeup.save(OUT / 'closeup.png')
    print('COMPOSED finish comparisons', flush=True)


if __name__ == '__main__':
    main()
