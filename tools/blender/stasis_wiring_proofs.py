"""Import engineered Y-up proof GLBs into Blender's native Z-up editable frame.

The importer performs the one Y-up to Z-up conversion; export_yup performs its
inverse. No extra asset rotation is applied. Source routes remain editable
non-exported curves alongside the material-grouped meshes.
"""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'assets/props/stasis-wiring'


def build():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=OUT/'proof-assemblies.json')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    manifest = json.loads(args.manifest.read_text())
    bpy.context.preferences.filepaths.save_version = 0
    for name, row in manifest['assemblies'].items():
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(ROOT/row['glb']))
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        if not meshes:
            raise RuntimeError('empty assembly import: '+name)
        for obj in meshes:
            if obj.name.startswith(('jacket','steel_pipe','bands')):
                for polygon in obj.data.polygons: polygon.use_smooth=True
        routes = bpy.data.collections.new('Editable route centerlines | not exported')
        bpy.context.scene.collection.children.link(routes)
        for route in row['routes']:
            curve = bpy.data.curves.new(route['id'],type='CURVE')
            curve.dimensions='3D'
            spline=curve.splines.new('POLY')
            spline.points.add(len(route['centerline_m'])-1)
            for point, xyz in zip(spline.points, route['centerline_m']):
                # Bay Y-up -> Blender Z-up, glTF +Z -> Blender -Y.
                point.co=(xyz[0],-xyz[2],xyz[1],1)
            obj=bpy.data.objects.new(route['id'],curve)
            routes.objects.link(obj)
            obj.hide_render=True
            obj.hide_set(True)
            obj['source_socket']=route.get('source_socket','retained rail clamp')
            obj['minimum_centerline_radius_m']=route['minimum_centerline_radius_m']
        bpy.context.scene['coordinate_frame']='Blender native Z-up; export glTF +Y-up'
        bpy.context.scene['issue']=110
        for image in bpy.data.images:
            if image.source=='FILE': image.pack()
        bpy.ops.object.select_all(action='DESELECT')
        for obj in meshes:
            obj.select_set(True)
        bpy.context.view_layer.objects.active=meshes[0]
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(name+'.blend')))
        bpy.ops.export_scene.gltf(filepath=str(ROOT/row['glb']),export_format='GLB',
            export_yup=True,use_selection=True,export_apply=True,
            export_cameras=False,export_lights=False,export_materials='EXPORT')


if __name__=='__main__':
    build()
