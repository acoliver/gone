"""Export a small float source table for subtexel physical-space gravity trails."""
import numpy as np


def write_sources(path, sources, seed):
    rng = np.random.default_rng(seed)
    points, parameters = [], []
    origins = np.array([source['position_blender'] for source in sources])
    for index, source in enumerate(sources):
        x, y, z = origins[index]
        if source.get('part') == 'HandlePocket':
            continue
        if source.get('part') == 'DoorVents':
            lo, hi = np.array(source['bounds_blender'])
            if hi[1] - lo[1] < .01:
                continue
            x += rng.uniform(-.018, .018)
        other = origins - origins[index]
        paired = np.any((np.linalg.norm(other[:, :2], axis=1) > .001) &
                        (np.linalg.norm(other[:, :2], axis=1) < .020) & (abs(other[:, 2]) < .004))
        width = (.0070 if paired else .0095) * rng.uniform(.97, 1.03)
        length = rng.uniform(.15, .24)
        points.append([x, z, -y, width])
        parameters.append([length, source.get('strength', 1), .0003 if paired else .0020, rng.uniform(0, 64)])
    values = np.array(points + parameters, dtype='<f4').ravel()
    data = ', '.join(str(byte) for byte in values.tobytes())
    path.write_text('[gd_resource type="ImageTexture" load_steps=2 format=3]\n\n'
                    '[sub_resource type="Image" id="Image_sources"]\n'
                    'data = {\n"data": PackedByteArray(' + data + '),\n'
                    '"format": "RGBAFloat",\n"height": 2,\n"mipmaps": false,\n"width": ' + str(len(points)) + '\n}\n\n'
                    '[resource]\nimage = SubResource("Image_sources")\n')
    return len(points)
