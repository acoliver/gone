"""Draw the authored route graph as a measured plan/section sheet (Pillow only)."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
SPEC=json.loads((ROOT/'art-source/stasis-wiring/route-spec.json').read_text())
OUT=ROOT/'art-source/stasis-wiring/functional-routing-sheet.png'
W,H=1280,1000
im=Image.new('RGB',(W,H),'#e9e5dc'); d=ImageDraw.Draw(im)
font_path='/System/Library/Fonts/Supplemental/Arial.ttf'
def font(n):
    try:return ImageFont.truetype(font_path,n)
    except OSError:return ImageFont.load_default()
def text(x,y,s,size=18,fill='#20282a'): d.text((x,y),s,font=font(size),fill=fill)
def line(points,fill,width=4): d.line(points,fill=fill,width=width,joint='curve')
# Header
text(38,22,'STASIS BAY  /  POWER + CONTROL ROUTING',28)
text(40,60,'Issue 110  •  authored routes  •  bay-local metres  •  +Y up',17,'#52605e')
# panels
d.rounded_rectangle((28,100,825,690),radius=12,fill='#f8f7f2',outline='#a8aaa2',width=2)
d.rounded_rectangle((845,100,1252,690),radius=12,fill='#f8f7f2',outline='#a8aaa2',width=2)
text(48,114,'PLAN  /  UNDER-PANEL DISTRIBUTION → FLOOR FEEDS',19)
text(862,114,'SECTION  /  SOURCE → HIDDEN BUS',19)
# plan map bay x [-6,6], z [-4,4]
def px(x): return 80+(x+6)*58
def pz(z): return 190+(z+4)*55
# wall + bay field
d.rectangle((px(-6),pz(-4),px(6),pz(4)),outline='#59625f',width=3)
text(px(-5.9),pz(-4)+8,'SOUTH WALL  Z=-4',13,'#53605c')
# pod bodies and labels
pods=SPEC['pod_base_nodes']
for i,pod in enumerate(pods,1):
    x,y,z=pod['position']; cx,cz=px(x),pz(z)
    d.rounded_rectangle((cx-30,cz-24,cx+30,cz+24),radius=5,fill='#d2d2ca',outline='#47514e',width=2)
    text(cx-18,cz-9,f'P{i}',15)
# enclosure at south wall
d.rectangle((px(-5.7)-14,pz(-3.82)-18,px(-5.7)+14,pz(-3.82)+18),fill='#9caa9c',outline='#273936',width=2)
text(px(-5.7)+20,pz(-3.82)-18,'E  existing enclosure / glands +Z',13)
# Under panel twin trunks shown across rear region; wall drops and floor feed routes distinct
for z,col,label in [(-2.60,'#bd6235','2 × POWER  Ø24 / R144'),(-2.45,'#367c91','6 × DATA  Ø6 / R48')]:
    line([(px(-5.7),pz(-3.55)),(px(-5.7),pz(z)),(px(4.8),pz(z))],col,5)
    for x in [-5.5,-4.7,-3.9,-3.1,-2.3,-1.5,-.7,.1,.9,1.7,2.5,3.3,4.1,4.8]:
        d.ellipse((px(x)-3,pz(z)-3,px(x)+3,pz(z)+3),fill='#263638')
    text(px(-5.35),pz(z)-22,label,13,col)
# two separated conduit/riser traces in wall gaps then hidden underground bus
for x,col in [(-4.1,'#9c592f'),(-2.7,'#276d80')]:
    line([(px(x),pz(-2.6)),(px(x),pz(-3.9)),(px(x),pz(-3.82))],col,4)
    text(px(x)+5,pz(-3.45),f'Ø60/25 conduit x={x}',12,col)
# hidden bus in floor and branches to all actual pod bases
line([(px(-4.8),pz(-3.35)),(px(-4.8),pz(2.9)),(px(-.6),pz(2.9)),(px(-.6),pz(-3.35))],'#766b58',3)
for i,pod in enumerate(pods,1):
    x,_,z=pod['position']; joint=(px(x),pz(z-0.12)); base=(px(x),pz(z))
    line([joint,base],'#766b58',3)
    d.ellipse((base[0]-5,base[1]-5,base[0]+5,base[1]+5),fill='#766b58')
text(104,632,'DASHED-COLOUR KEY: copper = power • blue = data • grey = concealed below slab',13)
# section depiction measured vertical planes
sx0,sy0=875,610
# section horizontal axes x simplified across floor; Y map
def sy(y): return 600-(y/3.3)*125
line([(sx0,sy(0)),(1225,sy(0))],'#59625f',3)
line([(sx0,sy(2.934)),(1225,sy(2.934))],'#a9a9a1',2)
line([(sx0,sy(2.631425)),(1225,sy(2.631425))],'#799087',2)
text(866,sy(2.934)-25,'panel underside Y=2.934',12)
text(866,sy(2.631425)+3,'max supplied lid Y=2.631425',12)
# wall enclosure, trunk, branch and floor
xw=900; d.rectangle((xw-13,sy(2.78)-20,xw+13,sy(2.78)+20),fill='#9caa9c',outline='#273936',width=2)
for y,col in [(2.82,'#bd6235'),(2.79,'#367c91')]:
    line([(xw+14,sy(y)),(1178,sy(y))],col,5)
line([(1090,sy(2.8)),(1090,sy(.25)),(1160,sy(.25)),(1160,sy(.02))],'#766b58',4)
# supports clips
for x in range(950,1160,38):
    d.line((x,sy(2.74),x,sy(2.88)),fill='#4e5551',width=3)
text(935,sy(2.82)-27,'supported twin trunks; rail clips 0.4–0.8 m',12)
text(1050,sy(1.8),'separate wall conduits',12)
text(1050,sy(.5),'concealed floor bus Y=-0.10',12)
text(1068,sy(.02)-27,'branch rises inside pod base',12)
text(878,632,'Vertical clearances are numeric planning bounds, not a swept-mesh proof.',12,'#8a4832')
# fault inset footer
# lower panel
d.rounded_rectangle((28,715,1252,965),radius=12,fill='#f8f7f2',outline='#a8aaa2',width=2)
text(50,730,'ONE LOCALIZED FAILURE  /  MECHANICAL CARRIER BREAK + POWER FAULT',19)
# top beam break simple profile
beam_y=805
d.rectangle((70,beam_y,360,beam_y+28),fill='#69716b',outline='#303a38',width=2)
d.rectangle((510,beam_y,815,beam_y+28),fill='#69716b',outline='#303a38',width=2)
# broken matching faces with single profile polygon
fract=[(360,beam_y),(378,beam_y+5),(368,beam_y+12),(389,beam_y+19),(375,beam_y+28)]
d.polygon(fract,fill='#69716b',outline='#303a38'); d.polygon([(x+450,y) for x,y in fract],fill='#69716b',outline='#303a38')
# fragment on floor
line([(170,895),(310,875),(445,895)],'#82583b',13)
text(65,925,'55 mm square carrier: 1 m removed at cell (4,4); matching fallen fragment beside preserved pickup rod',13)
# faults: intact retained clamp, short cable drops and 3 tiny cores, no data faults
for i,x in enumerate([900,1010,1120]):
    d.rectangle((x-15,beam_y-8,x+15,beam_y+4),fill='#69716b',outline='#303a38',width=2)
    line([(x,beam_y+5),(x+8,beam_y+70)],'#242727',7)
    line([(x+8,beam_y+70),(x+11,beam_y+78)],'#bb6b36',2)
    d.ellipse((x+8,beam_y+74,x+15,beam_y+81),fill='#df9a42')
text(875,920,'3 short copper tips from 2 power leads; cable ends remain above Y=2.1 m',13,'#8a4832')
text(50,976,'Black durable jackets / light scuff only • corrosion restricted to metal • pod-base entries hidden • route geometry still awaits physical clearance proof',13,'#303b39')
im.save(OUT,optimize=True)
print(OUT)
