"""Separate rendered alpha, fibre and resolution effects on measured tear lips."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_aging import diagnostics


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    for name, scale, control in [('normal', 1, None), ('double', 2, None),
                                  ('opaque', 1, 'opaque'), ('no-fringe', 1, 'no-fringe')]:
        out = args.out/name
        out.mkdir(parents=True, exist_ok=True)
        diagnostics(args.input.resolve(), out.resolve(), modes=['hero-labels', 'labels'],
                    scale=scale, control=control)
