"""Closed ceramic cup wall and separate curved handle, real-size tableware."""
from pathlib import Path
import math
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'photo_frame'))
import small_common as sc


def assemble(m):
    profile=[(0,0),(.032,0),(.035,.004),(.042,.085),(.044,.096),(.043,.10),
             (.038,.10),(.037,.095),(.036,.085),(.035,.080),(.034,.020),(.029,.011),(0,.011)]
    sc.lathe('Cup',profile,m['Ceramic'],40,{4:m['Glaze'],5:m['DustCeramic'],8:m['Stain'],11:m['DustCeramic']})
    centers=[(.038+.034*math.cos(a),0,.053+.036*math.sin(a))
             for a in [math.radians(-100+i*200/20) for i in range(21)]]
    sc.tube('Handle',centers,.006,m['Ceramic'],10)


if __name__=='__main__':
    sc.main(__file__,'mug',assemble)
