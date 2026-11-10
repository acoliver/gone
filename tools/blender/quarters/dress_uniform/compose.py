"""Lay out the neutral renders beside the design at readable matching scales."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[4]
SCRATCH = ROOT / 'tmp/fit/tunic/sim'
DESIGN = ROOT / 'docs/art/quarters/sheets/dress_uniform/hero.png'


def cell(image, size, caption):
    result = Image.new('RGB', (size[0], size[1] + 36), '#dcdcdc')
    fitted = ImageOps.contain(image.convert('RGB'), size)
    result.paste(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    ImageDraw.Draw(result).text((16, size[1] + 10), caption, fill='#222222')
    return result


def sheet(path, cells):
    result = Image.new('RGB', (sum(c.width for c in cells), max(c.height for c in cells)), '#dcdcdc')
    x = 0
    for c in cells:
        result.paste(c, (x, 0))
        x += c.width
    result.save(path)


def main():
    design = Image.open(DESIGN)
    render = Image.open(SCRATCH / 'hero-render.png')
    sheet(SCRATCH / 'compare-hero.png', [cell(design, (900, 1000), 'Design'), cell(render, (900, 1000), 'Sewn wool simulation')])
    sheet(SCRATCH / 'turntable.png', [cell(Image.open(SCRATCH / f'turn-{a}.png'), (700, 700), f'{a} degrees') for a in [30, 120, 210, 300]])
    w, h = design.size
    crop = design.crop((int(.26 * w), int(.18 * h), int(.75 * w), int(.52 * h)))
    crop.save(SCRATCH / 'design-detail-crop.png')
    sheet(SCRATCH / 'compare-detail.png', [cell(crop, (1000, 1000), 'Design: collar and breast details'), cell(Image.open(SCRATCH / 'detail-render.png'), (1000, 1000), 'Simulation: collar and breast details')])


if __name__ == '__main__':
    main()
