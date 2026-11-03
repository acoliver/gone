class_name Surfaces
extends RefCounted
## Architectural materials are finite shared resources. Identity and motion live
## on geometry instances, never in a material or a global per-owner cache.

const STEEL := preload("res://app/shaders/weathered_steel.gdshader")
const TAPE := preload("res://app/shaders/weathered_tape.gdshader")
const ROOT := "res://assets/surfaces/steel/"
const PANEL_PITCH := Vector2(1.5, 1.0)
const SCANS: Array[String] = ["green_metal_rust", "rusty_painted_metal", "rusty_metal_04"]
const ROLES := {
	&"wall": {}, &"floor": {"floor_surface": true}, &"ceiling": {},
	&"hatch_leaf": {"hatch_surface": true}, &"frame": {"hatch_surface": true},
	&"hardware": {"hatch_surface": true, "wheel_surface": true, "curved_surface": true},
	&"wheel": {"hatch_surface": true, "wheel_surface": true, "wheel_only": true, "curved_surface": true},
	&"plate_edge": {"edge_surface": true},
	&"rivet": {"rivet_surface": true, "curved_surface": true},
}
const PARTS: Array[StringName] = [
	&"PORT", &"STARBOARD", &"FORE", &"AFT", &"BACK", &"FLOOR", &"CEILING",
	&"WALL", &"FRAME", &"COAMING", &"LEAF", &"WHEEL/FORE", &"WHEEL/AFT",
	&"LANDING/PORT", &"LANDING/STARBOARD", &"LANDING/BACK", &"LANDING/FLOOR", &"LANDING/CEILING",
	&"SIDE--1", &"SIDE-1", &"LEFT", &"RIGHT", &"TOP", &"BOTTOM", &"RAILS", &"RUNGS", &"CLOSURES",
]
const IMAGES: Array[String] = [
	"r4-green_metal_rust-albedo.png", "r4-rusty_painted_metal-albedo.png", "r4-rusty_metal_04-albedo.png",
	"green_metal_rust_normal.jpg", "rusty_painted_metal_normal.jpg", "rusty_metal_04_normal.jpg",
	"green_metal_rust_orm.jpg", "rusty_painted_metal_orm.jpg", "rusty_metal_04_orm.jpg",
	"r3-rust_coarse_01-albedo.jpg", "r3-rust_coarse_01-normal.jpg",
]
static var _materials: Dictionary = {}
static var _textures: Dictionary = {}
static var _tape: ShaderMaterial

class SurfaceFrame:
	extends RefCounted
	var key: StringName
	var world_from_surface: Transform3D
	var floor_datum: float = 0.0
	var bounds: AABB
	var aperture := Vector2(1.08, 2.4)
	var seed_offset: Vector3

static func material(role: StringName) -> ShaderMaterial:
	assert(ROLES.has(role), "unknown steel role: %s" % role)
	if _materials.has(role): return _materials[role]
	var result := ShaderMaterial.new()
	result.shader = STEEL
	var hatch := role in [&"hatch_leaf", &"frame", &"hardware", &"wheel"]
	result.set_shader_parameter(&"gain", 0.265 if hatch else 0.19)
	result.set_shader_parameter(&"contrast", 0.35 if hatch else 0.65)
	result.set_shader_parameter(&"macro", 0.18 if hatch else 0.22)
	result.set_shader_parameter(&"seam_strength", 0.36)
	result.set_shader_parameter(&"colour_gain", Vector3.ONE)
	result.set_shader_parameter(&"panel_pitch", PANEL_PITCH)
	for option: String in ROLES[role]: result.set_shader_parameter(option, ROLES[role][option])
	for index: int in range(SCANS.size()):
		var scan := SCANS[index]
		var suffix: String = ["a", "b", "c"][index]
		result.set_shader_parameter("albedo_" + suffix, texture("r4-%s-albedo.png" % scan))
		for kind: String in ["normal", "orm"]:
			result.set_shader_parameter(kind + "_" + suffix, texture("%s_%s.jpg" % [scan, kind]))
	result.set_shader_parameter(&"oxide_grain", texture("r3-rust_coarse_01-albedo.jpg"))
	result.set_shader_parameter(&"oxide_normal", texture("r3-rust_coarse_01-normal.jpg"))
	_materials[role] = result
	return result

static func texture(file: String) -> Texture2D:
	assert(IMAGES.has(file), "texture belongs to the finite approved inventory: %s" % file)
	if not _textures.has(file):
		var resource := load(ROOT + file) as Texture2D
		assert(resource != null, "required steel texture is imported: %s" % (ROOT + file))
		_textures[file] = resource
	return _textures[file]

static func tape_material() -> ShaderMaterial:
	if _tape == null:
		_tape = ShaderMaterial.new()
		_tape.shader = TAPE
	return _tape

static func cache_size() -> int:
	return _materials.size() + (0 if _tape == null else 1)

static func weather_seed(owner_id: StringName, part: StringName) -> int:
	assert(owner_id != &"" and part != &"", "steel identity needs an owner and part")
	var value := 2166136261
	for byte: int in ("steel-v1/%s/%s" % [owner_id, part]).to_utf8_buffer():
		value = ((value ^ byte) * 16777619) & 0xffffffff
	return value

static func _seed_offset(owner_id: StringName, part: StringName) -> Vector3:
	var seed := weather_seed(owner_id, part)
	return Vector3(float(seed & 1023), float((seed >> 10) & 1023), float((seed >> 20) & 1023)) / 32.0

static func surface_frame(layout: ShipLayout, owner_id: StringName, part: StringName) -> SurfaceFrame:
	assert(PARTS.has(part), "unsupported steel plane: %s/%s" % [owner_id, part])
	var result := SurfaceFrame.new()
	result.key = StringName("%s/%s" % [owner_id, part])
	var frame := Transform3D.IDENTITY
	var bounds: AABB
	if owner_id == ShipLayout.BAY_ID:
		frame = layout.bay_to_world()
		bounds = layout.bay().local_bounds()
	elif owner_id == ShipLayout.POWER_ID:
		bounds = layout.power_room().bounds()
		frame.origin = Vector3(bounds.position.x, bounds.position.y, bounds.get_center().z)
		bounds = frame.affine_inverse() * bounds
	elif layout.has_space(owner_id):
		if "-S-" in String(owner_id): bounds = layout.section(owner_id).bounds()
		elif String(owner_id).ends_with("-LIFT"): bounds = layout.lift(owner_id).bounds()
		else: bounds = layout.connector(owner_id).bounds()
		frame.origin = Vector3(bounds.position.x, bounds.position.y, bounds.get_center().z)
		bounds = frame.affine_inverse() * bounds
		if String(part).begins_with("LANDING/"):
			bounds = frame.affine_inverse() * layout.well(layout.connector(owner_id).well_id()).landing_bounds(layout.connector(owner_id).deck_number())
	elif layout.well_ids().has(owner_id):
		bounds = layout.well(owner_id).bounds()
		frame.origin = Vector3(bounds.get_center().x, bounds.position.y, bounds.get_center().z)
		bounds = frame.affine_inverse() * bounds
	else:
		return door_frame(layout.door(owner_id), part)
	result.world_from_surface = frame
	result.floor_datum = bounds.position.y
	result.bounds = bounds
	result.seed_offset = _seed_offset(owner_id, part)
	_validate_frame(result)
	return result

static func door_frame(door: ShipLayout.DoorSpec, part: StringName) -> SurfaceFrame:
	assert(part in [&"LEAF", &"FRAME", &"COAMING", &"WALL", &"WHEEL/FORE", &"WHEEL/AFT"], "known door plane: %s/%s" % [door.id(), part])
	var result := SurfaceFrame.new()
	result.key = StringName("%s/%s" % [door.id(), part])
	result.world_from_surface = door.frame()
	result.aperture = door.leaf_aperture() if door.has_wheel() else door.aperture()
	result.bounds = AABB(Vector3(-door.aperture().x / 2, 0, -ShipLayout.WALL), Vector3(door.aperture().x, door.aperture().y, ShipLayout.WALL * 2))
	if part == &"WALL":
		result.bounds = AABB(Vector3(-ShipLayout.CORRIDOR_WIDTH / 2, 0, -ShipLayout.WALL), Vector3(ShipLayout.CORRIDOR_WIDTH, ShipLayout.CLEAR_HEIGHT, ShipLayout.WALL * 2))
	if part in [&"LEAF", &"WHEEL/FORE", &"WHEEL/AFT"] and door.has_wheel():
		result.world_from_surface *= door.hinge_frame()
		result.bounds.position.x = 0
	result.seed_offset = _seed_offset(door.id(), part)
	_validate_frame(result)
	return result

class MotionBinding:
	extends RefCounted
	var anchor: Node3D
	var pieces: Array[GeometryInstance3D] = []
	func _init(p_anchor: Node3D) -> void:
		anchor = p_anchor
	func refresh() -> void:
		Surfaces.present_frame(pieces, Surfaces.world_frame(anchor))

static func bind_solid(piece: GeometryInstance3D, layout: ShipLayout, solid: ShipGeometry.SolidSpec) -> void:
	var frame := frame_for_solid(layout, solid)
	if solid.material_role == &"door":
		var relative := solid.transform.affine_inverse() * frame.world_from_surface
		frame.bounds = relative * frame.bounds
		frame.floor_datum = (relative * Vector3(0, frame.floor_datum, 0)).y
		frame.world_from_surface = solid.transform
	bind(piece, role_for_solid(solid), frame)

static func frame_for_solid(layout: ShipLayout, solid: ShipGeometry.SolidSpec) -> SurfaceFrame:
	assert(solid.surface_owner != &"" and solid.surface_part != &"", "solid needs a recipe-owned surface identity: %s" % solid.id)
	return surface_frame(layout, solid.surface_owner, solid.surface_part)

static func role_for_solid(solid: ShipGeometry.SolidSpec) -> StringName:
	return &"hatch_leaf" if solid.material_role == &"door" else solid.material_role

static func bind(piece: GeometryInstance3D, role: StringName, frame: SurfaceFrame) -> void:
	_validate_frame(frame)
	assert(piece is MeshInstance3D or piece is MultiMeshInstance3D, "supported steel geometry: %s" % piece.name)
	piece.material_override = material(role)
	piece.set_meta(&"surface_frame", frame)
	piece.set_instance_shader_parameter(&"seed_offset", frame.seed_offset)
	piece.set_instance_shader_parameter(&"lateral_bounds", Vector4(frame.bounds.position.x, frame.bounds.end.x, frame.bounds.position.z, frame.bounds.end.z))
	piece.set_instance_shader_parameter(&"floor_datum", frame.floor_datum)
	piece.set_instance_shader_parameter(&"aperture", frame.aperture)
	_write_rows(piece, frame.world_from_surface)

static func _validate_frame(frame: SurfaceFrame) -> void:
	assert(frame != null and frame.key != &"", "surface has a stable identity")
	assert(frame.bounds.position.is_finite() and frame.bounds.size.is_finite() and frame.bounds.size.x > 0 and frame.bounds.size.y > 0 and frame.bounds.size.z > 0, "finite positive bounds: %s" % frame.key)
	assert(is_finite(frame.floor_datum) and frame.aperture.is_finite() and frame.seed_offset.is_finite(), "finite weather data: %s" % frame.key)
	_validate_rigid(frame.world_from_surface, frame.key)

static func _validate_rigid(frame: Transform3D, key: StringName) -> void:
	assert(frame.is_finite() and frame.basis.is_equal_approx(frame.basis.orthonormalized()) and is_equal_approx(frame.basis.determinant(), 1.0), "rigid surface frame: %s" % key)

static func _write_rows(piece: GeometryInstance3D, world_from_surface: Transform3D) -> void:
	var inverse := world_from_surface.affine_inverse()
	piece.set_instance_shader_parameter(&"surface_x", Vector4(inverse.basis.x.x, inverse.basis.y.x, inverse.basis.z.x, inverse.origin.x))
	piece.set_instance_shader_parameter(&"surface_y", Vector4(inverse.basis.x.y, inverse.basis.y.y, inverse.basis.z.y, inverse.origin.y))
	piece.set_instance_shader_parameter(&"surface_z", Vector4(inverse.basis.x.z, inverse.basis.y.z, inverse.basis.z.z, inverse.origin.z))

static func present_frame(pieces: Array[GeometryInstance3D], world_from_surface: Transform3D) -> void:
	_validate_rigid(world_from_surface, &"moving part")
	for piece: GeometryInstance3D in pieces: _write_rows(piece, world_from_surface)

static func world_frame(node: Node3D) -> Transform3D:
	var frame := node.transform
	var parent := node.get_parent() as Node3D
	while parent != null:
		frame = parent.transform * frame
		parent = parent.get_parent() as Node3D
	return frame

static func sample_position(piece: GeometryInstance3D, point: Vector3) -> Vector3:
	var x: Vector4 = piece.get_instance_shader_parameter(&"surface_x")
	var y: Vector4 = piece.get_instance_shader_parameter(&"surface_y")
	var z: Vector4 = piece.get_instance_shader_parameter(&"surface_z")
	var p := Vector4(point.x, point.y, point.z, 1)
	return Vector3(x.dot(p), y.dot(p), z.dot(p))
