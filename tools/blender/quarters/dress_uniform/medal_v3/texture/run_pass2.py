"""Retarget the existing offline utilities to tex2 without touching tex1 outputs."""
import json
import sys
import types
from pathlib import Path

SOURCE=Path(__file__).resolve().parent
ROOT=SOURCE.parents[5]
OUT=ROOT/'tmp/issue130-v3/tex2'
FIT=OUT/'geom'
name=sys.argv[sys.argv.index('--stage')+1]
common=types.ModuleType('common')
common.ROOT=ROOT;common.FIT=FIT;common.OUT=OUT;common.SIZE=2048
common.HY=Path('/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d')
sys.modules['common']=common
if name in ['bake3.py','bake12.py','bakecheck.py']:
    path=SOURCE.parent/name
    text=path.read_text().replace("SOURCE.parents[4]/'tmp/issue130-v3/fit1'","Path("+repr(str(FIT))+")")
elif name=='bake_maps.py':
    path=SOURCE/name
    text=path.read_text()
    code="""
    settings=json.loads((FIT/'shape-decisions.json').read_text())
    boundary=np.array(settings['star_outline_xz_mm'])/1000
    xy=v[:,[0,2]]
    inside=np.zeros(len(v),bool)
    minimum=np.full(len(v),np.inf)
    for a,b in zip(boundary,np.roll(boundary,-1,axis=0)):
        e=b-a
        u=np.clip(((xy-a)@e)/(e@e),0,1)
        minimum=np.minimum(minimum,np.linalg.norm(xy-(a+u[:,None]*e),axis=1))
        if abs(e[1])>1e-15:
            inside^=((a[1]>xy[:,1])!=(b[1]>xy[:,1]))&(xy[:,0]<(e[0]*(xy[:,1]-a[1])/e[1]+a[0]))
    star_distance=np.where(inside,-minimum,minimum)
    circle_distance=settings['enamel_border_radius_mm']/1000-np.linalg.norm(xy-np.array(settings['circle_center_xz_mm'])/1000,axis=1)
    enamel_values=np.clip(star_distance/.00006+.5,0,1)*np.clip(circle_distance/.00006+.5,0,1)*(v[:,1]<-.0007)
"""
    text=text.replace("    colors = mesh.color_attributes.new",code+"    colors = mesh.color_attributes.new")
    text=text.replace("from common import FIT, OUT, SIZE","from common import ROOT, FIT, OUT, SIZE")
    text=text.replace("colors.data[li].color = (enamel, convex[vi], concave[vi], 1.)","colors.data[li].color = (float(enamel_values[vi]) if obj.name.startswith('Body') else 0., convex[vi], concave[vi], 1.)")
    text=text.replace("json.loads((FIT/'bake-check.json').read_text())","{'status':'New geometry; see geom/verification.json. No fit2 bake audit is reused.'}")
    text=text.replace("'normal_reused':","'normal_bake':")
    text=text.replace("'2048 dimensions checked; existing exported Mikk-tangent normal/reach audit retained. No rebake or geometry edits.'","'New 2048 selected-to-active tangent normal bake on corrected geometry, separate rear reach composite.'")
elif name=='render_studio.py':
    path=SOURCE/name
    text=path.read_text()
    text=text.replace("(OUT/'projection/settings.json')","(ROOT/'tmp/issue130-v3/tex1/projection/settings.json')")
    text=text.replace('from common import FIT, OUT','from common import ROOT, FIT, OUT')
    text=text.replace("        bsdf.inputs['IOR'].default_value=1.5", """        bsdf.inputs['IOR'].default_value=1.5
        tex=nodes.new('ShaderNodeTexImage')
        tex.image=bpy.data.images.load(maps['coat-weight'],check_existing=True)
        tex.image.colorspace_settings.name='Non-Color'
        links.new(tex.outputs['Color'],bsdf.inputs['Coat Weight'])
        bsdf.inputs['Coat Roughness'].default_value=.09 if state=='remembered' else .15
        bsdf.inputs['Coat IOR'].default_value=1.5""")
elif name=='render_clay.py':
    path=SOURCE.parent/'render.py'
    text=path.read_text().replace("ROOT/'tmp/issue130-v3/fit1'","Path("+repr(str(FIT))+")")
    text=text.replace("""[('raw',OUT/'raw-oriented.glb'),('high',OUT/'medal-high.glb'),
                   ('low',OUT/'medal-low.glb'),('low-normalmapped',OUT/'medal-low-normalmapped.glb')]""", "[('high',OUT/'medal-high.glb')]")
    text=text.replace("match=json.loads((OUT/'camera-match.json').read_text())","match=json.loads((Path("+repr(str(ROOT/'tmp/issue130-v3/fit2/camera-match.json'))+")).read_text())")
    text=text.replace("    for name,(pos,target,scale) in views.items():","""    for name,(pos,target,scale) in views.items():
        if name not in ['front','three-quarter','star-close','edge']:continue""")
else:
    raise ValueError(name)
sys.path.insert(0,str(SOURCE.parent))
exec(compile(text,str(path),'exec'),{'__name__':'__main__','__file__':str(path)})
