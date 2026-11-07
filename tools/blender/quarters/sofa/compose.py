"""Compose the neutral captures without changing their aspect ratios."""
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'tmp/fit/sofa/cloth'
DESIGN = ROOT / 'docs/art/quarters/sheets/sofa/hero.png'


def tile(image, size=(800, 800)):
    image = ImageOps.contain(image.convert('RGB'), size, Image.Resampling.LANCZOS)
    result = Image.new('RGB', size, (216, 216, 216))
    result.paste(image, ((size[0]-image.width)//2, (size[1]-image.height)//2))
    return result


def sheet(images, name, columns):
    canvas = Image.new('RGB', (800*columns, 800*((len(images)+columns-1)//columns)), (216,216,216))
    for i, image in enumerate(images):
        canvas.paste(tile(image), ((i%columns)*800, (i//columns)*800))
    canvas.save(OUT / name)


def main():
    design = Image.open(DESIGN)
    sheet([design, Image.open(OUT/'fit-hero.png')], 'compare-hero.png', 2)
    # Same image-right arm as the positive-X arm in the fixed hero camera.
    crop = design.crop((int(design.width*.53), int(design.height*.28), design.width, int(design.height*.94)))
    sheet([crop, Image.open(OUT/'fit-detail.png')], 'compare-detail.png', 2)
    sheet([Image.open(OUT/f'turn-{a}.png') for a in (30,120,210,300)], 'turntable.png', 2)


if __name__ == '__main__':
    main()
