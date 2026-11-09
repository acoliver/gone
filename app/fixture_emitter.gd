class_name FixtureEmitter
extends RefCounted
## Reuse the hatch's weathered, caged lamp at an authored source position.

static var _steel: ShaderMaterial
static var _glass_dirt: ImageTexture
static var _glass_white_transmission: ImageTexture
static var _glass_roughness: ImageTexture
static var _glass_meshes: Dictionary[Mesh, ArrayMesh] = {}
static var _housings: Dictionary[Mesh, ArrayMesh] = {}
static var _service_housings: Dictionary[Mesh, ArrayMesh] = {}
static var _mounted_housings: Dictionary = {}

static func service_housing(source: Mesh) -> ArrayMesh:
	if not _service_housings.has(source):
		var importer := ImporterMesh.new()
		# Clearance checks retain one swept bound for each original fitting surface.
		for index: int in range(source.get_surface_count()):
			importer.add_surface(Mesh.PRIMITIVE_TRIANGLES, source.surface_get_arrays(index))
		importer.generate_lods(60, 0, [])
		var mesh := importer.get_mesh()
		mesh.set_meta(&"service_bounds", source.get_meta(&"service_bounds"))
		_service_housings[source] = mesh
	return _service_housings[source]

static func glass_mesh(source: Mesh) -> ArrayMesh:
	if not _glass_meshes.has(source):
		var arrays := source.surface_get_arrays(0)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var bounds := source.get_aabb()
		var uv := PackedVector2Array()
		for point: Vector3 in vertices:
			uv.append(Vector2((point.x - bounds.position.x) / bounds.size.x, (point.y - bounds.position.y) / bounds.size.y))
		arrays[Mesh.ARRAY_TEX_UV] = uv
		var importer := ImporterMesh.new()
		importer.add_surface(Mesh.PRIMITIVE_TRIANGLES, arrays)
		importer.generate_lods(60, 0, [])
		_glass_meshes[source] = importer.get_mesh()
	return _glass_meshes[source]

static func cage(parent: Node3D, mask: int, surface: Surfaces.SurfaceFrame, material: StandardMaterial3D, rotation: Basis = Basis.IDENTITY) -> MeshInstance3D:
	var assembly := Node3D.new()
	var service := ShipLayout.HatchServiceSpec.new(&"Lamp", Transform3D.IDENTITY)
	HatchServices._lamp(assembly, service, mask, surface)
	HatchServices._batch_metal(assembly, mask, surface)
	var lens: MeshInstance3D = assembly.get_node("Lens")
	var steel: MeshInstance3D = assembly.get_node("Steel")
	var source := steel.mesh
	if not _housings.has(source):
		var tool := SurfaceTool.new()
		tool.begin(Mesh.PRIMITIVE_TRIANGLES)
		for index: int in range(source.get_surface_count()):
			tool.append_from(source, index, Transform3D.IDENTITY)
		tool.index()
		var detail := tool.commit()
		var importer := ImporterMesh.new()
		importer.add_surface(Mesh.PRIMITIVE_TRIANGLES, detail.surface_get_arrays(0))
		importer.generate_lods(60, 0, [])
		var mesh := importer.get_mesh()
		mesh.set_meta(&"service_bounds", source.get_meta(&"service_bounds"))
		_housings[source] = mesh
	steel.mesh = _housings[source]
	steel.lod_bias = 0.5
	steel.material_override = steel_material()
	for piece: MeshInstance3D in [lens, steel]:
		assembly.remove_child(piece)
		piece.transform = Transform3D(rotation, rotation * Vector3(0, 0, 0.20)) * piece.transform
		parent.add_child(piece)
	lens.material_override = material
	assembly.free()
	return lens

static func wall_bracket(parent: Node3D, surface: Surfaces.SurfaceFrame, rotation: Basis) -> void:
	var bounds := surface.world_from_surface * surface.bounds
	var direction := rotation * Vector3.BACK
	var axis := 0 if absf(direction.x) > 0.5 else 2
	var side := signf(direction[axis])
	var reach := absf((bounds.position[axis] if side < 0 else bounds.end[axis]) - parent.position[axis])
	if reach <= 0.32: return
	var mount := MeshInstance3D.new()
	mount.name = "WallMount"
	mount.mesh = HatchModel.box_mesh(Vector3(0.045, 0.045, reach - 0.20))
	mount.basis = rotation
	mount.position = direction * (reach + 0.20) / 2
	parent.add_child(mount)
	combine_mount(parent, ^"WallMount")

static func bind(light: Light3D, emitter: MeshInstance3D, housing: MeshInstance3D) -> void:
	light.set_meta(&"fixture_emitter", emitter)
	light.set_meta(&"fixture_housing", housing)

static func seat(light: Light3D, emitter: MeshInstance3D, housing: MeshInstance3D) -> void:
	light.position = Surfaces.world_frame(light.get_parent()).affine_inverse() * (Surfaces.world_frame(emitter) * emitter.mesh.get_aabb().get_center())
	bind(light, emitter, housing)

static func beam(light: SpotLight3D, lens: MeshInstance3D, _surface: Surfaces.SurfaceFrame) -> void:
	var housing: MeshInstance3D
	for piece: MeshInstance3D in lens.get_parent().find_children("*", "MeshInstance3D", true, false):
		if piece != lens:
			housing = piece
			break
	assert(housing != null, "beam has its imported metal housing")
	# A flush recessed aperture emits from its glass, not from a drop below the ceiling.
	seat(light, lens, housing)
	light.basis = Surfaces.world_frame(light.get_parent()).basis.inverse() * Basis(Vector3.RIGHT, Vector3.FORWARD, Vector3.UP)
	light.spot_angle = 90.0
	light.spot_angle_attenuation = 0.0

static func wall_source(light: OmniLight3D, surface: Surfaces.SurfaceFrame, circuit: String, material: StandardMaterial3D, yaw: float) -> void:
	var lens := cage(light, light.light_cull_mask, surface, material, Basis(Vector3.UP, yaw))
	lens.set_meta(&"lamp_circuit", circuit)
	bind(light, lens, light.get_node("Steel"))

static func combine_mount(parent: Node3D, mount_path: NodePath = ^"CeilingMount") -> void:
	var steel: MeshInstance3D = parent.get_node("Steel")
	var mount: MeshInstance3D = parent.get_node(mount_path)
	var pose := steel.transform.affine_inverse() * mount.transform
	var key := [steel.mesh, mount.mesh, pose]
	if not _mounted_housings.has(key):
		var tool := SurfaceTool.new()
		tool.begin(Mesh.PRIMITIVE_TRIANGLES)
		tool.append_from(steel.mesh, 0, Transform3D.IDENTITY)
		tool.append_from(mount.mesh, 0, pose)
		tool.index()
		var detail := tool.commit()
		var importer := ImporterMesh.new()
		importer.add_surface(Mesh.PRIMITIVE_TRIANGLES, detail.surface_get_arrays(0))
		importer.generate_lods(60, 0, [])
		var mesh := importer.get_mesh()
		var bounds: Array = steel.mesh.get_meta(&"service_bounds").duplicate()
		bounds.append(pose * mount.mesh.get_aabb())
		mesh.set_meta(&"service_bounds", bounds)
		_mounted_housings[key] = mesh
	steel.mesh = _mounted_housings[key]
	steel.set_meta(&"mount_bounds", mount.transform * mount.mesh.get_aabb())
	mount.free()

static func steel_material() -> ShaderMaterial:
	if _steel == null:
		_steel = ShaderMaterial.new()
		_steel.shader = preload("res://app/shaders/fixture_steel.gdshader")
		_steel.set_shader_parameter("weathering_enabled", true)
		_steel.set_shader_parameter("grime_noise", _noise_volume())
	return _steel

static func _noise_volume() -> ImageTexture3D:
	var noise := FastNoiseLite.new()
	noise.seed = 1000
	noise.frequency = 0.8
	var slices: Array[Image] = []
	for z: int in range(64):
		var image := Image.create(64, 64, false, Image.FORMAT_R8)
		for y: int in range(64):
			for x: int in range(64):
				var value := (noise.get_noise_3d(x, y, z) + 1.0) * 0.5
				image.set_pixel(x, y, Color(value, value, value))
		slices.append(image)
	var texture := ImageTexture3D.new()
	var error := texture.create(Image.FORMAT_R8, 64, 64, 64, false, slices)
	assert(error == OK, "fixture noise volume must initialize")
	return texture

static func age_glass(material: StandardMaterial3D) -> void:
	if _glass_dirt == null:
		var image := Image.create(256, 128, false, Image.FORMAT_RGB8)
		var transmission := Image.create(256, 128, false, Image.FORMAT_RGB8)
		var roughness := Image.create(256, 128, false, Image.FORMAT_RGB8)
		var noise := FastNoiseLite.new()
		noise.seed = 1000
		noise.frequency = 0.065
		for y: int in range(image.get_height()):
			for x: int in range(image.get_width()):
				var patch := (noise.get_noise_2d(x, y) + 1.0) * 0.5
				var rim := pow(absf(float(y) / 127.0 * 2.0 - 1.0), 5)
				var dirt := clampf(0.10 + smoothstep(0.35, 0.67, patch) * 0.78 - rim * 0.42, 0.035, 0.88)
				image.set_pixel(x, y, Color(dirt, dirt, dirt))
				var through := lerpf(0.80 + 0.20 * dirt, 0.035, smoothstep(0.08, 0.30, rim))
				transmission.set_pixel(x, y, Color(through, through, through))
				var rough := 0.90 + 0.10 * (1.0 - dirt)
				roughness.set_pixel(x, y, Color(rough, rough, rough))
		image.generate_mipmaps()
		_glass_dirt = ImageTexture.create_from_image(image)
		transmission.generate_mipmaps()
		_glass_white_transmission = ImageTexture.create_from_image(transmission)
		roughness.generate_mipmaps()
		_glass_roughness = ImageTexture.create_from_image(roughness)
	material.resource_name = "AgedCageGlass"
	material.albedo_texture = _glass_dirt
	material.emission_texture = _glass_dirt
	material.emission_operator = BaseMaterial3D.EMISSION_OP_MULTIPLY
	material.roughness_texture = _glass_roughness
	material.roughness = 1.0

static func age_white_glass(material: StandardMaterial3D) -> void:
	age_glass(material)
	material.emission_texture = _glass_white_transmission
