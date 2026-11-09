class_name ShipDressing
extends RefCounted
## Pure corridor template, invoked only by ShipLayout. Poses use unit primitive
## bounds so construction, exclusion clipping and headless checks share data.

const UNIT := AABB(Vector3.ONE * -0.5, Vector3.ONE)
const RIB_PITCH: float = ShipLayout.DRESSING_RIB_PITCH
const PANEL_PITCH := ShipLayout.DRESSING_PANEL_PITCH
const RIVET_PITCH: float = 0.22

static func build(layout: ShipLayout, space: ShipLayout.Spec) -> ShipLayout.DressingSpec:
	var spec := ShipLayout.DressingSpec.new()
	spec.owner_id = space.id()
	spec.bounds = space.bounds()
	spec.rib_pitch = RIB_PITCH
	spec.panel_pitch = PANEL_PITCH
	_clearances(layout, space, spec)
	_structure(spec)
	_grate(layout, space, spec)
	return spec

static func _reserve(spec: ShipLayout.DressingSpec, id: StringName, bounds: AABB) -> void:
	spec.clearances.append(ShipLayout.DressingClearance.new(id, bounds))

static func _clearances(layout: ShipLayout, space: ShipLayout.Spec, spec: ShipLayout.DressingSpec) -> void:
	var b := spec.bounds
	_reserve(spec, &"WALK", AABB(Vector3(b.position.x, b.position.y + 0.001, b.position.z + 0.25), Vector3(b.size.x, 2.2, b.size.z - 0.5)))
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if space.id() not in door.spaces(): continue
		var aperture := door.aperture()
		_reserve(spec, StringName("%s/OPENING" % id), door.frame() * AABB(Vector3(-aperture.x / 2 - 0.24, 0, -0.25), Vector3(aperture.x + 0.48, aperture.y + 0.10, 0.70)))
		if door.animation() == ShipLayout.AnimationRecipe.HINGE:
			_reserve(spec, StringName("%s/SWING" % id), door.frame() * _sweep(door))
			# Room-side services and the sill need working clearance beyond the aperture.
			_reserve(spec, StringName("%s/SERVICES" % id), door.frame() * AABB(Vector3(-1.5, 0.001, -0.55), Vector3(3, 2.99, 1.30)))
		for face_id: StringName in door.face_ids():
			var face := layout.face(face_id)
			if face.source_space() != space.id(): continue
			var frame := door.frame() * face.label_frame()
			_reserve(spec, StringName("%s/LABEL" % face_id), frame * AABB(Vector3(-0.52, -0.28, 0), Vector3(1.04, 0.56, 1.0)))
			for service: ShipLayout.HatchServiceSpec in (door.hatch_services(door.spaces().find(space.id())) if door.has_wheel() else []):
				if service.kind == &"Lamp":
					var lamp := door.frame() * service.frame
					_reserve(spec, StringName("%s/LAMP" % face_id), lamp * AABB(Vector3(-0.24, -0.20, -0.35), Vector3(0.48, 0.40, 0.65)))
	if space is ShipLayout.ConnectorSpec:
		var well := layout.well(space.well_id())
		var landing := well.landing_bounds(space.deck_number())
		_reserve(spec, &"TRANSFER", AABB(Vector3(landing.position.x + 0.15, landing.position.y, well.climb_line().origin.z - 0.35), Vector3(landing.size.x - 0.30, 2.4, b.position.z - well.climb_line().origin.z + 0.7)))
		_reserve(spec, &"CLIMB", AABB(Vector3(well.climb_line().origin.x - 0.35, b.position.y, well.climb_line().origin.z - 0.35), Vector3(0.7, b.size.y, 0.7)))
	spec.clearances.append_array(space.service_reservations())
	spec.clearances.append_array(CeilingServices.build(layout, space).reservations())

static func _sweep(door: ShipLayout.DoorSpec) -> AABB:
	var result := AABB()
	for degree: int in range(131):
		var hinge := door.hinge_frame()
		hinge.basis = Basis(Vector3.UP, signf(door.swing_radians()) * deg_to_rad(degree))
		var bounds := hinge * ShipGeometry.hatch_leaf_bounds(door)
		result = bounds if degree == 0 else result.merge(bounds)
	return result.grow(0.001)

static func _batch(spec: ShipLayout.DressingSpec, family: StringName, shape: StringName, role: StringName, part: StringName) -> ShipLayout.DressingBatch:
	for batch: ShipLayout.DressingBatch in spec.batches:
		if batch.family == family: return batch
	var batch := ShipLayout.DressingBatch.new(family, shape, role, part)
	spec.batches.append(batch)
	return batch

static func _pose(center: Vector3, size: Vector3, basis: Basis = Basis.IDENTITY) -> Transform3D:
	return Transform3D(basis.scaled_local(size), center)

static func _clear(spec: ShipLayout.DressingSpec, pose: Transform3D) -> bool:
	var bounds := pose * UNIT
	for clearance: ShipLayout.DressingClearance in spec.clearances:
		if bounds.intersects(clearance.bounds): return false
	return true

static func _put(spec: ShipLayout.DressingSpec, family: StringName, size: Vector3, center: Vector3, role: StringName = &"wall", part: StringName = &"WALL", shape: StringName = &"box", basis: Basis = Basis.IDENTITY) -> void:
	var pose := _pose(center, size, basis)
	if _clear(spec, pose): _append(spec, family, shape, role, part, pose)

static func _append(spec: ShipLayout.DressingSpec, family: StringName, shape: StringName, role: StringName, part: StringName, pose: Transform3D) -> void:
	if String(family).begins_with("Grate") or family == &"SubfloorTray":
		var bounds := pose * UNIT
		for patch: AABB in spec.floor_patches:
			var start := Vector3(maxf(bounds.position.x, patch.position.x), bounds.position.y, maxf(bounds.position.z, patch.position.z))
			var end := Vector3(minf(bounds.end.x, patch.end.x), bounds.end.y, minf(bounds.end.z, patch.end.z))
			if end.x <= start.x or end.z <= start.z: continue
			# Keep the existing grid and transforms away from the ownership seam.
			var clipped := pose if start == bounds.position and end == bounds.end else _pose((start + end) / 2, end - start)
			var top := Vector3(0, spec.bounds.position.y - (spec.grate_depth if family == &"SubfloorTray" else 0.0), 0).y
			# Correct the f32 transform rounding at remote deck elevations.
			clipped.origin.y += top - (clipped * UNIT).end.y
			_batch(spec, family, shape, role, part).poses.append(clipped)
		return
	_batch(spec, family, shape, role, part).poses.append(pose)

## Subtract every reserved interval from a straight run, including its section.
static func _run(spec: ShipLayout.DressingSpec, family: StringName, a: Vector3, b: Vector3, width: Vector2, role: StringName, part: StringName, shape: StringName = &"box", extra: Array[AABB] = []) -> Array[PackedVector3Array]:
	var axis := (b - a).max_axis_index()
	assert(b[axis] > a[axis], "template spans increase along their axis")
	var dimensions := Vector3(width.x, width.x, width.y)
	if axis == 2: dimensions = Vector3(width.x, width.y, width.x)
	dimensions[axis] = b[axis] - a[axis]
	var envelope := AABB((a + b) / 2 - dimensions / 2, dimensions)
	var intervals: Array[Vector2] = [Vector2(a[axis], b[axis])]
	var exclusions: Array[AABB] = extra.duplicate()
	for clearance: ShipLayout.DressingClearance in spec.clearances: exclusions.append(clearance.bounds)
	for exclusion: AABB in exclusions:
		if not envelope.intersects(exclusion): continue
		var remaining: Array[Vector2] = []
		for interval: Vector2 in intervals:
			if exclusion.end[axis] <= interval.x or exclusion.position[axis] >= interval.y:
				remaining.append(interval)
				continue
			if exclusion.position[axis] > interval.x: remaining.append(Vector2(interval.x, exclusion.position[axis] - 0.002))
			if exclusion.end[axis] < interval.y: remaining.append(Vector2(exclusion.end[axis] + 0.002, interval.y))
		intervals = remaining
	var paths: Array[PackedVector3Array] = []
	for interval: Vector2 in intervals:
		if interval.y - interval.x < 0.025: continue
		var start := a
		var end := b
		start[axis] = interval.x
		end[axis] = interval.y
		var size := dimensions
		size[axis] = interval.y - interval.x
		var basis := Basis.IDENTITY
		if shape == &"cylinder":
			basis = Basis(Quaternion(Vector3.UP, (end - start).normalized()))
			size = Vector3(width.x, interval.y - interval.x, width.y)
		var pose := _pose((start + end) / 2, size, basis)
		_append(spec, family, shape, role, part, pose)
		paths.append(PackedVector3Array([start, end]))
	return paths

static func _structure(spec: ShipLayout.DressingSpec) -> void:
	var b := spec.bounds
	var center := b.get_center()
	var x := b.position.x + RIB_PITCH / 2
	while x < b.end.x:
		spec.rib_stations.append(x)
		for side: int in [-1, 1]:
			var z := center.z + side * (b.size.z / 2 - 0.06)
			var rib := _pose(Vector3(x, center.y, z), Vector3(0.11, b.size.y - 0.18, 0.12))
			if _clear(spec, rib):
				_put(spec, &"WallRibs", Vector3(0.11, b.size.y - 0.18, 0.12), Vector3(x, center.y, z))
				_put(spec, &"RibFeet", Vector3(0.23, 0.24, 0.17), Vector3(x, b.position.y + 0.12, z - side * 0.025))
				_put(spec, &"RibHeads", Vector3(0.20, 0.22, 0.18), Vector3(x, b.end.y - 0.11, z - side * 0.03))
		_run(spec, &"CeilingRibs", Vector3(x, b.end.y - 0.06, b.position.z + 0.04), Vector3(x, b.end.y - 0.06, b.end.z - 0.04), Vector2(0.11, 0.12), &"wall", &"CEILING")
		x += RIB_PITCH
	for side: int in [-1, 1]:
		var z := center.z + side * (b.size.z / 2 - 0.035)
		for height: float in [0.19, 0.38]:
			spec.kick_rail_paths.append_array(_run(spec, &"KickRails", Vector3(b.position.x + 0.05, b.position.y + height, z), Vector3(b.end.x - 0.05, b.position.y + height, z), Vector2(0.045, 0.07), &"pipe", &"WALL"))
		for row: int in range(1, int(b.size.y / PANEL_PITCH.y)):
			var y := b.position.y + row * PANEL_PITCH.y
			_run(spec, &"PlateLips", Vector3(b.position.x, y + 0.025, center.z + side * (b.size.z / 2 - 0.004)), Vector3(b.end.x, y + 0.025, center.z + side * (b.size.z / 2 - 0.004)), Vector2(0.008, 0.006), &"plate_edge", &"WALL")
			x = b.position.x + RIVET_PITCH / 2
			while x < b.end.x:
				_put(spec, &"WallRivets", Vector3(0.022, 0.009, 0.022), Vector3(x, y + 0.065, center.z + side * (b.size.z / 2 - 0.0045)), &"rivet", &"WALL", &"cylinder", Basis(Vector3.RIGHT, PI / 2))
				x += RIVET_PITCH

static func _grate(layout: ShipLayout, space: ShipLayout.Spec, spec: ShipLayout.DressingSpec) -> void:
	var solids := ShipGeometry.section_solids(layout, space) if space is ShipLayout.SectionSpec else ShipGeometry.connector_solids(layout, space)
	var floor_box := ShipGeometry.box_aabb(solids[0])
	spec.floor_patches = layout.visual_floor_patches(space)
	# Preserve the structural grid while clipping to uniquely owned visual patches.
	var b := AABB(Vector3(floor_box.min_corner().x, spec.bounds.position.y, floor_box.min_corner().z), Vector3(floor_box.half_extents().x * 2, spec.bounds.size.y, floor_box.half_extents().z * 2))
	spec.grate_footprint = AABB(Vector3(b.position.x, b.position.y - 0.09, b.position.z), Vector3(b.size.x, 0.09, b.size.z))
	var coamings: Array[AABB] = []
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if space.id() not in door.spaces() or not door.has_wheel(): continue
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_surround_solids(door):
			if "/STEP/" not in String(solid.id) and "/PIER/" not in String(solid.id): continue
			var box := ShipGeometry.box_aabb(solid)
			var bounds := AABB(box.min_corner(), box.max_corner() - box.min_corner())
			bounds.position.y = b.position.y - 0.10
			bounds.size.y = 0.20
			coamings.append(bounds)
	var x := b.position.x + 0.06
	while x < b.end.x:
		_run(spec, &"GrateCrossBars", Vector3(x, b.position.y - 0.027, b.position.z + 0.025), Vector3(x, b.position.y - 0.027, b.end.z - 0.025), Vector2(0.019, 0.054), &"floor", &"FLOOR", &"box", coamings)
		x += 0.12
	var z := b.position.z + 0.08
	while z < b.end.z:
		_run(spec, &"GrateLongBars", Vector3(b.position.x + 0.02, b.position.y - 0.011, z), Vector3(b.end.x - 0.02, b.position.y - 0.011, z), Vector2(0.022, 0.022), &"floor", &"FLOOR", &"box", coamings)
		z += 0.16
	x = b.position.x + 0.04
	while x < b.end.x:
		_run(spec, &"GrateCarriers", Vector3(x, b.position.y - 0.045, b.position.z + 0.015), Vector3(x, b.position.y - 0.045, b.end.z - 0.015), Vector2(0.055, 0.09), &"floor", &"FLOOR", &"box", coamings)
		x += PANEL_PITCH.x
	for side: int in [-1, 0, 1]:
		z = b.get_center().z + side * (b.size.z / 2 - 0.06)
		_run(spec, &"GrateSupports", Vector3(b.position.x, b.position.y - 0.0325, z), Vector3(b.end.x, b.position.y - 0.0325, z), Vector2(0.065, 0.055), &"floor", &"FLOOR", &"box", coamings)
	_put(spec, &"SubfloorTray", Vector3(b.size.x, 0.04, b.size.z), Vector3(b.get_center().x, b.position.y - spec.grate_depth - 0.02, b.get_center().z), &"subfloor", &"FLOOR")
