"""Run the established utilities against fit2 without overwriting fit1 sources."""
from pathlib import Path
import sys
import types
SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE))
name=sys.argv[sys.argv.index('--script')+1]
path=SOURCE/name
text=path.read_text().replace('tmp/issue130-v3/fit1','tmp/issue130-v3/fit2')
if name=='build.py':
 text=text.replace("bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'medal-fitted.blend'))",'')
 text=text.replace("elif field and any(field.data[i].value for i in fs):e.use_edge_sharp=True","elif field and any(field.data[i].value for i in fs):e.use_edge_sharp=bool(cr and cr.data[e.index].value>=.99)")
 text=text.replace('[2300,900]','[2300,1100]')
 text=text.replace("stats=reduce_body(o,goal);", """hardware_vertices={i for edge in projected_edges(mesh) for i in edge}
 hardware_importance=np.array([300. if any(i in hardware_vertices for i in t.vertices) else 1. for t in mesh.loop_triangles])
 stats=reduce_body(o,goal,hardware_importance);""")
 text=text.replace('from unwrap8 import unwrap','from unwrap2 import unwrap')
 reducer=types.ModuleType('reduce_low')
 reduction=(SOURCE/'reduce_low.py').read_text()
 reduction=reduction.replace('feature_weights={',"""region_attribute=mesh.attributes.get('body_region2')
    region_flags=np.array([region_attribute.data[t.polygon_index].value for t in mesh.loop_triangles]) if region_attribute else None
    feature_weights={""")
 reduction=reduction.replace('        # The enamel is a single-valued front membrane.',"""        cross_old=np.linalg.norm(normal_old,axis=1)
        longest_new=np.max(np.linalg.norm(new-np.roll(new,1,axis=1),axis=2),axis=1)
        longest_old=np.max(np.linalg.norm(old-np.roll(old,1,axis=1),axis=2),axis=1)
        if np.any(longest_new**2/lengths>np.maximum(60.,longest_old**2/cross_old*1.01)):
            continue
        # The enamel is a single-valued front membrane.""")
 reduction=reduction.replace("    crease=mesh.attributes.get('crease_edge') or", """    if region_flags is not None:
        region=mesh.attributes.get('body_region2') or mesh.attributes.new('body_region2','INT','FACE')
        for face,flag in zip(mesh.polygons,region_flags[valid]):region.data[face.index].value=int(flag)
    crease=mesh.attributes.get('crease_edge') or""")
 reduction=reduction.replace('normal_new[field_flags[remaining]>0,1]>=-1e-12','normal_new[(region_flags[remaining]==1) if region_flags is not None else (field_flags[remaining]>0),1]>=-1e-12')
 reduction=reduction.replace('        local=neighbours(a)|neighbours(b)',"""        if region_flags is not None and np.any(normal_new[region_flags[remaining]==2,1]<=1e-12):
            continue
        local=neighbours(a)|neighbours(b)""")
 exec(compile(reduction,str(SOURCE/'reduce_low.py'),'exec'),reducer.__dict__)
 sys.modules['reduce_low']=reducer
 text=text.replace('body_mesh=lows[0].data;body_mesh.calc_loop_triangles()',"""body_mesh=lows[0].data;body_mesh.calc_loop_triangles()
region=body_mesh.attributes['body_region2'];owners2=defaultdict(list);field_owners2=defaultdict(list)
for p in body_mesh.polygons:
 for e in p.edge_keys:
  owners2[tuple(sorted(e))].append(region.data[p.index].value)
  field_owners2[tuple(sorted(e))].append(body_mesh.attributes['enamel_field7'].data[p.index].value)
for e in body_mesh.edges:
 key=tuple(sorted(e.vertices))
 if len(set(owners2[key]))>1 or len(set(field_owners2[key]))>1:
  item=body_mesh.attributes['crease_edge'].data[e.index];item.value=max(item.value,.0002)""")
if name=='final.py':
 text=text.replace("(SOURCE/'surface_gate.py').read_text()", "(SOURCE/'surface_gate.py').read_text().replace('tmp/issue130-v3/fit1','tmp/issue130-v3/fit2')")
 text=text.replace('v3 fit1','v3 fit2').replace("str(SOURCE/'medal-fitted.blend')","str(OUT/'medal-fitted.blend')")
 text=text.replace("f'Editable source: `{SOURCE}/medal-fitted.blend`.'","f'Editable source: `{OUT}/medal-fitted.blend`.'")
exec(compile(text,str(path),'exec'),{'__name__':'__main__','__file__':str(path)})
