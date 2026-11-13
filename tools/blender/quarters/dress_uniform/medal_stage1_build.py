"""Build guide-fitted, continuous medal surfaces and the ribbon-constrained bail."""
import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

from medal_photoreal import HERE, activate, surface_tree


def mesh(name, vertices, faces, materials, slots=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata((np.asarray(vertices) / 1000).tolist(), [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    for material in materials:
        data.materials.append(material)
    if slots is not None:
        for face, slot in zip(data.polygons, slots):
            face.material_index = slot
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    for face in data.polygons:
        face.use_smooth = True
    return obj


def material(name, color, metallic, roughness):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Metallic'].default_value = metallic
    node.inputs['Roughness'].default_value = roughness
    return mat


def bridge(a, b, angles_a=None, angles_b=None):
    n, m = len(a), len(b)
    angles_a=np.arange(n)*2*np.pi/n if angles_a is None else angles_a
    angles_b=np.arange(m)*2*np.pi/m if angles_b is None else angles_b
    faces, i, j = [], 0, 0
    while i < n or j < m:
        ta=(angles_a[i+1] if i+1<n else angles_a[0]+2*np.pi) if i<n else float('inf')
        tb=(angles_b[j+1] if j+1<m else angles_b[0]+2*np.pi) if j<m else float('inf')
        if abs(ta-tb) < 1e-9:
            faces.append((a[i % n], a[(i+1) % n], b[(j+1) % m], b[j % m]))
            i, j = i+1, j+1
        elif ta < tb:
            faces.append((a[i % n], a[(i+1) % n], b[j % m]))
            i += 1
        else:
            faces.append((a[i % n], b[(j+1) % m], b[j % m]))
            j += 1
    return faces


def enamel_annulus(a,b,vertices):
    ids=a+b
    points=[Vector((vertices[i][0],vertices[i][2])) for i in ids]
    edges=[(i,(i+1)%len(a)) for i in range(len(a))]
    edges += [(len(a)+i,len(a)+(i+1)%len(b)) for i in range(len(b))]
    xy,_,faces,original,_,_=delaunay_2d_cdt(points,edges,[],0,1e-8)
    assert all(len(indices)==1 for indices in original), 'Unexpected new enamel intersection'
    hole=np.array([[vertices[i][0],vertices[i][2]] for i in b])
    def inside(point):
        x,y=point
        contained=False
        for p,q in zip(hole,np.roll(hole,-1,axis=0)):
            if (p[1]>y)!=(q[1]>y) and x<(q[0]-p[0])*(y-p[1])/(q[1]-p[1])+p[0]:
                contained=not contained
        return contained
    result=[]
    for face in faces:
        center=np.mean([xy[i][:] for i in face],axis=0)
        if not inside(center):result.append(tuple(ids[original[i][0]] for i in face))
    return result


class Features:
    def __init__(self, out):
        self.data = np.load(out / 'feature-fit.npz')
        self.report = json.loads((out / 'feature-fit.json').read_text())
        self.phase = float(self.data['phase'])
        self.inner, self.channel, self.crown = [x['radius_mm'] for x in self.report['landmarks']]
        self.peak = float(np.quantile(self.data['smooth_depth_mm'][:, self.data['radii_mm'] < .8], .95))
        anchors=self.phase+np.arange(10)*np.pi/5
        raw=np.interp(anchors%(2*np.pi),self.data['angles'],self.data['outline_mm'],period=2*np.pi)
        self.tip=float(np.median(raw[::2]))
        self.notch=float(np.median(raw[1::2]))
        self.star_angles=anchors
        rr=np.where(np.arange(10)%2==0,self.tip,self.notch)
        self.star_polygon=np.c_[rr*np.cos(anchors),rr*np.sin(anchors)]
        self.report['star_manufacturing_fit']=dict(raw_anchor_radii_mm=raw.tolist(),
            tip_radius_mm=self.tip,notch_radius_mm=self.notch,central_land_depth_mm=2.18,
            virtual_apex_depth_mm=2.20,ridge_bevel_mm=.035,
            reason='Use the median of the five guide arms/notches, straight contour edges and ten planar facets. The guide height field falls from about 3.28 mm centrally to about 0.95-1.37 mm at the contour; preserve its rising relief, not its angular noise.')

    def outline(self, angle):
        angle=np.asarray(angle)
        index=np.floor(((angle-self.phase)%(2*np.pi))/(np.pi/5)).astype(int)%10
        p=self.star_polygon[index]
        edge=self.star_polygon[(index+1)%10]-p
        direction=np.stack([np.cos(angle),np.sin(angle)],axis=-1)
        cross=lambda a,b:a[...,0]*b[...,1]-a[...,1]*b[...,0]
        return cross(p,edge)/cross(direction,edge)

    def rim(self, radius, grooves=True):
        # Monotone cubic sampled by the numerical fit rather than a hard-coded radial profile.
        x, y = self.data['rim_r_mm'], self.data['rim_d_mm']
        slopes = np.diff(y)/np.diff(x)
        tangents = np.zeros(len(x))
        for i in range(1, len(x)-1):
            if slopes[i-1]*slopes[i] > 0:
                tangents[i] = 2/(1/slopes[i-1]+1/slopes[i])
        idx = np.clip(np.searchsorted(x, radius)-1, 0, len(x)-2)
        h = x[idx+1]-x[idx]
        t = np.clip((radius-x[idx])/h, 0, 1)
        value = (2*t**3-3*t**2+1)*y[idx] + (t**3-2*t**2+t)*h*tangents[idx]
        value += (-2*t**3+3*t**2)*y[idx+1] + (t**3-t**2)*h*tangents[idx+1]
        if grooves:
            for rr in [13.58, 15.35]:
                value -= .16*np.exp(-.5*((radius-rr)/.11)**2)
        return value


def body(features, high, materials):
    vertices, loops, faces, slots, regions, loop_angles = [], [], [], [], [], []
    phase = features.phase

    def ring(n, radius, depth, label):
        angles = features.star_angles if n==10 else phase + np.arange(n)*2*np.pi/n
        rr = radius(angles) if callable(radius) else np.full(n, radius)
        dd = np.broadcast_to(depth(angles, rr) if callable(depth) else depth, (n,))
        loop = list(range(len(vertices), len(vertices)+n))
        vertices.extend(np.c_[rr*np.cos(angles), -dd, rr*np.sin(angles)].tolist())
        if loops:
            ff = enamel_annulus(loops[-1],loop,vertices) if label=='enamel' and n==10 and len(loops[-1])!=10 else bridge(loops[-1], loop, loop_angles[-1], angles)
            faces.extend(ff)
            slots.extend([1 if label == 'enamel' else 0]*len(ff))
            regions.extend([label]*len(ff))
        loops.append(loop)
        loop_angles.append(angles)

    n=320 if high else 96
    ring(n,15.88,0,'reverse')
    for t in (np.linspace(0,1,16)[1:] if high else [.35,.70,1.]):
        ring(n,15.88+.12*np.sin(t*np.pi/2),.55*t,'sidewall')
    if high:
        radii=np.linspace(16,features.inner-.35,241)[1:]
    else:
        dense=np.linspace(features.inner-.35,16,4097)
        retained=list(features.data['rim_r_mm'])+[13.58,15.35]
        while True:
            retained=sorted(set(retained))
            error=abs(features.rim(dense)-np.interp(dense,retained,features.rim(np.array(retained))))
            j=int(np.argmax(error))
            if error[j]<=.018:break
            retained.append(float(dense[j]))
        radii=retained[-2::-1]
    for rr in radii:
        ring(n,rr,features.rim(rr),'rim')
    ring(10,lambda a:features.outline(a)+.10,1.065,'enamel')
    ring(10,features.outline,1.,'enamel')
    ring(10,features.outline,1.25,'star_wall')
    # Homothetic straight-sided loops share exactly ten facet planes. The old
    # independently sampled height rings and shrinking circular centre crossed
    # those planes, creating an irregular pinched junction.
    roof_fraction=1-.08/features.tip
    for t in (np.linspace(0,1,5)[1:] if high else [.5,1.]):
        fraction=1-(1-roof_fraction)*t
        ring(10,lambda a,f=fraction:features.outline(a)*f,
             1.25+(1.30-1.25)*np.sin(t*np.pi/2),'star_bevel')
    land_fraction=roof_fraction*(2.20-2.18)/(2.20-1.30)
    ring(10,lambda a:features.outline(a)*land_fraction,2.18,'star_roof')
    faces += [tuple(reversed(loops[0])),tuple(loops[-1])]
    slots += [0,0]
    regions += ['reverse','star_center']
    obj=mesh('MedalHigh' if high else 'MedalLow',vertices,faces,materials,slots)
    attr=obj.data.attributes.new('FeatureRegion','INT','FACE')
    names=list(dict.fromkeys(regions))+['bail']
    for item,region,face in zip(attr.data,regions,obj.data.polygons):
        item.value=names.index(region)
        if region in ['star_roof','star_center']:face.use_smooth=False
    obj['feature_names']=json.dumps(names)
    obj['source_lineage']='guide-samples.npz triangle_ids; feature-fit.npz median guide-arm contour and ten-plane manufacturing correction'
    # Finish only the manufactured facet junctions, not the entire turned body.
    bm=bmesh.new();bm.from_mesh(obj.data)
    layer=bm.faces.layers.int['FeatureRegion']
    weight=bm.edges.layers.float.new('bevel_weight_edge')
    roof=names.index('star_roof');center=names.index('star_center')
    for edge in bm.edges:
        if len(edge.link_faces)==2 and all(f[layer] in [roof,center] for f in edge.link_faces):
            edge[weight]=1. if edge.calc_face_angle()>1e-4 else 0.
    bm.to_mesh(obj.data);bm.free()
    activate(obj)
    for v in obj.data.vertices:v.co*=1000
    bevel=obj.modifiers.new('Small facet ridge finish','BEVEL')
    bevel.limit_method='WEIGHT';bevel.width=.035;bevel.segments=3 if high else 2
    bevel.affect='EDGES';bevel.loop_slide=False
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for v in obj.data.vertices:v.co/=1000
    return obj


def swept_loop(name, path, widths, heights, count, brass, closed=True, tangents=None, section_axis=(0.,1.,0.)):
    vertices, loops = [], []
    for i,p in enumerate(path):
        before = path[(i-1)%len(path)] if closed or i else path[0]-(path[1]-path[0])
        after = path[(i+1)%len(path)] if closed or i<len(path)-1 else path[-1]+path[-1]-path[-2]
        tangent=(after-before) if tangents is None else np.array(tangents[i])
        tangent/=np.linalg.norm(tangent)
        u=np.array(section_axis); u-=tangent*np.dot(tangent,u); u/=np.linalg.norm(u)
        v=np.cross(tangent,u)
        angles=np.arange(count)*2*np.pi/count
        section=np.cos(angles)[:,None]*u*widths[i]/2+np.sin(angles)[:,None]*v*heights[i]/2
        loops.append(list(range(len(vertices),len(vertices)+count)))
        vertices.extend(p+section)
    faces=[]
    for i in range(len(path) if closed else len(path)-1):
        faces.extend(bridge(loops[i],loops[(i+1)%len(path)]))
    if not closed:
        faces += [tuple(reversed(loops[0])),tuple(loops[-1])]
    return mesh(name,vertices,faces,[brass])


def bail(out, high, brass):
    data=np.load(out/'ribbon-constraints.npz')
    ribbon=data['vertices']*1000
    width=float(np.ptp(ribbon[:,0]))
    cy,cz=-2.0,18.85
    # A solid tapered claw with a drilled eye, not a rectangular wire frame.
    # Its foot intersects the front rim only; no return cuts the circular wall.
    contour=np.array([[-3.0,14.55],[3.0,14.55],[2.55,15.7],
                      [1.65,17.85],[1.35,18.02],[-1.35,18.02],
                      [-1.65,17.85],[-2.55,15.7]])
    vertices=np.array([[x,y,z] for y in [cy-.45,cy+.45] for x,z in contour])
    n=len(contour)
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    eyelet=mesh('IntegralTaperedEyelet',vertices,faces,[brass])
    # The root bends rearward into the rim, while the eye remains ahead of cloth.
    for v in eyelet.data.vertices:
        z=v.co.z*1000
        v.co.y += max(0.,(15.9-z)/(15.9-14.55))*.0012
    activate(eyelet)
    for v in eyelet.data.vertices:v.co*=1000
    bevel=eyelet.modifiers.new('Claw edge finishing','BEVEL')
    bevel.width=.09;bevel.segments=4 if high else 2
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for v in eyelet.data.vertices:v.co/=1000
    a=np.arange(96 if high else 48)*2*np.pi/(96 if high else 48)
    hole=mesh('Eye drill',np.array([[.76*np.cos(t),y,17.+.76*np.sin(t)] for y in [-4.,0.] for t in a]),
              [tuple(reversed(range(len(a)))),tuple(range(len(a),2*len(a)))]+
              [(i,(i+1)%len(a),(i+1)%len(a)+len(a),i+len(a)) for i in range(len(a))],[brass])
    activate(eyelet)
    for item in [eyelet,hole]:
        for v in item.data.vertices:v.co*=1000
    mod=eyelet.modifiers.new('Round eye through claw','BOOLEAN')
    mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=hole
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for v in eyelet.data.vertices:v.co/=1000
    bpy.data.objects.remove(hole,do_unlink=True)
    # The closed 1 mm-wire jump ring lies in YZ and threads the eye's Y bore.
    count=128 if high else 64
    a=np.arange(count)*2*np.pi/count
    path=np.c_[np.zeros(count),cy+1.9*np.cos(a),cz+1.9*np.sin(a)]
    ring=swept_loop('SolidJumpRing',path,np.ones(count),np.ones(count),32 if high else 16,brass,
                    tangents=np.c_[np.zeros(count),-np.sin(a),np.cos(a)],section_axis=(1.,0.,0.))
    # A straight solid bar across the fixed ribbon, with rounded square section.
    bar=mesh('RibbonSuspenderBar',[[x,y,z] for x in [-width/2,width/2]
              for y,z in [(cy-.7,cz-.7),(cy+.7,cz-.7),(cy+.7,cz+.7),(cy-.7,cz+.7)]],
              [(3,2,1,0),(4,5,6,7)]+[(i,(i+1)%4,(i+1)%4+4,i+4) for i in range(4)],[brass])
    activate(bar)
    for v in bar.data.vertices:v.co*=1000
    bevel=bar.modifiers.new('Rounded rectangular solid bar','BEVEL')
    bevel.width=.28;bevel.segments=6 if high else 3
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for v in bar.data.vertices:v.co/=1000
    report=dict(eyelet_base_width_mm=6.,eyelet_top_width_mm=2.7,eyelet_height_mm=3.47,
        eyelet_section_depth_mm=.9,eyelet_bore_diameter_mm=1.52,
        jump_ring_wire_diameter_mm=1.,jump_ring_centreline_radius_mm=1.9,
        jump_ring_outer_diameter_mm=4.8,bar_width_mm=width,bar_section_mm=[1.4,1.4],
        bar_edge_radius_mm=.28,bar_center_mm=[0,cy,cz],
        ribbon_bottom_mm=float(ribbon[:,2].min()),
        bar_bottom_above_lowest_ribbon_edge_mm=cz-.7-float(ribbon[:,2].min()),
        seating_decision='Frozen ribbon is a closed strip with no folded tunnel. Seat a straight bar ahead of the lower hem, leaving the hem below its lower edge. Forward offset is set by the jump ring rear arc, not by pretending the asymmetric ribbon has a straight depth envelope. Literal cloth wrapping would require changing the ribbon and is deferred.')
    (out/'suspension-design.json').write_text(json.dumps(report,indent=2))
    return eyelet,[ring,bar]


def union(target, obj):
    activate(target)
    # Solve in millimetres so tiny rounded strap intersections are well conditioned.
    for item in [target,obj]:
        for vertex in item.data.vertices:vertex.co*=1000
    mod=target.modifiers.new('Continuous formed shell','BOOLEAN')
    mod.operation='UNION';mod.solver='EXACT';mod.object=obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for vertex in target.data.vertices:vertex.co/=1000
    bpy.data.objects.remove(obj,do_unlink=True)


def triangulate(obj):
    activate(obj)
    mod=obj.modifiers.new('Locked bake topology','TRIANGULATE')
    mod.quad_method='BEAUTY';mod.ngon_method='BEAUTY'
    bpy.ops.object.modifier_apply(modifier=mod.name)
    # Exact unions can leave a single redundant flap on a three-face edge.
    # Retain the closed shell, not those nonmanifold Boolean artifacts.
    bm=bmesh.new();bm.from_mesh(obj.data)
    pending=set(bm.faces);components=[]
    while pending:
        seed=pending.pop();component={seed};stack=[seed]
        while stack:
            face=stack.pop()
            for edge in face.edges:
                if len(edge.link_faces)==2:
                    for other in edge.link_faces:
                        if other in pending:
                            pending.remove(other);component.add(other);stack.append(other)
        components.append(component)
    shells=[component for component in components if len(component)>1]
    main=set().union(*shells)
    extras=[face for component in components if len(component)==1 for face in component]
    if extras:
        print('BOOLEAN COMPONENTS',obj.name,[len(c) for c in components],
              'EXTRA AREA',sum(f.calc_area() for f in extras),flush=True)
        assert len(shells)==3, 'Suspension must contain the body/eyelet, ring and bar'
        main_edges={edge for face in main for edge in face.edges}
        assert all(sum(face in main for face in edge.link_faces)==2 for edge in main_edges), 'Main shell is open'
        bmesh.ops.delete(bm,geom=extras,context='FACES_ONLY')
    isolated=[v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm,geom=isolated,context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free()
    obj.data.set_sharp_from_angle(angle=math.radians(45))
    obj.data.calc_loop_triangles()


def uv_fold_faces(obj):
    from detail_clearance import overlap_polygon
    uv=obj.data.uv_layers.active
    triangles=np.array([[uv.data[i].uv[:] for i in face.loop_indices] for face in obj.data.polygons])
    lo,hi=triangles.min(1),triangles.max(1)
    bad=set()
    for i,triangle in enumerate(triangles):
        candidates=np.flatnonzero(np.all((hi>=lo[i])&(lo<=hi[i]),axis=1))
        for j in candidates[candidates>i]:
            polygon=overlap_polygon(triangle,triangles[j])
            if len(polygon)<3:continue
            area=abs(np.sum(polygon[:,0]*np.roll(polygon[:,1],-1)-polygon[:,1]*np.roll(polygon[:,0],-1)))*.5
            if area>1e-12:bad.update([i,int(j)])
    return bad


def unwrap(obj):
    activate(obj)
    # Smart project separates front, reverse, bevels, sidewall and formed returns.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(50), island_margin=.0042,
                            margin_method='ADD', area_weight=1, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.seams_from_islands(mark_seams=True, mark_sharp=False)
    # The visible relief is one shallow disk. Projection-angle seams fragment
    # its terraces into hundreds of charts and spend the atlas on gutters.
    bm=bmesh.from_edit_mesh(obj.data)
    layer=bm.faces.layers.int['FeatureRegion']
    names=json.loads(obj['feature_names'])
    front={i for i,name in enumerate(names) if name not in ['reverse','sidewall','bail']}
    for edge in bm.edges:
        membership=[face[layer] in front for face in edge.link_faces]
        if all(membership):edge.seam=False
        elif any(membership):edge.seam=True
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=.0042)
    bpy.ops.uv.pack_islands(rotate=True, margin_method='ADD', margin=.0042)
    bpy.ops.object.mode_set(mode='OBJECT')
    # Slender Boolean return triangles can fold inside an otherwise valid chart.
    # Give those faces explicit seams, then unfold and pack their own charts.
    folded=uv_fold_faces(obj)
    if folded:
        keys={tuple(sorted(key)) for i in folded for key in obj.data.polygons[i].edge_keys}
        for edge in obj.data.edges:
            if tuple(sorted(edge.vertices)) in keys:edge.use_seam=True
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=.0042)
        bpy.ops.uv.pack_islands(rotate=True, margin_method='ADD', margin=.0042)
        bpy.ops.object.mode_set(mode='OBJECT')
    assert not uv_fold_faces(obj), 'UV chart still folds; do not export it'
    uv=obj.data.uv_layers.active
    reverse=[i for face in obj.data.polygons
             if face.normal.y>.95 and all(abs(obj.data.vertices[v].co.y)<1e-7 for v in face.vertices)
             for i in face.loop_indices]
    center=np.mean([uv.data[i].uv[:] for i in reverse],axis=0)
    for i in reverse:uv.data[i].uv=center+.55*(np.array(uv.data[i].uv[:])-center)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin_method='ADD', margin=.0042)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.data.uv_layers.active.name='MedalUV'


def build(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    features=Features(out)
    features.report['decisions']=[x for x in features.report['decisions'] if not any(word in x for word in ['twenty','strap cap','0.08 mm farther','suspension','0.14 mm'])]
    features.report['decisions'] += [
        '#130 fix: 96 angular rim stations and cross-section-adaptive support loops with 0.018 mm maximum profile interpolation error; retain both groove valleys in geometry.',
        '#130 second geometry fix: ten symmetric planar facets follow median guide tip/notch radii. Truncate one virtual apex at 2.18 mm, with 0.035 mm ridge finishing. No separately smoothed central height patch.',
        '#130 second geometry fix: solid tapered drilled claw integral with the rim, separate 1 mm-wire jump ring, and solid 1.4 mm rounded-square straight ribbon bar. No long supports or rear wire return.',
        '#130 second geometry fix: remove the former bail return that Boolean-cut the sidewall; the new claw foot joins only the front rim. Verify full-perimeter radial roundness, including triangle interiors.',
        '#130 fix: record the candidate asset-authored triangle increase separately in budget.json; no cloth or production-verifier edits during standalone stage one.'
    ]
    (out/'feature-fit.json').write_text(json.dumps(features.report,indent=2))
    brass=material('PreviewBrass',(.66,.43,.14),1,.26)
    enamel=material('PreviewBlueEnamel',(.008,.025,.095),0,.20)
    objects=[]
    for high in [True,False]:
        obj=body(features,high,[brass,enamel])
        loop,straps=bail(out,high,brass)
        for part in [loop,*straps]:
            attribute=part.data.attributes.new('FeatureRegion','INT','FACE')
            for face in attribute.data:face.value=json.loads(obj['feature_names']).index('bail')
        union(obj,loop)
        activate(obj)
        for part in straps:part.select_set(True)
        bpy.ops.object.join()
        triangulate(obj)
        if not high:
            unwrap(obj)
        objects.append(obj)
        print(obj.name,'TRIANGLES',len(obj.data.loop_triangles),flush=True)
    high,low=objects
    data=features.data
    clean=mesh('GuideFaired',data['clean_vertices']*1000,data['raw_faces'],[brass])
    clean['feature_labels']='1 reverse; 2 sidewall; 3 field; 4 rim; 5 suspension; 6 star'
    label=clean.data.attributes.new('GuideFeature','INT','POINT')
    pin=clean.data.attributes.new('FeaturePinned','BOOLEAN','POINT')
    for a,b in zip(label.data,data['labels']):a.value=int(b)
    for a,b in zip(pin.data,data['pinned']):a.value=bool(b)
    clean.hide_render=True;clean.hide_set(True)
    with bpy.data.libraries.load(str(out/'registered-guide.blend'),link=False) as (_,target):
        target.objects=['ImmutableRegisteredGuide']
    raw=target.objects[0];bpy.context.collection.objects.link(raw)
    raw.hide_render=True;raw.hide_set(True)
    for name, radius in [('InnerCrest',features.inner),('OuterChannel',features.channel),('OuterCrown',features.crown),('StarContour',None)]:
        a=features.phase+np.arange(256)*2*np.pi/256
        rr=features.outline(a) if radius is None else np.full(256,radius)
        dd=np.full(256,1.25) if radius is None else np.full(256,features.rim(radius))
        curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D'
        poly=curve.splines.new('POLY');poly.points.add(255)
        for point,p in zip(poly.points,np.c_[rr*np.cos(a),-dd,rr*np.sin(a)]/1000):point.co=(*p,1)
        poly.use_cyclic_u=True
        ob=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(ob);ob.hide_render=True;ob.hide_set(True)
    for name,members in [('SourceGuide',[raw,clean]),('CorrectedMedal',[high,low]),
                         ('FeatureCurves',[o for o in bpy.context.scene.objects if o.type=='CURVE'])]:
        collection=bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        for obj in members:
            for previous in list(obj.users_collection):previous.objects.unlink(obj)
            collection.objects.link(obj)
    text=bpy.data.texts.new('MedalCorrectionReport.json')
    text.write(json.dumps(features.report,indent=2))
    bpy.context.scene['stage1_decisions']=json.dumps(features.report['decisions'])
    bpy.context.scene['source_registration']=(out/'registration.json').read_text()
    bpy.context.preferences.filepaths.save_version=0
    high.hide_render=False;low.hide_render=True
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'medal-high.blend'))
    high.hide_render=True;low.hide_render=False
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'medal-low.blend'))
    for obj in objects:
        activate(obj)
        obj.hide_set(False)
        bpy.ops.export_scene.gltf(filepath=str(out/('medal-high.glb' if obj==high else 'medal-low.glb')),
                                  use_selection=True,export_yup=True,export_apply=True,export_texcoords=True,
                                  export_normals=True,export_tangents=bool(obj.data.uv_layers),export_materials='EXPORT')
    # Independent numerical verification reads these exact triangulated/exported positions and UVs.
    for obj,key in [(high,'high'),(low,'low')]:
        obj.data.calc_loop_triangles()
        uv=obj.data.uv_layers.active
        np.savez_compressed(out/f'{key}-geometry.npz',vertices=np.array([v.co[:] for v in obj.data.vertices]),
                            faces=np.array([t.vertices[:] for t in obj.data.loop_triangles]),
                            materials=np.array([t.material_index for t in obj.data.loop_triangles]),
                            regions=np.array([obj.data.attributes['FeatureRegion'].data[t.polygon_index].value for t in obj.data.loop_triangles]),
                            region_names=np.array(json.loads(obj['feature_names'])),
                            uv=np.array([[uv.data[i].uv[:] for i in t.loops] for t in obj.data.loop_triangles]) if uv else np.empty((0,3,2)))
    print('GEOMETRY COMPLETE',flush=True)
