"""Run installed MLX Delight and Paint, preserving fitted geometry as colour-only source."""
import gc
import json
import sys
import numpy as np
from PIL import Image
from common import FIT, OUT, HY, INPUT

sys.path.insert(0, str(HY))
import mlx.core as mx
from paint import load_reference
from mlx_hunyuan3d.delight import DelightPipeline, recorrect_rgb
from mlx_hunyuan3d.paint_pipeline import PaintPipeline

mx.set_memory_limit(40 * 2**30)
mx.set_cache_limit(6 * 2**30)
reference = load_reference(str(INPUT))
Image.fromarray((reference * 255).astype('uint8')).save(OUT / 'paint/reference-letterboxed.png')
delight = DelightPipeline.from_pretrained(str(HY / 'weights/Hunyuan3D-2/hunyuan3d-delight-v2-0'))
delit = delight(reference, num_inference_steps=50, seed=42)
reference = recorrect_rgb(delit, reference, np.ones(reference.shape[:2], np.float32))
Image.fromarray((reference * 255).astype('uint8')).save(OUT / 'paint/reference-delighted.png')
del delight, delit
gc.collect()
mx.clear_cache()
parts = json.loads((FIT / 'low-arrays.json').read_text())
vertices, faces, offset = [], [], 0
for part in parts:
    vertices.extend(part['vertices'])
    faces.extend((np.array(part['triangles']) + offset).tolist())
    offset += len(part['vertices'])
vertices, faces = np.array(vertices), np.array(faces)
# Native Blender coordinates: -Y front and +Z up. Paint's installed normalizer
# maps those to its +Z camera/front and +Y up; no production mesh is exported.
pipeline = PaintPipeline.from_pretrained(str(HY / 'weights/Hunyuan3D-2'), dtype='float16')
result = pipeline(vertices, faces, reference, resolution=512, texture_size=2048,
                  seed=1307301, bake_diagnostics=True)
for i, view in enumerate(result['views']):
    Image.fromarray((view * 255).astype('uint8')).save(OUT / f'paint/view-{i}.png')
Image.fromarray((result['texture'] * 255).astype('uint8')).save(OUT / 'paint/hunyuan-atlas-colour.png')
np.savez_compressed(OUT / 'paint/atlas.npz', vertices=result['vertices'],
                    faces=result['faces'], uv=result['uvs'], texture=result['texture'])
np.savez_compressed(OUT / 'paint/coverage.npz', **result['bake_diagnostics'])
(OUT / 'paint/settings.json').write_text(json.dumps({
    'input': str(INPUT), 'geometry': str(FIT / 'medal-low.glb'),
    'geometry_arrays': str(FIT / 'low-arrays.json'),
    'frame': 'Unchanged native Blender -Y front, +Z up, metres; installed Paint normalization only.',
    'paint_model': str(HY / 'weights/Hunyuan3D-2/hunyuan3d-paint-v2-0-turbo'),
    'vae': str(HY / 'weights/Hunyuan3D-2/hunyuan3d-paint-v2-0/vae'),
    'delight_model': str(HY / 'weights/Hunyuan3D-2/hunyuan3d-delight-v2-0'),
    'delight_steps': 50, 'delight_seed': 42, 'delight_prompt': '', 'delight_guidance_scale': 1.0,
    'reference_border_ratio': .05, 'resolution': 512, 'texture_size': 2048,
    'dtype': 'float16', 'seed': 1307301, 'paint_prompt': 'Learned checkpoint image-conditioning embeddings; no text prompt.',
    'scheduler': {'timesteps': [int(x) for x in pipeline.scheduler.timesteps]},
    'azimuths': [0,90,180,270,0,180], 'elevations': [0,0,0,0,90,-90],
    'view_weights': [1,.1,.5,.1,.05,.05],
    'memory_limit_gib': 40, 'cache_limit_gib': 6,
    'output_is_colour_reference_only': True,
}, indent=2))
print('PAINT_COMPLETE', flush=True)
