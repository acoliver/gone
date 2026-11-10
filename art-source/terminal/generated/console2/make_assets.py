from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage

root = Path(__file__).resolve().parent
inputs = root / 'inputs'
outputs = root / 'outputs'

for source in sorted(outputs.glob('*.png')):
    if source.name.endswith('.metadata.png'):
        continue
    image = Image.open(source).convert('RGB')
    rgb = np.asarray(image, dtype=np.float32)
    h, w = rgb.shape[:2]
    corners = np.array([rgb[0, 0], rgb[0, w-1], rgb[h-1, 0], rgb[h-1, w-1]])
    bg = np.median(corners, axis=0)
    distance = np.sqrt(np.sum((rgb - bg) ** 2, axis=2))
    foreground = distance > 34.0
    labels, count = ndimage.label(foreground)
    if count:
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        foreground = labels == sizes.argmax()
    foreground = ndimage.binary_fill_holes(foreground)
    foreground = ndimage.binary_dilation(foreground, iterations=2)
    alpha = Image.fromarray((foreground * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=1.0))
    rgba = image.convert('RGBA')
    rgba.putalpha(alpha)
    rgba.save(inputs / f'{source.stem}-rgba.png')

font = ImageFont.load_default()
def sheet(kind, names, thumb_size):
    cell_w, cell_h = thumb_size[0] + 32, thumb_size[1] + 58
    sheet = Image.new('RGB', (cell_w * 2, cell_h * 2), (238, 238, 238))
    draw = ImageDraw.Draw(sheet)
    for i, name in enumerate(names):
        x, y = (i % 2) * cell_w, (i // 2) * cell_h
        label = name.replace('.png', '')
        draw.text((x + 12, y + 8), label, fill=(20, 20, 20), font=font)
        tile = Image.new('RGBA', thumb_size, (235, 235, 235, 255))
        obj = Image.open(inputs / f'{label}-rgba.png').convert('RGBA')
        obj.thumbnail((thumb_size[0] - 12, thumb_size[1] - 12), Image.Resampling.LANCZOS)
        tile.alpha_composite(obj, ((thumb_size[0] - obj.width) // 2, (thumb_size[1] - obj.height) // 2))
        sheet.paste(tile.convert('RGB'), (x + 16, y + 34))
    sheet.save(root / f'{kind}-sheet.png')

sheet('console', [f'console-s{s}' for s in range(510, 514)], (360, 480))
sheet('keyboard', [f'keyboard-s{s}' for s in range(520, 524)], (480, 360))
print('Generated RGBA cutouts and contact sheets')
