"""Place full-resolution matched captures beside each other without rescaling."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'docs/art/quarters/sheets/bed_soft'


def main(powder_control=False):
    columns = [(OUT, 'aged-before', 'Before'), (OUT, 'aged', 'After')]
    filename = 'dry-decay-before-after.png'
    if powder_control:
        columns = [(ROOT / 'tmp/bed_soft2/powder-off', 'aged', 'Powder OFF'),
                   (OUT, 'aged', 'Powder ON')]
        filename = 'powder-controls.png'
    sheet = Image.new('RGB', (2560, 2080), (228, 224, 216))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=24)
    for row, view in enumerate(('doorway', 'three_quarter')):
        for column, (folder, prefix, label) in enumerate(columns):
            image = Image.open(folder / f'{prefix}-{view}.png').convert('RGB')
            assert image.size == (1280, 1000)
            x, y = column * 1280, row * 1040
            draw.text((x + 16, y + 8), f'{label}: {view}',
                      fill=(25, 25, 25), font=font)
            sheet.paste(image, (x, y + 40))
    sheet.save(OUT / filename)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--powder-control', action='store_true')
    main(parser.parse_args().powder_control)
