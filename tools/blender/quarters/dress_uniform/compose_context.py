"""Pair unchanged-lighting locker captures with explicit state labels."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def compose(directory):
    for view, name in [('hero', 'tunic-in-locker-before-after.png'),
                       ('closeup', 'tunic-in-locker-closeup.png'),
                       ('heap', 'tunic-in-locker-heap.png')]:
        before = Image.open(directory/f'before-{view}.png').convert('RGB')
        after = Image.open(directory/f'after-{view}.png').convert('RGB')
        result = Image.new('RGB', (before.width+after.width, max(before.height, after.height)+40), (25, 27, 26))
        result.paste(before, (0, 40))
        result.paste(after, (before.width, 40))
        draw = ImageDraw.Draw(result)
        draw.text((20, 12), 'Unaged | identical locker lighting', fill='white')
        draw.text((before.width+20, 12), '1000 years | identical locker lighting', fill='white')
        result.save(directory/name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    compose(parser.parse_args().out)
