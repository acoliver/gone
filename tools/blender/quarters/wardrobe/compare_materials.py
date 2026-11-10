"""Pair wardrobe and accepted locker at the capture's unchanged physical scale."""
import shutil

from PIL import Image

from materials import SCRATCH, SOURCE


def main():
    directory = SCRATCH / 'render'
    for view in ('hero', 'front', 'top', 'roof', 'detail', 'hardware', 'trim'):
        sheet = Image.new('RGB', (2048, 2048))
        for y, state in enumerate(('as_built', 'aged')):
            for x, prop in enumerate(('wardrobe', 'storage_locker_module')):
                image = Image.open(directory / f'{prop}-{state}-{view}.png').convert('RGB')
                if image.size != (1024, 1024):
                    raise ValueError(f'capture dimensions changed: {prop}/{state}/{view}')
                sheet.paste(image, (x*1024, y*1024))
        sheet.save(directory / f'matched-{view}.png')
        sheet.save(SOURCE / f'matched-{view}.png')
    for name in ('wardrobe-aged-roof-regions.png', 'wardrobe-aged-trim-materials.png', 'capture.json'):
        shutil.copyfile(directory / name, SOURCE / name)
    print('Matched sheets: wardrobe left, locker right; as-built top, aged bottom')


if __name__ == '__main__':
    main()
