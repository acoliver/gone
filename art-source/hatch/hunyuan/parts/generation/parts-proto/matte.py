import json
import os
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from rembg import new_session, remove

source, target = map(Path, sys.argv[1:])
image = Image.open(source).convert('RGB')
session = new_session('u2net', providers=['CPUExecutionProvider'])
rgba = remove(image, session=session).convert('RGBA')
alpha = np.asarray(rgba.getchannel('A'))
assert alpha.max() > 0 and alpha.min() == 0, 'Matte must have foreground and transparent background'
rgba.save(target)
info = {'source': str(source), 'output': str(target), 'method': 'rembg U2-Net CPU, default parameters, no manual cleanup', 'model': os.environ['U2NET_HOME'] + '/u2net.onnx', 'size': list(rgba.size), 'alpha_bbox_xyxy': rgba.getchannel('A').getbbox(), 'foreground_fraction': float((alpha > 0).mean()), 'opaque_fraction': float((alpha == 255).mean())}
target.with_suffix('.json').write_text(json.dumps(info, indent=2))
print(json.dumps(info))
