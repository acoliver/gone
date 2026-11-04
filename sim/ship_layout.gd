class_name ShipLayout
extends RefCounted
## Authored ship placement data. Production adopts this frame in S03.

const BOW := Vector3(-1, 0, 0)
const STERN := Vector3(1, 0, 0)
const PORT := Vector3(0, 0, -1)
const STARBOARD := Vector3(0, 0, 1)
const DECK_PITCH: float = 5.5
const CLEAR_HEIGHT: float = 3.2
const WALL: float = 0.2
const CORRIDOR_WIDTH: float = 3.0
const DRESSING_RIB_PITCH: float = 2.0
const DRESSING_PANEL_PITCH := Vector2(1.5, 1.0)
const HATCH_WIDTH: float = 1.2
const HATCH_HEIGHT: float = 2.4
const DOOR_LABEL_HEIGHT: float = 1.82
const HATCH_LABEL_OUTSET: float = 0.04
const HATCH_LABEL_SIZE := Vector2(0.92, 0.46)
const BAY_ID: StringName = &"D14-BAY"
const POWER_ID: StringName = &"D14-POWER"
const BAY_DOOR_ID: StringName = &"D14-BAY-DOOR"
const BAY_HATCH_KEY_ID: StringName = &"D14-BAY-HATCH-KEY"
const EMERGENCY_FILL_CEILING_DROP: float = 0.77
const POWER_DOOR_ID: StringName = &"D14-POWER-DOOR"
const POWER_CENTER_X: float = 27.0
const POWER_NEAR_Z: float = -(Pods.AISLE_HALF_WIDTH + WALL)
const POWER_FAR_Z: float = POWER_NEAR_Z - Pods.ROOM_WIDTH
const POWER_MIN_X: float = POWER_CENTER_X - Pods.ROOM_LENGTH / 2.0
const POWER_MAX_X: float = POWER_CENTER_X + Pods.ROOM_LENGTH / 2.0
const POWER_GENERATOR_CENTER := Vector3(POWER_CENTER_X, 0, (POWER_NEAR_Z + POWER_FAR_Z) / 2.0)

enum Policy { CRANK, NEVER_OPENS, ROD_PRY, PRESS_SLIDE }
enum DoorKind { HATCH, SIDE, LIFT, BAY, POWER }
enum AnimationRecipe { HINGE, FIXED, SLIDE }
enum EmergencyLightRole { BAY_POOL, BAY_HATCH, ROOM_POOL }

class EmergencyFixtureSpec:
	extends RefCounted
	var id: StringName
	var role: EmergencyLightRole
	var frame: Transform3D
	func _init(p_id: StringName, p_role: EmergencyLightRole, p_frame: Transform3D) -> void:
		id = p_id
		role = p_role
		frame = p_frame

class Spec:
	extends RefCounted
	var _id: StringName
	var _deck: int
	func id() -> StringName:
		return _id
	func deck_number() -> int:
		return _deck
	func data() -> Dictionary:
		return {"id": _id, "deck": _deck}

class DressingBatch:
	extends RefCounted
	var family: StringName
	var shape: StringName
	var role: StringName
	var surface_part: StringName
	var poses: Array[Transform3D] = []
	func _init(p_family: StringName, p_shape: StringName, p_role: StringName, p_part: StringName) -> void:
		family = p_family
		shape = p_shape
		role = p_role
		surface_part = p_part

class DressingClearance:
	extends RefCounted
	var id: StringName
	var bounds: AABB
	func _init(p_id: StringName, p_bounds: AABB) -> void:
		id = p_id
		bounds = p_bounds

class DressingSpec:
	extends RefCounted
	var owner_id: StringName
	var bounds: AABB
	var rib_pitch: float = ShipLayout.DRESSING_RIB_PITCH
	var panel_pitch := ShipLayout.DRESSING_PANEL_PITCH
	var rib_stations: Array[float] = []
	var pipe_paths: Array[PackedVector3Array] = []
	var kick_rail_paths: Array[PackedVector3Array] = []
	var grate_footprint: AABB
	var grate_depth: float = 0.20
	var clearances: Array[DressingClearance] = []
	var batches: Array[DressingBatch] = []

class DeckSpec:
	extends Spec
	var _connector_ids: Array[StringName]
	var _section_ids: Array[StringName]
	func _init(number: int, p_connector_ids: Array[StringName], p_section_ids: Array[StringName]) -> void:
		_id = StringName("D%02d" % number)
		_deck = number
		_connector_ids = p_connector_ids.duplicate()
		_section_ids = p_section_ids.duplicate()
	func connector_ids() -> Array[StringName]:
		return _connector_ids.duplicate()
	func section_ids() -> Array[StringName]:
		return _section_ids.duplicate()
	func data() -> Dictionary:
		var result := super.data()
		result["connector_ids"] = _connector_ids.duplicate(true)
		result["section_ids"] = _section_ids.duplicate(true)
		return result
	func floor_y() -> float:
		return (14 - _deck) * ShipLayout.DECK_PITCH

class SectionSpec:
	extends Spec
	var _number: int
	var _bounds: AABB
	var _opening_ids: Array[StringName]
	var _side_door_ids: Array[StringName]
	var _circuit: StringName
	var _is_built: bool
	func _init(p_id: StringName, p_deck: int, p_number: int, p_bounds: AABB, p_opening_ids: Array[StringName], p_side_door_ids: Array[StringName], p_circuit: StringName, p_is_built: bool) -> void:
		_id = p_id
		_deck = p_deck
		_number = p_number
		_bounds = p_bounds
		_opening_ids = p_opening_ids.duplicate()
		_side_door_ids = p_side_door_ids.duplicate()
		_circuit = p_circuit
		_is_built = p_is_built
	func number() -> int:
		return _number
	func bounds() -> AABB:
		return _bounds
	func opening_ids() -> Array[StringName]:
		return _opening_ids.duplicate()
	func side_door_ids() -> Array[StringName]:
		return _side_door_ids.duplicate()
	func circuit() -> StringName:
		return _circuit
	func emergency_light_role() -> EmergencyLightRole:
		return ShipLayout.EmergencyLightRole.ROOM_POOL
	func emergency_fixture_frames() -> Array[Transform3D]:
		var frames: Array[Transform3D] = []
		var pitch := _bounds.size.x / 4
		for station: int in range(4):
			for side: int in [-1, 1]:
				frames.append(Transform3D(Basis(), Vector3(_bounds.position.x + (station + 0.5) * pitch, _bounds.position.y + 2.65, _bounds.get_center().z + side * (_bounds.size.z / 2 - 0.10))))
		return frames
	func regular_light_frames() -> Array[Transform3D]:
		var frames: Array[Transform3D] = []
		var pitch := _bounds.size.x / 4
		for station: int in range(4):
			frames.append(Transform3D(Basis(), Vector3(_bounds.position.x + (station + 0.5) * pitch, _bounds.end.y - 0.08, _bounds.get_center().z)))
		return frames
	func ceiling_trays() -> Array[ShipGeometry.SolidSpec]:
		var datum := Vector3(_bounds.position.x, _bounds.end.y - ShipGeometry.TRAY_CEILING_DROP, _bounds.get_center().z)
		return [
			ShipGeometry.SolidSpec.new(datum + Vector3(10.5, 0, 0.35), Vector3(9, ShipGeometry.TRAY_HEIGHT, ShipGeometry.TRAY_WIDTH), Quaternion(Vector3.RIGHT, 0.05)),
			ShipGeometry.SolidSpec.new(datum + Vector3(17, -0.04, -0.55), Vector3(3.2, ShipGeometry.TRAY_HEIGHT, ShipGeometry.TRAY_WIDTH), Quaternion(Vector3.UP, PI / 2) * Quaternion(Vector3.RIGHT, -0.06)),
		]
	func ceiling_loops() -> Array[ShipGeometry.WireLoop]:
		var datum := Vector3(_bounds.position.x, _bounds.position.y, _bounds.get_center().z)
		return [
			ShipGeometry.WireLoop.new(datum + Vector3(7.6, 2.72, 0.42), Quaternion(Vector3.RIGHT, PI / 2) * Quaternion(Vector3.UP, 0.8)),
			ShipGeometry.WireLoop.new(datum + Vector3(15.4, 2.66, -0.48), Quaternion(Vector3.RIGHT, PI / 2) * Quaternion(Vector3.UP, 2.1)),
		]
	func ceiling_damage_bounds() -> Array[AABB]:
		var boxes: Array[AABB] = []
		for solid: ShipGeometry.SolidSpec in ceiling_trays():
			var box := ShipGeometry.box_aabb(solid)
			boxes.append(AABB(box.min_corner(), box.max_corner() - box.min_corner()).grow(0.02))
		for loop: ShipGeometry.WireLoop in ceiling_loops():
			var size := Vector3.ONE * ShipGeometry.WIRE_OUTER_RADIUS * 2
			boxes.append(AABB(loop.center - size / 2, size).grow(0.02))
		return boxes
	func emergency_fill_positions() -> Array[Vector3]:
		var positions: Array[Vector3] = []
		for index: int in range(7):
			positions.append(Vector3(_bounds.position.x + 1.5 + index * 3.0, _bounds.end.y - 0.85, _bounds.get_center().z))
		return positions
	func emergency_end_fill_position() -> Vector3:
		return Vector3(_bounds.end.x - 0.9, _bounds.position.y + 1.7, _bounds.get_center().z)

	func is_built() -> bool:
		return _is_built
	func data() -> Dictionary:
		var result := super.data()
		result["number"] = _number
		result["bounds"] = _bounds
		result["opening_ids"] = _opening_ids.duplicate(true)
		result["side_door_ids"] = _side_door_ids.duplicate(true)
		result["circuit"] = _circuit
		result["is_built"] = _is_built
		return result

class ConnectorSpec:
	extends Spec
	var _pitch_index: int
	var _bounds: AABB
	var _hatch_ids: Array[StringName]
	var _well_id: StringName
	var _lift_id: StringName
	var _port_opening: Transform3D
	var _shared_wall_owner: StringName
	var _is_built: bool
	func _init(p_id: StringName, p_deck: int, p_pitch_index: int, p_bounds: AABB, p_hatch_ids: Array[StringName], p_well_id: StringName, p_lift_id: StringName, p_port_opening: Transform3D, p_shared_wall_owner: StringName, p_is_built: bool) -> void:
		_id = p_id
		_deck = p_deck
		_pitch_index = p_pitch_index
		_bounds = p_bounds
		_hatch_ids = p_hatch_ids.duplicate()
		_well_id = p_well_id
		_lift_id = p_lift_id
		_port_opening = p_port_opening
		_shared_wall_owner = p_shared_wall_owner
		_is_built = p_is_built
	func pitch_index() -> int:
		return _pitch_index
	func bounds() -> AABB:
		return _bounds
	func hatch_ids() -> Array[StringName]:
		return _hatch_ids.duplicate()
	func well_id() -> StringName:
		return _well_id
	func lift_id() -> StringName:
		return _lift_id
	func port_opening() -> Transform3D:
		return _port_opening
	func landing_key_position() -> Vector3:
		# The low landing key reaches the shaft rails and the connector centre floor.
		return Vector3(_bounds.get_center().x + (0.85 if _pitch_index == 1 else 0.0), _bounds.position.y + 0.50, -2.50)
	func shared_wall_owner() -> StringName:
		return _shared_wall_owner
	func is_built() -> bool:
		return _is_built
	func data() -> Dictionary:
		var result := super.data()
		result["pitch_index"] = _pitch_index
		result["bounds"] = _bounds
		result["hatch_ids"] = _hatch_ids.duplicate(true)
		result["well_id"] = _well_id
		result["lift_id"] = _lift_id
		result["port_opening"] = _port_opening
		result["shared_wall_owner"] = _shared_wall_owner
		result["is_built"] = _is_built
		return result

class HatchServiceSpec:
	extends RefCounted
	var kind: StringName
	var frame: Transform3D
	var route := PackedVector3Array()
	var radius: float
	var stand_off: float = 0.0
	func _init(p_kind: StringName, p_frame: Transform3D, p_route := PackedVector3Array(), p_radius: float = 0.0) -> void:
		kind = p_kind
		frame = p_frame
		route = p_route
		radius = p_radius

class DoorSpec:
	extends Spec
	var _kind: int
	var _policy: int
	var _frame: Transform3D
	var _aperture: Vector2
	var _spaces: Array[StringName]
	var _face_ids: Array[StringName]
	var _owner_id: StringName
	var _animation: int
	var _has_wheel: bool
	func _init(p_id: StringName, p_deck: int, p_kind: int, p_policy: int, p_frame: Transform3D, p_aperture: Vector2, p_spaces: Array[StringName], p_face_ids: Array[StringName], p_owner_id: StringName, p_animation: int, p_has_wheel: bool) -> void:
		_id = p_id
		_deck = p_deck
		_kind = p_kind
		_policy = p_policy
		_frame = p_frame
		_aperture = p_aperture
		_spaces = p_spaces.duplicate()
		_face_ids = p_face_ids.duplicate()
		_owner_id = p_owner_id
		_animation = p_animation
		_has_wheel = p_has_wheel
	func kind() -> int:
		return _kind
	func policy() -> int:
		return _policy
	func frame() -> Transform3D:
		return _frame
	func aperture() -> Vector2:
		return _aperture
	func spaces() -> Array[StringName]:
		return _spaces.duplicate()
	func face_ids() -> Array[StringName]:
		return _face_ids.duplicate()
	func owner_id() -> StringName:
		return _owner_id
	func animation() -> int:
		return _animation
	func has_wheel() -> bool:
		return _has_wheel
	func data() -> Dictionary:
		var result := super.data()
		result["kind"] = _kind
		result["policy"] = _policy
		result["frame"] = _frame
		result["aperture"] = _aperture
		result["spaces"] = _spaces.duplicate(true)
		result["face_ids"] = _face_ids.duplicate(true)
		result["owner_id"] = _owner_id
		result["animation"] = _animation
		result["has_wheel"] = _has_wheel
		return result
	func leaf_aperture() -> Vector2:
		return _aperture - Vector2(0.12, 0)
	func hinge_frame() -> Transform3D:
		assert(_animation == ShipLayout.AnimationRecipe.HINGE, "hinge recipe required")
		# The complete double-sided hardware must clear the bulkhead before rotating.
		var into := 1.0 if swing_radians() < 0 else -1.0
		return Transform3D(Basis(), Vector3(-_aperture.x / 2.0 + 0.03, 0, ShipLayout.WALL / 2.0 + into * 0.30))
	func swing_radians(run_seed: int = 0) -> float:
		assert(_animation == ShipLayout.AnimationRecipe.HINGE, "hinge recipe required")
		var value := HatchResistance.hash_bytes("hatch-rest-v1|%d|%s" % [run_seed, _id])
		var degrees := 100.0 + 30.0 * float(value) / 4294967295.0
		return deg_to_rad(degrees) * (-1.0 if String(_id).ends_with("-FORE") or _kind == ShipLayout.DoorKind.BAY else 1.0)
	func hatch_services(side: int) -> Array[HatchServiceSpec]:
		assert(_animation == ShipLayout.AnimationRecipe.HINGE and side in [0, 1], "hinged service face")
		var face := Transform3D.IDENTITY if side == 0 else Transform3D(Basis(Vector3.LEFT, Vector3.UP, Vector3.FORWARD), Vector3(0, 0, ShipLayout.WALL))
		# Connector cages reach the floor/lift while remaining above the leaf sweep.
		var connector_face := _spaces[side] in [ShipLayout.connector_id(_deck, 0), ShipLayout.connector_id(_deck, 1)]
		var lamp_x := 0.80 if connector_face else (0.0 if _kind == ShipLayout.DoorKind.BAY and side == 1 else _aperture.x / 2 + 0.39)
		var lamp_stand_off := 0.30 if connector_face else 0.0
		var services: Array[HatchServiceSpec] = [
			HatchServiceSpec.new(&"Control", face * Transform3D(Basis(), Vector3(-_aperture.x / 2 - 0.48, 1.37, -0.10))),
			HatchServiceSpec.new(&"Lamp", face * Transform3D(Basis(), Vector3(lamp_x, _aperture.y + 0.16, -0.11 - lamp_stand_off))),
		]
		services[1].stand_off = lamp_stand_off
		for x: float in [-1.04, -1.15]:
			var top := 2.72 if x > -1.1 else 2.82
			services.append(HatchServiceSpec.new(&"Conduit", face, PackedVector3Array([Vector3(x, 1.63, -0.08), Vector3(x, top, -0.08), Vector3(1.12, top, -0.08)]), 0.018))
		services.append(HatchServiceSpec.new(&"Conduit", face, PackedVector3Array([Vector3(-1.08, 1.11, -0.08), Vector3(-1.08, 0.29, -0.08), Vector3(-1.48, 0.29, -0.08)]), 0.021))
		services.append(HatchServiceSpec.new(&"Conduit", face, PackedVector3Array([Vector3(1.12, 0.20, -0.065), Vector3(1.12, 2.82, -0.065)]), 0.032))
		if side == 0 and hinge_frame().origin.z < ShipLayout.WALL / 2:
			# The swing-side control must sit opposite the parked leaf, not behind it.
			for service: HatchServiceSpec in services:
				service.frame.origin.x *= -1
				for index: int in range(service.route.size()): service.route[index].x *= -1
		return services
	func closed_blocker() -> AABB:
		return AABB(Vector3(-_aperture.x / 2.0, 0, 0), Vector3(_aperture.x, _aperture.y, ShipLayout.WALL))

class FaceSpec:
	extends Spec
	var _door_id: StringName
	var _source_space: StringName
	var _destination_section: int
	var _surface_frame: Transform3D
	var _interaction_frame: Transform3D
	func _init(p_id: StringName, p_deck: int, p_door_id: StringName, p_source_space: StringName, p_destination_section: int, p_surface_frame: Transform3D, p_interaction_frame: Transform3D) -> void:
		_id = p_id
		_deck = p_deck
		_door_id = p_door_id
		_source_space = p_source_space
		_destination_section = p_destination_section
		_surface_frame = p_surface_frame
		_interaction_frame = p_interaction_frame
	func door_id() -> StringName:
		return _door_id
	func source_space() -> StringName:
		return _source_space
	func destination_section() -> int:
		return _destination_section
	func surface_frame() -> Transform3D:
		return _surface_frame
	func interaction_frame() -> Transform3D:
		return _interaction_frame
	func label_frame() -> Transform3D:
		var frame := _surface_frame
		frame.origin += Vector3.UP * ShipLayout.DOOR_LABEL_HEIGHT + frame.basis.z * ShipLayout.HATCH_LABEL_OUTSET
		return frame
	func label_size() -> Vector2:
		return ShipLayout.HATCH_LABEL_SIZE
	func leaf_label_frame(door: DoorSpec) -> Transform3D:
		var frame := _surface_frame
		frame.origin = Vector3(door.leaf_aperture().x / 2, ShipLayout.DOOR_LABEL_HEIGHT, frame.basis.z.z * (ShipLayout.WALL / 2 + ShipLayout.HATCH_LABEL_OUTSET))
		return frame
	func data() -> Dictionary:
		var result := super.data()
		result["door_id"] = _door_id
		result["source_space"] = _source_space
		result["destination_section"] = _destination_section
		result["surface_frame"] = _surface_frame
		result["interaction_frame"] = _interaction_frame
		return result

class LiftSpec:
	extends Spec
	var _connector_id: StringName
	var _door_id: StringName
	var _bounds: AABB
	var _label_anchor: Transform3D
	func _init(p_id: StringName, p_deck: int, p_connector_id: StringName, p_door_id: StringName, p_bounds: AABB, p_label_anchor: Transform3D) -> void:
		_id = p_id
		_deck = p_deck
		_connector_id = p_connector_id
		_door_id = p_door_id
		_bounds = p_bounds
		_label_anchor = p_label_anchor
	func connector_id() -> StringName:
		return _connector_id
	func door_id() -> StringName:
		return _door_id
	func bounds() -> AABB:
		return _bounds
	func label_anchor() -> Transform3D:
		return _label_anchor
	func label_size() -> Vector2:
		return Vector2(0.92, 0.23)
	func data() -> Dictionary:
		var result := super.data()
		result["connector_id"] = _connector_id
		result["door_id"] = _door_id
		result["bounds"] = _bounds
		result["label_anchor"] = _label_anchor
		return result

class LadderWellSpec:
	extends Spec
	var _bounds: AABB
	var _climb_line: Transform3D
	var _landings: Array[Transform3D]
	var _transfer_paths: Array[PackedVector3Array]
	func _init(p_id: StringName, p_bounds: AABB, p_climb_line: Transform3D, p_landings: Array[Transform3D], p_transfer_paths: Array[PackedVector3Array]) -> void:
		_id = p_id
		_deck = 0
		_bounds = p_bounds
		_climb_line = p_climb_line
		_landings = p_landings.duplicate()
		_transfer_paths = p_transfer_paths.duplicate(true)
	func bounds() -> AABB:
		return _bounds
	func climb_line() -> Transform3D:
		return _climb_line
	func landings() -> Array[Transform3D]:
		return _landings.duplicate()
	func transfer_paths() -> Array[PackedVector3Array]:
		return _transfer_paths.duplicate(true)
	func data() -> Dictionary:
		var result := super.data()
		result["bounds"] = _bounds
		result["climb_line"] = _climb_line
		result["landings"] = _landings.duplicate(true)
		result["transfer_paths"] = _transfer_paths.duplicate(true)
		return result
	func landing(deck: int) -> Transform3D:
		assert(deck >= 1 and deck <= 30, "landing deck exists")
		return _landings[deck - 1]
	func transfer_path(deck: int) -> PackedVector3Array:
		assert(deck >= 1 and deck <= 30, "transfer deck exists")
		return _transfer_paths[deck - 1].duplicate()
	func doorway_size() -> Vector2:
		return Vector2(1.3, 2.4)
	func landing_bounds(deck: int) -> AABB:
		var origin := landing(deck).origin
		return AABB(Vector3(_bounds.position.x, origin.y, -3.3), Vector3(_bounds.size.x, ShipLayout.CLEAR_HEIGHT, 1.8))
	func top_deck() -> int:
		return 1
	func bottom_deck() -> int:
		return 30

class BaySpec:
	extends Spec
	var _section_id: StringName
	var _frame: Transform3D
	func _init(p_id: StringName, p_deck: int, p_section_id: StringName, p_frame: Transform3D) -> void:
		_id = p_id
		_deck = p_deck
		_section_id = p_section_id
		_frame = p_frame
	func section_id() -> StringName:
		return _section_id
	func frame() -> Transform3D:
		return _frame
	func data() -> Dictionary:
		var result := super.data()
		result["section_id"] = _section_id
		result["frame"] = _frame
		result["regular_light_frames"] = regular_light_frames()
		result["ceiling_vent_frames"] = ceiling_vent_frames()
		return result
	func regular_light_frames() -> Array[Transform3D]:
		var frames: Array[Transform3D] = []
		for x: float in [-4.0, 0.0, 4.0]:
			for z: float in [-1.6, 1.6]:
				frames.append(Transform3D(Basis(), Vector3(x, Pods.ROOM_CEILING_HEIGHT - 0.08, z)))
		return frames
	func emergency_fixtures(registry: Pods.PodRegistry) -> Array[EmergencyFixtureSpec]:
		var fixtures: Array[EmergencyFixtureSpec] = []
		for pod: Pods.Pod in registry.pods():
			var placement := pod.placement()
			var side := signf(placement.center.y)
			var frame := Transform3D(Basis(), Vector3(placement.center.x, 2.65, side * (Pods.ROOM_WIDTH / 2.0 - 0.10)))
			fixtures.append(EmergencyFixtureSpec.new(StringName("D14-BAY-POD-%d-KEY" % pod.id().index()), ShipLayout.EmergencyLightRole.BAY_POOL, frame))
		var lintel: ShipGeometry.SolidSpec = ShipGeometry.hatch_solids()[2]
		fixtures.append(EmergencyFixtureSpec.new(ShipLayout.BAY_HATCH_KEY_ID, ShipLayout.EmergencyLightRole.BAY_HATCH, Transform3D(Basis(Vector3.UP, PI / 2.0), lintel.center + Vector3(-0.10, 0.22, 0.0))))
		return fixtures
	func emergency_fill_positions() -> Array[Vector3]:
		var positions: Array[Vector3] = []
		for frame: Transform3D in regular_light_frames():
			positions.append(frame.origin - Vector3.UP * ShipLayout.EMERGENCY_FILL_CEILING_DROP)
		return positions
	func ceiling_vent_frames() -> Array[Transform3D]:
		return [Transform3D(Basis(), Vector3(-3, 3.05, 0)), Transform3D(Basis(), Vector3(3, 3.05, 0))]
	func local_bounds() -> AABB:
		return AABB(Vector3(-Pods.ROOM_LENGTH / 2, 0, -Pods.ROOM_WIDTH / 2), Vector3(Pods.ROOM_LENGTH, Pods.ROOM_CEILING_HEIGHT, Pods.ROOM_WIDTH))
	func rod_local() -> Transform3D:
		return Transform3D(Basis(), Vector3(-0.6, 0, -1.55))
	func template() -> Pods.PodRegistry:
		return Pods.PodRegistry.frozen()

class PowerRoomSpec:
	extends Spec
	var _section_id: StringName
	var _bounds: AABB
	var _door_id: StringName
	var _console_stations: Array[Transform3D]
	var _generator_anchor: Transform3D
	func _init(p_id: StringName, p_deck: int, p_section_id: StringName, p_bounds: AABB, p_door_id: StringName, p_console_stations: Array[Transform3D], p_generator_anchor: Transform3D) -> void:
		_id = p_id
		_deck = p_deck
		_section_id = p_section_id
		_bounds = p_bounds
		_door_id = p_door_id
		_console_stations = p_console_stations.duplicate()
		_generator_anchor = p_generator_anchor
	func section_id() -> StringName:
		return _section_id
	func bounds() -> AABB:
		return _bounds
	func door_id() -> StringName:
		return _door_id
	func console_stations() -> Array[Transform3D]:
		return _console_stations.duplicate()
	func generator_anchor() -> Transform3D:
		return _generator_anchor
	func emergency_light_role() -> EmergencyLightRole:
		return ShipLayout.EmergencyLightRole.ROOM_POOL
	func emergency_fill_positions() -> Array[Vector3]:
		var positions: Array[Vector3] = []
		var mount_y := Pods.ROOM_CEILING_HEIGHT - 0.08
		for x: float in [24.0, ShipLayout.POWER_CENTER_X, 30.0]:
			for z: float in [-3.7, -7.7]:
				positions.append(Vector3(x, mount_y - ShipLayout.EMERGENCY_FILL_CEILING_DROP, z))
		return positions
	func data() -> Dictionary:
		var result := super.data()
		result["section_id"] = _section_id
		result["bounds"] = _bounds
		result["door_id"] = _door_id
		result["console_stations"] = _console_stations.duplicate(true)
		result["generator_anchor"] = _generator_anchor
		return result

class LayoutError:
	extends RefCounted
	enum Kind { DUPLICATE_ID, INVALID_DECK, INVALID_DIMENSIONS, BAD_REFERENCE, BAD_FACES, OVERLAPPING_APERTURES, ROOM_COUNT, OPENABILITY }
	var kind: int
	var id: StringName
	func _init(p_kind: int, p_id: StringName) -> void:
		kind = p_kind
		id = p_id

class Result:
	extends RefCounted
	var layout: ShipLayout
	var error: LayoutError
	func is_ok() -> bool:
		return error == null

var _records: Dictionary = {}
var _anchors: Dictionary = {}

static func section_id(deck: int, number: int) -> StringName:
	return StringName("D%02d-S-%03d" % [deck, number])

static func connector_id(deck: int, n: int) -> StringName:
	return StringName("D%02d-C-%s" % [deck, "M%03d" % -n if n < 0 else "%03d" % n])

static func authored() -> Result:
	return try_new(_authored_records())

static func try_new(specs: Array[Spec]) -> Result:
	var layout := ShipLayout.new()
	for spec: Spec in specs:
		if layout._records.has(spec.id()):
			return _failure(LayoutError.Kind.DUPLICATE_ID, spec.id())
		if not spec is LadderWellSpec and (spec.deck_number() < 1 or spec.deck_number() > 30):
			return _failure(LayoutError.Kind.INVALID_DECK, spec.id())
		var values := spec.data()
		for value: Variant in values.values():
			if value is AABB and (not value.position.is_finite() or not value.size.is_finite() or value.size.x <= 0 or value.size.y <= 0 or value.size.z <= 0):
				return _failure(LayoutError.Kind.INVALID_DIMENSIONS, spec.id())
			if value is Transform3D and (not value.origin.is_finite() or not value.basis.is_finite() or not value.basis.is_orthonormal()):
				return _failure(LayoutError.Kind.INVALID_DIMENSIONS, spec.id())
		if spec is DoorSpec and (not spec.aperture().is_finite() or spec.aperture().x <= 0 or spec.aperture().y <= 0):
			return _failure(LayoutError.Kind.INVALID_DIMENSIONS, spec.id())
		layout._records[spec.id()] = spec
	for spec: Spec in specs:
		for reference: StringName in _references(spec):
			if not layout._records.has(reference) or not layout._reference_matches(spec, reference):
				return _failure(LayoutError.Kind.BAD_REFERENCE, spec.id())
		if not spec is LadderWellSpec and not layout._records.get(StringName("D%02d" % spec.deck_number())) is DeckSpec:
			return _failure(LayoutError.Kind.BAD_REFERENCE, spec.id())
		if spec is DoorSpec:
			if spec.face_ids().size() != 2 or spec.spaces().size() != 2 or spec.spaces()[0] == spec.spaces()[1]:
				return _failure(LayoutError.Kind.BAD_FACES, spec.id())
			for index: int in range(2):
				var face_spec: Spec = layout._records[spec.face_ids()[index]]
				if not face_spec is FaceSpec or face_spec.door_id() != spec.id() or face_spec.source_space() != spec.spaces()[index] or face_spec.deck_number() != spec.deck_number():
					return _failure(LayoutError.Kind.BAD_FACES, spec.id())
				if not layout.has_space(spec.spaces()[index]):
					return _failure(LayoutError.Kind.BAD_REFERENCE, spec.id())
		if spec is FaceSpec:
			var parent: Spec = layout._records[spec.door_id()]
			if not parent is DoorSpec or not spec.id() in parent.face_ids():
				return _failure(LayoutError.Kind.BAD_FACES, spec.id())
	var door_ids := layout.door_ids()
	for index: int in range(door_ids.size()):
		var first := layout.door(door_ids[index])
		for next: int in range(index + 1, door_ids.size()):
			var second := layout.door(door_ids[next])
			if first.deck_number() == second.deck_number() and _apertures_overlap(first, second):
				return _failure(LayoutError.Kind.OVERLAPPING_APERTURES, second.id())
	if layout._ids_of(BaySpec).size() != 1 or layout._ids_of(PowerRoomSpec).size() != 1:
		return _failure(LayoutError.Kind.ROOM_COUNT, &"rooms")
	var expected_cranks: Array[StringName] = [&"D14-C-000-H-FORE", &"D14-C-000-H-AFT", &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]
	for id: StringName in door_ids:
		var door_spec := layout.door(id)
		var expected := Policy.NEVER_OPENS
		if id in expected_cranks:
			expected = Policy.CRANK
		elif id == BAY_DOOR_ID:
			expected = Policy.ROD_PRY
		elif id == POWER_DOOR_ID:
			expected = Policy.PRESS_SLIDE
		if door_spec.policy() != expected:
			return _failure(LayoutError.Kind.OPENABILITY, id)
	for id: StringName in expected_cranks + [BAY_DOOR_ID, POWER_DOOR_ID]:
		if not id in door_ids:
			return _failure(LayoutError.Kind.OPENABILITY, id)
	layout._anchors[&"D14-HALL-SWITCH"] = Transform3D(Basis(Vector3.UP, PI), Vector3(16.2, 1.25, 1.45))
	layout._anchors[&"D14-BAY-ROD"] = layout.bay_to_world() * layout.bay().rod_local()
	layout._anchors[&"D14-POWER-CONSOLE"] = Transform3D(Basis(), Vector3(22.05, 0, -7.5))
	var result := Result.new()
	result.layout = layout
	return result

static func _failure(kind: int, id: StringName) -> Result:
	var result := Result.new()
	result.error = LayoutError.new(kind, id)
	return result

func _reference_matches(spec: Spec, id: StringName) -> bool:
	var target: Spec = _records[id]
	if not target is LadderWellSpec and target.deck_number() != spec.deck_number():
		return false
	if spec is DeckSpec:
		return (id in spec.connector_ids() and target is ConnectorSpec and target.is_built()) or (id in spec.section_ids() and target is SectionSpec and target.is_built())
	if spec is SectionSpec:
		return target is DoorSpec
	if spec is ConnectorSpec:
		return (id in spec.hatch_ids() and target is DoorSpec) or (id == spec.well_id() and target is LadderWellSpec) or (id == spec.lift_id() and target is LiftSpec) or (id == spec.shared_wall_owner() and has_space(id))
	if spec is DoorSpec:
		return (id in spec.face_ids() and target is FaceSpec) or ((id in spec.spaces() or id == spec.owner_id()) and has_space(id))
	if spec is FaceSpec:
		return (id == spec.door_id() and target is DoorSpec) or (id == spec.source_space() and has_space(id))
	if spec is LiftSpec:
		return (id == spec.connector_id() and target is ConnectorSpec) or (id == spec.door_id() and target is DoorSpec)
	if spec is BaySpec:
		return target is SectionSpec
	if spec is PowerRoomSpec:
		return (id == spec.section_id() and target is SectionSpec) or (id == spec.door_id() and target is DoorSpec)
	return true

static func _references(spec: Spec) -> Array[StringName]:
	var refs: Array[StringName] = []
	if spec is DeckSpec:
		refs.append_array(spec.connector_ids())
		refs.append_array(spec.section_ids())
	elif spec is SectionSpec:
		refs.append_array(spec.opening_ids())
		refs.append_array(spec.side_door_ids())
	elif spec is ConnectorSpec and spec.is_built():
		refs.append_array(spec.hatch_ids())
		refs.append_array([spec.well_id(), spec.lift_id(), spec.shared_wall_owner()])
	elif spec is DoorSpec:
		refs.append_array(spec.spaces())
		refs.append_array(spec.face_ids())
		refs.append(spec.owner_id())
	elif spec is FaceSpec:
		refs.append_array([spec.door_id(), spec.source_space()])
	elif spec is LiftSpec:
		refs.append_array([spec.connector_id(), spec.door_id()])
	elif spec is BaySpec:
		refs.append(spec.section_id())
	elif spec is PowerRoomSpec:
		refs.append_array([spec.section_id(), spec.door_id()])
	return refs

static func _apertures_overlap(a: DoorSpec, b: DoorSpec) -> bool:
	if absf(a.frame().basis.z.dot(b.frame().basis.z)) < 0.999:
		return false
	var offset := a.frame().affine_inverse() * b.frame().origin
	return absf(offset.z) < WALL and absf(offset.x) < (a.aperture().x + b.aperture().x) / 2.0 and offset.y < a.aperture().y and offset.y + b.aperture().y > 0

func _lookup(id: StringName, type: GDScript) -> Spec:
	assert(_records.has(id) and is_instance_of(_records[id], type), "layout id resolves to the required spec: %s" % id)
	return _records[id]

func deck(number: int) -> DeckSpec:
	return _lookup(StringName("D%02d" % number), DeckSpec)

func section(id: StringName) -> SectionSpec:
	return _lookup(id, SectionSpec)

func connector(id: StringName) -> ConnectorSpec:
	return _lookup(id, ConnectorSpec)

func door(id: StringName) -> DoorSpec:
	return _lookup(id, DoorSpec)

func face(id: StringName) -> FaceSpec:
	return _lookup(id, FaceSpec)

func lift(id: StringName) -> LiftSpec:
	return _lookup(id, LiftSpec)

func well(id: StringName) -> LadderWellSpec:
	return _lookup(id, LadderWellSpec)

func well_ids() -> Array[StringName]:
	return _ids_of(LadderWellSpec)

func ladder_doorway_frame(well_id: StringName, deck_number: int) -> Transform3D:
	for id: StringName in deck(deck_number).connector_ids():
		var spec := connector(id)
		if spec.well_id() == well_id:
			return spec.port_opening()
	assert(false, "ladder doorway belongs to a deck connector: %s" % well_id)
	return Transform3D.IDENTITY

func bay() -> BaySpec:
	return _lookup(BAY_ID, BaySpec)

func power_room() -> PowerRoomSpec:
	return _lookup(POWER_ID, PowerRoomSpec)

func dressing(space_id: StringName) -> DressingSpec:
	var space: Spec = _records[space_id]
	assert((space is SectionSpec or space is ConnectorSpec) and space.is_built(), "dressing requires a built corridor space: %s" % space_id)
	return ShipDressing.build(self, space)

func anchor(id: StringName) -> Transform3D:
	assert(_anchors.has(id), "layout anchor exists: %s" % id)
	return _anchors[id]

func bay_to_world() -> Transform3D:
	return bay().frame()

func world_to_bay() -> Transform3D:
	return bay_to_world().affine_inverse()

func floor_y(deck_number: int) -> float:
	return deck(deck_number).floor_y()

func has_space(id: StringName) -> bool:
	return _records.has(id) and (_records[id] is SectionSpec or _records[id] is ConnectorSpec or _records[id] is BaySpec or _records[id] is PowerRoomSpec or _records[id] is LiftSpec)

func _ids_of(type: GDScript) -> Array[StringName]:
	var ids: Array[StringName] = []
	for id: StringName in _records:
		if is_instance_of(_records[id], type):
			ids.append(id)
	ids.sort_custom(func(a: StringName, b: StringName) -> bool: return String(a) < String(b))
	return ids

func deck_ids() -> Array[StringName]:
	return _ids_of(DeckSpec)

func door_ids() -> Array[StringName]:
	return _ids_of(DoorSpec)

func connector_ids() -> Array[StringName]:
	var ids: Array[StringName] = []
	for id: StringName in _ids_of(ConnectorSpec):
		if connector(id).is_built():
			ids.append(id)
	return ids

func records() -> Array[Spec]:
	var specs: Array[Spec] = []
	var ids := _records.keys()
	ids.sort_custom(func(a: StringName, b: StringName) -> bool: return String(a) < String(b))
	for id: StringName in ids:
		specs.append(_records[id])
	return specs

func serialize() -> String:
	var values: Array[Dictionary] = []
	for spec: Spec in records():
		values.append(spec.data())
	return var_to_str(values)

static func _frame_x(position: Vector3) -> Transform3D:
	return Transform3D(Basis(Vector3(0, 0, -1), Vector3.UP, Vector3.RIGHT), position)

static func _add_door(specs: Array[Spec], id: StringName, deck: int, kind: int, policy: int, frame: Transform3D, aperture: Vector2, spaces: Array[StringName], owner: StringName, destinations: Vector2i, suffixes: Array[StringName]) -> void:
	var faces: Array[StringName] = [StringName("%s/%s" % [id, suffixes[0]]), StringName("%s/%s" % [id, suffixes[1]])]
	var animation := AnimationRecipe.HINGE if kind == DoorKind.HATCH else AnimationRecipe.FIXED
	if kind == DoorKind.BAY:
		animation = AnimationRecipe.HINGE
	elif kind == DoorKind.POWER:
		animation = AnimationRecipe.SLIDE
	specs.append(DoorSpec.new(id, deck, kind, policy, frame, aperture, spaces, faces, owner, animation, kind in [DoorKind.HATCH, DoorKind.BAY]))
	for index: int in range(2):
		var local := Transform3D(Basis(Vector3(-1, 0, 0), Vector3.UP, Vector3(0, 0, -1)), Vector3.ZERO)
		if index == 1:
			local = Transform3D(Basis(), Vector3(0, 0, WALL))
		var interaction := local
		interaction.origin += Vector3(0, 1.2, 0)
		specs.append(FaceSpec.new(faces[index], deck, id, spaces[index], destinations[index], local, interaction))

static func _authored_records() -> Array[Spec]:
	var specs: Array[Spec] = []
	for d: int in range(1, 31):
		var y: float = (14 - d) * DECK_PITCH
		var connector_ids: Array[StringName] = [connector_id(d, 0), connector_id(d, 1)]
		var built_sections: Array[StringName] = []
		for number: int in range(40, 43):
			var id := section_id(d, number)
			var start: float = 30 * (number - 41) + 6
			var side_ids: Array[StringName] = []
			var openings: Array[StringName] = []
			if d == 14:
				built_sections.append(id)
				for offset: int in [3, 9, 15]:
					for side: String in ["PORT", "STARBOARD"]:
						if number == 41 and offset == 9 and side == "STARBOARD":
							continue
						var side_id := StringName("%s-SIDE-%03d-%s" % [id, offset, side])
						side_ids.append(side_id)
						var frame := Transform3D(Basis(), Vector3(start + offset, y, -1.5 if side == "PORT" else 1.5))
						if side == "PORT":
							frame.basis = Basis(Vector3(-1, 0, 0), Vector3.UP, Vector3(0, 0, -1))
						# The outer side is an unbuilt space, not a playable room.
						var outside := StringName("%s/UNBUILT" % side_id)
						specs.append(SectionSpec.new(outside, d, number, AABB(Vector3(start + offset - 0.5, y, -2 if side == "PORT" else 1.7), Vector3(1, CLEAR_HEIGHT, 0.3)), [], [], &"emergency", false))
						_add_door(specs, side_id, d, DoorKind.SIDE, Policy.NEVER_OPENS, frame, Vector2(1, 2.2), [id, outside], id, Vector2i(number, number), [&"HALL", &"OUTER"])
				var fore_hatch := StringName("%s-H-AFT" % connector_id(d, number - 41))
				var aft_hatch := StringName("%s-H-FORE" % connector_id(d, number - 40))
				openings.append(fore_hatch)
				openings.append_array(side_ids)
				openings.append(aft_hatch)
				if number == 41:
					openings.append_array([BAY_DOOR_ID, POWER_DOOR_ID])
			specs.append(SectionSpec.new(id, d, number, AABB(Vector3(start, y, -1.5), Vector3(24, CLEAR_HEIGHT, 3)), openings, side_ids, &"opening" if number == 41 else &"emergency", d == 14))
		for n: int in range(2):
			var id := connector_id(d, n)
			var start: float = 30 * n
			var hatches: Array[StringName] = [StringName("%s-H-FORE" % id), StringName("%s-H-AFT" % id)]
			var well_id := StringName("C-%03d-LADDER" % n)
			var lift_id := StringName("%s-LIFT" % id)
			var lift_door := StringName("%s-DOOR" % lift_id)
			var well_x: float = 3.0 if n == 0 else 34.5
			specs.append(ConnectorSpec.new(id, d, n, AABB(Vector3(start, y, -1.5), Vector3(6, CLEAR_HEIGHT, 3)), hatches, well_id, lift_id, Transform3D(Basis(), Vector3(well_x, y, -1.5)), id, true))
			var policy := Policy.CRANK if d == 14 else Policy.NEVER_OPENS
			_add_door(specs, hatches[0], d, DoorKind.HATCH, policy, _frame_x(Vector3(start, y, 0)), Vector2(HATCH_WIDTH, HATCH_HEIGHT), [section_id(d, n + 40), id], id, Vector2i(n + 41, n + 40), [&"FORE", &"AFT"])
			_add_door(specs, hatches[1], d, DoorKind.HATCH, policy, _frame_x(Vector3(start + 6, y, 0)), Vector2(HATCH_WIDTH, HATCH_HEIGHT), [id, section_id(d, n + 41)], id, Vector2i(n + 41, n + 40), [&"FORE", &"AFT"])
			var lift_frame := Transform3D(Basis(), Vector3(start + 3, y, 1.5))
			specs.append(LiftSpec.new(lift_id, d, id, lift_door, AABB(Vector3(start + 2.1, y, 1.5), Vector3(1.8, CLEAR_HEIGHT, 3)), Transform3D(Basis(Vector3.LEFT, Vector3.UP, Vector3.FORWARD), Vector3(start + 3, y + DOOR_LABEL_HEIGHT, 1.488))))
			_add_door(specs, lift_door, d, DoorKind.LIFT, Policy.NEVER_OPENS, lift_frame, Vector2(1.8, 2.4), [id, lift_id], id, Vector2i(n + 41, n + 41), [&"HALL", &"LIFT"])
		specs.append(DeckSpec.new(d, connector_ids, built_sections))
	for n: int in [-1, 2]:
		var id := connector_id(14, n)
		var hatch_id := StringName("%s-H-%s" % [id, "AFT" if n == -1 else "FORE"])
		specs.append(ConnectorSpec.new(id, 14, n, AABB(Vector3(30 * n, 0, -1.5), Vector3(6, CLEAR_HEIGHT, 3)), [hatch_id], &"", &"", Transform3D.IDENTITY, id, false))
		var spaces: Array[StringName] = [section_id(14, 42), id]
		if n == -1:
			spaces.assign([id, section_id(14, 40)])
		_add_door(specs, hatch_id, 14, DoorKind.HATCH, Policy.NEVER_OPENS, _frame_x(Vector3(-24 if n == -1 else 60, 0, 0)), Vector2(HATCH_WIDTH, HATCH_HEIGHT), spaces, id, Vector2i(n + 41, n + 40), [&"FORE", &"AFT"])
	for n: int in range(2):
		var x: float = 3 if n == 0 else 34.5
		var landings: Array[Transform3D] = []
		var paths: Array[PackedVector3Array] = []
		for d: int in range(1, 31):
			var y: float = (14 - d) * DECK_PITCH
			landings.append(Transform3D(Basis(), Vector3(x, y, -2.9)))
			paths.append(PackedVector3Array([Vector3(x, y, -2.9), Vector3(x, y, -4.3)]))
		specs.append(LadderWellSpec.new(StringName("C-%03d-LADDER" % n), AABB(Vector3(x - 0.85, -88, -5.8), Vector3(1.7, 162.7, 4.3)), Transform3D(Basis(), Vector3(x, 0, -4.3)), landings, paths))
	specs.append(BaySpec.new(BAY_ID, 14, &"D14-S-041", Transform3D(Basis(Vector3(0, 0, -1), Vector3.UP, Vector3.RIGHT), Vector3(15, 0, 7.7))))
	var consoles: Array[Transform3D] = []
	var positions := power_console_positions()
	var yaws := power_console_yaws()
	for index: int in range(positions.size()):
		consoles.append(Transform3D(Basis(Vector3.UP, yaws[index]), positions[index]))
	specs.append(PowerRoomSpec.new(POWER_ID, 14, &"D14-S-041", AABB(Vector3(POWER_MIN_X, 0, POWER_FAR_Z), Vector3(Pods.ROOM_LENGTH, CLEAR_HEIGHT, Pods.ROOM_WIDTH)), POWER_DOOR_ID, consoles, Transform3D(Basis(), POWER_GENERATOR_CENTER)))
	_add_door(specs, BAY_DOOR_ID, 14, DoorKind.BAY, Policy.ROD_PRY, Transform3D(Basis(), Vector3(15, 0, 1.5)), Vector2(HATCH_WIDTH, HATCH_HEIGHT), [&"D14-S-041", BAY_ID], BAY_ID, Vector2i(41, 41), [&"HALL", &"BAY"])
	_add_door(specs, POWER_DOOR_ID, 14, DoorKind.POWER, Policy.PRESS_SLIDE, Transform3D(Basis(Vector3(-1, 0, 0), Vector3.UP, Vector3(0, 0, -1)), Vector3(POWER_CENTER_X, 0, -1.5)), Vector2(1, 2.2), [&"D14-S-041", POWER_ID], POWER_ID, Vector2i(41, 41), [&"HALL", &"POWER"])
	return specs

static func power_console_positions() -> Array[Vector3]:
	return [Vector3(POWER_MIN_X, 0, -3.7), Vector3(POWER_MIN_X, 0, -7.5), Vector3(POWER_MAX_X, 0, -3.7), Vector3(POWER_MAX_X, 0, -7.5), Vector3(24.5, 0, POWER_FAR_Z), Vector3(29.5, 0, POWER_FAR_Z)]

static func power_console_yaws() -> Array[float]:
	return [PI / 2.0, PI / 2.0, -PI / 2.0, -PI / 2.0, 0.0, 0.0]
