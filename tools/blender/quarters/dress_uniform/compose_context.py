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


def target_match(directory, target):
    hero = Image.open(directory/'after-hero.png').convert('RGB')
    reference = Image.open(target).convert('RGB')
    reference.thumbnail((hero.width, hero.height), Image.Resampling.LANCZOS)
    result = Image.new('RGB', (hero.width*2, hero.height+40), (25, 27, 26))
    result.paste(hero, (0, 40))
    result.paste(reference, (hero.width+(hero.width-reference.width)//2,
                             40+(hero.height-reference.height)//2))
    draw = ImageDraw.Draw(result)
    draw.text((20, 12), '1000 years | in-locker candidate', fill='white')
    draw.text((hero.width+20, 12), 'Fixed overall-look target | placement follows plan', fill='white')
    result.save(directory/'tunic-target-match.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--target', type=Path)
    args = parser.parse_args()
    compose(args.out)
    if args.target:
        target_match(args.out, args.target)
