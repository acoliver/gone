"""Regenerate seed-720 weather from baked world positions, normals and true edges."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

R = Path(__file__).resolve().parent
BUILD = json.loads((R / 'build-stats.json').read_text())
SLOTS = np.linspace(-.455, .455, 14)
stats = {}


def save(name, values):
    Image.fromarray((np.flipud(np.clip(values, 0, 1)) * 255 + .5).astype('uint8')).save(R / (name + '.png'))


def noise(p, scale, seed):
    q = p / scale
    cell = np.floor(q).astype(np.int64)
    f = q - cell
    f = f * f * (3 - 2 * f)
    out = np.zeros(p.shape[:-1])
    for i in range(2):
        for j in range(2):
            for k in range(2):
                c = cell + [i, j, k]
                v = (c[..., 0] * 73856093) ^ (c[..., 1] * 19349663) ^ (c[..., 2] * 83492791) ^ seed
                v = (v ^ (v >> 13)) * 1274126177
                v = (v ^ (v >> 16)) & 0xffffffff
                weight = (f[..., 0] if i else 1 - f[..., 0]) * (f[..., 1] if j else 1 - f[..., 1]) * (f[..., 2] if k else 1 - f[..., 2])
                out += weight * (v / 4294967295.)
    return out


for prefix in ['body', 'grille', 'hardware']:
    p = np.load(R / (prefix + '_position.npy'))[:, :, :3] - [.55, .11, .1]
    n = np.load(R / (prefix + '_normals.npy'))[:, :, :3] * 2 - 1
    x, y, z = np.moveaxis(p, -1, 0)
    valid = (np.linalg.norm(n, axis=-1) > .7) & (np.linalg.norm(n, axis=-1) < 1.2)
    edges = np.load(R / (prefix + '_sharp_edges.npy'))
    distance = cKDTree(edges).query(p.reshape(-1, 3), workers=4)[0].reshape(x.shape)
    edge = np.exp(-(distance / .012) ** 1.8)
    if prefix == 'grille':
        edge = np.exp(-(distance / .0034) ** 1.4)
    chip = edge * np.clip((.65 * noise(p, .028, 72005) + .35 * noise(p, .0035, 84371) - .32) * 4.5, 0, 1)
    channel = np.exp(-((abs(y) - .056) / .010) ** 2) * (z < -.064) * (abs(x) < .507)
    side = np.clip((abs(n[:, :, 0]) + abs(n[:, :, 1]) - .3) * 1.8, 0, 1)
    streak = np.zeros_like(x)
    heads = np.zeros_like(x)
    for stud in BUILD['side_fasteners']:
        drop = stud['z'] - z
        centre = stud['x'] + .0013 * (noise(p, .023, 329) - .5)
        width = .0034 + .0018 * np.clip(drop / .075, 0, 1)
        line = np.exp(-((x - centre) / width) ** 2) * np.clip((.09 - drop) / .035, 0, 1) * (drop >= 0) * np.exp(-abs(y - stud['y']) / .009) * side
        streak = np.maximum(streak, .80 * line)
        heads = np.maximum(heads, np.exp(-(((x - stud['x']) / .009) ** 2 + ((z - stud['z']) / .008) ** 2)) * np.exp(-abs(y - stud['y']) / .008))
    for xx in [-.46, -.28, -.10, .10, .28, .46]:
        for yy in [-.044, .044]:
            heads = np.maximum(heads, np.exp(-(((x - xx) / .008) ** 2 + ((y - yy) / .008) ** 2)) * np.exp(-abs(z + .099) / .012))
        drop = -.045 - z
        line = np.exp(-((x - xx) / .0035) ** 2) * np.clip((.09 - drop) / .03, 0, 1) * (drop >= 0)
        shoulder = np.clip((abs(y) - .055) / .006, 0, 1) * np.clip((.108 - abs(y)) / .004, 0, 1)
        streak = np.maximum(streak, .75 * line * shoulder)
    deposit = .12 + .88 * np.clip((noise(p / [1, .6, .7], .055, 67) - .27) * 2.7, 0, 1)
    upward = np.clip(n[:, :, 2], 0, 1)
    ledge = channel * (.30 + .70 * upward)
    crust = np.exp(-((abs(y) - .077) / .016) ** 2) * (z < -.072) * (abs(x) < .505)
    if prefix == 'body':
        base_colour = np.array([.355, .383, .255])
        soot = .92 * channel
        rust = np.clip(.95 * chip + .75 * heads + .003, 0, .96)
        dust = np.clip(.95 * upward * deposit + .85 * ledge * deposit + .95 * crust * deposit, 0, .97)
        dust = np.maximum(dust, (.20 + .75 * deposit) * (z < -.025))
    elif prefix == 'grille':
        base_colour = np.array([.225, .247, .160])
        corner = np.zeros_like(x)
        for xc in SLOTS:
            for sign in [-1, 1]:
                corner = np.maximum(corner, np.exp(-((abs(x - xc) - .016) / .007) ** 2 - ((y - sign * .030) / .010) ** 2))
        soot = np.clip(.48 * np.exp(-(y / .062) ** 4) + .20 * edge + .48 * corner, 0, .92)
        rust = np.clip(.80 * chip + .003, 0, .90)
        streak *= .15
        # Keep the central bar faces dark; deposits collect against channel walls.
        dust = (.85 * upward + .78 * np.exp(-((abs(y) - .044) / .010) ** 2)) * deposit
    else:
        base_colour = np.array([.310, .343, .218])
        soot = .40 * np.exp(-((abs(y) - .046) / .007) ** 2) * (abs(x) < .498)
        rust = np.clip(.95 * chip + .70 * heads + .003, 0, .96)
        streak *= .40
        dust = np.clip(.95 * upward * deposit + .42 * channel * deposit + .55 * crust * deposit, 0, .95)
        dust *= np.clip((upward - .35) / .40, 0, 1)
    soot = np.clip(soot * (.45 + 1.15 * noise(p, .009, 99183)), 0, .94)
    base = np.broadcast_to(base_colour, (*x.shape, 3)).copy()
    base *= 1 + .008 * (noise(p, .0009, 145) - .5)[:, :, None]
    dust *= (1 - .80 * np.maximum(rust, streak)) * np.clip(distance / .006, 0, 1)
    chalk = .55 + .40 * noise(p / [1, .60, .65], .065, 71044)
    faded = base * (1 - chalk[:, :, None]) + np.array([.88, .92, .73]) * chalk[:, :, None]
    if prefix == 'grille':
        faded = base * .915
    elif prefix == 'hardware':
        faded = np.array([.110, .120, .085]) * (.85 + .15 * noise(p, .045, 8102))[:, :, None]
    wear = .08 * chip
    oxide = np.array([.20, .082, .032]) * (.65 + .50 * noise(p, .008, 529))[:, :, None]
    metal = np.array([.13, .14, .108])
    dust_colour = np.array([.88, .86, .75]) * (.90 + .10 * noise(p, .035, 5381))[:, :, None]

    def colour(r, st, du=dust):
        r = np.maximum(r, st)
        c = faded * (1 - r[:, :, None]) + oxide * r[:, :, None]
        c = c * (1 - soot[:, :, None]) + np.array([.018, .021, .013]) * soot[:, :, None]
        c = c * (1 - wear[:, :, None]) + metal * wear[:, :, None]
        return c * (1 - du[:, :, None]) + dust_colour * du[:, :, None]

    final = colour(rust, streak)
    rough = np.ones_like(x)
    metallic = np.zeros_like(x)
    broad = distance > .015
    allrust = np.maximum(rust, streak)
    zones = np.stack([(distance < .0025).astype(float), broad.astype(float), (streak > .12).astype(float)], -1) * valid[:, :, None]
    images = {
        'albedo': final, 'no_rust': colour(np.zeros_like(x), np.zeros_like(x)),
        'no_streak': colour(rust, np.zeros_like(x)), 'no_dust': colour(rust, streak, np.zeros_like(x)),
        'control': base, 'orm': np.stack([np.ones_like(x), rough, metallic], -1),
        'control_orm': np.stack([np.ones_like(x), np.full_like(x, .70), np.full_like(x, .48)], -1),
        'rust': np.repeat(allrust[:, :, None], 3, -1), 'soot': np.repeat(soot[:, :, None], 3, -1),
        'zones': zones, 'dustmask': np.repeat((dust > .10)[:, :, None], 3, -1) * valid[:, :, None],
        'topmask': np.repeat((upward > .35)[:, :, None], 3, -1) * valid[:, :, None],
        'shellmask': np.repeat(((distance > .005) & (prefix == 'body'))[:, :, None], 3, -1) * valid[:, :, None],
    }
    for name, values in images.items():
        save(prefix + '_' + name, values)
    em, bm = allrust[valid & (distance < .0025)].mean(), allrust[valid & broad].mean()
    stats[prefix] = {'albedo_mean_abs_effect': float(np.abs(final - base)[valid].mean()), 'edge_rust_mean': float(em), 'broad_rust_mean': float(bm), 'edge_to_broad_rust_ratio': float(em / bm), 'dust_mean': float(dust[valid].mean())}

# Preserve the established glass level at the aperture centres. Off-centre stains
# attenuate emission locally and never change any scene light's output.
w, h = 2048, 256
xx, yy = np.linspace(-.485, .485, w)[None, :], np.linspace(-.042, .042, h)[:, None]
bright = np.broadcast_to((.92 + .045 * np.sin((xx + .23) * 5.7)) * (1 - .51 * np.exp(-((xx + .175) / .106) ** 6)), (h, w)).copy()
shadow = np.ones((h, w))
for cx, cy, wx, wy, depth in [(-.397, .018, .025, .021, .12), (-.202, -.025, .031, .022, .14), (.115, .019, .029, .019, .13), (.364, -.014, .038, .026, .11)]:
    shadow *= 1 - depth * np.exp(-((xx - cx) / wx) ** 2 - ((yy - cy) / wy) ** 2)
bright *= shadow * (.98 - .025 * (yy / .042) ** 2)
drift = .012 * np.sin((xx + .2) * 4.3)
tint = np.stack([np.ones_like(xx), .91 * (1 + drift), .76 * (1 + drift * .6)], -1)
linear_control = bright[:, :, None] * tint * 1.08
stain = np.ones((h, w))
for cx, cy, wx, wy, depth in [(-.420, .031, .040, .015, .78), (-.270, -.029, .036, .016, .68), (-.035, .032, .050, .016, .75), (.155, -.031, .035, .014, .80), (.348, .028, .045, .013, .72), (.448, -.030, .025, .015, .65)]:
    stain *= 1 - depth * np.exp(-((xx - cx) / wx) ** 2 - ((yy - cy) / wy) ** 2)
for cx, cy, wx, wy in [(-.383, .013, .013, .017), (.105, -.014, .018, .015), (.395, .010, .015, .018)]:
    stain *= 1 - .90 * np.exp(-((xx - cx) / wx) ** 4 - ((yy - cy) / wy) ** 2)
for index, cy, strength in [(1, .006, .65), (5, -.008, .54), (12, -.006, .45)]:
    stain *= 1 - strength * np.exp(-(((xx - SLOTS[index]) / .016) ** 2 + ((yy - cy) / .022) ** 2))
linear = linear_control * stain[:, :, None]
nearest_slot = np.min(np.abs(xx[:, :, None] - SLOTS), axis=2)
slot_border = np.maximum(np.clip((nearest_slot - .007) / .010, 0, 1), np.clip((abs(yy) - .011) / .020, 0, 1))
glass_points = np.stack(np.broadcast_arrays(xx, yy, np.zeros((h, w))), -1)
edge_stain = .82 * slot_border * (.65 + .35 * noise(glass_points, .018, 7362))
linear *= (1 - edge_stain[:, :, None])
emission = np.where(linear <= .0031308, linear * 12.92, 1.055 * np.maximum(linear, 0) ** (1 / 2.4) - .055)
save('glass_emission', emission)
encoded_control = np.where(linear_control <= .0031308, linear_control * 12.92, 1.055 * np.maximum(linear_control, 0) ** (1 / 2.4) - .055)
intensity = encoded_control @ [.299, .587, .114]
save('glass_control', np.stack([intensity * .97, intensity, intensity], -1))
stats.update({'texture_repeat': False, 'texture_resolution_px': [1024, 1024], 'glass_resolution_px': [2048, 256], 'edge_decay_m': .012, 'streak_fwhm_m': [.0034 * 2 * np.sqrt(np.log(2)), .0052 * 2 * np.sqrt(np.log(2))], 'gravity_blender': [0, 0, -1], 'scene_light_energy_changed': False, 'method': 'True-edge paint loss, fastener gravity tails, channel soot, normal and ledge dust; nonperiodic world-space hashed fields; off-centre glass stains'})
(R / 'weather-stats.json').write_text(json.dumps(stats, indent=2) + '\n')
print(json.dumps(stats, indent=2))
