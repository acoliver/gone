import numpy as np,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def measure_lip(vertices,faces,plane,offset=(0,0,0)):
 tree=BVHTree.FromPolygons(vertices.tolist(),faces.tolist())
 a,b,c=plane;n=Vector((-a,-b,1)).normalized();offset=Vector(offset);result=[]
 for x in [-.39,-.195,0,.195,.39]:
  anchor=Vector((x,-.680,a*x+b*(-.680)+c))+offset
  top=tree.ray_cast(anchor+n*.10,-n)[0]
  bottom=tree.ray_cast(anchor-n*.10,n)[0]
  assert top is not None and bottom is not None
  front=[]
  for z in np.linspace(.510,.528,10):
   start=Vector((x,-1.5,float(z)))+offset
   hit=tree.ray_cast(start,Vector((0,1,0)))[0];assert hit is not None
   front.append(list(hit-offset))
  points=np.array(front);slope=np.polyfit(points[:,2],points[:,1],1)[0]
  result.append({'x_m':x,'normal_thickness_mm':(top-bottom).dot(n)*1000,'front_face_angle_from_vertical_deg':math.degrees(math.atan(slope)),'top_m':list(top),'bottom_m':list(bottom)})
 return result
