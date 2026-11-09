"""Closed oval head and curved handle with individual natural-bristle tufts."""
from pathlib import Path
import math
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'photo_frame'))
import small_common as sc


def oval(name,rx,ry,z0,z1,mat,cy=.055):
    obj=sc.bt.cylinder(name,1,z1-z0,(0,cy,(z0+z1)/2),mat,sides=24,edge=0)
    for v in obj.data.vertices:
        v.co.x*=rx; v.co.y*=ry
    return obj


def assemble(m):
    plastic=m['HardPlastic'].node_tree.nodes['Principled BSDF']
    plastic.inputs['Base Color'].default_value=(.024,.036,.018,1)
    plastic.inputs['Roughness'].default_value=.28
    oval('Head',.035,.047,.008,.021,m['HardPlastic'])
    import bpy
    rows=[(-.12,.005),(-.115,.011),(-.097,.0115),(-.052,.009),(-.008,.011),(.014,.014)]
    outline=[(w,y) for y,w in rows]+[(-w,y) for y,w in reversed(rows)]
    vertices=[(x+.002*math.sin(y*32),y,z) for z in [.003,.018] for x,y in outline]
    n=len(outline)
    faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    handle=sc.bt.cage('Handle',vertices,faces,m['HardPlastic'],0)
    sc.bt.bevel(handle,.002,2)
    for poly in handle.data.polygons:
        poly.use_smooth=abs(poly.normal.z)<.99
    cutter=sc.bt.cylinder('HangingHoleCutter',.0027,.04,(0,-.110,.01),m['Rubber'],sides=10,edge=0)
    bpy.context.view_layer.objects.active=handle
    mod=handle.modifiers.new('HangingHole','BOOLEAN')
    mod.operation='DIFFERENCE'; mod.solver='EXACT'; mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    m['Rubber'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.005,.007,.004,1)
    oval('GripInsert',.0058,.037,.018,.0212,m['Rubber'],cy=-.058)
    oval('BristlePad',.031,.042,.021,.026,m['Rubber'])
    index=0
    for row in range(8):
        y=(row-3.5)*.010
        for col in range(7):
            x=(col-3)*.009
            if (x/.029)**2+(y/.040)**2>1 or (row,col)==(0,3): continue
            for fiber in range(3):
                angle=fiber*math.tau/3+index*.47
                fx=x+.002*math.cos(angle); fy=y+.055+.002*math.sin(angle)
                top=.044+(.0013*math.sin(index*1.7+fiber))
                tx=fx+.0007*math.cos(angle); ty=fy+.0007*math.sin(angle)
                sc.tube(f'BristleTuft_{index:02}_{fiber}',[(fx,fy,.025),(tx,ty,top)],.0011,m['Bristle'],3)
            index+=1


if __name__=='__main__':
    sc.main(__file__,'hairbrush',assemble)
