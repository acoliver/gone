"""Re-settle the remembered quilt while retaining the baked pressure shells."""
import json
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build import ASSETS, bake_origin, collision, drop_to, export, material, mesh_points, save, settle_quilt


def main():
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'bed-soft-working.blend'))
    record = json.loads((HERE / 'simulation.json').read_text())
    mattress = bpy.data.objects['Mattress']
    material('CottonTicking', (.50, .46, .37))
    material('CottonPillow', (.78, .76, .70))
    for name in ('Pillow_L', 'Pillow_R'):
        obj = bpy.data.objects[name]
        p = mesh_points(obj)
        low, high = p[:, 2].min(), p[:, 2].max()
        for vertex in obj.data.vertices:
            vertex.co.z = low + (vertex.co.z - low) * .12 / (high - low)
        drop_to(obj, mattress)
        bake_origin(obj)
        record[name]['finished_height_m'] = .12
        record[name]['bounds_native_m'] = [mesh_points(obj).min(0).tolist(), mesh_points(obj).max(0).tolist()]
    bpy.data.objects.remove(bpy.data.objects['Quilt'], do_unlink=True)
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and (obj.get('bed_frame') or obj.name in ('Mattress', 'Pillow_L', 'Pillow_R', 'SupportFloor')):
            collision(obj, .0005)
    record['Quilt'] = settle_quilt(mattress)
    (HERE / 'simulation.json').write_text(json.dumps(record, indent=2) + '\n')
    save(HERE / 'bed-soft-working.blend', record)
    export(ASSETS / 'bed_soft.glb')


if __name__ == '__main__':
    main()
