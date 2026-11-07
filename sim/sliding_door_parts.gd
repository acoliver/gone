class_name SlidingDoorParts
extends RefCounted
## Ordinary doors share one in-wall leaf, pocket, trim and flush-track recipe.

const THICKNESS := 0.05
const BORDER_RAISE := 0.002
const FRAME_BAND := 0.05
const FRAME_PROUD := 0.012
const POCKET_DEPTH := 0.08
const POCKET_CLEARANCE := 0.02
const PULL_DEPTH := 0.008
const LABEL_SIZE := Vector2(0.80, 0.60)
const LABEL_HEIGHT := 1.75

static func applies(door: ShipLayout.DoorSpec) -> bool:
	return door.kind() in [ShipLayout.DoorKind.POWER, ShipLayout.DoorKind.SIDE]

static func has_pocket(door: ShipLayout.DoorSpec) -> bool:
	return door.kind() == ShipLayout.DoorKind.POWER

static func leaf_width(door: ShipLayout.DoorSpec) -> float:
	# Preserve the 1.15 m stroke and 1 m passage. The overlapping leaf stops
	# 10 mm beyond the pocket jamb, where its leading edge can still be reached.
	return 2 * (Doors.POWER_SLIDE - door.aperture().x / 2 - 0.01)

static func cavity(door: ShipLayout.DoorSpec) -> AABB:
	assert(has_pocket(door), "only the power door opens into a pocket")
	var width := leaf_width(door)
	var start := -width / 2 - POCKET_CLEARANCE + minf(0, door.slide_sign() * Doors.POWER_SLIDE)
	return AABB(Vector3(start, 0, (ShipLayout.WALL - POCKET_DEPTH) / 2), Vector3(width + Doors.POWER_SLIDE + 2 * POCKET_CLEARANCE, door.aperture().y + POCKET_CLEARANCE, POCKET_DEPTH))

static func pocket(door: ShipLayout.DoorSpec) -> AABB:
	var result := cavity(door)
	if door.slide_sign() > 0:
		result.size.x = result.end.x - door.aperture().x / 2
		result.position.x = door.aperture().x / 2
	else:
		result.size.x = -door.aperture().x / 2 - result.position.x
	return result

static func leaf_solid(door: ShipLayout.DoorSpec) -> ShipGeometry.SolidSpec:
	assert(applies(door), "ordinary door required")
	return ShipGeometry.transformed(ShipGeometry.SolidSpec.new(Vector3(0, door.aperture().y / 2, ShipLayout.WALL / 2), Vector3(leaf_width(door), door.aperture().y, THICKNESS + 2 * BORDER_RAISE), Quaternion.IDENTITY, StringName("%s/LEAF" % door.id()), &"door"), door.frame())

static func pull_rect(door: ShipLayout.DoorSpec) -> Rect2:
	return Rect2(Vector2(-leaf_width(door) / 2 + 0.02, 1.02), Vector2(0.22, 0.24))

static func label_rect() -> Rect2:
	return Rect2(Vector2(0.10, LABEL_HEIGHT) - LABEL_SIZE / 2, LABEL_SIZE)

static func label_frame(door: ShipLayout.DoorSpec, side: int) -> Transform3D:
	var sign_z := -1.0 if side == 0 else 1.0
	return Transform3D(Basis() if side == 1 else Basis(Vector3.LEFT, Vector3.UP, Vector3.FORWARD), Vector3(0.10, LABEL_HEIGHT - door.aperture().y / 2, sign_z * (THICKNESS / 2 + BORDER_RAISE + 0.0002)))

static func _box(parts: Array[HatchParts.Part], id: String, size: Vector3, center: Vector3) -> void:
	if size.x > 0 and size.y > 0 and size.z > 0:
		parts.append(HatchParts.Part.new(StringName(id), &"box", size, Transform3D(Basis(), center)))

static func subtract(box: AABB, cut: AABB) -> Array[AABB]:
	var hit := box.intersection(cut)
	if not hit.has_volume(): return [box]
	var pieces: Array[AABB] = []
	var lo := box.position
	var hi := box.end
	var a := hit.position
	var b := hit.end
	for pair: Array in [[lo, Vector3(a.x, hi.y, hi.z)], [Vector3(b.x, lo.y, lo.z), hi], [Vector3(a.x, lo.y, lo.z), Vector3(b.x, a.y, hi.z)], [Vector3(a.x, b.y, lo.z), Vector3(b.x, hi.y, hi.z)], [Vector3(a.x, a.y, lo.z), Vector3(b.x, b.y, a.z)], [Vector3(a.x, a.y, b.z), Vector3(b.x, b.y, hi.z)]]:
		var piece := AABB(pair[0], pair[1] - pair[0])
		if piece.has_volume(): pieces.append(piece)
	return pieces

static func leaf_parts(door: ShipLayout.DoorSpec) -> Array[HatchParts.Part]:
	var parts: Array[HatchParts.Part] = []
	var width := leaf_width(door)
	var height := door.aperture().y
	var pull := pull_rect(door)
	_box(parts, "core", Vector3(width, height, THICKNESS - PULL_DEPTH * 2), Vector3(0, height / 2, ShipLayout.WALL / 2))
	for side: int in [-1, 1]:
		var z := ShipLayout.WALL / 2 + side * (THICKNESS - PULL_DEPTH) / 2
		var skin := AABB(Vector3(-width / 2, 0, z - PULL_DEPTH / 2), Vector3(width, height, PULL_DEPTH))
		var cut := AABB(Vector3(pull.position.x, pull.position.y, skin.position.z - 0.001), Vector3(pull.size.x, pull.size.y, skin.size.z + 0.002))
		for box: AABB in subtract(skin, cut): _box(parts, "skin/%s/%d" % [side, parts.size()], box.size, box.get_center())
		_box(parts, "pull-base/%s" % side, Vector3(pull.size.x, pull.size.y, 0.001), Vector3(pull.get_center().x, pull.get_center().y, ShipLayout.WALL / 2 + side * (THICKNESS / 2 - PULL_DEPTH + 0.0005)))
		z = ShipLayout.WALL / 2 + side * (THICKNESS + BORDER_RAISE) / 2
		for x: float in [-0.35, 0.56]: _box(parts, "border/%s/%s" % [side, x], Vector3(0.02, height - 0.20, BORDER_RAISE), Vector3(x, height / 2, z))
		for y: float in [0.10, height - 0.10]: _box(parts, "border/%s/%s" % [side, y], Vector3(0.93, 0.02, BORDER_RAISE), Vector3(0.105, y, z))
		_box(parts, "glyph-plate/%s" % side, Vector3(LABEL_SIZE.x, LABEL_SIZE.y, BORDER_RAISE), Vector3(0.10, LABEL_HEIGHT, z))
		for x: float in [-0.35, 0.56]:
			for index: int in range(15):
				var point := Vector3(x, lerpf(0.12, height - 0.12, index / 14.0), z)
				parts.append(HatchParts.Part.new(StringName("rivet/%s/%s/%s" % [side, x, index]), &"cylinder", Vector3(0.014, BORDER_RAISE, 0.014), Transform3D(Basis(Quaternion(Vector3.UP, Vector3.BACK * side)), point), 0.007))
	return parts

static func fixed_solids(door: ShipLayout.DoorSpec) -> Array[ShipGeometry.SolidSpec]:
	var solids: Array[ShipGeometry.SolidSpec] = []
	var aperture := door.aperture()
	for side: int in [-1, 1]:
		var z := -FRAME_PROUD / 2 if side < 0 else ShipLayout.WALL + FRAME_PROUD / 2
		for x: float in [-1, 1]:
			var solid := ShipGeometry.SolidSpec.new(Vector3(x * (aperture.x + FRAME_BAND) / 2, (aperture.y + FRAME_BAND) / 2, z), Vector3(FRAME_BAND, aperture.y + FRAME_BAND, FRAME_PROUD), Quaternion.IDENTITY, StringName("%s/TRIM/%s/%s" % [door.id(), side, x]), &"door", &"frame_detail")
			solid.surface_identity(door.id(), &"FRAME")
			solids.append(ShipGeometry.transformed(solid, door.frame()))
		var top := ShipGeometry.SolidSpec.new(Vector3(0, aperture.y + FRAME_BAND / 2, z), Vector3(aperture.x, FRAME_BAND, FRAME_PROUD), Quaternion.IDENTITY, StringName("%s/TRIM/%s/TOP" % [door.id(), side]), &"door", &"frame_detail")
		top.surface_identity(door.id(), &"FRAME")
		solids.append(ShipGeometry.transformed(top, door.frame()))
	# A flush steel threshold closes the bottom of the tunnel on both faces;
	# its narrower track continues inside the power pocket.
	var threshold := ShipGeometry.SolidSpec.new(Vector3(0, -0.0012, ShipLayout.WALL / 2), Vector3(aperture.x + FRAME_BAND * 2, 0.002, ShipLayout.WALL), Quaternion.IDENTITY, StringName("%s/THRESHOLD" % door.id()), &"door", &"frame_detail")
	threshold.surface_identity(door.id(), &"COAMING")
	solids.append(ShipGeometry.transformed(threshold, door.frame()))
	var slot := cavity(door) if has_pocket(door) else AABB(Vector3(-aperture.x / 2, 0, (ShipLayout.WALL - POCKET_DEPTH) / 2), Vector3(aperture.x, 0, POCKET_DEPTH))
	var track := ShipGeometry.SolidSpec.new(Vector3(slot.get_center().x, -0.001, ShipLayout.WALL / 2), Vector3(slot.size.x, 0.002, POCKET_DEPTH), Quaternion.IDENTITY, StringName("%s/TRACK" % door.id()), &"door", &"frame_detail")
	track.surface_identity(door.id(), &"COAMING")
	solids.append(ShipGeometry.transformed(track, door.frame()))
	return solids

static func is_host_wall(door: ShipLayout.DoorSpec, solid: ShipGeometry.SolidSpec) -> bool:
	if solid.material_role != &"wall": return false
	var local := door.frame().affine_inverse() * solid.transform * AABB(-solid.size / 2, solid.size)
	# Jambs and lintels are parts of the same host band, regardless of height.
	return absf(local.position.z) <= 0.000001 and absf(local.end.z - ShipLayout.WALL) <= 0.000001

# Drawn returns only. The original solid wall boxes remain the collision recipe.
static func wall_cuts(layout: ShipLayout, solid: ShipGeometry.SolidSpec) -> Array[AABB]:
	var cuts: Array[AABB] = []
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if not applies(door) or not is_host_wall(door, solid): continue
		var relative := solid.transform.affine_inverse() * door.frame()
		if has_pocket(door): cuts.append(relative * cavity(door))
		if door.kind() == ShipLayout.DoorKind.SIDE:
			cuts.append(relative * AABB(Vector3(-door.aperture().x / 2, 0, -FRAME_PROUD), Vector3(door.aperture().x, door.aperture().y, ShipLayout.WALL + 2 * FRAME_PROUD)))
	return cuts

static func wall_boxes(layout: ShipLayout, solid: ShipGeometry.SolidSpec) -> Array[AABB]:
	var boxes: Array[AABB] = [AABB(-solid.size / 2, solid.size)]
	for cut: AABB in wall_cuts(layout, solid):
		var remainder: Array[AABB] = []
		for box: AABB in boxes: remainder.append_array(subtract(box, cut))
		boxes = remainder
	return boxes
