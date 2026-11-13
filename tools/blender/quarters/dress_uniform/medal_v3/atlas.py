"""Shared, non-flipping surface unwrap for the medal's 2048 baking atlas."""
from pathlib import Path
import json
import math
import bpy

SOURCE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[5]
OUT=ROOT/'tmp/issue130-v3/fit1'


def isolate_overlapping_triangles(objects):
    triangles=[]
    for obj in objects:
        obj.data.calc_loop_triangles()
        uv=obj.data.uv_layers.active.data
        for t in obj.data.loop_triangles:
            triangles.append((obj,t.polygon_index,list(t.loops),
                              [uv[i].uv.copy() for i in t.loops]))
    grid={}
    conflicts=set()
    tested=set()
    def overlaps(a,b):
        for polygon in [a,b]:
            for i in range(3):
                p,q=polygon[i],polygon[(i+1)%3]
                dx,dy=float(q.x)-float(p.x),float(q.y)-float(p.y)
                length=math.hypot(dx,dy)
                nx,ny=-dy/length,dx/length
                pa=[float(v.x)*nx+float(v.y)*ny for v in a]
                pb=[float(v.x)*nx+float(v.y)*ny for v in b]
                if min(max(pa),max(pb))-max(min(pa),min(pb)) <= 1e-10:
                    return False
        return True
    for i,(_,_,_,uv) in enumerate(triangles):
        lo=[math.floor(min(v[j] for v in uv)*64) for j in range(2)]
        hi=[math.floor(max(v[j] for v in uv)*64) for j in range(2)]
        for x in range(lo[0],hi[0]+1):
            for y in range(lo[1],hi[1]+1):
                cell=grid.setdefault((x,y),[])
                for other in cell:
                    pair=(other,i)
                    if pair not in tested:
                        tested.add(pair)
                        if overlaps(triangles[other][3],uv):
                            conflicts.update(pair)
                cell.append(i)
    # A few concave charts can retain internal overlaps after SLIM. Detach only
    # the participating triangles, retaining their existing surface unwrap.
    for n,index in enumerate(sorted(conflicts)):
        obj,polygon,loops,uv=triangles[index]
        assert len(obj.data.polygons[polygon].vertices)==3
        for loop,co in zip(loops,uv):
            obj.data.uv_layers.active.data[loop].uv=(co.x+2+n*.01,co.y)
    for obj in objects:
        obj['uv_detached_conflict_triangles']=sum(triangles[i][0]==obj for i in conflicts)
    return len(conflicts)


def unwrap(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
        for edge in obj.data.edges:
            edge.use_seam=False
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(42), island_margin=.006,
                            margin_method='FRACTION', area_weight=.1, scale_to_bounds=False)
    # Projection supplies chart boundaries. SLIM unfolds those actual surfaces
    # instead of leaving concave relief folded over itself in planar projection.
    bpy.ops.uv.seams_from_islands(mark_seams=True, mark_sharp=False)
    bpy.ops.uv.unwrap(method='MINIMUM_STRETCH', no_flip=True, iterations=30,
                     margin_method='FRACTION', margin=.006)
    bpy.ops.uv.pack_islands(rotate=True, scale=True, merge_overlap=False,
                           margin_method='FRACTION', margin=.006,
                           shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')
    detached=isolate_overlapping_triangles(objects)
    if detached:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.seams_from_islands(mark_seams=True,mark_sharp=False)
        bpy.ops.uv.pack_islands(rotate=True,scale=True,merge_overlap=False,
                               margin_method='FRACTION',margin=.006,shape_method='CONCAVE')
        bpy.ops.object.mode_set(mode='OBJECT')
    print('UV_ISOLATED_CONFLICT_TRIANGLES',detached,flush=True)
    image=bpy.data.images.get('Medal_Bake_Atlas_2048')
    if image is None:
        image=bpy.data.images.new('Medal_Bake_Atlas_2048',width=2048,height=2048,alpha=False)
    image['purpose']='Empty 2048 atlas target. Surface texture baking is a later stage.'
    for obj in objects:
        obj['bake_atlas']='Medal_Bake_Atlas_2048'


if __name__=='__main__':
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'medal-fitted.blend'))
    objects=list(bpy.data.collections['05_GAME_LOW_2048_UV'].objects)
    bpy.context.view_layer.update()
    unwrap(objects)
    bpy.ops.export_scene.gltf(filepath=str(SOURCE/'medal-low.glb'),use_selection=True,
                             export_format='GLB',export_yup=True,export_normals=True,
                             export_texcoords=True,export_attributes=False)
    payload=json.loads((OUT/'low-arrays.json').read_text())
    for data in payload:
        mesh=bpy.data.objects[data['name']].data
        mesh.calc_loop_triangles()
        uv=mesh.uv_layers.active.data
        assert [tuple(v) for v in data['vertices']]==[v.co[:] for v in mesh.vertices]
        data['triangle_uv']=[[uv[i].uv[:] for i in t.loops] for t in mesh.loop_triangles]
    (OUT/'low-arrays.json').write_text(json.dumps(payload,separators=(',',':')))
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'medal-fitted.blend'))
    print('ATLAS_COMPLETE',flush=True)
