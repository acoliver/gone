"""Fail before capture if Godot's native garment scene came from an older GLB."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[4]


def verify():
    result = []
    for name in ('dress_uniform', 'dress_uniform_aged'):
        asset = ROOT / 'assets/props/quarters' / (name + '.glb')
        settings = asset.with_suffix('.glb.import').read_text()
        native_path = re.search(r'^path="res://([^"]+)"', settings, re.MULTILINE).group(1)
        native = ROOT / Path(native_path).with_suffix('.md5')
        stored = re.search(r'source_md5="([^"]+)"', native.read_text()).group(1)
        current = hashlib.md5(asset.read_bytes()).hexdigest()
        if stored != current:
            raise ValueError(f'{asset.name}: stale native import {stored}; source is {current}')
        result.append(dict(asset=str(asset.relative_to(ROOT)), native=str(native.relative_to(ROOT)), source_md5=current))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify()
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: both native garment imports match current source GLBs')
