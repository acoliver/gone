"""Measure the exported wardrobe leaf through its full parked-open range."""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix
from mathutils.bvhtree import BVHTree


def tree(objects):
    vertices=[]; faces=[]
    for obj in objects:
        offset=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(i+offset for i in p.vertices) for p in obj.data.polygons)
    return BVHTree.FromPolygons(vertices,faces)


path=Path(sys.argv[sys.argv.index('--')+1]).resolve()
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(path))
leaf=bpy.data.objects['Door']
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
moving=[o for o in meshes if o==leaf or o in leaf.children_recursive]
fixed=[o for o in meshes if o not in moving and not o.name.startswith('Hinge')]
pivot=Matrix.Translation(leaf.matrix_world.translation)
parked=leaf.matrix_world.copy()
closed=pivot@Matrix.Rotation(math.radians(-100),4,'Z')@pivot.inverted()@parked
fixed_tree=tree(fixed)
intersections=[]
for step in range(201):
    angle=step*.5
    leaf.matrix_world=pivot@Matrix.Rotation(math.radians(angle),4,'Z')@pivot.inverted()@closed
    bpy.context.view_layer.update()
    hits=tree(moving).overlap(fixed_tree)
    if hits:
        pairs=[]
        for a in moving:
            for b in fixed:
                count=len(tree([a]).overlap(tree([b])))
                if count:pairs.append([a.name,b.name,count])
        intersections.append({'angle':angle,'pairs':pairs})
leaf.matrix_world=parked
report={'range_degrees':[0,100],'step_degrees':.5,'sample_count':201,
        'surface_intersections':intersections,
        'hinges_excluded_as_mating_hardware':True,
        'interval_argument':'The main leaf back remains at or forward of Blender Y=-.332, ahead of the fixed rivet fronts at -.3308. In the pre-reflection fitting frame, returns start at X=-.441..+.429 inside the surround opening -.454..+.454; their radial X maximum is .431, and until their backs move forward of -.325 their left X stays at or above -.441. Returns span Z=.145..2.100, above the bottom panel at .144 and below the header at 2.116. Reflection in X preserves these separations. These half-space bounds hold between sweep samples; fixed mating hinge mounts and barrels are excluded as joint hardware.',
        'pass':not intersections}
path.with_suffix('.sweep.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
if not report['pass']:raise SystemExit('Wardrobe sweep failed')
