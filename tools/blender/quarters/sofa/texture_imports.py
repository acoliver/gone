"""Keep sofa colour, cutout alpha and packed mask roles independent on import."""
import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[4]
ASSETS = ROOT / 'assets/props/quarters/sofa'


def main():
    template = (ROOT / 'assets/props/quarters/storage_locker_module/as_built_albedo.png.import').read_text()
    for file in sorted(ASSETS.glob('*.png')):
        path = 'res://' + file.relative_to(ROOT).as_posix()
        imported = 'res://.godot/imported/' + file.name + '-' + hashlib.md5(path.encode()).hexdigest() + '.ctex'
        text = re.sub(r'^uid=.*\n', '', template, flags=re.MULTILINE)
        text = re.sub(r'res://\.godot/imported/[^"\]]+\.ctex', imported, text)
        text = text.replace('res://assets/props/quarters/storage_locker_module/as_built_albedo.png', path)
        text = text.replace('detect_3d/compress_to=1', 'detect_3d/compress_to=0')
        file.with_suffix('.png.import').write_text(text)


if __name__ == '__main__':
    main()
