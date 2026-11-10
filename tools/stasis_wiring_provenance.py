"""Content binding for build inputs, protected baselines and native readbacks."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT/os.environ.get('STASIS_WIRING_RESULTS','tmp/verify-stasis-wiring/production-corrected')
CONTEXT = RESULTS/'context.json' if 'STASIS_WIRING_RESULTS' in os.environ else ROOT/'tmp/verify-stasis-wiring/production-install/context.json'
ASSETS = ROOT/'assets/props/stasis-wiring'


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot(paths, root=ROOT):
    return {str(Path(p).relative_to(root)):fingerprint(p) for p in sorted(set(paths))}


def verify(record, root=ROOT):
    actual = snapshot([root/p for p in record],root)
    mismatches = [p for p in record if actual[p] != record[p]]
    if mismatches:
        raise ValueError('fingerprint mismatch: '+', '.join(mismatches))
    return actual


def implementation_inputs():
    paths = [ROOT/'project.godot', ROOT/'main.tscn', ROOT/'tests/run_tests.gd', ROOT/'tests/runner_guard_test.gd']
    for directory in ['app','sim','harness']:
        paths.extend((ROOT/directory).glob('*.gd'))
        paths.extend((ROOT/directory).glob('*.gdshader'))
    for pattern in ['*stasis_wiring*.py','*stasis_wiring*.gd','*seat*.py','*seat*.gd','blender/stasis_wiring*.py']:
        paths.extend((ROOT/'tools').glob(pattern))
    paths.extend((ROOT/'tests').glob('*.gd'))
    paths.extend([ROOT/'tools/test_seat_rail.py', ROOT/'tools/run_seat_production_tests.gd',ROOT/'tools/check_seat_production.py'])
    paths.extend(p for p in (ROOT/'assets/props').rglob('*.glb') if not p.is_relative_to(ASSETS))
    paths.extend([ASSETS/'sockets.json',ASSETS/'provenance.json',ASSETS/'stasis-wiring-enclosure.glb',
                  ROOT/'assets/props/pod/pod-v4.glb',ROOT/'assets/props/bay-ceiling/intact.glb',
                  ROOT/'tools/build_stasis_wiring.py',ROOT/'tools/build_supported_transition.py',
                  ROOT/'tools/capture_seat_rail_readability.gd', ROOT/'tools/seat_rail_context_checks.py',
                  ASSETS/'proof-assemblies.json',ASSETS/'supported-transition-aligned.json',
                  CONTEXT])
    paths.extend(p for p in (ASSETS/'seat-rail').rglob('*') if p.is_file() and p.suffix not in ['.import','.uid'])
    return paths


def establish_protected_baseline():
    # These files are not task outputs or implementation files being corrected.
    paths = [p for p in (ROOT/'app').glob('*.gd') if p.name!='stasis_wiring.gd']
    paths += list((ROOT/'app').glob('*.gdshader'))
    paths += list((ROOT/'sim').glob('*.gd'))
    paths += [ROOT/'tests/run_tests.gd',ROOT/'tests/runner_guard_test.gd',
              ASSETS/'stasis-wiring-enclosure.glb', ASSETS/'sockets.json', ASSETS/'provenance.json',
              ROOT/'tools/seat_rail.py',ROOT/'tools/blender/seat_rail.py']
    paths += [p for p in (ASSETS/'seat-rail').rglob('*') if p.is_file() and p.name!='manifest.json' and p.suffix not in ['.import','.uid']]
    paths += list((ROOT/'art-source/stasis-wiring/seat-rail').glob('*'))
    paths += list((ROOT/'assets/props/pod').glob('*.glb'))
    paths += list((ROOT/'assets/props/bay-ceiling').glob('*.glb'))
    RESULTS.mkdir(parents=True,exist_ok=True)
    path = RESULTS/'protected-before.json'
    if path.exists():
        verify(json.loads(path.read_text()))
    else:
        path.write_text(json.dumps(snapshot(paths),indent=2)+'\n')
    return json.loads(path.read_text())


def verify_capture(data, root=ROOT):
    before, after = data['fingerprints_before'], data['fingerprints_after']
    if before != after:
        raise ValueError('capture inputs changed during rendering')
    verify(before,root)
    if data['protected_before'] != data['protected_after']:
        raise ValueError('protected inputs changed during capture')
    verify(data['protected_before'],root)
    verify(data['readback_sha256'],root)
    for shot in data['captures']:
        if fingerprint(shot['path']) != shot['sha256']:
            raise ValueError('PNG fingerprint mismatch: '+shot['path'])
    return True


if __name__ == '__main__':
    print(json.dumps(establish_protected_baseline(),indent=2))
