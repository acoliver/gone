"""Keep the reference bed legible beside both exported-asset render angles."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[4]
ART = ROOT / 'docs/art/quarters'
SHEETS = ART / 'sheets/bed_soft'
BOXES = {'remembered': (315, 478, 542, 680), 'aged': (315, 478, 535, 728)}


def main():
    font = ImageFont.load_default(size=22)
    for state, box in BOXES.items():
        concept = Image.open(ART / ('concept-now.png' if state == 'aged' else 'concept-remembered.png')).convert('RGB')
        reference = concept.crop(box)
        reference.save(SHEETS / f'{state}-reference-bed.png')
        panels = [(reference, 'Concept bed (local image-comparer crop)'),
                  (concept if state == 'aged' else Image.open(SHEETS / 'hero.png'),
                   'Full present-day concept' if state == 'aged' else 'Selected soft-goods design'),
                  (Image.open(SHEETS / f'{state}-doorway.png'), 'Exported asset: doorway'),
                  (Image.open(SHEETS / f'{state}-three_quarter.png'), 'Exported asset: three-quarter')]
        sheet = Image.new('RGB', (1200, 1040), (228, 224, 216))
        draw = ImageDraw.Draw(sheet)
        for index, (image, label) in enumerate(panels):
            x, y = (index % 2) * 600, (index // 2) * 520
            draw.text((x + 14, y + 10), label, fill=(25, 25, 25), font=font)
            fitted = ImageOps.contain(image.convert('RGB'), (580, 470))
            sheet.paste(fitted, (x + (600 - fitted.width) // 2, y + 44 + (470 - fitted.height) // 2))
        sheet.save(SHEETS / f'{state}-comparison.png')


if __name__ == '__main__':
    main()
