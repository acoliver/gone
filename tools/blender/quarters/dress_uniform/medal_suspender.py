"""#130 closed-slot suspender and full-width ribbon, without changing body or ring."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
from aging_support import components
from tunic_details import extract_ribbon, points, binding, geometry_hash
from build import activate, recalc, join_named
from medal_mount_checks import upper_ribbon_samples, assert_upper_preserved

ATLAS_RECT = (1725, 0, 256)


def closed_frame(name, outer, inner, depth):
    vertices = []
    for y in depth:
        for shape in [outer, inner]:
            vertices.extend([(x, y, z) for x, z in shape])
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces.extend([(i, j, 4+j, 4+i), (8+i, 12+i, 12+j, 8+j),
                      (i, 8+i, 8+j, j), (4+i, 4+j, 12+j, 12+i)])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    recalc(obj)
    return obj


def rectangle(x, bottom, top):
    return [(-x, bottom), (x, bottom), (x, top), (-x, top)]


def suspender(brass):
    obj = closed_frame('ClosedSlotSuspender', rectangle(.0124, .02185, .0254),
                       rectangle(.0115, .0224, .024), [-.0027, -.0013])
    lug = closed_frame('RingLug', rectangle(.0012, .01955, .02215),
                       rectangle(.0007, .02005, .0214), [-.0025, -.0015])
    for v in obj.data.vertices: v.co.y -= .0008
    activate(obj)
    boolean = obj.modifiers.new('Integral ring lug', 'BOOLEAN')
    boolean.operation = 'UNION'
    boolean.solver = 'EXACT'
    boolean.object = lug
    bpy.ops.object.modifier_apply(modifier=boolean.name)
    bpy.data.objects.remove(lug, do_unlink=True)
    # Millimetre-space bevel avoids Blender's small-coordinate modifier tolerance.
    for v in obj.data.vertices: v.co *= 1000
    bevel = obj.modifiers.new('Finished suspender edges', 'BEVEL')
    bevel.width = .065
    bevel.segments = 1
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for v in obj.data.vertices: v.co /= 1000
    recalc(obj)
    obj.data.materials.append(brass)
    obj.data.update()
    # Separate nonoverlapping face charts in unused atlas space; neutral normals on this new solid.
    x0, y0, size = ATLAS_RECT
    assert len(obj.data.polygons) <= 144
    for name in ['DetailUV', 'BakeUV']:
        layer = obj.data.uv_layers.new(name=name)
        for p in obj.data.polygons:
            axis = int(np.argmax(abs(np.array(p.normal))))
            axes = [k for k in range(3) if k != axis]
            coords = np.array([obj.data.vertices[i].co[:] for i in p.vertices])[:, axes]
            coords = (coords-coords.min(0)) / np.maximum(np.ptp(coords, axis=0), 1e-12)
            col, row = p.index % 12, p.index // 12
            uv = (coords * 12 + [x0+col*20+4, y0+row*20+4]) / 2048
            for i, value in zip(p.loop_indices, uv): layer.data[i].uv = value
    colour = obj.data.color_attributes.new(name='RibbonColours', type='FLOAT_COLOR', domain='CORNER')
    for value in colour.data: value.color = (1, 1, 1, 1)
    for p in obj.data.polygons: p.use_smooth = False
    return obj


def full_loop(ribbon, template, origin, frame):
    old = ribbon.data
    local = np.einsum('ij,kj->ik', points(ribbon)-origin, frame)
    reference = np.einsum('ij,kj->ik', points(template)-origin, frame)
    assert len(reference) == 70
    stations = np.array([0.,.25,.35,.5,.65,.75,1.])
    top = []
    for side in range(2):
        row = []
        for t in stations:
            a = min(int(t*4),3); f = t*4-a
            target = reference[side*35+5+a]*(1-f)+reference[side*35+6+a]*f
            row.append(int(np.argmin(np.linalg.norm(local-target,axis=1))))
        top.append(row)
    names = list(old.uv_layers.keys())
    attr = {}
    for p in old.polygons:
        for i in p.loop_indices:
            attr[old.loops[i].vertex_index] = np.r_[*[old.uv_layers[n].data[i].uv[:] for n in names], old.color_attributes['RibbonColours'].data[i].color[:]]
    vertices = local.tolist()
    values = [attr[i] for i in range(len(local))]
    faces, corners = [], []
    for p in old.polygons:
        if min(local[list(p.vertices),2]) < .02319: continue
        faces.append(list(p.vertices))
        corners.append([np.r_[*[old.uv_layers[n].data[i].uv[:] for n in names], old.color_attributes['RibbonColours'].data[i].color[:]] for i in p.loop_indices])
    # The incoming cloth passes through the slot above the lower rail, then wraps below it.
    path = [(-1.6,23.1),(-2.4,23.1),(-3.5,23.1)]
    normals = [(0.,1.)]*len(path)
    for angle in np.linspace(-.5*np.pi,-np.pi,5)[1:]:
        path.append((-3.5+.5*np.cos(angle),23.6+.5*np.sin(angle)))
        normals.append((-np.cos(angle),-np.sin(angle)))
    path.append((-4.,25.335)); normals.append((1.,0.))
    for angle in np.linspace(np.pi,.5*np.pi,7)[1:]:
        path.append((-3.435+.565*np.cos(angle),25.335+.565*np.sin(angle)))
        normals.append((-np.cos(angle),-np.sin(angle)))
    path.append((-2.165,25.9)); normals.append((0.,-1.))
    for angle in np.linspace(.5*np.pi,0,7)[1:]:
        path.append((-2.165+.565*np.cos(angle),25.335+.565*np.sin(angle)))
        normals.append((-np.cos(angle),-np.sin(angle)))
    path.append((-1.6,24.6)); normals.append((-1.,0.))
    path = np.array(path)*.001
    outward = np.array(normals)
    longitudinal = np.r_[0., np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
    layers = [top]
    for k, (yz, normal) in enumerate(zip(path, outward)):
        row = []
        for side in range(2):
            ids = []
            for j,t in enumerate(stations):
                a=min(int(t*4),3); fraction=t*4-a
                width_x=reference[a,0]*(1-fraction)+reference[a+1,0]*fraction
                p = np.r_[width_x, yz + normal*(.0004 if side==0 else -.0004)]
                ids.append(len(vertices)); vertices.append(p.tolist())
                value=attr[top[side][j]].copy()
                value[1] += (.0016 + longitudinal[k]) / 1.066
                values.append(value)
            row.append(ids)
        layers.append(row)
    for previous, following in zip(layers, layers[1:]):
        for side in range(2):
            for j in range(6): faces.append([previous[side][j],previous[side][j+1],following[side][j+1],following[side][j]])
        for j in [0,6]: faces.append([previous[0][j],following[0][j],following[1][j],previous[1][j]])
    for j in range(6): faces.append([layers[-1][0][j],layers[-1][1][j],layers[-1][1][j+1],layers[-1][0][j+1]])
    used = sorted({i for f in faces for i in f}); remap = {v:i for i,v in enumerate(used)}
    mesh = bpy.data.meshes.new('UnbrokenWovenRibbon')
    world = origin+np.einsum('ij,jk->ik', np.array(vertices)[used], frame)
    saved_world = points(ribbon)
    for k,i in enumerate(used):
        if i<len(local): world[k]=saved_world[i]
    mesh.from_pydata(world.tolist(), [], [[remap[i] for i in f] for f in faces])
    mesh.materials.append(old.materials[0])
    for n,name in enumerate(names):
        layer = mesh.uv_layers.new(name=name)
        for p in mesh.polygons:
            for c,i in enumerate(p.loop_indices):
                v = corners[p.index][c] if p.index<len(corners) else values[used[mesh.loops[i].vertex_index]]
                layer.data[i].uv = v[n*2:n*2+2]
    colour = mesh.color_attributes.new(name='RibbonColours', type='FLOAT_COLOR', domain='CORNER')
    for p in mesh.polygons:
        for c,i in enumerate(p.loop_indices):
            colour.data[i].color = (corners[p.index][c] if p.index<len(corners) else values[used[mesh.loops[i].vertex_index]])[-4:]
    ribbon.data = mesh
    recalc(ribbon)
    for p in mesh.polygons: p.use_smooth = True
    anchors=np.array(json.loads(ribbon['attachment'])['base_blender_m'])
    return [remap[i] for i in used if i<len(local) and np.any(np.max(abs(anchors-saved_world[i]),axis=1)<1e-9)]


def refresh_maps(obj, state):
    prefix = 'aged' if state=='present' else 'as_built'
    for mat in obj.data.materials[:2]:
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                role = next(k for k in ['albedo','normal','orm'] if k in node.image.name.lower())
                image = bpy.data.images.load(str(ROOT/f'assets/props/quarters/dress_uniform/medal/{prefix}_{role}.png'), check_existing=False)
                image.colorspace_settings.name = 'sRGB' if role=='albedo' else 'Non-Color'
                image.pack(); node.image = image
        bsdf = next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        bsdf.inputs['Coat Weight'].default_value = .35 if 'Enamel' in mat.name else 0
        bsdf.inputs['Coat Roughness'].default_value = .26 if state=='present' else .18


def build(baseline, original, output):
    output.mkdir(parents=True, exist_ok=True)
    report = {}
    for name,state in [('working','remembered'),('pilot','present')]:
        bpy.ops.wm.open_mainfile(filepath=str(baseline/f'tunic-{name}.blend'))
        old = bpy.data.objects['Medal']; body = bpy.data.objects['TunicBody']
        frozen = {o.name:geometry_hash(o) for o in bpy.context.scene.objects if o.type=='MESH' and o!=old}
        metadata = dict(old.items())
        f = json.loads(old['medal_frame']); origin,frame = np.array(f['origin']),np.array(f['frame'])
        upper = upper_ribbon_samples(old, f)
        with bpy.data.libraries.load(str(original/f'tunic-{name}.blend'), link=False) as (_, dest): dest.objects=['Medal']
        source = dest.objects[0]
        bpy.context.collection.objects.link(source)
        source.data.materials[2] = old.data.materials[2]
        template = extract_ribbon(source)
        ribbon = extract_ribbon(old)
        bpy.data.objects.remove(source,do_unlink=True)
        anchors = full_loop(ribbon, template, origin, frame)
        bpy.data.objects.remove(template,do_unlink=True)
        # Retain the exact original body, integral eyelet and ring vertices, topology and UVs.
        groups = components(old)
        keep = [g for g in groups if len(g) in [3017,1024]]
        assert len(keep)==2
        keep_ids = set(keep[0])|set(keep[1])
        bm = bmesh.new();bm.from_mesh(old.data);bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in keep_ids],context='VERTS')
        bm.to_mesh(old.data);bm.free()
        while len(old.data.materials)>2: old.data.materials.pop(index=len(old.data.materials)-1)
        refresh_maps(old,state)
        weave = ribbon.data.materials[0].copy()
        weave.name = 'RibbonFabric_Medal'
        ribbon.data.materials[0] = weave
        bsdf = next(n for n in weave.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        uv = weave.node_tree.nodes.new('ShaderNodeUVMap'); uv.uv_map='DetailUV'
        scale = weave.node_tree.nodes.new('ShaderNodeMapping')
        scale.inputs['Scale'].default_value=(680,680,1)
        weave.node_tree.links.new(uv.outputs[0],scale.inputs[0])
        colour = weave.node_tree.nodes.new('ShaderNodeTexImage')
        colour.image=bpy.data.images.load(str(ROOT/'assets/props/quarters/dress_uniform/medal/ribbon_weave_albedo.png'),check_existing=False)
        colour.image.colorspace_settings.name='sRGB'; colour.image.pack()
        weave.node_tree.links.new(scale.outputs[0],colour.inputs['Vector'])
        stripes = next(n for n in weave.node_tree.nodes if n.type=='VERTEX_COLOR')
        pigment = weave.node_tree.nodes.new('ShaderNodeMix')
        pigment.data_type='RGBA'; pigment.blend_type='MULTIPLY'; pigment.inputs[0].default_value=1
        weave.node_tree.links.new(colour.outputs['Color'],pigment.inputs[6])
        weave.node_tree.links.new(stripes.outputs['Color'],pigment.inputs[7])
        weave.node_tree.links.new(pigment.outputs[2],bsdf.inputs['Base Color'])
        tex = weave.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image=bpy.data.images.load(str(ROOT/'assets/props/quarters/dress_uniform/medal/ribbon_weave_normal.png'),check_existing=False)
        tex.image.colorspace_settings.name='Non-Color'; tex.image.pack()
        weave.node_tree.links.new(scale.outputs[0],tex.inputs['Vector'])
        normal = weave.node_tree.nodes.new('ShaderNodeNormalMap'); normal.uv_map='DetailUV'
        weave.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color'])
        weave.node_tree.links.new(normal.outputs[0],bsdf.inputs['Normal'])
        roughness = weave.node_tree.nodes.new('ShaderNodeTexImage')
        roughness.image=bpy.data.images.load(str(ROOT/'assets/props/quarters/dress_uniform/medal/ribbon_weave_roughness.png'),check_existing=False)
        roughness.image.colorspace_settings.name='Non-Color'; roughness.image.pack()
        weave.node_tree.links.new(scale.outputs[0],roughness.inputs['Vector'])
        weave.node_tree.links.new(roughness.outputs['Color'],bsdf.inputs['Roughness'])
        bsdf.inputs['Roughness'].default_value=.59 if state=='present' else .52
        bsdf.inputs['Specular IOR Level'].default_value=.4
        holder = suspender(old.data.materials[0])
        holder.data.transform(Matrix.Translation(Vector(origin)) @ Matrix(frame.T.tolist()).to_4x4())
        metal_count = len(old.data.vertices)+len(holder.data.vertices)
        obj = join_named([old,holder],'Medal')
        obj = join_named([obj,ribbon],'Medal')
        for key,value in metadata.items(): obj[key]=value
        obj['ribbon_loop'] = json.dumps(dict(loop_wrap_degrees=180,folded_tongues=1,full_width=True,cloth_thickness_m=.0008,
            slot_width_m=.023,slot_height_m=.0016,minimum_design_clearance_m=.00008,
            ring_lug_separate_from_ribbon=True,loop_bottom_local_z_m=.0227))
        eyelet = json.loads(metadata['eyelet'])
        eyelet['construction']='integral eyelet, unchanged jump ring, closed-slot straight-bar suspender with lower lug'
        eyelet['ribbon_loop']=json.loads(obj['ribbon_loop'])
        obj['eyelet']=json.dumps(eyelet)
        positions = points(obj)
        reverse = list(json.loads(metadata['attachment'])['metal_base_vertex_indices'])
        bases = reverse+[metal_count+i for i in anchors]
        attachment = json.loads(metadata['attachment'])
        attachment.update(base_vertex_indices=bases,base_blender_m=positions[bases].tolist())
        obj['attachment']=json.dumps(attachment)
        fitted=json.loads(metadata['fitted_medal']);obj.data.calc_loop_triangles()
        solid=sum(t.material_index<2 for t in obj.data.loop_triangles)
        fitted['solid_triangles']=solid;obj['fitted_medal']=json.dumps(fitted)
        if name=='pilot':
            record=json.loads(bpy.context.scene['tunic5_record'])
            record['bindings']['Medal']=binding(obj,[list(range(metal_count)),list(range(metal_count,len(positions)))],body,True)
            bpy.context.scene['tunic5_record']=json.dumps(record)
        assert_upper_preserved(upper,obj,f)
        assert all(geometry_hash(bpy.data.objects[n])==h for n,h in frozen.items())
        for mesh in bpy.context.scene.objects:
            if mesh.type=='MESH' and mesh.get('aged_export' if name=='pilot' else 'export'):mesh.data.name=mesh.name
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(output/f'tunic-{name}.blend'))
        report[name]={'solid_triangles':solid,'ribbon_triangles':len(obj.data.loop_triangles)-solid,'upper_samples_exact':len(upper)}
    (output/'suspender.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['baseline','original','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    build(a.baseline.resolve(),a.original.resolve(),a.output.resolve())
