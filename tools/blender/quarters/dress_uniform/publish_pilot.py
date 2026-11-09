"""Publish only the explicitly accepted tunic pilot and its editable source."""
import argparse
import json
from pathlib import Path
import shutil
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import ROOT
from common import export

HERE = Path(__file__).resolve().parent


def export_source(output):
    bpy.ops.wm.open_mainfile(filepath=str(HERE/'tunic-pilot.blend'))
    export(output)


def publish(candidate, dust_report):
    gates = json.loads((candidate/'gates.json').read_text())
    hem = json.loads((candidate/'hem-boundary-check.json').read_text())
    if not hem['pass'] or hem['upper_bound_m'] > .0015:
        raise ValueError('Extended hem exceeds the unchanged reduction-error limit')
    gates['G32']['extended_hem'] = hem
    failures = {key for key, item in gates.items() if key.startswith('G') and not item['pass_gate']}
    if failures != {'G3', 'G6'} or not gates['armhole_opening']['pass_gap']:
        raise ValueError(f'Pilot exception allows only G3/G6 failures, got {failures}')
    seating = json.loads((candidate/'attachment-audit.json').read_text())
    dust = json.loads(dust_report.read_text())
    if not seating['all_bases_within_2mm'] or not dust['pass']:
        raise ValueError('Pilot seating or rendered dust visibility failed')
    raw = (candidate/'candidate.glb').read_bytes()
    if raw != (candidate/'repeat.glb').read_bytes():
        raise ValueError('Candidate does not reproduce byte-identically')
    bpy.ops.wm.open_mainfile(filepath=str(candidate/'finished.blend'))
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH' or not obj.get('aged_export'):
            bpy.data.objects.remove(obj, do_unlink=True)
    materials = {mat for obj in bpy.context.scene.objects for mat in obj.data.materials}
    for mat in materials:
        nodes = mat.node_tree.nodes
        keep = {nodes.get('Material Output')}
        pending = list(keep)
        while pending:
            node = pending.pop()
            for socket in node.inputs:
                for link in socket.links:
                    if link.from_node not in keep:
                        keep.add(link.from_node)
                        pending.append(link.from_node)
        for node in list(nodes):
            if node not in keep:
                nodes.remove(node)
    bpy.data.orphans_purge(do_recursive=True)
    textures = ROOT/'assets/props/quarters/dress_uniform'
    textures.mkdir(exist_ok=True)
    images = {node.image for mat in materials for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE'}
    copied = {}
    for image in images:
        name = Path(image.filepath_raw).name
        data = bytes(image.packed_file.data)
        destination = textures/name
        if name in copied and copied[name] != data:
            raise ValueError(f'Tunic texture name collision: {name}')
        copied[name] = data
        destination.write_bytes(data)
        image.filepath_raw = '//../../../../assets/props/quarters/dress_uniform/'+name
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'tunic-pilot.blend'))
    export(candidate/'source-export.glb')
    export_source(candidate/'source-repeat.glb')
    if raw != (candidate/'source-export.glb').read_bytes() or raw != (candidate/'source-repeat.glb').read_bytes():
        raise ValueError('Pruned standalone source changed exported bytes')
    shutil.copyfile(candidate/'candidate.glb', ROOT/'assets/props/quarters/dress_uniform_aged.glb')
    gates['pilot_publication'] = dict(allowed=True, exceptions=['G3', 'G6'],
                                     authority='Andrew accepts pass12 geometry as the pilot; thresholds unchanged',
                                     byte_identical=True)
    (HERE/'pilot-gates.json').write_text(json.dumps(gates, indent=2)+'\n')
    (HERE/'pilot-seating.json').write_text(json.dumps(seating, indent=2)+'\n')
    (HERE/'pilot-dust.json').write_text(json.dumps(dust, indent=2)+'\n')
    print('PUBLISHED: standalone source and game GLB are byte-identical to the measured candidate')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', type=Path)
    p.add_argument('--dust-report', type=Path)
    p.add_argument('--export-only', type=Path)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    if a.export_only:
        export_source(a.export_only.resolve())
    else:
        if not a.candidate or not a.dust_report:
            p.error('--candidate and --dust-report are required for publication')
        publish(a.candidate.resolve(), a.dust_report.resolve())
