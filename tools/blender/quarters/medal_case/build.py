"""Open steel presentation case, separate brass medal and hinged lid."""
from pathlib import Path
import math
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'photo_frame'))
import small_common as sc


def assemble(m):
    sc.box('CaseFloor',(.14,.14,.008),(0,0,.004),m['PaintedSteel'],.002)
    for name,dims,pos in [
        ('SideL',(.006,.14,.026),(-.067,0,.017)),
        ('SideR',(.006,.14,.026),(.067,0,.017)),
        ('Front',(.128,.006,.026),(0,-.067,.017)),
        ('Back',(.128,.006,.026),(0,.067,.017)),
    ]:
        sc.box(name,dims,pos,m['PaintedSteel'],.001)
    sc.box('Lining',(.123,.122,.005),(0,0,.011),m['Lining'],.001)
    lid=sc.box('Lid',(.14,.007,.097),(0,.066,.0725),m['PaintedSteel'],.002)
    sc.bt.hinge_origin(lid,(0,.066,.024))
    sc.box('LidLining',(.122,.002,.078),(0,.061,.073),m['Lining'],.0004)
    for i,x in enumerate([-.045,.045]):
        sc.bt.cylinder(f'Hinge_{i}',.004,.025,(x,.065,.026),m['Brass'],axis=(1,0,0),sides=12,edge=0)
    sc.box('FrontClasp',(.018,.003,.016),(0,-.072,.021),m['Brass'],.001)
    sc.bt.cylinder('Medal',.030,.004,(0,-.013,.018),m['Brass'],sides=32,edge=.0005)
    sc.box('Ribbon',(.036,.038,.0015),(0,.028,.017),m['Ribbon'],0)
    for x in [-.012,.012]:
        sc.box('RibbonStripe',(.005,.038,.0004),(x,.028,.018),m['RibbonIvory'],0)
    vertices=[(0,-.013,.025)]
    for i in range(10):
        a=math.pi/2+i*math.tau/10
        r=.022 if i%2==0 else .009
        vertices.append((r*math.cos(a),-.013+r*math.sin(a),.023))
    vertices.append((0,-.013,.021))
    faces=[]
    for i in range(10):
        a=1+i; b=1+(i+1)%10
        faces.extend([(0,a,b),(11,b,a)])
    sc.bt.cage('MedalStar',vertices,faces,m['Brass'],0)


if __name__=='__main__':
    sc.main(__file__,'medal_case',assemble)
