from pathlib import Path
import shutil
P=Path(__file__).resolve().parent
O=P/'assembly3';O.mkdir(exist_ok=True)
for name in ['geometry.py','bake.py','build.py','fit.py','placement.py','tessellate.py','textures.py','validate.py','check_scene.py']:
 shutil.copyfile(P/'assembly2'/name,O/name)
print(O)
