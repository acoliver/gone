"""Standing steel frame, separate glass cover and durable polymer print."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import small_common as sc


def assemble(m):
    for name, dims, center in [
        ('FrameLeft',(.011,.012,.15),(-.0895,-.021,.096)),
        ('FrameRight',(.011,.012,.15),(.0895,-.021,.096)),
        ('FrameTop',(.168,.012,.011),(0,-.021,.1655)),
        ('FrameBottom',(.168,.012,.011),(0,-.021,.0265)),
    ]:
        sc.box(name,dims,center,m['PaintedSteel'],.001)
    sc.box('BackPlate',(.173,.004,.130),(0,-.012,.096),m['BareSteel'],.001)
    photo=sc.image_material('PhotoPrint',sc.ROOT/'assets/props/quarters/textures/photo_frame/print.png',.48)
    plate=sc.box('PhotoPlate',(.162,.001,.112),(0,-.017,.096),photo,0)
    glass=sc.bt.material('Glass',(.72,.83,.85,.045),0,.075)
    glass.surface_render_method='DITHERED'
    glass.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=.045
    pane=sc.box('GlassCover',(.164,.0014,.114),(0,-.019,.096),glass,.00035)
    pane['runtime_shader']='res://app/pod_glass.gdshader'
    pane['substrate']='Closed 1.4 mm cover for standalone glTF; replace material with pod-style glass at room integration.'
    sc.bt.beam('EaselLeg',(0,.012,.137),(0,.052,.006),.009,m['BareSteel'])
    sc.box('BaseFoot',(.11,.085,.006),(0,.0095,.003),m['PaintedSteel'],.001)
    for i,(x,z) in enumerate([(-.0895,.03),(.0895,.03),(-.0895,.162),(.0895,.162)]):
        sc.bt.cylinder(f'CornerScrew_{i}',.002,.0015,(x,-.028,z),m['BareSteel'],axis=(0,-1,0),sides=8,edge=0)


if __name__=='__main__':
    sc.main(__file__,'photo_frame',assemble)
