"""Require the ten fixed overview captures to retain their reference display luma."""
from pathlib import Path
import argparse
import json

from PIL import Image, ImageStat

BASELINE = Path(__file__).resolve().parents[1] / 'tests/fixtures/overviews-219a257.json'


def within_limit(actual, reference):
    return abs(actual - reference) <= reference * 0.15


def check(directory, baseline=BASELINE):
    directory = Path(directory)
    reference = json.loads(Path(baseline).read_text())
    records = json.loads((directory / 'views.json').read_text())
    views = {view['name']: view for view in records}
    failures = []
    if len(views) != len(records):
        failures.append('duplicate view names')
    rows = []
    for expected in reference['views']:
        name = expected['name']
        if name not in views:
            failures.append(f'{name}: missing view')
            continue
        if any(views[name][field] != expected[field] for field in ['eye', 'target']):
            failures.append(f'{name}: camera differs from 219a257')
        path = directory / (name + '.png')
        if not path.is_file():
            failures.append(f'{name}: missing image')
            continue
        with Image.open(path) as image:
            if list(image.size) != reference['resolution']:
                failures.append(f'{name}: resolution differs from 219a257')
                continue
            luma = ImageStat.Stat(image.convert('L')).mean[0]
        before = expected['mean_display_luma']
        change = 100 * (luma / before - 1)
        rows.append(dict(name=name, baseline=before, actual=luma, change_percent=change))
        if not within_limit(luma, before):
            failures.append(f'{name}: display luma {before:.4f} -> {luma:.4f} ({change:+.2f}%) exceeds 15%')
    return rows, failures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    rows, failures = check(args.directory)
    for row in rows:
        print('{name}: {baseline:.4f} -> {actual:.4f} ({change_percent:+.2f}%)'.format(**row))
    for failure in failures:
        print('FAIL', failure)
    if args.out:
        args.out.write_text(json.dumps(dict(views=rows, failures=failures), indent=2) + '\n')
    raise SystemExit(1 if failures else 0)
