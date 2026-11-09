"""Re-settle the remembered quilt while retaining the baked pressure shells."""
import json
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build import ASSETS, collision, export, material, mesh_points, pressure_shell, save, settle_quilt


def main():
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'bed-soft-working.blend'))
    record = json.loads((HERE / 'simulation.json').read_text())
    mattress = bpy.data.objects['Mattress']
    material('CottonTicking', (.50, .46, .37))
    material('CottonPillow', (.78, .76, .70))
    for name in ('Pillow_L', 'Pillow_R'):
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    top = float(mesh_points(mattress)[:, 2].max())
    for name, x in (('Pillow_L', -.355), ('Pillow_R', .355)):
        _, record[name] = pressure_shell(name, (.65, .43, .155), (x, .70, top + .10), (12, 10, 4), mattress)
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
