class_name RoomGeometry
extends Node3D
## Greybox room shell and torn-ceiling dressing, ported from gone_app
## geometry.rs (spawn_room_shell, spawn_ceiling_damage). Every mesh is an
## engine primitive spawned verbatim from the pure placements in
## Placement. The shell's three surfaces — floor, ceiling, walls — wear
## the authored industrial texture sets (issue #35) as triplanar
## StandardMaterial3D, cached once per process so the game, harness,
## and capture scenes share resources; cable trays and wire loops stay
## flat grey dressing.

const TRAY_SHADE: float = 0.24
const WIRE_SHADE: float = 0.18

## Authored triplanar density per surface: uv1_scale is UV repeats per
## meter, so each texture tile spans the reciprocal (floor 1.0 m, walls
## ~1.33 m, ceiling 1.25 m). The values differ per surface on purpose —
## equal scales would phase-align the wall and floor seams into one
## unbroken line around the room, and the deliberate offsets keep
## standing and mid-room views from reading a grid.
const FLOOR_UV1_SCALE := Vector3(1.0, 1.0, 1.0)
const WALL_UV1_SCALE := Vector3(0.75, 0.75, 0.75)
const CEILING_UV1_SCALE := Vector3(0.8, 0.8, 0.8)

static var _box_cache: Dictionary = {}
static var _surface_material_cache: Dictionary = {}

static func build() -> RoomGeometry:
	var room := RoomGeometry.new()
	var shell := Placement.room_shell()
	for index: int in range(shell.size()):
		var material := wall_material()
		if index == 0:
			material = floor_material()
		elif index == 1:
			material = ceiling_material()
		room.add_child(_box_instance(shell[index], material))
	room.add_child(_build_ceiling_damage())
	return room

static func floor_material() -> StandardMaterial3D:
	return _surface_material("floor", FLOOR_UV1_SCALE)

static func ceiling_material() -> StandardMaterial3D:
	return _surface_material("ceiling", CEILING_UV1_SCALE)

static func wall_material() -> StandardMaterial3D:
	return _surface_material("wall", WALL_UV1_SCALE)

## The torn ceiling: cable tray runs concentrated over the room center,
## each tipped off level, with hanging wire loops beneath them.
static func _build_ceiling_damage() -> Node3D:
	var damage := Node3D.new()
	damage.name = "CeilingDamage"
	var tray_material := _flat_grey(TRAY_SHADE)
	var wire_material := _flat_grey(WIRE_SHADE)
	for placement: Placement.SolidPlacement in Placement.cable_trays():
		damage.add_child(_box_instance(placement, tray_material))
	for loop: Placement.WireLoop in Placement.wire_loops():
		var mesh := TorusMesh.new()
		mesh.inner_radius = Placement.WIRE_INNER_RADIUS
		mesh.outer_radius = Placement.WIRE_OUTER_RADIUS
		var wire := MeshInstance3D.new()
		wire.mesh = mesh
		wire.material_override = wire_material
		wire.position = loop.center
		wire.quaternion = loop.rotation
		damage.add_child(wire)
	return damage

## One textured material per surface role, built once per process and
## cached: albedo + normal + the packed ORM map. The ORM texture carries
## occlusion in R, roughness in G, and metallic in B, so the same
## resource feeds the three slots and the per-slot channel selects its
## own color while the roughness and metallic scalars stay at the
## map-driven 1.0. Triplanar mapping covers the hand-built boxes, which
## carry no authored UVs; uv1_scale is authored per surface.
static func _surface_material(surface: String, uv1_scale: Vector3) -> StandardMaterial3D:
	if _surface_material_cache.has(surface):
		return _surface_material_cache[surface]
	var orm := _surface_texture(surface, "orm")
	var material := StandardMaterial3D.new()
	material.albedo_texture = _surface_texture(surface, "albedo")
	material.normal_enabled = true
	material.normal_texture = _surface_texture(surface, "normal")
	material.ao_enabled = true
	material.ao_texture = orm
	material.ao_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_RED
	material.roughness = 1.0
	material.roughness_texture = orm
	material.roughness_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_GREEN
	material.metallic = 1.0
	material.metallic_texture = orm
	material.metallic_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_BLUE
	material.uv1_triplanar = true
	material.uv1_scale = uv1_scale
	_surface_material_cache[surface] = material
	return material

static func _surface_texture(surface: String, kind: String) -> Texture2D:
	var path := "res://assets/surfaces/%s/%s.png" % [surface, kind]
	var texture: Texture2D = load(path)
	assert(texture != null, "surface texture %s is imported" % path)
	return texture

static func _box_instance(placement: Placement.SolidPlacement, material: StandardMaterial3D) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.mesh = _box_mesh(placement.size)
	instance.material_override = material
	instance.position = placement.center
	instance.quaternion = placement.rotation
	return instance

static func _box_mesh(size: Vector3) -> BoxMesh:
	if _box_cache.has(size):
		return _box_cache[size]
	var mesh := BoxMesh.new()
	mesh.size = size
	_box_cache[size] = mesh
	return mesh

static func _flat_grey(shade: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(shade, shade, shade)
	material.roughness = 0.95
	return material
