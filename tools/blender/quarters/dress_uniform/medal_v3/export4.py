"""Export fitted selections even when their source collection is hidden."""
from pathlib import Path
import bpy


def export(objects,path):
    collections={c for obj in objects for c in obj.users_collection}
    hidden={c:c.hide_viewport for c in collections}
    for c in collections:
        c.hide_viewport=False
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.hide_select=False
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    assert set(bpy.context.selected_objects)==set(objects)
    bpy.ops.export_scene.gltf(filepath=str(path),use_selection=True,export_format='GLB',
        export_yup=True,export_materials='EXPORT',export_normals=True,export_texcoords=True)
    for c,value in hidden.items():
        c.hide_viewport=value


if __name__=='__main__':
    out=Path(__file__).resolve().parents[5]/'tmp/issue130-v3/fit1'
    bpy.ops.wm.open_mainfile(filepath=str(out/'medal-fitted.blend'))
    for kind in ['High','Low']:
        export([bpy.data.objects[p+'_'+kind] for p in ['Body','Loop','Bar']],out/('medal-'+kind.lower()+'.glb'))
    print('EXPORT4_COMPLETE',flush=True)
