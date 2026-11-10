"""Compare diagnostic contour controls without changing acceptance thresholds."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.measure import approximate_polygon

from diagnostic_labels import decode_labels
from lip_metrics import contour_runs, polyline_metrics


def measure(directory, scale):
    cameras = json.loads((directory/'tunic-cameras.json').read_text())
    values = []
    for camera in ['hero-labels', 'labels']:
        labels = decode_labels(np.array(Image.open(directory/f'tunic-{camera}.png').convert('RGB')))
        cloth = (labels == 1) | (labels == 2)
        for tear, sides in cameras[camera]['tear_lips'].items():
            for side, data in sides.items():
                runs = contour_runs(cloth, data['segments_yx'], data['radius_px'],
                                    competitors=[s for other, d in sides.items() if other != side for s in d['segments_yx']],
                                    occluded=(labels == 4) | (labels == 5))
                for run in runs:
                    result = polyline_metrics(run/scale)
                    values.append(dict(camera=camera, tear=tear, side=side, **result))
    return values


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = {name: measure(args.out/name, 2 if name == 'double' else 1)
              for name in ['normal', 'double', 'opaque', 'no-fringe']}
    (args.out/'measurements.json').write_text(json.dumps(report, indent=2)+'\n')
    for name, values in report.items():
        eligible = [v for v in values if v['length_px'] >= 64]
        print(name, 'runs', len(values), 'max straight', max(v['longest_straight_run_px'] for v in values),
              'dimensions', [(v['camera'], v['tear'], v['side'], round(v['contour_dimension'], 4)) for v in eligible])
