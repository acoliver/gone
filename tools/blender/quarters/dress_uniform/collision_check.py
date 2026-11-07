"""Find intersecting exported GLB mesh pairs with Blender's BVH implementation."""
import json
import sys
from pathlib import Path
import bpy
from mathutils.bvhtree import BVHTree

args=sys.argv[sys.argv.index('--')+1:]
source=Path(args[args.index('--input')+1])
report_path=Path(args[args.index('--report')+1])
bpy.ops.import_scene.gltf(filepath=str(source))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']

def part_name(name):
    return name.split('.')[0]

def tree(obj):
    deps=bpy.context.evaluated_depsgraph_get()
    eval_obj=obj.evaluated_get(deps)
    mesh=eval_obj.to_mesh()
    verts=[obj.matrix_world@v.co for v in mesh.vertices]
    faces=[tuple(p.vertices) for p in mesh.polygons]
    result=BVHTree.FromPolygons(verts,faces,all_triangles=False)
    eval_obj.to_mesh_clear()
    return result

by_part={}
for obj in objects:by_part.setdefault(part_name(obj.name),[]).append(obj)
parts={name:tree_group for name,tree_group in ((name,[tree(o) for o in group]) for name,group in by_part.items())}
collisions=[]
names=sorted(parts)
for i,a in enumerate(names):
    for b in names[i+1:]:
        overlap_count=sum(len(ta.overlap(tb)) for ta in parts[a] for tb in parts[b])
        if overlap_count:collisions.append({'parts':[a,b],'overlap_pairs':overlap_count})
result={'intersecting_part_pairs':collisions,'pass':not collisions}
report_path.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
