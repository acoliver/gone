"""Metric curvature filtering, locked-atlas validation and concept-referenced medal textures."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SIZE = 2048


def filter_curvature(out):
    source = np.load(out / 'curvature-source.npz')
    v, signed = source['vertices'], source['signed']
    tree = cKDTree(v)
    fields = []
    for sigma in [.0001, .0004]:
        result = np.empty(len(v))
        for start in range(0, len(v), 1000):
            points = v[start:start + 1000]
            neighbours = tree.query_ball_point(points, sigma * 2.5)
            for j, ids in enumerate(neighbours):
                weights = np.exp(-np.sum((v[ids] - points[j]) ** 2, axis=1) / (2 * sigma ** 2))
                result[start + j] = np.sum(signed[ids] * weights) / weights.sum()
        fields.append(result)
        print('FILTERED', sigma, np.percentile(result, [0, 10, 50, 90, 100]), flush=True)
    convex = np.clip((np.maximum(fields[0], 0) * .65 + np.maximum(fields[1], 0) * .35) / 4000, 0, 1)
    concave = np.clip((np.maximum(-fields[0], 0) * .65 + np.maximum(-fields[1], 0) * .35) / 4000, 0, 1)
    np.savez_compressed(out / 'curvature-filtered.npz', convex=convex, concave=concave,
                        signed_010mm=fields[0], signed_040mm=fields[1])


def raster_context(data):
    face = np.full((SIZE, SIZE), -1, np.int32)
    bary = np.zeros((SIZE, SIZE, 3), np.float32)
    overlaps = 0
    for i, uv in enumerate(data['uv']):
        pts = uv * SIZE - .5
        lo = np.maximum(np.ceil(pts.min(0)).astype(int), 0)
        hi = np.minimum(np.floor(pts.max(0)).astype(int), SIZE - 1)
        if np.any(hi < lo): continue
        x, y = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1))
        inv = np.linalg.inv(np.column_stack((pts[1] - pts[0], pts[2] - pts[0])))
        bc = np.stack((x - pts[0, 0], y - pts[0, 1]), -1) @ inv.T
        bc = np.concatenate((1 - bc.sum(-1, keepdims=True), bc), -1)
        mask = np.min(bc, axis=-1) > 1e-7
        dst = face[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
        overlaps += int(np.sum(mask & (dst >= 0)))
        dst[mask] = i
        bary[lo[1]:hi[1]+1, lo[0]:hi[0]+1][mask] = bc[mask]
    return face, bary, overlaps


def normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def srgb_to_linear(v):
    return np.where(v <= .04045, v / 12.92, ((v + .055) / 1.055) ** 2.4)


def linear_to_srgb(v):
    return np.where(v <= .0031308, v * 12.92, 1.055 * np.maximum(v, 0) ** (1 / 2.4) - .055)


def save_png(path, data, color=False):
    if color: data = linear_to_srgb(data)
    data = np.clip(data, 0, 1)
    if data.ndim == 2: data = np.repeat(data[:, :, None], 3, axis=2)
    Image.fromarray(np.uint8(np.flipud(data) * 255 + .5)).save(path)


def validate(out):
    data = np.load(out / 'low-bake-context.npz')
    face, bary, overlaps = raster_context(data)
    mask = face >= 0
    valid = np.maximum(face, 0)
    expected = data['regions'][valid]
    ids = np.load(out / 'projected_regions.npy')[:, :, 0]
    missed = mask & (ids < 1 / 32)
    wrong = mask & ~missed & (np.abs(ids - (expected + 1) / 16) > .025)
    normal = np.load(out / 'geometry_normal.npy')[:, :, :3] * 2 - 1
    normals = data['normals'].reshape(-1, 3, 3)[valid]
    n = normalize(np.sum(normals * bary[:, :, :, None], axis=2))
    t = normalize(np.sum(data['tangent'][valid] * bary[:, :, :, None], axis=2))
    t = normalize(t - np.sum(t * n, axis=2, keepdims=True) * n)
    signs = np.sign(np.sum(data['sign'][valid] * bary, axis=2))
    b = np.cross(n, t) * signs[:, :, None]
    decoded = normalize(t * normal[:, :, 0:1] + b * normal[:, :, 1:2] + n * normal[:, :, 2:3])
    high = normalize(np.load(out / 'high_shading_normal.npy')[:, :, :3] * 2 - 1)
    angle = np.degrees(np.arccos(np.clip(np.sum(decoded * high, -1), -1, 1)))
    front_names = ['rim', 'enamel', 'star_wall', 'star_bevel', 'star_roof', 'star_center', 'bail', 'sidewall']
    visible = mask & np.isin(expected, [data['region_names'].tolist().index(x) for x in front_names])
    error = angle[visible & ~missed & ~wrong]
    # Triangle-centroid coverage complements the pixel-interior test for narrow strips.
    centres = np.floor(data['uv'].mean(1) * SIZE).astype(int)
    centroid_miss = int(np.sum(ids[centres[:, 1], centres[:, 0]] < 1 / 32))
    report = dict(covered_texels=int(mask.sum()), uv_overlapping_interior_texels=overlaps,
                  missed_texels=int(missed.sum()), wrong_region_texels=int(wrong.sum()),
                  uncovered_triangle_centroids=centroid_miss,
                  tangent_frame_normal_error_degrees=dict(median=float(np.median(error)), p95=float(np.percentile(error, 95)),
                    method='Baked tangent normal decoded with interpolated orthonormal low tangent frame vs high OBJECT-space normal bake at the same cage hits'),
                  finite_unit_tangents=bool(np.isfinite(data['tangent']).all() and np.max(abs(np.linalg.norm(data['tangent'], axis=2)-1)) < 1e-4))
    save_png(out / 'coverage.png', mask.astype(float))
    save_png(out / 'cage-misses.png', np.stack((missed, wrong, np.zeros_like(mask)), -1).astype(float))
    save_png(out / 'normal-error-heatmap.png', np.stack((np.clip(angle / 15, 0, 1), np.zeros_like(angle), np.zeros_like(angle)), -1) * mask[:, :, None])
    np.savez_compressed(out / 'atlas-context.npz', face=face, bary=bary, expected=expected, mask=mask,
                        tangent=t, bitangent=b, normal=n, decoded=decoded, high_normal=high)
    (out / 'bake-quality.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)
    return report


def repair(out):
    atlas=np.load(out/'atlas-context.npz')
    mask,expected=atlas['mask'],atlas['expected']
    ids=np.load(out/'projected_regions_raw.npy')[:,:,0]
    unresolved=mask&(np.abs(ids-(expected+1)/16)>.025)
    rows=[]
    indices=np.indices(mask.shape)
    for i in range(9):
        region=mask&(expected==i)
        missing=region&unresolved
        valid=region&~unresolved
        distance,nearest=distance_transform_edt(~valid,return_indices=True)
        rows.append(dict(region=i,subtexel_seam_samples=int(missing.sum()),maximum_completion_distance_texels=float(distance[missing].max()) if missing.any() else 0))
        indices[:,missing]=nearest[:,missing]
    nearest_atlas=distance_transform_edt(~mask,return_distances=False,return_indices=True)
    for key in ['projected_regions','geometry_normal','curvature_convex','curvature_concave','surface_position','high_shading_normal','ao_near','ao_local']:
        raw=np.load(out/(key+'_raw.npy'))
        completed=raw[tuple(indices)]
        completed=completed[tuple(nearest_atlas)]
        np.save(out/(key+'.npy'),completed)
        save_png(out/(key+'.png'),completed[:,:,:3])
    report=dict(method='Within-feature nearest valid high-surface sample completion at patch seams, followed by ownership-aware atlas dilation; no source geometry changes',
        raw_unresolved_samples=int(unresolved.sum()),regions=rows,
        raw_wrong_feature_ids=int(np.sum(mask&~unresolved&(np.abs(ids-(expected+1)/16)>.025))),
        final_unresolved_samples=0,limitation='Raw cage misses are retained and reported separately; completed texels are not new ray hits')
    (out/'seam-completion.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)


def texture(out, masters=True):
    atlas = np.load(out / 'atlas-context.npz')
    data = np.load(out / 'low-bake-context.npz')
    mask, face = atlas['mask'], atlas['face']
    expected = atlas['expected']; names = data['region_names'].tolist()
    nearest = distance_transform_edt(~mask, return_distances=False, return_indices=True)
    def dilate(v): return v[tuple(nearest)]
    position = (np.load(out / 'surface_position.npy')[:, :, :3] - .5) / 20
    x, y, z = [position[:, :, i] * 1000 for i in range(3)]
    r = np.hypot(x, z); theta = np.arctan2(z, x)
    region = np.maximum(face, 0)
    enamel = data['materials'][region] == 1
    convex = np.load(out / 'curvature_convex.npy')[:, :, 0]
    concave = np.load(out / 'curvature_concave.npy')[:, :, 0]
    near = np.load(out / 'ao_near.npy')[:, :, 0]
    local = np.load(out / 'ao_local.npy')[:, :, 0]
    # A restrained seam/local combination, never multiplied into albedo.
    occlusion = np.clip(1 - .30 * (1-near) - .20 * (1-local), .5, 1)
    concept = ROOT / 'docs/art/quarters/sheets/medal/c-machined-rim-seed130303.png'
    source = np.asarray(Image.open(concept).convert('RGB'), np.float32) / 255
    crop = source[348:871, 266:779]
    Image.fromarray(np.uint8(crop*255)).save(out / 'concept-body-color-source.jpg', quality=94)
    brass_pixels = (crop[:, :, 0] > crop[:, :, 2] * 1.5) & (crop[:, :, 0] > crop[:, :, 1] * 1.08) & (crop[:, :, 1] > .12)
    rgb = srgb_to_linear(crop)
    lum = rgb @ [.2126, .7152, .0722]
    brass_pixels &= (lum > .035) & (lum < .70)
    chroma = rgb / np.maximum(lum[:, :, None], .001)
    median_chroma = np.median(chroma[brass_pixels], axis=0)
    # Remove luminance and holes from the source before using its color variation.
    flattened = np.where(brass_pixels[:, :, None], chroma, median_chroma)
    flattened = gaussian_filter(flattened, (5, 5, 0))
    coords = np.array([np.clip((16-z)/32, 0, 1) * (crop.shape[0]-1), np.clip((x+16)/32, 0, 1) * (crop.shape[1]-1)])
    sampled = np.stack([map_coordinates(flattened[:, :, k], coords, order=1) for k in range(3)], -1)
    variation = np.clip(sampled / median_chroma, .85, 1.15)
    brass_base = np.array([.66, .43, .14])
    # Concept chromaticity is mixed conservatively with the accepted clean reflected-metal color.
    ref = median_chroma / np.max(median_chroma)
    brass_base = .8 * brass_base + .2 * ref * .66
    oxide_sample = np.median(rgb[brass_pixels & (lum < np.percentile(lum[brass_pixels], 25))], axis=0)
    oxide_base = oxide_sample / np.max(oxide_sample) * .085
    rng = np.random.default_rng(130303)
    scratch = np.zeros_like(x)
    rim = expected == names.index('rim')
    star = np.isin(expected, [names.index(k) for k in ['star_roof', 'star_bevel', 'star_center']])
    # Circumferential lathe texture, attenuated at the atlas Nyquist limit.
    brushing = .5 + .25 * np.sin(r * 2*np.pi/.085) + .15 * np.sin(r * 2*np.pi/.137 + 1.1)
    for _ in range(95):
        radius = rng.uniform(11.6, 15.9); center = rng.uniform(-np.pi, np.pi)
        width = rng.uniform(.01, .04); length = rng.uniform(.2, 1.5)
        along = np.arctan2(np.sin(theta-center), np.cos(theta-center)) * radius
        # The minimum filter footprint is a texel, rather than an unfiltered white line.
        across = np.exp(-.5*((r-radius)/max(width/2.355,.018))**2)
        ends = np.clip((length/2 - np.abs(along))/.06, 0, 1)
        scratch = np.maximum(scratch, across*ends*rim)
    phase = np.pi/2
    sector = np.floor(((theta-phase) % (2*np.pi))/(np.pi/5)).astype(int)
    direction = phase + (sector+.5)*np.pi/5
    across = -x*np.sin(direction)+z*np.cos(direction)
    facet_finish = .5 + .35*np.sin(across*2*np.pi/.11)
    for _ in range(55):
        cx, cz = rng.uniform(-10,10,2); length=rng.uniform(.2,1.5); width=rng.uniform(.01,.04)
        a=phase+(np.floor(((np.arctan2(cz,cx)-phase)%(2*np.pi))/(np.pi/5))+.5)*np.pi/5
        along=(x-cx)*np.cos(a)+(z-cz)*np.sin(a)
        cross=-(x-cx)*np.sin(a)+(z-cz)*np.cos(a)
        field=np.exp(-.5*(cross/max(width/2.355,.018))**2)*np.clip((length/2-abs(along))/.06,0,1)*star
        scratch=np.maximum(scratch,field)
    enamel_scuff=np.zeros_like(x)
    for _ in range(12):
        cx,cz=rng.uniform(-10,10,2);a=rng.uniform(0,np.pi)
        along=(x-cx)*np.cos(a)+(z-cz)*np.sin(a)
        across=-(x-cx)*np.sin(a)+(z-cz)*np.cos(a)
        length=rng.uniform(.25,.8)
        field=np.exp(-.5*(across/.025)**2)*np.clip((length/2-abs(along))/.06,0,1)*enamel
        enamel_scuff=np.maximum(enamel_scuff,field)
    finish=np.where(rim, brushing, np.where(star, facet_finish,.5))
    # Micrometre-scale height gradients become a perturbation in the existing tangent frame.
    height=(scratch*.0000006+(finish-.5)*.00000018)*~enamel
    height=gaussian_filter(height,.6)
    uv=data['uv']; points=data['vertices'][data['faces']]
    uv_edges=uv[:,1:]-uv[:,:1]
    uv_area=np.abs(uv_edges[:,0,0]*uv_edges[:,1,1]-uv_edges[:,0,1]*uv_edges[:,1,0])/2
    geom_area=np.linalg.norm(np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0]),axis=1)/2
    metres_per_texel=np.sqrt(geom_area/uv_area)/SIZE
    scale=metres_per_texel[np.maximum(face,0)]
    dv,du=np.gradient(height)
    micro=np.stack((-du/scale,-dv/scale,np.ones_like(height)),-1)
    geom=np.load(out/'geometry_normal.npy')[:,:,:3]*2-1
    detailed=normalize(geom+np.stack((micro[:,:,0],micro[:,:,1],np.zeros_like(x)),-1))
    save_png(out/'geometry_runtime_normal.png',dilate(normalize(geom)*.5+.5))
    cavity=np.clip(concave*.8+(1-near)*1.1+(1-local)*.35,0,1)
    cavity=np.clip(cavity-convex*.35,0,1)
    tarnish=np.clip((cavity-.16)/.42,0,1)*~enamel
    edge=(convex>.12)&~enamel&mask
    cavities=(cavity>.30)&~enamel&mask
    materials={}
    master=ROOT/'assets/props/quarters/dress_uniform/medal';master.mkdir(parents=True,exist_ok=True)
    for aged,prefix in [(False,'as_built'),(True,'aged')]:
        rough=np.where(enamel,.31 if aged else .215,.385 if aged else .30).astype(np.float32)
        rough+=np.where(enamel,0,(finish-.5)*.045+scratch*.045)
        rough=np.where((convex>.15)&~enamel,np.minimum(rough,.33 if aged else .20),rough)
        metal=np.where(enamel,0,.96 if aged else .985)
        albedo=np.where(enamel[:,:,None],np.array([.008,.025,.095]),brass_base*variation)
        untarnished_rough=rough+enamel_scuff*.055 if aged else rough.copy()
        save_png(out/(prefix+'_untarnished_albedo.png'),dilate(albedo),color=True)
        save_png(out/(prefix+'_untarnished_orm.png'),dilate(np.stack((occlusion,untarnished_rough,metal),-1)))
        stain=tarnish if aged else tarnish*.10
        albedo=albedo*(1-stain[:,:,None])+oxide_base*stain[:,:,None]
        rough=rough*(1-stain)+(.65 if aged else .37)*stain
        metal=metal*(1-stain)+.025*stain
        if aged:
            rough+=enamel_scuff*.055
        orm=np.stack((occlusion,rough,metal),-1)
        no_scratch=orm.copy();no_scratch[:,:,1]-=scratch*.045
        if aged:no_scratch[:,:,1]-=enamel_scuff*.055
        save_png(out/(prefix+'_no_scratch_orm.png'),dilate(no_scratch))
        if masters:
            save_png(master/(prefix+'_albedo.png'),dilate(albedo),color=True)
            save_png(master/(prefix+'_normal.png'),dilate(detailed*.5+.5))
            save_png(master/(prefix+'_orm.png'),dilate(orm))
        materials[prefix]=dict(brass_linear_base=brass_base.tolist(),oxide_linear_base=oxide_base.tolist(),
            brass_metallic_percentiles=np.percentile(metal[mask&~enamel],[0,50,100]).tolist(),
            brass_roughness_percentiles=np.percentile(rough[mask&~enamel],[0,50,100]).tolist(),
            enamel_roughness_percentiles=np.percentile(rough[mask&enamel],[0,50,100]).tolist(),
            enamel_metallic=0,enamel_specular=.5,enamel_coat_weight=.65,
            enamel_coat_roughness=.23 if aged else .13,brass_coat_weight=0)
    for key in ['curvature_convex','curvature_concave','ao_near','ao_local','geometry_normal']:
        import shutil
        if masters:shutil.copyfile(out/(key+'.png'),master/(key+'.png'))
    for key,value in [('tarnish_mask',tarnish),('scratch_mask',scratch),('convex_edge_mask',edge),('cavity_mask',cavities)]:
        save_png(out/(key+'.png'),value)
    save_png(out/'flat_normal.png',np.broadcast_to(np.array([.5,.5,1.]),(SIZE,SIZE,3)))
    flipped=detailed.copy();flipped[:,:,1]*=-1
    save_png(out/'inverted_green_normal.png',dilate(flipped*.5+.5))
    overstrong=normalize(geom+18*np.stack((micro[:,:,0],micro[:,:,1],np.zeros_like(x)),-1))
    save_png(out/'overstrong_normal.png',dilate(overstrong*.5+.5))
    np.savez_compressed(out/'material-fields.npz',tarnish=tarnish,cavity=cavity,convex=convex,scratch=scratch,mask=mask,enamel=enamel)
    ratio=float(np.mean(tarnish[cavities]>.5)/max(np.mean(tarnish[edge]>.5),1/edge.sum()))
    materials['authoring']=dict(source_concept=str(concept),source_crop=[266,348,779,871],
        color_method='Concept brass chromaticity with luminance removed; nonrepeating full-body source patch; generated lighting discarded',
        concept_brass_selected_pixels=int(brass_pixels.sum()),concept_median_chroma=median_chroma.tolist(),
        curvature_filter_sigmas_mm=[.1,.4],scratch_width_mm=[.01,.04],scratch_length_mm=[.2,1.5],
        scratch_depth_micrometres=.6,brushing_depth_micrometres=.18,ao_formula='1 - .30*(1-AO_0.3mm) - .20*(1-AO_2mm)',
        tarnish_cavity_occupancy=float(np.mean(tarnish[cavities]>.5)),tarnish_edge_occupancy=float(np.mean(tarnish[edge]>.5)),
        tarnish_cavity_to_edge_occupancy_ratio=ratio,uniform_tint_negative_control_ratio=1.0,
        hunyuan_paint='Not needed; exact material masks and controlled concept color used',
        tiling='No repeat sampling: one unique atlas; full-face source swatch is clamped once',
        master_directory=str(master))
    (out/'materials.json').write_text(json.dumps(materials,indent=2))
    print(json.dumps(materials,indent=2),flush=True)


if __name__=='__main__':
    mode,out=sys.argv[1],Path(sys.argv[2])
    if mode=='filter':filter_curvature(out)
    elif mode=='validate':validate(out)
    elif mode=='texture':texture(out)
    elif mode=='repair':repair(out)
    elif mode=='controls':texture(out,masters=False)
    else:raise ValueError(mode)
