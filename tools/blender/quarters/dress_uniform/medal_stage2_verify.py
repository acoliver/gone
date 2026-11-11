"""Independent standalone stage-two geometry preservation and texture-binding checks."""
import json
from pathlib import Path
import struct
import sys

import bpy
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from medal_stage2_bake import mesh_arrays


def verify(out):
    bpy.ops.wm.open_mainfile(filepath=str(HERE/'medal-low.blend'))
    originals={name:mesh_arrays(bpy.data.objects[name]) for name in ['MedalHigh','MedalLow']}
    uv=np.array([p.uv[:] for p in bpy.data.objects['MedalLow'].data.uv_layers.active.data])
    atlas=np.load(out/'atlas-context.npz')
    rows=[]
    for state in ['remembered','present']:
        bpy.ops.wm.open_mainfile(filepath=str(out/f'medal-pbr-{state}.blend'))
        result={'state':state,'objects':{}}
        for name in ['MedalHigh','MedalLow']:
            obj=bpy.data.objects[name];now=mesh_arrays(obj)
            preserved={key:bool(np.array_equal(value,now[key])) for key,value in originals[name].items()}
            assert all(preserved.values()),(state,name,preserved)
            if name=='MedalLow':
                assert np.array_equal(uv,np.array([p.uv[:] for p in obj.data.uv_layers.active.data]))
            obj.data.calc_tangents(uvmap='MedalUV')
            t=np.array([p.tangent[:] for p in obj.data.loops]);n=np.array([p.vector[:] for p in obj.data.corner_normals])
            tangent_error=float(np.max(abs(np.linalg.norm(t,axis=1)-1)))
            ortho_error=float(np.max(abs(np.sum(t*n,axis=1))))
            if name=='MedalLow':
                assert tangent_error<1e-4 and ortho_error<1e-4,(name,tangent_error,ortho_error)
            textures=[]
            for mat in obj.data.materials:
                for node in mat.node_tree.nodes:
                    if node.type=='TEX_IMAGE':
                        image=node.image;role='albedo' if image.name.endswith('_albedo.png') else 'data'
                        assert image.colorspace_settings.name==('sRGB' if role=='albedo' else 'Non-Color'),image.name
                        assert tuple(image.size)==(2048,2048),image.name
                        assert node.extension=='EXTEND'
                        textures.append(dict(material=mat.name,image=image.filepath,colorspace=image.colorspace_settings.name,filter=node.interpolation))
            coords=np.array([p.uv[:] for p in obj.data.uv_layers.active.data]).reshape(-1,3,2).mean(axis=1)
            ix=np.clip((coords*2048).astype(int),0,2047)
            sampled=atlas['expected'][ix[:,1],ix[:,0]]
            sampled_mask=atlas['mask'][ix[:,1],ix[:,0]]
            # Only atlas interiors classify confidently; gutter samples are deliberately dilated.
            material_wrong=sampled_mask&((sampled==2)!=(now['regions']==2))
            area=np.array([p.area for p in obj.data.polygons])
            result['objects'][name]=dict(triangles=len(obj.data.polygons),preserved=preserved,
                unit_tangent_max_error=tangent_error,tangent_normal_orthogonality_max_error=ortho_error,
                material_slots=len(obj.data.materials),textures=textures,
                mapped_face_centres_in_wrong_material_interior=int(material_wrong.sum()),
                mapped_wrong_material_surface_area_fraction=float(area[material_wrong].sum()/area.sum()))
        rows.append(result)
    maps=[]
    master=HERE.parents[3]/'assets/props/quarters/dress_uniform/medal'
    for path in sorted(master.glob('*.png')):
        width,height,depth,color_type=struct.unpack('>IIBB',path.read_bytes()[16:26])
        # #130: the mounted cloth patch is 512 square; standalone medal maps remain 2048.
        expected = (512,512) if path.name in ['as_built_contact.png','aged_contact.png'] else (2048,2048)
        assert (width,height)==expected
        maps.append(dict(name=path.name,width=width,height=height,bit_depth=depth,png_color_type=color_type))
    rays=json.loads((out/'cage-ray-audit.json').read_text())
    report=dict(geometry_and_low_uv_preservation_pass=True,states=rows,maps=maps,
        actual_cage_rays=rays['total_rays'],actual_cage_misses=rays['misses'],actual_wrong_region_hits=rays['wrong_region_hits'],
        raw_cage_zero_misses_pass=rays['misses']==0,raw_cage_limit='See cage-ray-audit.json and seam-completion.json: subtexel seam completion is not counted as a ray hit')
    (out/'source-verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':verify(Path(sys.argv[sys.argv.index('--')+1]))
