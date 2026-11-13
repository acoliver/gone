"""Set bounded GPU storage, mipmaps and explicit colour/data roles for baked maps."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def configure(path):
    settings = path.with_suffix(path.suffix+'.import')
    source = 'res://'+path.relative_to(ROOT).as_posix()
    text = settings.read_text() if settings.exists() else (
        '[remap]\n\nimporter="texture"\ntype="CompressedTexture2D"\n\n'
        f'[deps]\n\nsource_file="{source}"\n\n[params]\n')
    params = {'compress/mode': '2', 'compress/high_quality': 'true',
              'compress/normal_map': '1' if path.stem.endswith('_normal') else '2',
              'mipmaps/generate': 'true', 'process/fix_alpha_border': 'false',
              'process/premult_alpha': 'false', 'process/size_limit': '0'}
    for name, value in params.items():
        pattern = '^'+re.escape(name)+'=.*$'
        if re.search(pattern, text, re.MULTILINE):
            text = re.sub(pattern, name+'='+value, text, flags=re.MULTILINE)
        else:
            text += name+'='+value+'\n'
    settings.write_text(text)


if __name__ == '__main__':
    for path in sorted((ROOT / 'assets/props/quarters/steel').glob('*/*.png')):
        configure(path)
