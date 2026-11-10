"""Compose matched sofa cloth-colour and material-control captures."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'tmp/mat/sofa3'
FONT = ImageFont.load_default(size=24)


def pair(left, right, name, labels):
    sheet = Image.new('RGB', (2048, 1072), '#202020')
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate([left, right]):
        image = Image.open(path).convert('RGB').resize((1024, 1024), Image.Resampling.LANCZOS)
        sheet.paste(image, (index * 1024, 48))
        draw.text((index * 1024 + 18, 12), labels[index], font=FONT, fill='white')
    sheet.save(OUT / name)


def main():
    pair(OUT / 'aged-present-hero.png', ROOT / 'docs/art/quarters/sheets/sofa/aged-target.png', 'target-compare.png', ['Godot present light', 'Aged target version 2: colours/materials only'])
    pair(OUT / 'as_built-neutral-hero.png', ROOT / 'docs/art/quarters/sheets/sofa/hero.png', 'design-compare.png', ['Godot neutral light', 'Approved as-built design'])
    pair(OUT / 'debris-off.png', OUT / 'debris-on.png', 'debris-on-off.png', ['Floor debris disabled', 'Floor debris enabled'])
    before_after = Image.new('RGB', (2048, 2144), '#202020')
    draw = ImageDraw.Draw(before_after)
    for row, (state, light) in enumerate([('as_built', 'neutral'), ('aged', 'present')]):
        name = '%s-%s-hero.png' % (state, light)
        for col, directory in enumerate([OUT / 'baseline', OUT]):
            before_after.paste(Image.open(directory / name).convert('RGB'), (col * 1024, row * 1072 + 48))
            draw.text((col * 1024 + 16, row * 1072 + 12), '%s: %s' % (state, 'previous oatmeal brief' if col == 0 else 'approved cloth colours'), font=FONT, fill='white')
    before_after.save(OUT / 'before-after.png')
    closeup = Image.new('RGB', (2048, 2144), '#202020')
    draw = ImageDraw.Draw(closeup)
    for row, angle in enumerate(['detail', 'streaks']):
        for col, state in enumerate(['as_built', 'aged']):
            closeup.paste(Image.open(OUT / ('%s-neutral-%s.png' % (state, angle))).convert('RGB'), (col * 1024, row * 1072 + 48))
            draw.text((col * 1024 + 16, row * 1072 + 12), '%s, neutral, 0.6 m: %s' % (state, 'upholstery' if row == 0 else 'throw'), font=FONT, fill='white')
    closeup.save(OUT / 'closeup.png')
    print('COMPOSED cloth-colour comparisons', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    OUT = parser.parse_args().out.resolve()
    main()
