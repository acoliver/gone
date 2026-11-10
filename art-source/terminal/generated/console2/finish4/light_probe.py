import bpy
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'console.blend'));b=bpy.data.objects['ConsoleBody'];p=next(n for n in b.active_material.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Specular IOR Level'].default_value=.10
for name,loc,power in [('Key',(-2,-3,1.6),180),('Fill',(2,-2,1.2),110),('Rim',(1,.7,1.3),45)]:
 o=bpy.data.objects[name];o.location=loc;o.data.energy=power;o.rotation_euler=(Vector((0,-.35,.65))-o.location).to_track_quat('-Z','Y').to_euler()
s=bpy.context.scene;s.camera=bpy.data.objects['ThreeQuarter'];s.render.filepath=str(O/'light-probe.png');bpy.ops.render.render(write_still=True)
