class_name FixtureEmitter
extends RefCounted
## Reuse the hatch's weathered, caged lamp at an authored source position.

static var _housings: Dictionary[Mesh, ArrayMesh] = {}
static var _mounted_housings: Dictionary = {}

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
	for piece: MeshInstance3D in [lens, steel]:
		assembly.remove_child(piece)
		piece.transform = Transform3D(rotation, rotation * Vector3(0, 0, 0.20)) * piece.transform
		parent.add_child(piece)
	lens.material_override = material
	assembly.free()
	if parent.has_node("CeilingMount"): combine_mount(parent)
	return lens

static func bind(light: Light3D, emitter: MeshInstance3D, housing: MeshInstance3D) -> void:
	light.set_meta(&"fixture_emitter", emitter)
	light.set_meta(&"fixture_housing", housing)

static func seat(light: Light3D, emitter: MeshInstance3D, housing: MeshInstance3D) -> void:
	light.position = Surfaces.world_frame(light.get_parent()).affine_inverse() * (Surfaces.world_frame(emitter) * emitter.mesh.get_aabb().get_center())
	bind(light, emitter, housing)

static func suspended(light: OmniLight3D, ceiling_y: float, surface: Surfaces.SurfaceFrame, circuit: String, material: StandardMaterial3D) -> void:
	var lens := cage(light, light.light_cull_mask, surface, material, Basis(Vector3.RIGHT, -PI / 2))
	lens.set_meta(&"lamp_circuit", circuit)
	DressingMounts.ceiling_stem(light, ceiling_y, surface)
	combine_mount(light)
	bind(light, lens, light.get_node("Steel"))

static func beam(light: OmniLight3D, lens: MeshInstance3D, surface: Surfaces.SurfaceFrame) -> void:
	var housing: MeshInstance3D
	for piece: MeshInstance3D in lens.get_parent().find_children("*", "MeshInstance3D", true, false):
		if piece != lens:
			housing = piece
			break
	assert(housing != null, "beam has its imported metal housing")
	var asset := lens.get_parent() as Node3D
	var ceiling_y := asset.position.y
	var emitter := Surfaces.world_frame(lens) * lens.mesh.get_aabb().get_center()
	var offset := Surfaces.world_frame(asset.get_parent()).basis.inverse() * (Surfaces.world_frame(light).origin - emitter)
	# Fit the visible assembly to the measured source, preserving every incident-light sample.
	asset.position += offset
	var mount := MeshInstance3D.new()
	mount.name = "CeilingMount"
	var stock := BoxMesh.new()
	stock.size = Vector3(0.045, ceiling_y - asset.position.y + 0.001, 0.045)
	# Ceiling-anchored stock overlaps the housing by 1 mm instead of leaving a floating joint.
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	tool.append_from(stock, 0, Transform3D(Basis.IDENTITY, Vector3(0, -stock.size.y / 2, 0)))
	mount.mesh = tool.commit()
	mount.position = Vector3(asset.position.x, ceiling_y, asset.position.z)
	mount.layers = lens.layers
	mount.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	Surfaces.bind(mount, &"hardware", surface)
	asset.get_parent().add_child(mount)
	bind(light, lens, housing)

static func wall_source(light: OmniLight3D, surface: Surfaces.SurfaceFrame, circuit: String, material: StandardMaterial3D, yaw: float) -> void:
	var lens := cage(light, light.light_cull_mask, surface, material, Basis(Vector3.UP, yaw))
	lens.set_meta(&"lamp_circuit", circuit)
	bind(light, lens, light.get_node("Steel"))

static func combine_mount(parent: Node3D) -> void:
	var steel: MeshInstance3D = parent.get_node("Steel")
	var mount: MeshInstance3D = parent.get_node("CeilingMount")
	var pose := steel.transform.affine_inverse() * mount.transform
	var key := [steel.mesh, pose]
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
