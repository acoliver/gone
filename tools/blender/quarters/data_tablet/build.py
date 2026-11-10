"""Rugged hard-plastic tablet with a separate inactive display."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'photo_frame'))
import small_common as sc


def assemble(m):
    plastic=m['HardPlastic'].node_tree.nodes['Principled BSDF']
    plastic.inputs['Base Color'].default_value=(.029,.042,.024,1)
    plastic.inputs['Roughness'].default_value=.32
    rubber=m['Rubber'].node_tree.nodes['Principled BSDF']
    rubber.inputs['Base Color'].default_value=(.009,.012,.009,1)
    screen=m['Display'].node_tree.nodes['Principled BSDF']
    screen.inputs['Base Color'].default_value=(.001,.002,.003,1)
    screen.inputs['Roughness'].default_value=.12
    screen.inputs['Specular IOR Level'].default_value=.10
    sc.box('Shell',(.18,.26,.016),(0,0,.008),m['HardPlastic'],.005,4)
    sc.box('ScreenBezel',(.164,.239,.0014),(0,0,.016),m['Rubber'],.0005,3)
    sc.box('DarkScreen',(.147,.216,.0008),(0,0,.0171),m['Display'],.0002,2)
    for i,(x,y) in enumerate([(-.079,-.119),(.079,-.119),(-.079,.119),(.079,.119)]):
        sc.box(f'CornerBumper_{i}',(.019,.020,.013),(x,y,.009),m['HardPlastic'],.003,2)
        sc.bt.cylinder(f'Screw_{i}',.003,.0008,(x,y,.0164),m['BareSteel'],sides=12,edge=0)
        sc.box(f'ScrewSlot_{i}',(.0038,.0007,.0003),(x,y,.0169),m['Rubber'],0)
    sc.bt.cylinder('PowerButton',.0035,.002,(.090,0,.008),m['Rubber'],axis=(1,0,0),sides=12,edge=0)


if __name__=='__main__':
    sc.main(__file__,'data_tablet',assemble)
