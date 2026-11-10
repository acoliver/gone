"""Choose measured face edits after spatially uniform photometric calibration."""
import json

import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import least_squares

from colour import lab, linear, srgb
from locker_faces import SOURCE, SCRATCH, FACES, scores, eligible, pack, paint_fields
from locker_swatches import flatten_lighting


def from_lab(value):
    l,a,b = np.moveaxis(value,-1,0)
    f = np.stack([(l+16)/116+a/500,(l+16)/116,(l+16)/116-b/200],-1)
    xyz = np.where(f>6/29,f**3,3*(6/29)**2*(f-4/29))*[.95047,1,1.08883]
    energy = xyz @ np.linalg.inv(np.array([[.4124564,.3575761,.1804375],[.2126729,.7151522,.0721750],[.0193339,.1191920,.9503041]])).T
    return np.clip(srgb(np.maximum(energy,0)),0,1)


def calibrate(image, reference):
    raw = np.asarray(image.convert('RGB'),float)/255
    flat = flatten_lighting(raw)
    step = max(1,int(np.sqrt(flat.shape[0]*flat.shape[1]/18000)))
    sample = flat[::step,::step]
    target = np.asarray(reference.convert('RGB'),float)/255
    observed = lab(sample)
    expected = lab(target)
    source_paint = paint_fields(Image.fromarray(np.uint8(sample*255)))[1] >= .5
    target_paint = paint_fields(reference)[1] >= .5
    classes = [(source_paint,target_paint),(~source_paint,~target_paint)]
    if any(not a.any() or not b.any() for a,b in classes):
        return image,dict(error='missing pigment class')
    centre = observed.mean((0,1))
    desired = expected.mean((0,1))
    def transform(values, parameters):
        return (values-centre) @ parameters[:9].reshape(3,3).T + parameters[9:]
    def flatten_plane(colour):
        energy = linear(colour)
        h,w = energy.shape[:2]
        yy,xx = np.mgrid[:h,:w]
        design = np.stack([xx.ravel()/w-.5,yy.ravel()/h-.5,np.ones(w*h)],-1)
        lum = energy @ [.2126,.7152,.0722]
        coefficient = np.linalg.lstsq(design,lum.ravel(),rcond=None)[0]
        plane = (design[:,:2] @ coefficient[:2]).reshape(h,w)
        adjusted = np.maximum(lum-plane,.002)
        return np.clip(srgb(np.clip(energy*adjusted[...,None]/np.maximum(lum[...,None],1e-6),0,1)),0,1)
    def residual(parameters):
        converted = lab(flatten_plane(from_lab(transform(observed,parameters))))
        # A single affine colour transform applies everywhere. It never uses a
        # spatial mask to replace colour or manufacture a corrosion boundary.
        result = []
        for a,b in classes:
            result.extend((converted[a].mean(0)-expected[b].mean(0)).tolist())
            result.extend((converted[a].std(0)-expected[b].std(0)).tolist())
        result.extend(((converted.mean((0,1))-desired)*.5).tolist())
        result.extend(((parameters[:9].reshape(3,3)-np.eye(3))*.3).ravel().tolist())
        return np.array(result)
    fit = least_squares(residual,np.r_[np.eye(3).ravel(),desired],max_nfev=50)
    colour = flatten_plane(from_lab(transform(lab(flat),fit.x)))
    result = Image.fromarray(np.uint8(np.round(colour*255)))
    return result,dict(flatten_log_linear_plane=True,lab_affine_matrix=fit.x[:9].reshape(3,3).tolist(),
                       lab_input_centre=centre.tolist(),lab_output_centre=fit.x[9:].tolist(),
                       method='global spatially uniform Lab affine, no pigment replacement or spatial colour masks')


def main():
    all_rows, selection = {}, {}
    cached = json.loads((SOURCE/'candidate-scores.json').read_text()) if (SOURCE/'candidate-scores.json').exists() else {}
    for name,face in FACES.items():
        reference = Image.open(SOURCE/f'{name}-source.png').convert('RGB')
        rows = []
        for path in sorted(SOURCE.glob(name+'-[0-9]*.png')):
            if not path.stem.rsplit('-',1)[1].isdigit():
                continue
            metadata = json.loads(path.with_suffix('.metadata.json').read_text())
            if metadata.get('visual_rejection'): continue
            raw = Image.open(path).convert('RGB')
            for method in ('affine','quantile-affine','quantile33-affine','quantile67-affine'):
                chosen = path.stem+'-'+method+'.png'
                existing = next((r for r in cached.get(name,[]) if r['chosen']==chosen),None)
                if existing is not None and (SOURCE/chosen).exists():
                    rows.append(existing)
                    continue
                input_image = raw
                transfer = {}
                if method != 'affine':
                    a = lab(np.asarray(raw)/255)
                    b = lab(np.asarray(reference)/255)
                    quantiles = np.linspace(0,1,257)
                    original = [np.quantile(a[...,c],quantiles) for c in range(3)]
                    target = [np.quantile(b[...,c],quantiles) for c in range(3)]
                    corrected = np.stack([np.interp(a[...,c],original[c],target[c]) for c in range(3)],-1)
                    amount = {'quantile-affine':1.,'quantile33-affine':.33,'quantile67-affine':.67}[method]
                    corrected = a + (corrected-a)*amount
                    input_image = Image.fromarray(np.uint8(np.round(from_lab(corrected)*255)))
                    transfer = dict(amount=amount,input_quantiles=np.array(original).tolist(),target_quantiles=np.array(target).tolist())
                image, calibration = calibrate(input_image,reference)
                chosen = path.stem+'-'+method+'.png'
                image.save(SOURCE/chosen)
                values = scores(image,reference,face)
                rank = (sum(v for k,v in values.items() if k.endswith('delta_e'))
                        + values['secondary_autocorrelation']*8
                        + values['planar_light_gradient']*20
                        + abs(values['broad_rust']-.15)*10)
                row = dict(seed=metadata['seed'],raw=path.name,chosen=chosen,calibration=calibration,
                           transfer=transfer,scores=values,rank_score=rank,
                           eligible=eligible(values,name=='hardware'))
                rows.append(row)
                print(name,row['seed'],method,row['eligible'],values,flush=True)
        all_rows[name] = rows
        valid = [row for row in rows if row['eligible']]
        # Failed faces remain reported and must not be described as accepted.
        pool = valid or rows
        selection[name] = min(pool,key=lambda r:(sum(max(0,v-8) for k,v in r['scores'].items() if k.endswith('delta_e'))
                              +max(0,1.8-r['scores']['edge_broad_ratio'])*10
                              +max(0,r['scores']['planar_light_gradient']-.06)*100
                              +max(0,r['scores']['secondary_autocorrelation']-.5)*20,r['rank_score']))
    (SOURCE/'candidate-scores.json').write_text(json.dumps(all_rows,indent=2)+'\n')
    (SOURCE/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
    pack(selection)
    sheet = Image.new('RGB',(1024,len(FACES)*390),'#24282a')
    draw = ImageDraw.Draw(sheet)
    for index,(name,row) in enumerate(selection.items()):
        for col,path in enumerate([f'{name}-source.png',row['chosen']]):
            image = Image.open(SOURCE/path).convert('RGB')
            image.thumbnail((490,340))
            sheet.paste(image,(col*512+(512-image.width)//2,index*390+32))
        draw.text((12,index*390+8),f'{name} source | seed {row["seed"]}: {"PASS" if row["eligible"] else "FAIL"}',fill='white')
    sheet.save(SCRATCH/'faces.png')
    door = Image.open(SOURCE/selection['door']['chosen']).convert('RGB')
    crop = Image.open(SOURCE/'door-source.png').convert('RGB').resize(door.size,Image.Resampling.LANCZOS)
    comparison = Image.new('RGB',(door.width*2,door.height))
    comparison.paste(door,(0,0)); comparison.paste(crop,(door.width,0))
    comparison.save(SCRATCH/'pattern-compare.png')
    print('ELIGIBLE',sum(r['eligible'] for r in selection.values()),'/',len(selection),flush=True)


if __name__=='__main__': main()
