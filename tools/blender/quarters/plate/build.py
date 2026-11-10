"""Closed shallow ceramic dish with raised lip and circular foot."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'photo_frame'))
import small_common as sc


def assemble(m):
    for name in ['Ceramic','Stain','DustCeramic']:
        shader=m[name].node_tree.nodes['Principled BSDF']
        shader.inputs['Base Color'].default_value=(.66,.64,.57,1)
        shader.inputs['Roughness'].default_value=.17
    profile=[(0,.003),(.070,.003),(.071,0),(.080,0),(.081,.005),
             (.115,.017),(.122,.022),(.125,.024),(.125,.025),(.123,.026),
             (.119,.025),(.114,.022),(.108,.019),(.089,.009),
             (.084,.0075),(.079,.0075),(0,.0075)]
    sc.lathe('Dish',profile,m['Ceramic'],48,{8:m['DustCeramic'],10:m['Glaze'],14:m['Stain'],15:m['DustCeramic']})


if __name__=='__main__':
    sc.main(__file__,'plate',assemble)
