class_name PodMesh
extends RefCounted
## Realistic stasis pod visuals, issue #37: one merged, multi-surface
## ArrayMesh per pod state (sealed / empty-open / player), built purely
## and deterministically so the seven pods instance three shared meshes.
## The authored greybox solids in PodBody stay the single source for
## colliders and placement parity; this module is dressing only and
## keeps its mass out of the frozen exit aperture mouth strip above the
## traversal band. All numbers are pod-local meters: local +Z is the
## foot (the opening), local -Z the head, up is +Y. The lens is dead:
## dark red, non-emissive, matching the unpowered opening beat.

## The five shared materials, one per surface slot; materials live on
## the mesh surfaces, so all three meshes and all seven instances share
## exactly this set — never a per-pod material instance.
enum Slot { HULL, RUBBER, COUCH, BLANKET, LENS }

## Worn military painted steel, one shared material for every hard
## part. The base albedo is the latch/hardware spec; per-part vertex
## tints (the material runs vertex_color_use_as_albedo, a multiply)
## split its value so dim red light still tells the parts apart: the
## chassis tint lands the effective albedo back on the dark
## grey-green, the lid tint seats the lid slabs lighter than the hull,
## and the latch blocks and hinge barrels ride the untinted base, a
## touch lighter than the lid and glinting under the red fixtures.
const HULL_ALBEDO: Color = Color(0.24, 0.26, 0.23)
const HULL_ROUGHNESS: float = 0.42
const HULL_METALLIC: float = 0.7
const CHASSIS_TINT: Color = Color(0.667, 0.692, 0.652)
const LID_TINT: Color = Color(0.875, 0.885, 0.87)
const WHITE_TINT: Color = Color(1.0, 1.0, 1.0)

## The sealed lid's crown depth over its rim plane: deep enough that
## the red fixtures draw a highlight band across the crown.
const SEALED_LID_BOW: float = 0.07

## Rubber gasket black.
const RUBBER_ALBEDO: Color = Color(0.02, 0.021, 0.023)
const RUBBER_ROUGHNESS: float = 0.92

## Interior fabric: the lightest surfaces on an open pod. The cavity
## floor plate and the foot stop ride a slightly darker tint on the
## same shared material.
const COUCH_ALBEDO: Color = Color(0.34, 0.31, 0.27)
const COUCH_ROUGHNESS: float = 0.95
const COUCH_STOP_TINT: Color = Color(0.82, 0.82, 0.82)

## Occupancy blanket: worn olive-grey fabric, fully matte, the
## lightest read on the pods so its drape breaks the box outline.
const BLANKET_ALBEDO: Color = Color(0.38, 0.34, 0.27)
const BLANKET_ROUGHNESS: float = 1.0

## The dead status lens: dark red glass, unlit, low roughness so the
## emergency fixtures glint off it without ever emitting.
const LENS_ALBEDO: Color = Color(0.28, 0.02, 0.02)
const LENS_ROUGHNESS: float = 0.18

## The pod silhouette the dressing must stay inside (pod-local): the
## authored footprint plus the skid and indicator dressing slack.
const BOUND_MIN: Vector3 = Vector3(-0.55, 0.0, -1.16)
const BOUND_MAX: Vector3 = Vector3(0.55, 2.7, 1.16)

static var _state_meshes: Dictionary = {}
static var _slot_materials: Array[StandardMaterial3D] = []

## The cached mesh for one pod state: the same ArrayMesh resource is
## handed to every pod in that state, so the seven pods draw from three
## meshes total.
static func for_state(state: int) -> ArrayMesh:
	if not _state_meshes.has(state):
		_state_meshes[state] = build_state_mesh(state)
	return _state_meshes[state]

## A fresh, uncached build of one state's mesh: the determinism pin
## builds twice and compares arrays, so construction must allocate anew
## but produce identical bytes.
static func build_state_mesh(state: int) -> ArrayMesh:
	var builder := PodBuilder.new()
	builder.hull_chassis()
	match state:
		Pods.PodState.SEALED:
			builder.sealed_top()
		Pods.PodState.EMPTY_OPEN:
			builder.open_top()
		Pods.PodState.PLAYER:
			builder.player_top()
	return builder.commit()

## The shared material for one slot, created once per process.
static func material_for_slot(slot: int) -> StandardMaterial3D:
	if _slot_materials.is_empty():
		_slot_materials.resize(Slot.size())
	if _slot_materials[slot] == null:
		_slot_materials[slot] = _make_material(slot)
	return _slot_materials[slot]

## The pinned shared-material count across all pod meshes.
static func slot_count() -> int:
	return Slot.size()

static func _make_material(slot: int) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	match slot:
		Slot.HULL:
			material.albedo_color = HULL_ALBEDO
			material.roughness = HULL_ROUGHNESS
			material.metallic = HULL_METALLIC
			material.vertex_color_use_as_albedo = true
		Slot.RUBBER:
			material.albedo_color = RUBBER_ALBEDO
			material.roughness = RUBBER_ROUGHNESS
		Slot.COUCH:
			material.albedo_color = COUCH_ALBEDO
			material.roughness = COUCH_ROUGHNESS
			material.vertex_color_use_as_albedo = true
		Slot.BLANKET:
			material.albedo_color = BLANKET_ALBEDO
			material.roughness = BLANKET_ROUGHNESS
		Slot.LENS:
			material.albedo_color = LENS_ALBEDO
			material.roughness = LENS_ROUGHNESS
			material.metallic = 0.1
	# Every pod system is dead through the opening beat: nothing emits.
	material.emission_enabled = false
	return material

## Deterministic pod-local mesh assembly. One SurfaceTool per material
## slot; parts append transformed triangles and the commit folds them
## into one multi-surface ArrayMesh. Winding is corrected per face
## against an expected outward direction, so every helper stays
## orientation-safe under rotation.
class PodBuilder:
	extends RefCounted

	var _tools: Array[SurfaceTool] = []

	## The vertex tint applied to every vertex emitted from here on:
	## parts set it before emitting. Slots whose material ignores
	## vertex colors are unaffected by whatever it holds.
	var _tint: Color = Color(1.0, 1.0, 1.0)

	func _init() -> void:
		_tools.resize(PodMesh.Slot.size())

	func _tool(slot: int) -> SurfaceTool:
		if _tools[slot] == null:
			var tool := SurfaceTool.new()
			tool.begin(Mesh.PRIMITIVE_TRIANGLES)
			_tools[slot] = tool
		return _tools[slot]

	## One quad as two triangles, flat-shaded, emitted in local space
	## through `t` (identity for pod-frame parts).
	func _quad(slot: int, a: Vector3, b: Vector3, c: Vector3, d: Vector3, outward: Vector3, t: Transform3D) -> void:
		var normal := (b - a).cross(c - a)
		assert(normal.length_squared() > 1e-12, "degenerate quad in pod mesh")
		if normal.dot(outward) < 0.0:
			var mid_a := a
			var mid_b := b
			a = d
			b = c
			c = mid_b
			d = mid_a
			normal = -normal
		var tool := _tool(slot)
		tool.set_normal(t.basis * normal.normalized())
		tool.set_color(_tint)
		tool.add_vertex(t * a)
		tool.add_vertex(t * b)
		tool.add_vertex(t * c)
		tool.add_vertex(t * a)
		tool.add_vertex(t * c)
		tool.add_vertex(t * d)

	## One triangle, flat-shaded, winding corrected to `outward`.
	func _tri(slot: int, a: Vector3, b: Vector3, c: Vector3, outward: Vector3, t: Transform3D) -> void:
		var normal := (b - a).cross(c - a)
		assert(normal.length_squared() > 1e-12, "degenerate triangle in pod mesh")
		if normal.dot(outward) < 0.0:
			var mid := b
			b = c
			c = mid
			normal = -normal
		var tool := _tool(slot)
		tool.set_normal(t.basis * normal.normalized())
		tool.set_color(_tint)
		tool.add_vertex(t * a)
		tool.add_vertex(t * b)
		tool.add_vertex(t * c)

	## A plain six-face box, pod frame.
	func box(slot: int, center: Vector3, size: Vector3) -> void:
		chamfered_box(slot, center, size, 0.0)

	## A chamfered box: the six faces inset by the chamfer, twelve
	## 45-degree edge quads, and eight corner triangles. A zero chamfer
	## degenerates exactly to the plain box, so the edges and corners
	## are skipped rather than emitted collapsed.
	func chamfered_box(slot: int, center: Vector3, size: Vector3, chamfer: float) -> void:
		var half := size * 0.5
		var c: float = minf(chamfer, minf(minf(half.x, half.y), half.z) * 0.45)
		var axes := [Vector3.RIGHT, Vector3.UP, Vector3.BACK]
		var identity := Transform3D()
		for axis_index: int in range(3):
			var edge_a: Vector3 = axes[axis_index]
			var edge_b: Vector3 = axes[(axis_index + 1) % 3]
			var edge_c: Vector3 = axes[(axis_index + 2) % 3]
			var half_a: float = size[axis_index] / 2.0
			var half_b: float = size[(axis_index + 1) % 3] / 2.0
			var half_c: float = size[(axis_index + 2) % 3] / 2.0
			# The two faces normal to edge_a, inset by the chamfer.
			for dir: float in [-1.0, 1.0]:
				var face_center := center + edge_a * (dir * half_a)
				var corner_0 := face_center - edge_b * (half_b - c) - edge_c * (half_c - c)
				var corner_1 := face_center + edge_b * (half_b - c) - edge_c * (half_c - c)
				var corner_2 := face_center + edge_b * (half_b - c) + edge_c * (half_c - c)
				var corner_3 := face_center - edge_b * (half_b - c) + edge_c * (half_c - c)
				_quad(slot, corner_0, corner_1, corner_2, corner_3, edge_a * dir, identity)
			if c <= 0.0:
				continue
			# The four chamfer quads bridging the faces normal to edge_a
			# and edge_b, running along edge_c.
			for dir_a: float in [-1.0, 1.0]:
				for dir_b: float in [-1.0, 1.0]:
					var outward := (edge_a * dir_a + edge_b * dir_b).normalized()
					var span := half_c - c
					var on_a_0 := center + edge_a * (dir_a * half_a) + edge_b * (dir_b * (half_b - c)) - edge_c * span
					var on_a_1 := center + edge_a * (dir_a * half_a) + edge_b * (dir_b * (half_b - c)) + edge_c * span
					var on_b_0 := center + edge_a * (dir_a * (half_a - c)) + edge_b * (dir_b * half_b) - edge_c * span
					var on_b_1 := center + edge_a * (dir_a * (half_a - c)) + edge_b * (dir_b * half_b) + edge_c * span
					_quad(slot, on_a_0, on_b_0, on_b_1, on_a_1, outward, identity)
			# The four corners spanning all three axes.
			for dir_a: float in [-1.0, 1.0]:
				for dir_b: float in [-1.0, 1.0]:
					for dir_c: float in [-1.0, 1.0]:
						var outward := (edge_a * dir_a + edge_b * dir_b + edge_c * dir_c).normalized()
						var q1 := center + edge_a * (dir_a * half_a) + edge_b * (dir_b * (half_b - c)) + edge_c * (dir_c * (half_c - c))
						var q2 := center + edge_a * (dir_a * (half_a - c)) + edge_b * (dir_b * half_b) + edge_c * (dir_c * (half_c - c))
						var q3 := center + edge_a * (dir_a * (half_a - c)) + edge_b * (dir_b * (half_b - c)) + edge_c * (dir_c * half_c)
						_tri(slot, q1, q2, q3, outward, identity)

	## A cylinder along the local X axis, for hinge barrels: open prism
	## sides plus two fan caps, `segments` around.
	func cylinder_x(slot: int, center: Vector3, radius: float, length: float, segments: int) -> void:
		var identity := Transform3D()
		var half_x := length / 2.0
		for index: int in range(segments):
			var angle_0 := TAU * index / segments
			var angle_1 := TAU * (index + 1) / segments
			var radial_0 := Vector3(0.0, cos(angle_0), sin(angle_0))
			var radial_1 := Vector3(0.0, cos(angle_1), sin(angle_1))
			var mid := (radial_0 + radial_1).normalized() * radius
			var near_0 := center + Vector3(-half_x, 0.0, 0.0) + radial_0 * radius
			var near_1 := center + Vector3(-half_x, 0.0, 0.0) + radial_1 * radius
			var far_0 := center + Vector3(half_x, 0.0, 0.0) + radial_0 * radius
			var far_1 := center + Vector3(half_x, 0.0, 0.0) + radial_1 * radius
			_quad(slot, near_0, far_0, far_1, near_1, mid, identity)
			# Fan caps: flat triangles from each cap center.
			var cap_neg := center + Vector3(-half_x, 0.0, 0.0)
			var cap_pos := center + Vector3(half_x, 0.0, 0.0)
			_tri(slot, cap_neg, near_0, near_1, Vector3.LEFT, identity)
			_tri(slot, cap_pos, far_1, far_0, Vector3.RIGHT, identity)

	## The crown height over the flat rim plane of a bowed slab.
	static func crown(half: Vector3, bow: float, x: float, z: float) -> float:
		var fx: float = 1.0 - (x / half.x) * (x / half.x)
		var fz: float = 1.0 - (z / half.z) * (z / half.z)
		return half.y + bow * fx * fz

	## A lid slab with a parabolic crown on its local +Y face and a flat
	## bottom: a segmented top grid, vertical skirts on all four edges,
	## and a flat underside. Built about the local origin, then carried
	## into the pod frame by `t` (identity for the sealed lid; the open
	## lid and canopy pass rotations).
	func bowed_slab(slot: int, t: Transform3D, size: Vector3, bow: float, seg_x: int, seg_z: int) -> void:
		var half := size * 0.5
		# Top grid, flat-shaded per cell.
		for iz: int in range(seg_z):
			for ix: int in range(seg_x):
				var x_0 := -half.x + size.x * ix / seg_x
				var x_1 := -half.x + size.x * (ix + 1) / seg_x
				var z_0 := -half.z + size.z * iz / seg_z
				var z_1 := -half.z + size.z * (iz + 1) / seg_z
				var p_0 := Vector3(x_0, crown(half, bow, x_0, z_0), z_0)
				var p_1 := Vector3(x_1, crown(half, bow, x_1, z_0), z_0)
				var p_2 := Vector3(x_1, crown(half, bow, x_1, z_1), z_1)
				var p_3 := Vector3(x_0, crown(half, bow, x_0, z_1), z_1)
				_quad(slot, p_0, p_1, p_2, p_3, Vector3.UP, t)
		# Skirts: from each top edge down to the flat underside. The
		# edges normal to X are flat along their length; the edges
		# normal to Z follow the crown, so they are subdivided.
		for dir_x: float in [-1.0, 1.0]:
			var top_a := Vector3(dir_x * half.x, half.y, -half.z)
			var top_b := Vector3(dir_x * half.x, half.y, half.z)
			var bot_a := Vector3(dir_x * half.x, -half.y, -half.z)
			var bot_b := Vector3(dir_x * half.x, -half.y, half.z)
			_quad(slot, top_a, bot_a, bot_b, top_b, Vector3.RIGHT * dir_x, t)
		for dir_z: float in [-1.0, 1.0]:
			for ix: int in range(seg_x):
				var x_0 := -half.x + size.x * ix / seg_x
				var x_1 := -half.x + size.x * (ix + 1) / seg_x
				var top_a := Vector3(x_0, crown(half, bow, x_0, dir_z * half.z), dir_z * half.z)
				var top_b := Vector3(x_1, crown(half, bow, x_1, dir_z * half.z), dir_z * half.z)
				var bot_a := Vector3(x_0, -half.y, dir_z * half.z)
				var bot_b := Vector3(x_1, -half.y, dir_z * half.z)
				_quad(slot, top_a, top_b, bot_b, bot_a, Vector3.BACK * dir_z, t)
		# Flat underside.
		var u_0 := Vector3(-half.x, -half.y, -half.z)
		var u_1 := Vector3(half.x, -half.y, -half.z)
		var u_2 := Vector3(half.x, -half.y, half.z)
		var u_3 := Vector3(-half.x, -half.y, half.z)
		_quad(slot, u_0, u_3, u_2, u_1, Vector3.DOWN, t)

	## A double-sided quad strip: thin fabric is visible from both
	## sides, so each cell is emitted twice with opposite windings.
	func fabric_strip(slot: int, a: Vector3, b: Vector3, c: Vector3, d: Vector3, reference: Vector3, t: Transform3D) -> void:
		_quad(slot, a, b, c, d, reference, t)
		_quad(slot, a, b, c, d, -reference, t)

	## The shared hull chassis every state carries: skid rails and feet,
	## the beveled tray (base, side walls stopping at the mouth line,
	## head wall), rim flanges, hinge barrels and mounts on the head top
	## edge, and the dead status lens proud of the indicator plate.
	func hull_chassis() -> void:
		_tint = CHASSIS_TINT
		# Mounting skid: rails flush outside the shell walls plus four
		# blocky feet; flush at the head face, overhanging the foot.
		for side: float in [-1.0, 1.0]:
			chamfered_box(Slot.HULL, Vector3(side * 0.48, 0.03, 0.015), Vector3(0.06, 0.06, 2.23), 0.012)
		for side_x: float in [-1.0, 1.0]:
			for side_z: float in [-1.0, 1.0]:
				chamfered_box(Slot.HULL, Vector3(side_x * 0.48, 0.035, side_z * 1.05), Vector3(0.1, 0.07, 0.16), 0.012)
		# The tray: beveled base slab, side walls stopping at the
		# authored mouth line, head wall between them.
		chamfered_box(Slot.HULL, Vector3(0.0, 0.05, 0.0), Vector3(0.9, 0.1, 2.2), 0.015)
		for side: float in [-1.0, 1.0]:
			chamfered_box(Slot.HULL, Vector3(side * 0.42, 0.45, -0.03), Vector3(0.06, 0.7, 2.14), 0.012)
		chamfered_box(Slot.HULL, Vector3(0.0, 0.45, -1.07), Vector3(0.78, 0.7, 0.06), 0.012)
		# Rim flanges: slightly proud lips the lids seat against, ending
		# exactly at the authored mouth wall line so the exit strip stays
		# open at the foot.
		for side: float in [-1.0, 1.0]:
			box(Slot.HULL, Vector3(side * 0.425, 0.7925, -0.03), Vector3(0.11, 0.025, 2.14))
		box(Slot.HULL, Vector3(0.0, 0.7925, -1.065), Vector3(0.84, 0.025, 0.07))
		# Hinges on the head top edge: barrels with mount plates. The
		# barrels ride the untinted steel base so they glint.
		for side: float in [-1.0, 1.0]:
			_tint = WHITE_TINT
			cylinder_x(Slot.HULL, Vector3(side * 0.27, 0.802, -1.095), 0.026, 0.18, 8)
			_tint = CHASSIS_TINT
			box(Slot.HULL, Vector3(side * 0.27, 0.765, -1.121), Vector3(0.16, 0.07, 0.042))
		# The dead lens, seated 1 mm into the authored indicator plate so
		# no face is coplanar, its front proud of the plate.
		box(Slot.LENS, Vector3(0.0, 0.55, 1.1455), Vector3(0.1, 0.05, 0.013))

	## The sealed pod's top: the bowed lid seated on the flanges, the
	## compressed rubber seam where lid meets rim, and two over-center
	## latch blocks clamping the foot edge inside the mouth wall line.
	func sealed_top() -> void:
		# Side seams end at the mouth wall line like the shell walls.
		for side: float in [-1.0, 1.0]:
			box(Slot.RUBBER, Vector3(side * 0.44, 0.812, -0.03), Vector3(0.04, 0.02, 2.14))
		for dir_z: float in [-1.0, 1.0]:
			# The foot-side seam stops short of the mouth wall line.
			var strip_z: float = -1.06 if dir_z < 0.0 else 1.02
			box(Slot.RUBBER, Vector3(0.0, 0.812, strip_z), Vector3(0.84, 0.02, 0.04))
		# The closed lid: seated on the flanges, tinted lighter than the
		# chassis, its crown bowed deep enough to catch a highlight band
		# from the red fixtures.
		_tint = LID_TINT
		bowed_slab(
			Slot.HULL,
			Transform3D(Basis(), Vector3(0.0, 0.83, 0.0)),
			Vector3(0.9, 0.06, 2.2),
			SEALED_LID_BOW,
			6,
			12
		)
		# The over-center latches clamp the foot edge, a touch lighter.
		_tint = WHITE_TINT
		for side: float in [-1.0, 1.0]:
			chamfered_box(Slot.HULL, Vector3(side * 0.26, 0.785, 0.95), Vector3(0.1, 0.06, 0.14), 0.012)

	## The open pod's rim: the rubber gasket ring around the aperture,
	## stopping short of the mouth strip.
	func gasket_ring() -> void:
		for side: float in [-1.0, 1.0]:
			box(Slot.RUBBER, Vector3(side * 0.415, 0.814, -0.03), Vector3(0.05, 0.018, 2.06))
		box(Slot.RUBBER, Vector3(0.0, 0.814, -1.055), Vector3(0.74, 0.018, 0.05))

	## The open cavity's interior: dark floor plate, mattress pad, side
	## bolsters, head pillow, and a foot stop, all clear of the capsule's
	## lying band except the pad the body presses into.
	func restraint_couch() -> void:
		# The cavity floor plate rides the slightly darker stop tint so
		# the mattress and pillow above it read as the lightest surfaces.
		_tint = COUCH_STOP_TINT
		box(Slot.COUCH, Vector3(0.0, 0.106, 0.0), Vector3(0.78, 0.012, 2.08))
		_tint = WHITE_TINT
		box(Slot.COUCH, Vector3(0.0, 0.127, -0.02), Vector3(0.72, 0.03, 1.86))
		for side: float in [-1.0, 1.0]:
			chamfered_box(Slot.COUCH, Vector3(side * 0.34, 0.165, -0.02), Vector3(0.08, 0.09, 1.78), 0.025)
		chamfered_box(Slot.COUCH, Vector3(0.0, 0.175, -0.9), Vector3(0.46, 0.1, 0.28), 0.03)
		# The foot stop: the slightly darker pad the feet press into.
		_tint = COUCH_STOP_TINT
		chamfered_box(Slot.COUCH, Vector3(0.0, 0.15, 0.9), Vector3(0.6, 0.07, 0.12), 0.02)

	## The empty-open pod's top: gasket ring, restraint couch, the lid
	## propped on its hinges at the authored 60-degree tilt, and the
	## occupancy blanket draped over the +X rim at the authored hang.
	func open_top() -> void:
		gasket_ring()
		restraint_couch()
		propped_lid()
		hanging_blanket()

	## The open lid: a bowed slab at the authored hinge line and tilt.
	func propped_lid() -> void:
		var rotation := Quaternion(Vector3.RIGHT, -PodBody.LID_OPEN_TILT)
		var offset := rotation * Vector3(0.0, 0.0, (Pods.POD_LENGTH - PodBody.LID_SETBACK) / 2.0)
		var hinge := Vector3(0.0, Pods.POD_HEIGHT, -Pods.POD_LENGTH / 2.0)
		_tint = LID_TINT
		bowed_slab(
			Slot.HULL,
			Transform3D(Basis(rotation), hinge + offset),
			Vector3(0.88, 0.06, Pods.POD_LENGTH - PodBody.LID_SETBACK),
			0.02,
			4,
			8
		)

	## The player pod's top: gasket ring, restraint couch, and the lid
	## stood upright as a canopy over the head end.
	func player_top() -> void:
		gasket_ring()
		restraint_couch()
		_tint = LID_TINT
		bowed_slab(
			Slot.HULL,
			Transform3D(Basis(Quaternion(Vector3.RIGHT, PI / 2.0)), Vector3(0.0, 1.45, -1.07)),
			Vector3(0.9, 0.06, 1.3),
			0.025,
			3,
			6
		)

	## The occupancy blanket: a double-sided fabric panel rising out of
	## the couch, cresting the rim, then folding further over the rim's
	## exterior so the drape reaches past the skid line and breaks the
	## box outline against the wall, with the hanging curtain's folds
	## deepening downward. The silhouette stays inside the pinned pod
	## envelope.
	func hanging_blanket() -> void:
		var z_lo := -Pods.POD_LENGTH / 2.0 + PodBody.BLANKET_FROM_FOOT
		var identity := Transform3D()
		# The over-rim flap profile, from mattress to the outside fold.
		var stations: Array[Vector2] = [
			Vector2(0.3, 0.19),
			Vector2(0.39, 0.23),
			Vector2(0.445, 0.55),
			Vector2(0.455, 0.815),
			Vector2(0.515, 0.78),
			Vector2(0.545, 0.68),
		]
		for index: int in range(stations.size() - 1):
			var from: Vector2 = stations[index]
			var to: Vector2 = stations[index + 1]
			for iz: int in range(5):
				var z_0 := z_lo + PodBody.BLANKET_WIDTH * iz / 5.0
				var z_1 := z_lo + PodBody.BLANKET_WIDTH * (iz + 1) / 5.0
				var a := Vector3(from.x, from.y, z_0 + blanket_ripple(z_0, z_lo))
				var b := Vector3(to.x, to.y, z_0 + blanket_ripple(z_0, z_lo))
				var c := Vector3(to.x, to.y, z_1 + blanket_ripple(z_1, z_lo))
				var d := Vector3(from.x, from.y, z_1 + blanket_ripple(z_1, z_lo))
				var reference := Vector3(0.0, 1.0, 0.0) if index < 3 else Vector3(1.0, 0.0, 0.0)
				fabric_strip(Slot.BLANKET, a, b, c, d, reference, identity)
		# The hanging curtain: folds deepen toward the bottom edge.
		for iy: int in range(6):
			var y_0 := 0.68 - 0.44 * iy / 6.0
			var y_1 := 0.68 - 0.44 * (iy + 1) / 6.0
			for iz: int in range(5):
				var z_0 := z_lo + PodBody.BLANKET_WIDTH * iz / 5.0
				var z_1 := z_lo + PodBody.BLANKET_WIDTH * (iz + 1) / 5.0
				var a := Vector3(0.525 + blanket_folds(z_0, y_0), y_0, z_0)
				var b := Vector3(0.525 + blanket_folds(z_1, y_0), y_0, z_1)
				var c := Vector3(0.525 + blanket_folds(z_1, y_1), y_1, z_1)
				var d := Vector3(0.525 + blanket_folds(z_0, y_1), y_1, z_0)
				fabric_strip(Slot.BLANKET, a, b, c, d, Vector3.RIGHT, identity)

	## The flap's gentle lengthwise ripple, in meters.
	static func blanket_ripple(z: float, z_lo: float) -> float:
		return 0.012 * sin((z - z_lo) / PodBody.BLANKET_WIDTH * 2.5 * PI + 0.5)

	## The curtain's fold displacement: three lengthwise waves whose
	## depth grows toward the hanging bottom edge, in meters.
	static func blanket_folds(z: float, y: float) -> float:
		var depth: float = clampf((0.68 - y) / (0.68 - 0.24), 0.0, 1.0)
		var z_lo: float = -Pods.POD_LENGTH / 2.0 + PodBody.BLANKET_FROM_FOOT
		return 0.02 * sin((z - z_lo) / PodBody.BLANKET_WIDTH * 3.0 * PI + 0.35) * depth

	## Fold every populated slot into one multi-surface ArrayMesh with
	## the shared materials assigned per surface.
	func commit() -> ArrayMesh:
		var mesh := ArrayMesh.new()
		for slot: int in range(PodMesh.Slot.size()):
			if _tools[slot] == null:
				continue
			var tool: SurfaceTool = _tools[slot]
			tool.set_material(PodMesh.material_for_slot(slot))
			tool.commit(mesh)
		return mesh
