class_name CeilingServices
extends RefCounted
## Service positions use the owning space's coordinate frame, including the bay.

const DETECTOR_SIZE := Vector3(0.22, 0.22, 0.055)
const HEAD_SIZE := Vector3(0.16, 0.25, 0.14)
const FIXTURE_BOUNDS := AABB(Vector3(-0.55, -0.10, -0.11), Vector3(1.10, 0.10, 0.22))
const PIPE_RADIUS := 0.025

var bounds: AABB
var detectors: Array[Dictionary] = []
var detector_exclusions: Array[AABB] = []
var heads: Array[Transform3D] = []
var pipes: Array[Transform3D] = []
var tees: Array[Transform3D] = []
var clips: Array[Transform3D] = []
var ducts: Array[Transform3D] = []
var fixtures: Array[Transform3D] = []

static func build(layout: ShipLayout, space: ShipLayout.Spec) -> CeilingServices:
	var result := CeilingServices.new()
	result.bounds = space.local_bounds() if space is ShipLayout.BaySpec else space.bounds()
	var b := result.bounds
	var to_local := layout.world_to_bay() if space is ShipLayout.BaySpec else Transform3D.IDENTITY
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if space.id() not in door.spaces(): continue
		var a := door.aperture()
		result.detector_exclusions.append(to_local * door.frame() * AABB(Vector3(-a.x / 2 - 0.25, 0, -0.45), Vector3(a.x + 0.5, a.y + 0.20, 0.9)))
		if door.has_wheel():
			for service: ShipLayout.HatchServiceSpec in door.hatch_services(door.spaces().find(space.id())):
				var frame := to_local * door.frame() * service.frame
				if service.kind == &"Conduit":
					for index: int in range(service.route.size() - 1):
						var start := service.route[index].min(service.route[index + 1])
						var end := service.route[index].max(service.route[index + 1])
						result.detector_exclusions.append(frame * AABB(start, end - start).grow(service.radius))
				else:
					result.detector_exclusions.append(frame * AABB(Vector3(-0.28, -0.20, -0.2), Vector3(0.56, 0.40, 0.4)))
		for face_id: StringName in door.face_ids():
			var face := layout.face(face_id)
			if face.source_space() == space.id():
				result.detector_exclusions.append(to_local * door.frame() * face.label_frame() * AABB(Vector3(-0.52, -0.28, -0.1), Vector3(1.04, 0.56, 0.2)))
	for service: ShipLayout.ServiceReservation in space.service_reservations():
		if service.kind == ShipLayout.ServiceKind.SWITCH: result.detector_exclusions.append(service.bounds)
	if space is ShipLayout.PowerRoomSpec:
		for frame: Transform3D in space.console_stations():
			result.detector_exclusions.append(frame * AABB(Vector3(-0.65, 0, 0), Vector3(1.3, 1.9, 0.7)))
	if space is ShipLayout.ConnectorSpec:
		result.detector_exclusions.append(space.port_opening() * AABB(Vector3(-0.9, 0, -0.3), Vector3(1.8, 2.6, 0.6)))
	# Side-wall conduit is continuous at this height in the corridor template.
	if space is ShipLayout.SectionSpec or space is ShipLayout.ConnectorSpec:
		for side: int in [-1, 1]:
			result.detector_exclusions.append(AABB(Vector3(b.position.x, b.end.y - 0.658, b.get_center().z + side * (b.size.z / 2 - 0.018) - 0.018), Vector3(b.size.x, 0.036, 0.036)))
	var sight_blockers: Array[AABB] = []
	if space is ShipLayout.BaySpec:
		for pod: Pods.Pod in space.template().pods():
			var placement := ShipGeometry.pod_world_transform(pod.placement())
			for part: PodGeometry.PodSolid in PodGeometry.pod_solids(pod.state()):
				var frame := Transform3D(Basis(placement[0] * Quaternion(Vector3.RIGHT, part.roll_radians)), placement[0] * part.center + placement[1])
				sight_blockers.append(frame * AABB(-part.size / 2, part.size))
	for axis: int in [2, 0]:
		for side: int in [-1, 1]:
			if result.detectors.size() == 2: break
			var along := 0 if axis == 2 else 2
			var stations: Array[float] = []
			for station: int in range(floori((b.size[along] - 1.0) / 0.25) + 1):
				stations.append(b.position[along] + 0.5 + station * 0.25)
			stations.sort_custom(func(a: float, c: float) -> bool: return absf(a - b.get_center()[along]) < absf(c - b.get_center()[along]))
			for station: float in stations:
				var center := b.get_center()
				center[along] = station
				center.y = b.position.y + 2.2
				center[axis] += side * (b.size[axis] / 2 - DETECTOR_SIZE.z / 2)
				var angle := (PI if side > 0 else 0.0) if axis == 2 else (-side * PI / 2)
				var frame := Transform3D(Basis(Vector3.UP, angle), center)
				var box := frame * AABB(-DETECTOR_SIZE / 2, DETECTOR_SIZE)
				var clear := true
				for obstacle: AABB in result.detector_exclusions:
					if box.grow(0.15).intersects(obstacle): clear = false; break
				var eye := b.get_center()
				for offset: Vector2 in [Vector2.ZERO, Vector2(-0.07, -0.07), Vector2(0.07, -0.07), Vector2(-0.07, 0.07), Vector2(0.07, 0.07)]:
					var front := frame * Vector3(offset.x, offset.y, DETECTOR_SIZE.z / 2)
					for obstacle: AABB in sight_blockers:
						if obstacle.intersects_segment(eye, front) != null: clear = false; break
				if not clear: continue
				result.detectors.append({"wall": "%d/%d" % [axis, side], "frame": frame, "bounds": box})
				break
	assert(result.detectors.size() == 2, "room needs two clear detector walls: %s" % space.id())
	var count := ceili(b.size.x / 3.0)
	var pitch := b.size.x / count
	# Keep the supply below the rib heads and exposed on the room side of the wall.
	var pipe_y := b.end.y - 0.28
	# A lift's entrance lintel occupies its near wall; use its solid back wall.
	var into := -1.0 if space is ShipLayout.LiftSpec else 1.0
	var wall_z := b.end.z if space is ShipLayout.LiftSpec else b.position.z
	var pipe_z := wall_z + into * 0.10
	result.pipes.append(_pose(Vector3(b.get_center().x, pipe_y, pipe_z), Vector3(b.size.x, PIPE_RADIUS * 2, PIPE_RADIUS * 2)))
	for index: int in range(count):
		var x := b.position.x + (index + 0.5) * pitch
		var head := _pose(Vector3(x, pipe_y - HEAD_SIZE.y / 2 + PIPE_RADIUS, wall_z + into * HEAD_SIZE.z / 2), HEAD_SIZE)
		if into < 0: head.basis = Basis(Vector3.UP, PI) * head.basis
		result.heads.append(head)
		result.tees.append(_pose(Vector3(x, pipe_y, pipe_z), Vector3(0.10, 0.064, 0.064)))
		result.tees.append(Transform3D(Basis(Vector3.BACK, PI / 2).scaled_local(Vector3(0.08, 0.032, 0.032)), Vector3(x + into * 0.012, pipe_y - 0.04, pipe_z - into * 0.02)))
		result.clips.append(_pose(Vector3(x + 0.18, pipe_y, wall_z + into * 0.065), Vector3(0.035, 0.075, 0.13)))
	if space is ShipLayout.SectionSpec:
		var segments := ceili(b.size.x / 0.8)
		var length := b.size.x / segments
		for index: int in range(segments):
			result.ducts.append(_pose(Vector3(b.position.x + (index + 0.5) * length, b.end.y - 0.175, b.end.z - 0.45), Vector3(length, 0.35, 0.44)))
	var frames: Array[Transform3D] = []
	if space is ShipLayout.BaySpec or space is ShipLayout.SectionSpec: frames = space.regular_light_frames()
	if space is ShipLayout.PowerRoomSpec:
		for x: float in [b.position.x + b.size.x / 4, b.get_center().x, b.end.x - b.size.x / 4]:
			for z: float in [b.position.z + 2.0, b.end.z - 2.0]:
				frames.append(Transform3D(Basis(), Vector3(x, b.end.y, z)))
	for frame: Transform3D in frames:
		frame.origin.y = b.end.y
		result.fixtures.append(frame)
	return result

static func _pose(center: Vector3, size: Vector3) -> Transform3D:
	return Transform3D(Basis.from_scale(size), center)

func reservations() -> Array[ShipLayout.DressingClearance]:
	var result: Array[ShipLayout.DressingClearance] = []
	for row: Dictionary in detectors:
		result.append(ShipLayout.DressingClearance.new(&"FIRE_DETECTOR", row.bounds.grow(0.002)))
	for pose: Transform3D in heads + pipes + tees + clips + ducts:
		result.append(ShipLayout.DressingClearance.new(&"CEILING_SERVICE", (pose * ShipDressing.UNIT).grow(0.002)))
	return result
