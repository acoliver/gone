"""Validate capture readback and summarize observed frames, not isolated GPU speed."""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from stasis_wiring_provenance import verify_capture, fingerprint

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'tmp/verify-stasis-wiring/production-corrected'


def frames(rows):
    intervals = np.diff([r['wall_usec'] for r in rows])/1000.
    return {'samples': len(rows), 'median_wall_frame_ms': float(np.median(intervals)),
            'p95_wall_frame_ms': float(np.percentile(intervals, 95)),
            'median_process_ms': float(np.median([r['process_ms'] for r in rows])),
            'median_physics_ms': float(np.median([r['physics_ms'] for r in rows])),
            'draw_calls_range': [min(r['draw_calls'] for r in rows), max(r['draw_calls'] for r in rows)],
            'primitives_range': [min(r['primitives'] for r in rows), max(r['primitives'] for r in rows)]}


def main():
    data = json.loads((OUT/'capture-manifest.json').read_text())
    verify_capture(data)
    assert data['protected_before']==data['protected_after']
    assert data['source_preserved'] is True
    opening = json.loads((OUT/'normal-opening-result.json').read_text())
    assert opening['standing_reached'] and opening['power_calls'] == opening['teleports'] == 0
    ordinary = {Path(s['path']).stem:s for s in data['captures'] if not s['diagnostic_only']}
    awake = ordinary['normal-opening-awake-in-pod']
    rising = ordinary['normal-opening-get-up']
    assert rising['phase'] == 'ExitingPod'
    assert rising['camera_world_m'][1] > awake['camera_world_m'][1]+.05
    report = {'scope': '1280x900 native Metal main.tscn with concurrent sibling Godot jobs. Wall intervals include harness/forced draw, CPU scheduling and readback. No isolated FPS, GPU timing or before/after performance claim.',
              'capture_manifest_sha256':fingerprint(OUT/'capture-manifest.json'),
              'verified_snapshot_sha256':data['fingerprints_before'],
              'normal_opening': frames(json.loads((OUT/'normal-frame-performance.json').read_text())),
              'diagnostic_fixed_camera': {}, 'readback': []}
    for shot in data['captures']:
        path = Path(shot['path'])
        image = np.asarray(Image.open(path).convert('RGB'))
        assert image.shape == (900, 1280, 3), path
        if not shot['diagnostic_only']:
            assert shot['eyes']['lid_openness'] >= .3 and shot['wake_overlay_visible'], path
        report['readback'].append({'path': str(path), 'bytes': path.stat().st_size, 'sha256':fingerprint(path),
                                  'channel_range': int(image.max())-int(image.min()),
                                  'variance': float(image.var())})
        assert image.var() > 0, path
        if 'fixed_camera_frames' in shot:
            report['diagnostic_fixed_camera'][path.stem] = frames(shot['fixed_camera_frames'])
    report['normal_png_count'] = sum(not shot['diagnostic_only'] for shot in data['captures'])
    report['diagnostic_png_count'] = sum(shot['diagnostic_only'] for shot in data['captures'])
    assert report['normal_png_count']==6 and report['diagnostic_png_count']==10
    report['visual_review'] = 'Image-comparer remains responsible for appearance; nonuniform readback is not approval.'
    (OUT/'performance-readback.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'readback'},indent=2))


if __name__ == '__main__':
    main()
