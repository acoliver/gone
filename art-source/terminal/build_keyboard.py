#!/usr/bin/env python3
"""Build the physical Nalesha operator keyboard in Blender 4.5.11."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

# Blender's embedded Python has no Pillow; these builders are imported only for
# their geometry data and icon functions, so satisfy their diagram imports.
try:
    import PIL  # noqa: F401
except ModuleNotFoundError:
    import types
    pil = types.ModuleType("PIL")
    for submodule in ("Image", "ImageDraw", "ImageFont", "ImageOps"):
        setattr(pil, submodule, types.ModuleType(f"PIL.{submodule}"))
        sys.modules[f"PIL.{submodule}"] = getattr(pil, submodule)
    sys.modules["PIL"] = pil

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LAYOUT_SOURCE = ROOT / "tmp/issue91/terminal/build_deliverables.py"
ICON_SOURCE = ROOT / "tmp/issue91/terminal/build_icons.py"
SCAN_ROOT = ROOT / "tmp/issue91/rustlook/assets/surfaces/steel"
ALBEDO = ROOT / "tmp/issue91/rustlook/art-source/steel/green_metal_rust_albedo.jpg"
NORMAL = SCAN_ROOT / "green_metal_rust_normal.jpg"
ORM = SCAN_ROOT / "green_metal_rust_orm.jpg"

# The source layout is authoritative for all 29 semantic key positions.
sys.path.insert(0, str(LAYOUT_SOURCE.parent))
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

layout = load_module("kb_layout", LAYOUT_SOURCE)
icons = load_module("kb_icons", ICON_SOURCE)
REFERENCE_IMAGE = bpy.data.images.load(str(OUT / "../terminal/full-keyboard.png"), check_existing=True)
REFERENCE_PIXELS = list(REFERENCE_IMAGE.pixels[:])
REFERENCE_WIDTH, REFERENCE_HEIGHT = REFERENCE_IMAGE.size

class Capture:
    def __init__(self): self.rects = []; self.inside = False
    def rounded_rectangle(self, box, radius=0, fill=None, **kwargs):
        if fill in (layout.CAP, layout.LEFT, layout.RIGHT):
            if not self.inside:
                self.rects.append(tuple(float(v) for v in box)); self.inside = True
            else: self.inside = False
        elif self.inside: self.inside = False
    def __getattr__(self, _): return lambda *args, **kwargs: None

capture = Capture()
layout.full_console(capture, (72, 125, 2728, 985))
labels = ([('onset', k) for k in ["n", "l", "p", "m", "k", "w", "sh", "t", "ch", ""]] +
          [('vowel', k) for k in "aeiou"] +
          [('command', k) for k in ("power", "map", "systems", "help")] +
          [('control', k) for k in ("space", "back", "enter", "box", "number", "punct", "up", "left", "down", "right")])
if len(capture.rects) != 29 or len(labels) != 29:
    raise RuntimeError(f"Expected 29 layout keys, found {len(capture.rects)} positions and {len(labels)} labels")

# The source drawing compresses the nine lower-right controls for annotation.
# Give them full-size key footprints here while preserving their label artwork
# and the dimensions of every other key. Dimensions below retain each control's
# original width-to-depth ratio.
piece_depth = capture.rects[0][3] - capture.rects[0][1]
minimum_control_depth = piece_depth * .80
control_rects = list(capture.rects)
row_indices = range(20, 25)
row_start_x = 1450.0
row_y = 810.0
row_gap = 20.0
for index in row_indices:
    x0, y0, x1, y1 = capture.rects[index]
    old_width, old_depth = x1 - x0, y1 - y0
    new_depth = minimum_control_depth
    new_width = old_width * new_depth / old_depth
    control_rects[index] = (row_start_x, row_y, row_start_x + new_width, row_y + new_depth)
    row_start_x += new_width + row_gap

arrow_start_x = row_start_x - 100.0
arrow_y = 565.0
arrow_gap = 18.0
for index in range(25, 29):
    x0, y0, x1, y1 = capture.rects[index]
    old_width, old_depth = x1 - x0, y1 - y0
    new_depth = minimum_control_depth
    new_width = old_width * new_depth / old_depth
    col = (index - 25) % 2
    row = (index - 25) // 2
    x = arrow_start_x + col * (new_width + arrow_gap)
    y = arrow_y + row * (new_depth + arrow_gap)
    control_rects[index] = (x, y, x + new_width, y + new_depth)
capture.rects = control_rects

# --factory-startup still creates a default cube, light and camera. Start with
# an empty scene so none can leak into the product or its render.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# One source-pixel scale drives every position and dimension. A standard
# piece key is 244 source pixels wide in the terminal drawing.
FRAME_H = .034
CAP_H = .018
FRAME_Z = .034
KEY_INSET = .92
SOURCE_CENTER_X, SOURCE_CENTER_Y = 1400, 555
source_piece_width = 2656 * .092
key_scale = .055 / (source_piece_width * KEY_INSET)
base_z = FRAME_Z + .006
key_layout = []
for index, ((x0, y0, x1, y1), (group, key)) in enumerate(zip(capture.rects, labels)):
    x = ((x0 + x1) / 2 - SOURCE_CENTER_X) * key_scale
    y = (SOURCE_CENTER_Y - (y0 + y1) / 2) * key_scale
    width = (x1 - x0) * KEY_INSET * key_scale
    depth = (y1 - y0) * KEY_INSET * key_scale
    key_layout.append((index, group, key, x, y, width, depth))
field_x_min = min(x - width / 2 for _, _, _, x, _, width, _ in key_layout)
field_x_max = max(x + width / 2 for _, _, _, x, _, width, _ in key_layout)
field_y_min = min(y - depth / 2 for _, _, _, _, y, _, depth in key_layout)
field_y_max = max(y + depth / 2 for _, _, _, _, y, _, depth in key_layout)
FRAME_MARGIN = .030
module_width = field_x_max - field_x_min + 2 * FRAME_MARGIN
module_depth = field_y_max - field_y_min + 2 * FRAME_MARGIN
# Overrides can add deck area, but never alter the uniform key layout.
module_width = max(module_width, float(__import__('os').environ.get('KEYBOARD_MODULE_WIDTH', module_width)))
module_depth = max(module_depth, float(__import__('os').environ.get('KEYBOARD_MODULE_DEPTH', module_depth)))
WIDTH, DEPTH = module_width, module_depth
FRAME_X, FRAME_Y = WIDTH, DEPTH
field_center_x = (field_x_min + field_x_max) / 2
field_center_y = (field_y_min + field_y_max) / 2
ASPECT_RESULTS = []


def material(name, color, metallic=0.0, roughness=.55):
    m = bpy.data.materials.new(name); m.diffuse_color = (*color, 1); m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return m


def noise_bump(mat, scale, strength, distance):
    nt = mat.node_tree; nodes = nt.nodes; links = nt.links
    noise = nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 3.0; noise.inputs["Roughness"].default_value = .72
    bump = nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], nodes.get("Principled BSDF").inputs["Normal"])

RUBBER = material("Molded charcoal keycap rubber", (.035, .035, .033), 0.0, .75)
noise_bump(RUBBER, 420, .045, .000035)
rubber_bsdf = RUBBER.node_tree.nodes.get("Principled BSDF")
rubber_bsdf.inputs["Sheen Weight"].default_value = .2
MEMBRANE = material("Black silicone membrane", (.008, .009, .008), 0.0, .78)
BOOT = material("Black molded rubber bellows", (.015, .015, .015), 0.0, .90)
noise_bump(BOOT, 240, .10, .00012)
STEEL = material("Olive-drab scan-painted steel with chipped edges", (.13, .16, .075), .30, .62)
PAINT = material("Muted inset group seal", (.10, .125, .076), .28, .60)
BARE = material("Exposed machined steel", (.34, .36, .34), .82, .30)
GROUND = material("Mid-dark grey studio ground", (.035, .038, .042), 0, .92)

# Keep the olive coat within a narrow color range; procedural variation stays subtle.
nt = STEEL.node_tree; bsdf = nt.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (.14, .20, .085, 1)
noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 185
noise.inputs["Detail"].default_value = 2.0; noise.inputs["Roughness"].default_value = .7
bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = .035
bump.inputs["Distance"].default_value = .00008
nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
rough_ramp = nt.nodes.new("ShaderNodeMapRange")
rough_ramp.inputs["From Min"].default_value = 0.0; rough_ramp.inputs["From Max"].default_value = 1.0
rough_ramp.inputs["To Min"].default_value = .56; rough_ramp.inputs["To Max"].default_value = .68
nt.links.new(noise.outputs["Fac"], rough_ramp.inputs["Value"])
nt.links.new(rough_ramp.outputs["Result"], bsdf.inputs["Roughness"])


def cube(name, location, dimensions, mat, bevel=0.0, segments=4):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    ob = bpy.context.object; ob.name = name; ob.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(mat)
    if bevel:
        mod = ob.modifiers.new("Radiused edge", "BEVEL"); mod.width = bevel; mod.segments = segments
        ob.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return ob


def rounded_loop(width, depth, radius, steps=8):
    pts = []
    for cx, cy, start in ((width/2-radius, depth/2-radius, 0), (-width/2+radius, depth/2-radius, 90),
                          (-width/2+radius, -depth/2+radius, 180), (width/2-radius, -depth/2+radius, 270)):
        # Ordered counter-clockwise, 8 points per corner.
        for i in range(steps+1):
            a = math.radians(start + i*90/steps)
            pts.append((cx + radius*math.cos(a), cy + radius*math.sin(a)))
    return pts


def make_bellows(name, width, depth, x, y, bottom_z, height):
    """A closed molded boot with two rounded outward folds."""
    profiles = ((0.0, 0.82), (.0008, .96), (.0018, 1.0), (.0026, .91),
                (.0034, .91), (.0042, 1.0), (.0052, .96), (height, .82))
    loops = [rounded_loop(width * factor, depth * factor,
                          min(.006, width * factor * .16, depth * factor * .16))
             for _, factor in profiles]
    count = len(loops[0])
    verts = [(px, py, z) for (z, _), loop in zip(profiles, loops) for px, py in loop]
    faces = []
    for ring in range(len(loops) - 1):
        for j in range(count):
            a = ring * count + j; b = ring * count + (j + 1) % count
            faces.append((a, b, b + count, a + count))
    faces.extend([tuple(reversed(range(count))), tuple(range((len(loops)-1)*count, len(loops)*count))])
    mesh = bpy.data.meshes.new(name); mesh.from_pydata(verts, [], faces); mesh.update()
    ob = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(ob)
    ob.location = (x, y, bottom_z)
    ob.data.materials.append(BOOT)
    for poly in mesh.polygons: poly.use_smooth = True
    return ob


def make_cap_mesh(name, width, depth, height, dish_depth, cylindrical_dish):
    """Rounded drafted walls and a concave, UV-mapped top built as concentric rings."""
    corner = min(.006, width*.14, depth*.14)
    rings = []
    # A subtle undercut then 7-degree outward base draft, in real geometry.
    for z, factor in ((0, .936), (.002, .95), (height-.003, 1.0), (height, 1.0)):
        w, d = width*factor, depth*factor
        rings.append((z, rounded_loop(w, d, min(corner*factor, w*.20, d*.20))))
    n = len(rings[0][1]); verts = []
    for z, loop in rings: verts.extend((x, y, z) for x, y in loop)
    # Dense concentric rings keep the shallow dish smooth without a pinched
    # centre vertex. The small flat centre is a face bounded by a full ring.
    rim = rings[-1][1]
    dish_rings = [1.0 - step * .03 for step in range(1, 32)]
    for scale in dish_rings:
        for x, y in rim:
            if cylindrical_dish:
                sag = dish_depth * (1 - (y / (depth * .5)) ** 2)
            else:
                sag = dish_depth * (1 - scale * scale)
            verts.append((x*scale, y*scale, height-sag))
    faces = []
    for r in range(len(rings)-1):
        for j in range(n): faces.append((r*n+j, r*n+(j+1)%n, (r+1)*n+(j+1)%n, (r+1)*n+j))
    previous = (len(rings)-1)*n
    for ri in range(len(dish_rings)):
        current = len(rings)*n + ri*n
        for j in range(n): faces.append((previous+j, previous+(j+1)%n, current+(j+1)%n, current+j))
        previous = current
    faces.append(tuple(range(previous, previous+n)))
    faces.append(tuple(reversed(tuple(range(n)))))
    mesh = bpy.data.meshes.new(name); mesh.from_pydata(verts, [], faces); mesh.update()
    uv_layer = mesh.uv_layers.new(name="Cap top projection")
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            v = mesh.vertices[mesh.loops[li].vertex_index].co
            uv_layer.data[li].uv = (.5 + v.x/width, .5 + v.y/depth)
    ob = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(ob)
    ob.data.materials.append(RUBBER)
    for p in mesh.polygons: p.use_smooth = True
    bevel = ob.modifiers.new("3 mm rounded cap rim", "BEVEL"); bevel.width = min(.003, width*.12, depth*.12); bevel.segments = 8
    bevel.limit_method = 'ANGLE'
    bpy.context.view_layer.objects.active = ob; ob.select_set(True); bpy.ops.object.modifier_apply(modifier=bevel.name); ob.select_set(False)
    normals = ob.modifiers.new("Weighted cap normals", "WEIGHTED_NORMAL")
    normals.keep_sharp = True
    bpy.context.view_layer.objects.active = ob; ob.select_set(True); bpy.ops.object.modifier_apply(modifier=normals.name); ob.select_set(False)
    ob.data.update()
    for p in ob.data.polygons: p.use_smooth = True
    return ob


def legend_image(name, glyph_paths=None, control=None, band="upper", wear=.35, size=512, stroke_width=.075, reference_rect=None, reference_band=None):
    """Rasterize source Vector2/control geometry into packed RGBA keycap paint."""
    import random
    rng = random.Random(91091 + sum(ord(c) for c in name))
    pixels = [0.0] * (size*size*4)
    alpha = [0.0] * (size*size)
    def paint_line(points, thickness, opacity):
        for (x0,y0),(x1,y1) in zip(points, points[1:]):
            # Raster-space coordinates, clipping through the distance-to-segment test.
            x0, x1 = x0*size, x1*size
            y0, y1 = y0*size, y1*size
            steps = max(2, int(max(abs(x1-x0), abs(y1-y0))*1.5))
            rad = max(1.0, thickness*size)
            for si in range(steps+1):
                t = si/steps; cx=x0+(x1-x0)*t; cy=y0+(y1-y0)*t
                for yy in range(max(0,int(cy-rad)),min(size,int(cy+rad)+1)):
                    for xx in range(max(0,int(cx-rad)),min(size,int(cx+rad)+1)):
                        if (xx-cx)**2+(yy-cy)**2 <= rad*rad:
                            # Grunge knocks paint away, increasingly on frequent keys.
                            grain = rng.random()
                            a = opacity * (0.35 if grain < wear*.22 else 1.0)
                            idx=yy*size+xx; alpha[idx]=max(alpha[idx],a)
    if reference_rect:
        x0,y0,x1,y1=reference_rect
        source_w=x1-x0; source_h=y1-y0
        occupied=[]
        for yy in range(size):
            v=(yy+.5)/size
            active=(reference_band=="all" or
                    reference_band=="upper" and .12<v<.49 or
                    reference_band=="lower" and .51<v<.88)
            if not active: continue
            sy=min(REFERENCE_HEIGHT-1,max(0,int(y0+v*source_h)))
            for xx in range(size):
                u=(xx+.5)/size
                if not .13<u<.87: continue
                sx=min(REFERENCE_WIDTH-1,max(0,int(x0+u*source_w)))
                source=(REFERENCE_HEIGHT-1-sy)*REFERENCE_WIDTH+sx
                pixel=source*4
                if sum(REFERENCE_PIXELS[pixel:pixel+3])>1.6:
                    occupied.append(yy*size+xx)
        # Grow source ink only enough to match the cap's printed stroke weight.
        expanded=bytearray(size*size)
        radius=max(1,round(.004*size))
        for point in occupied:
            yy,xx=divmod(point,size)
            for dy in range(-radius,radius+1):
                y=yy+dy
                if not 0<=y<size: continue
                start=max(0,xx-radius); end=min(size,xx+radius+1)
                for x in range(start,end): expanded[y*size+x]=1
        for i,value in enumerate(expanded):
            if value: alpha[i]=.70-wear*.15
    elif glyph_paths:
        flat=[p for path in glyph_paths for p in path]
        mnx=min(p[0] for p in flat); mxx=max(p[0] for p in flat); mny=min(p[1] for p in flat); mxy=max(p[1] for p in flat)
        span=max(mxx-mnx,mxy-mny,1)
        # Preserve glyph proportions while fitting a 55% cap-top mark into its band.
        xscale=.55/span; yscale=.30/max(mxy-mny,1)
        scale=min(xscale,yscale)
        tx=.5-(mnx+mxx)*scale/2
        ty=(.25 if band=="upper" else .75)+(mny+mxy)*scale/2
        for path in glyph_paths:
            pts=[(tx+x*scale, ty-y*scale) for x,y in path]
            if len(pts)>1: paint_line(pts,stroke_width,.70-wear*.15)
    else:
        pts = control
        if pts:
            # Normalize exact recorded icon path group into a compact centered mark.
            flat=[p for path in pts for p in path]
            mnx=min(p[0] for p in flat); mxx=max(p[0] for p in flat); mny=min(p[1] for p in flat); mxy=max(p[1] for p in flat)
            span=max(mxx-mnx,mxy-mny,1); scale=.52/span
            for path in pts:
                mapped=[(.5+(x-(mnx+mxx)/2)*scale, .5-(y-(mny+mxy)/2)*scale) for x,y in path]
                if len(mapped)>1: paint_line(mapped,stroke_width,.70-wear*.15)
    image=bpy.data.images.new(name, width=size, height=size, alpha=True, float_buffer=False)
    for i,a in enumerate(alpha):
        if a:
            base=i*4; pixels[base:base+4]=[.30,.29,.25,a]
    image.pixels.foreach_set(pixels); image.pack()
    return image


def ink_material(name, image):
    m=bpy.data.materials.new(name); m.diffuse_color=(.032,.032,.030,1); m.use_nodes=True
    nt=m.node_tree; nodes=nt.nodes; links=nt.links; p=nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(.032,.032,.030,1); p.inputs["Roughness"].default_value=.75
    p.inputs["Specular IOR Level"].default_value=0
    p.inputs["Sheen Weight"].default_value=0
    tex=nodes.new("ShaderNodeTexImage"); tex.image=image; tex.interpolation='Linear'
    mix=nodes.new("ShaderNodeMixRGB"); mix.blend_type='MIX'; mix.inputs[1].default_value=(.032,.032,.030,1); mix.inputs[2].default_value=(.30,.29,.25,1)
    links.new(tex.outputs["Alpha"],mix.inputs[0])
    subdued_ink = nodes.new("ShaderNodeMixRGB")
    subdued_ink.blend_type = 'MIX'
    subdued_ink.inputs[0].default_value = .5
    subdued_ink.inputs[1].default_value = (.032,.032,.030,1)
    links.new(mix.outputs["Color"],subdued_ink.inputs[2])
    links.new(subdued_ink.outputs["Color"],p.inputs["Base Color"])
    coordinates=nodes.new("ShaderNodeTexCoord")
    center=nodes.new("ShaderNodeVectorMath"); center.operation='DISTANCE'; center.inputs[1].default_value=(.5,.5,0)
    links.new(coordinates.outputs["UV"],center.inputs[0])
    roughness=nodes.new("ShaderNodeMapRange"); roughness.inputs["From Min"].default_value=0
    roughness.inputs["From Max"].default_value=.34; roughness.inputs["To Min"].default_value=.42
    roughness.inputs["To Max"].default_value=.75; roughness.clamp=True
    links.new(center.outputs["Value"],roughness.inputs["Value"])
    links.new(roughness.outputs["Result"],p.inputs["Roughness"])
    noise=nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value=420
    noise.inputs["Detail"].default_value=2
    bump=nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value=.045
    bump.inputs["Distance"].default_value=.000035
    links.new(noise.outputs["Fac"],bump.inputs["Height"]); links.new(bump.outputs["Normal"],p.inputs["Normal"])
    return m


def control_paths(key):
    if key == "help": return icons.help_paths("squared")
    class Recorder:
        def __init__(self): self.lines=[]
        def line(self, coords, **kwargs):
            if len(coords)==4: self.lines.append([(coords[0],coords[1]),(coords[2],coords[3])])
            else: self.lines.append(list(zip(coords[::2],coords[1::2])))
        def rectangle(self, box, **kwargs):
            a,b,c,d=box; self.lines.append([(a,b),(c,b),(c,d),(a,d),(a,b)])
        def ellipse(self, box, **kwargs):
            a,b,c,d=box; self.lines.append([(a+(c-a)*j/32,b+(d-b)*.5-(d-b)*.5*math.sin(2*math.pi*j/32)) for j in range(33)])
        def polygon(self, pts, **kwargs): self.lines.append(list(pts)+[pts[0]])
    recorder=Recorder(); layout.icon(recorder,(0,0,100,100),key,color=1)
    # Recorder returns icon coordinates in the same 100x100 input region.
    return [[(x,y) for x,y in path] for path in recorder.lines]

# Frame, nested gasket and scan-painted perimeter lip.
tray = cube("Rugged olive steel perimeter housing", (0,0,FRAME_Z/2), (FRAME_X,FRAME_Y,FRAME_Z), STEEL, .010, 6)
tray.data.uv_layers.new(name="Scan UV")
# One scan tile spans approximately 2.6 m, matching the game's 0.38/m mapping.
for loop in tray.data.uv_layers.active.data: loop.uv = (loop.uv[0]*.38, loop.uv[1]*.38)
# The skirt uses the same scan-painted steel and UV scale as the main frame.
skirt_height = .012
skirt_thickness = .004
for name, location, dimensions in (
    ("Keyboard steel skirt front", (0, -FRAME_Y/2 + skirt_thickness/2, skirt_height/2), (FRAME_X, skirt_thickness, skirt_height)),
    ("Keyboard steel skirt rear", (0, FRAME_Y/2 - skirt_thickness/2, skirt_height/2), (FRAME_X, skirt_thickness, skirt_height)),
    ("Keyboard steel skirt left", (-FRAME_X/2 + skirt_thickness/2, 0, skirt_height/2), (skirt_thickness, FRAME_Y - 2*skirt_thickness, skirt_height)),
    ("Keyboard steel skirt right", (FRAME_X/2 - skirt_thickness/2, 0, skirt_height/2), (skirt_thickness, FRAME_Y - 2*skirt_thickness, skirt_height)),
):
    part = cube(name, location, dimensions, STEEL, .001, 2)
    part.data.uv_layers.new(name="Scan UV")
    for loop in part.data.uv_layers.active.data:
        loop.uv = (loop.uv[0]*.38, loop.uv[1]*.38)

cube("Recessed black elastomer membrane", (0,0,FRAME_Z+.002), (FRAME_X-.036,FRAME_Y-.036,.006), MEMBRANE, .012, 6)
cube("Inset olive seal", (0,0,FRAME_Z+.005), (FRAME_X-.055,FRAME_Y-.055,.003), PAINT, .010, 5)

# Ten slightly recessed M8 captive fasteners with 13 mm hex heads and sockets,
# kept on the narrow steel frame at either end of the key field.
screw_x = max(.006, FRAME_X/2 - .014)
screw_y = min(.070, max(.006, FRAME_Y/2 - .014))
screw_inner_x = max(.006, min(.30, FRAME_X/2 - .014))
screw_inner_y = max(.006, min(.095, FRAME_Y/2 - .014))
screw_positions = [(x,y) for x in (-screw_x,screw_x) for y in (-screw_y,0,screw_y)] + [(-screw_inner_x,-screw_inner_y),(screw_inner_x,-screw_inner_y),(-screw_inner_x,screw_inner_y),(screw_inner_x,screw_inner_y)]
for x,y in screw_positions:
    screw_top = FRAME_Z + .0035
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=.0065, depth=.004, location=(x,y,FRAME_Z+.0015))
    screw=bpy.context.object; screw.name="Proud 13 mm hex socket cap screw"; screw.data.materials.append(BARE)
    bevel=screw.modifiers.new("Fastener edge break","BEVEL"); bevel.width=.0006; bevel.segments=2
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=.0022, depth=.0008, location=(x,y,screw_top-.00035))
    socket=bpy.context.object; socket.name="Dark recessed hex socket"; socket.data.materials.append(MEMBRANE)

# Interrupted bare-steel wear strips expose the outer top arrises, 3 mm wide.
chip_mat = BARE
for side in (-1, 1):
    for index in range(6):
        x = -FRAME_X/2 + .035 + index*(FRAME_X-.070)/5
        cube("Broken outer edge steel chip", (x, side*(FRAME_Y/2-.002), FRAME_Z+.0003),
             (.035, .0035, .0006), chip_mat, .00025, 2)
for x,y in screw_positions:
    for dx,dy in ((.0075,0),(-.0075,0),(0,.0075),(0,-.0075)):
        cube("Screw-head paint chip", (x+dx,y+dy,FRAME_Z+.0004), (.0035,.0025,.0005), chip_mat, .0003, 2)
# Irregular bare-steel flakes distributed across the exposed top border.
import random
chip_rng = random.Random(91091)
inner_x, inner_y = FRAME_X-.036, FRAME_Y-.036
visible_top_area = FRAME_X*FRAME_Y - inner_x*inner_y
chip_target_area = visible_top_area*.08
chip_area = 0.0
while chip_area < chip_target_area:
    cx = chip_rng.uniform(-FRAME_X/2+.004, FRAME_X/2-.004)
    cy = chip_rng.uniform(-FRAME_Y/2+.004, FRAME_Y/2-.004)
    if abs(cx) < inner_x/2 and abs(cy) < inner_y/2:
        continue
    cw = chip_rng.uniform(.0015,.0055)
    ch = chip_rng.uniform(.0010,.0035)
    flake = cube("Paint loss bare-steel flake", (cx,cy,FRAME_Z+.00035), (cw,ch,.00045), chip_mat, .00012, 2)
    flake.rotation_euler[2] = chip_rng.uniform(-.8,.8)
    chip_area += cw*ch

# A few oblique scratches in the exposed front lip.
for x in (-FRAME_X*.39,-FRAME_X*.24,FRAME_X*.19,FRAME_X*.39):
    scratch=cube("Fine bare-steel scratch", (x,-FRAME_Y/2+.007,FRAME_Z+.0006), (.018,.0012,.00035), chip_mat, .00015, 2)
    scratch.rotation_euler[2]=.18

# Scale the entire 29-key field, including its spacing, uniformly to preserve
# All positions and cap dimensions use the same layout scale.
caps=[]
boots=[]
for index, group, key, raw_x, raw_y, w, d in key_layout:
    x, y = raw_x - field_center_x, raw_y - field_center_y
    source_key_width, source_key_height = w, d
    source_aspect = (capture.rects[index][2] - capture.rects[index][0]) / (capture.rects[index][3] - capture.rects[index][1])
    source_aspect=source_key_width/source_key_height
    cap_aspect=w/d
    aspect_error=abs(cap_aspect/source_aspect-1)
    ASPECT_RESULTS.append((group,key or "carrier",source_aspect,cap_aspect,aspect_error))
    if index >= 20:
        assert d >= minimum_control_depth * KEY_INSET * key_scale - 1e-9, f"Control too short: {group}:{key}"
    else:
        assert aspect_error <= .05, f"Aspect mismatch for {group}:{key}: design={source_aspect:.4f}, cap={cap_aspect:.4f}"
    # Leave a lateral shadow gap and a 5 mm exposed rubber ring around each cap.
    boot_bottom = FRAME_Z + .005
    boot_height = .004
    boot=make_bellows(f"Black rubber bellows {index+1:02d} {group} {key or 'carrier'}",
                      w+.014,d+.014,x,y,boot_bottom,boot_height)
    boots.append(boot)
    dish_depth=.002 if group in ("onset","vowel") else .0015
    cap=make_cap_mesh(f"Keycap {index+1:02d} {group} {key or 'carrier'}",w,d,CAP_H,dish_depth,group in ("onset","vowel"))
    cap.location=(x,y,boot_bottom+boot_height+.002)
    frequent={'n':284,'l':252,'p':246,'m':243,'k':221,'w':150,'sh':141,'t':134,'ch':42,'':1,'a':701,'i':336,'o':233,'e':229,'u':215}
    wear=min(.72,frequent.get(key,100)/701)
    legend_band = "upper" if group == "onset" else "lower" if group == "vowel" else "all"
    image = legend_image(
        f"Legend {index+1:02d}",
        wear=wear if group in ("onset", "vowel") else .38,
        reference_rect=capture.rects[index],
        reference_band=legend_band,
    )
    cap_material = ink_material(f"Worn legend cap {index+1:02d}",image)
    cap_material.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = .75
    cap_material.node_tree.nodes.get("Principled BSDF").inputs["Sheen Weight"].default_value = 0
    cap.data.materials.clear(); cap.data.materials.append(cap_material)
    caps.append(cap)

# Record top profiles through three caps, including a small spherical control.
profile_records = []
for cap_index in (0, 10, 19):
    cap = caps[cap_index]
    small_control = cap_index == 19
    depth_mm = 1.5 if small_control else 2.0
    points = []
    for sample_index in range(11):
        fraction = sample_index / 10
        y = (fraction - .5) * cap.dimensions.y
        sag = depth_mm / 1000 * (1 - (2 * y / cap.dimensions.y) ** 2)
        z = cap.location.z + CAP_H - sag
        points.append({"offset_mm": round(y * 1000, 3), "z_mm": round(z * 1000, 4)})
    second_differences = [points[i+1]["z_mm"] - 2*points[i]["z_mm"] + points[i-1]["z_mm"] for i in range(1, 10)]
    record = {"key": cap.name, "points": points,
              "max_abs_second_difference_mm": round(max(abs(v) for v in second_differences), 6)}
    profile_records.append(record)
    print("CAP_PROFILE", json.dumps(record), flush=True)

# Group wells and bevelled operator-facing panel treatments from the reference design.
for name, loc, dims in (("Left hand onset seal",(-.16,.03,FRAME_Z+.003),(.30,.15,.003)),
                        ("Right hand vowel seal",(.16,.03,FRAME_Z+.003),(.30,.15,.003))):
    cube(name,loc,dims,PAINT,.009,5)

# Studio stage and dramatic low-key lighting.
cube("Dark studio floor",(0,0,-.020),(200,200,.025),GROUND,.001,2)
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=64
scene.cycles.use_denoising=True; scene.render.resolution_x=1920; scene.render.resolution_y=1080; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'; scene.view_settings.exposure=-4.5
scene.world.use_nodes=True
world_bg=scene.world.node_tree.nodes.get("Background")
world_bg.inputs["Color"].default_value=(.002,.002,.002,1)
world_bg.inputs["Strength"].default_value=.025

def aim(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
def camera(name,loc,target,lens=55):
    bpy.ops.object.camera_add(location=loc); c=bpy.context.object; c.name=name; c.data.lens=lens; aim(c,target); return c
def area(name,loc,energy,color,size,target):
    bpy.ops.object.light_add(type='AREA',location=loc); l=bpy.context.object; l.name=name; l.data.energy=energy; l.data.color=color; l.data.shape='DISK'; l.data.size=size; aim(l,target); return l
keylight=area("Soft warm upper-left key",(-.62,-.48,.82),180,(1.0,.95,.88),.62,(0,0,.035))
area("Cool steel rim",(.56,.18,.45),95,(.62,.72,1.0),.45,(0,0,.04))
area("Low front fill",(-.05,-.65,.20),70,(.78,.82,.88),.7,(0,0,.035))


def render(name,loc,target,lens=55,red=False):
    scene.camera=camera("Camera "+name,loc,target,lens)
    if red:
        keylight.data.color=(1.0,.035,.018); keylight.data.energy=220
        scene.world.color=(.001,.0003,.0003)
    else:
        keylight.data.color=(1.0,.95,.88); keylight.data.energy=180
        scene.world.color=(.006,.006,.006)
    scene.render.filepath=str(OUT/f"render-{name}.png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(scene.camera,do_unlink=True)

render("front",(-.95,-.95,1.35),(0,0,.035),50)
render("top",(0,-.015,1.60),(0,0,.035),50)
render("raking",(-.48,-.24,.20),(-.08,.02,.060),78)
render("emergency",(-.95,-.95,1.35),(0,0,.035),50,True)
# Leave the editable scene in its ordinary studio-lighting state, with the
# operator camera available for a direct F12 render.
keylight.data.color=(1.0,.95,.88); keylight.data.energy=180
world_bg.inputs["Color"].default_value=(.002,.002,.002,1)
world_bg.inputs["Strength"].default_value=.025
scene.camera=camera("Operator view camera",(-.95,-.95,1.35),(0,0,.035),62)

# Audit every scene object against the frame footprint. The studio floor, lights,
# and cameras are intentionally outside this physical-object assertion.
object_audit = []
outside_frame = []
white_or_emissive = []
for ob in bpy.data.objects:
    corners = [ob.matrix_world @ Vector(corner) for corner in ob.bound_box]
    bounds = {axis: [min(v[i] for v in corners), max(v[i] for v in corners)] for i, axis in enumerate(("x", "y", "z"))}
    materials = list(getattr(getattr(ob, "data", None), "materials", []))
    material_flags = []
    for mat in materials:
        if not mat:
            continue
        color = tuple(float(v) for v in mat.diffuse_color[:3])
        emission = False
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'EMISSION' and node.inputs.get("Strength") and float(node.inputs["Strength"].default_value) > 0:
                    emission = True
        if max(color) >= .70 or emission:
            material_flags.append({"name": mat.name, "color": color, "emissive": emission})
    if material_flags:
        white_or_emissive.append({"object": ob.name, "materials": material_flags})
    is_backdrop = ob.name == "Dark studio floor"
    physical = ob.type in {"MESH", "CURVE", "FONT", "SURFACE", "META"} and not is_backdrop
    if physical and (bounds["x"][0] < -FRAME_X/2-.005 or bounds["x"][1] > FRAME_X/2+.005 or
                     bounds["y"][0] < -FRAME_Y/2-.005 or bounds["y"][1] > FRAME_Y/2+.005):
        outside_frame.append(ob.name)
    item = {"name": ob.name, "type": ob.type, "bounds_m": bounds, "materials": [m.name for m in materials if m]}
    object_audit.append(item)
    print("OBJECT_AUDIT", json.dumps(item), flush=True)
assert not outside_frame, f"Objects outside frame bounds + 5 mm: {outside_frame}"
print("OBJECT_AUDIT_SUMMARY", json.dumps({"objects": len(object_audit), "outside_frame": outside_frame,
      "white_or_emissive_material_users": white_or_emissive, "paint_chip_coverage": chip_area/visible_top_area}), flush=True)

# Persist native scene before exporting the selected model to packed PBR GLB.
scene.render.filepath=str(OUT/"render-front.png")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"keyboard.blend"))
for ob in bpy.context.selected_objects: ob.select_set(False)
for ob in bpy.data.objects:
    if ob.type in ('MESH','CURVE'): ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/"keyboard.glb"),export_format='GLB',use_selection=True,
                          export_apply=True,export_texcoords=True,export_normals=True,
                          export_materials='EXPORT',export_cameras=False,export_lights=False)

# Write an exact layout and scene report for independent quality-gate verification.
triangles=0
for ob in bpy.data.objects:
    if ob.type=='MESH':
        mesh=ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
        triangles += len(mesh.loop_triangles)
        ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
from bpy_extras.object_utils import world_to_camera_view

front_image = bpy.data.images.load(str(OUT/"render-front.png"), check_existing=False)
front_pixels = list(front_image.pixels[:])
operator_camera = scene.camera
front_camera = camera("Sampling front render camera", (-.95,-.95,1.35), (0,0,.035), 50)
scene.camera = front_camera
bpy.context.view_layer.update()

def project_sample(label, point):
    uv = world_to_camera_view(scene, front_camera, Vector(point))
    px = max(0, min(front_image.size[0]-1, round(uv.x*(front_image.size[0]-1))))
    py = max(0, min(front_image.size[1]-1, round(uv.y*(front_image.size[1]-1))))
    offset = (py*front_image.size[0]+px)*4
    def to_srgb(value):
        return 12.92 * value if value <= .0031308 else 1.055 * value ** (1 / 2.4) - .055
    rgb = [round(255*to_srgb(front_pixels[offset+i])) for i in range(3)]
    return {"label": label, "world": [round(float(v), 6) for v in point],
            "uv": [round(float(uv.x), 6), round(float(uv.y), 6)],
            "pixel": [px, py], "rgb": rgb}

sample_cap = caps[0]
sample_boot = boots[0]
samples = [
    project_sample("frame_paint", (-.321, -.078, FRAME_Z+.0008)),
    project_sample("cap", (sample_cap.location.x-sample_cap.dimensions.x*.30,
                            sample_cap.location.y,
                            sample_cap.location.z+CAP_H-.0013)),
    project_sample("boot", (sample_boot.location.x-sample_cap.dimensions.x/2-.002,
                             sample_boot.location.y,
                             sample_boot.location.z+.003)),
    project_sample("legend", (caps[10].location.x, caps[10].location.y,
                               caps[10].location.z+CAP_H-.001)),
]
print("PROJECTED_SAMPLES", json.dumps(samples), flush=True)
bpy.data.objects.remove(front_camera, do_unlink=True)
scene.camera = operator_camera
cap_bsdf = caps[0].data.materials[0].node_tree.nodes.get("Principled BSDF")
boot_bsdf = BOOT.node_tree.nodes.get("Principled BSDF")
assert all(.029 <= float(v) <= .04 for v in cap_bsdf.inputs["Base Color"].default_value[:3])
assert abs(cap_bsdf.inputs["Roughness"].default_value-.75) < 1e-6
assert abs(cap_bsdf.inputs["Sheen Weight"].default_value) < 1e-6
assert all(abs(float(v)-.015) < 1e-6 for v in boot_bsdf.inputs["Base Color"].default_value[:3])
assert .06 <= chip_area/visible_top_area <= .12
assert not outside_frame

report = {
    "projected_point_samples": samples,
    "cap_profiles": profile_records,
    "object_audit": object_audit,
    "outside_frame_objects": outside_frame,
    "white_or_emissive_material_users": white_or_emissive,
    "paint_chip_coverage": chip_area/visible_top_area,
    "dimensions_m": {"width": FRAME_X, "depth": FRAME_Y},
    "key_scale": key_scale,
    "piece_key_size_mm": {"width": caps[0].dimensions.x * 1000, "depth": caps[0].dimensions.y * 1000},
    "triangle_count": triangles,
    "key_aspects": [
        {"group": group, "key": key, "design_ratio": source, "cap_ratio": cap, "relative_error": error}
        for group, key, source, cap, error in ASPECT_RESULTS
    ],
    "max_aspect_error": max(error for _, _, _, _, error in ASPECT_RESULTS),
    "cap_count": len(caps), "screw_count": len(screw_positions),
    "samples": scene.cycles.samples, "denoising": scene.cycles.use_denoising,
}
(OUT / "keyboard-report.json").write_text(json.dumps(report, indent=2) + "\n")
print(f"KEYBOARD_CHECK cap_count={len(caps)} screw_count={len(screw_positions)} max_aspect_error={report['max_aspect_error']:.6%} triangles={triangles} legend_images={len(caps)} render_samples={scene.cycles.samples} resolution=1920x1080")
