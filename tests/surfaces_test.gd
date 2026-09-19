extends SimTestCase
## The room shell's textured surface pass (issue #35): every surface
## material wears the authored industrial maps (albedo + normal + packed
## ORM with per-slot channel selection), triplanar mapping is on with
## pinned per-surface uv1_scale, materials are cached once per process
## so two builds share references, the albedo luma still matches the
## prep manifest, and the pass adds no lights, colliders, or extra
## meshes.

const MANIFEST_TOLERANCE: float = 2.0 / 255.0

func test_surface_materials_wear_the_authored_texture_maps() -> void:
	for surface: String in ["wall", "floor", "ceiling"]:
		var material := _material_for(surface)
		assert_true(material.albedo_texture != null, "%s albedo map is loaded" % surface)
		assert_true(material.normal_enabled, "%s normal mapping is enabled" % surface)
		assert_true(material.normal_texture != null, "%s normal map is loaded" % surface)
		assert_true(material.ao_enabled, "%s ambient occlusion is enabled" % surface)
		var orm: Texture2D = material.ao_texture
		assert_true(orm != null, "%s ORM map is loaded" % surface)
		assert_true(
			material.get("ambient_occlusion_texture") == null,
			"%s carries no Godot 3.x ambient_occlusion_texture remap name" % surface
		)
		assert_true(
			material.roughness_texture == orm and material.metallic_texture == orm,
			"%s roughness and metallic ride the same ORM resource" % surface
		)
		assert_true(
			material.ao_texture_channel == BaseMaterial3D.TEXTURE_CHANNEL_RED,
			"%s occlusion reads the ORM R channel" % surface
		)
		assert_true(
			material.roughness_texture_channel == BaseMaterial3D.TEXTURE_CHANNEL_GREEN,
			"%s roughness reads the ORM G channel" % surface
		)
		assert_true(
			material.metallic_texture_channel == BaseMaterial3D.TEXTURE_CHANNEL_BLUE,
			"%s metallic reads the ORM B channel" % surface
		)
		assert_float_equal(material.roughness, 1.0, "%s roughness scalar stays map-driven" % surface)
		assert_float_equal(material.metallic, 1.0, "%s metallic scalar stays map-driven" % surface)
		assert_true(
			material.albedo_color == Color(1.0, 1.0, 1.0, 1.0),
			"%s albedo stays untinted; the maps carry the gray" % surface
		)

func test_room_shell_swaps_textured_materials_in_place() -> void:
	var room := RoomGeometry.build()
	var shell: Array[Placement.SolidPlacement] = Placement.room_shell()
	assert_int_equal(room.get_child_count(), 7, "six shell boxes plus the ceiling damage group")
	for index: int in range(shell.size()):
		var box: MeshInstance3D = room.get_child(index)
		var expected := RoomGeometry.wall_material()
		if index == 0:
			expected = RoomGeometry.floor_material()
		elif index == 1:
			expected = RoomGeometry.ceiling_material()
		assert_true(
			box.material_override == expected,
			"shell box %d swaps in its surface material by reference" % index
		)
	assert_true(
		RoomGeometry.floor_material() != RoomGeometry.wall_material()
			and RoomGeometry.wall_material() != RoomGeometry.ceiling_material()
			and RoomGeometry.ceiling_material() != RoomGeometry.floor_material(),
		"each surface owns one distinct material instance"
	)
	assert_int_equal(
		_count_instances(room, MeshInstance3D),
		shell.size() + Placement.cable_trays().size() + Placement.wire_loops().size(),
		"the pass swaps materials in place; no meshes are added"
	)
	var damage := room.get_child(shell.size())
	for child: Node in damage.get_children():
		var dressing: MeshInstance3D = child
		assert_true(
			dressing.material_override is StandardMaterial3D
				and dressing.material_override.albedo_texture == null,
			"tray and wire dressing keeps its flat grey material"
		)

func test_triplanar_and_uv1_scale_are_pinned_per_surface() -> void:
	var pinned: Array = [
		["floor", Vector3(1.0, 1.0, 1.0)],
		["wall", Vector3(0.75, 0.75, 0.75)],
		["ceiling", Vector3(0.8, 0.8, 0.8)],
	]
	for entry: Array in pinned:
		var surface: String = entry[0]
		var scale: Vector3 = entry[1]
		var material := _material_for(surface)
		assert_true(
			material.uv1_triplanar,
			"%s maps triplanar; the shell boxes carry no authored UVs" % surface
		)
		assert_true(
			material.get("uv1_triplanar_enabled") == null,
			"%s carries no Godot 3.x uv1_triplanar_enabled remap name" % surface
		)
		assert_vec3_equal(
			material.uv1_scale,
			scale,
			"%s uv1_scale is pinned: one tile spans %.2f m" % [surface, 1.0 / scale.x]
		)
		assert_vec3_equal(
			material.uv1_offset,
			Vector3.ZERO,
			"%s uv1 stays unshifted" % surface
		)

func test_two_builds_yield_identical_material_references_and_params() -> void:
	var first := RoomGeometry.build()
	var second := RoomGeometry.build()
	for surface: String in ["wall", "floor", "ceiling"]:
		var slot := 2
		if surface == "floor":
			slot = 0
		elif surface == "ceiling":
			slot = 1
		var from_first: StandardMaterial3D = first.get_child(slot).material_override
		var from_second: StandardMaterial3D = second.get_child(slot).material_override
		assert_true(
			from_first == from_second,
			"both builds share the one cached %s material reference" % surface
		)
		assert_true(
			from_first == _material_for(surface),
			"the accessor hands out the same %s instance every call" % surface
		)
		assert_vec3_equal(
			from_first.uv1_scale,
			from_second.uv1_scale,
			"the %s tile scale holds across builds" % surface
		)
		assert_true(
			from_first.uv1_triplanar == from_second.uv1_triplanar,
			"the %s triplanar flag holds across builds" % surface
		)
		assert_true(
			from_first.albedo_texture == from_second.albedo_texture,
			"the %s maps never reload across builds" % surface
		)

func test_albedo_luma_matches_the_prep_manifest() -> void:
	var expected: Array = [
		["wall", 94.95],
		["floor", 84.13],
		["ceiling", 77.81],
	]
	for entry: Array in expected:
		var surface: String = entry[0]
		var texture: Texture2D = _material_for(surface).albedo_texture
		assert_true(texture != null, "%s albedo texture is loaded before metering" % surface)
		var image := texture.get_image()
		assert_true(
			image != null and not image.is_empty(),
			"%s albedo image data is readable" % surface
		)
		var luma := _mean_luma(image)
		assert_true(
			absf(luma - float(entry[1])) <= MANIFEST_TOLERANCE,
			"%s albedo mean luma stays within 2/255 of the manifest: expected %.2f, got %.2f"
			% [surface, float(entry[1]), luma]
		)

func test_room_geometry_adds_no_lights_or_colliders() -> void:
	var room := RoomGeometry.build()
	assert_int_equal(
		_count_instances(room, Light3D),
		0,
		"the texture pass introduces no light of any kind"
	)
	assert_int_equal(
		_count_instances(room, CollisionShape3D),
		0,
		"the texture pass introduces no colliders"
	)

func _material_for(surface: String) -> StandardMaterial3D:
	if surface == "floor":
		return RoomGeometry.floor_material()
	if surface == "ceiling":
		return RoomGeometry.ceiling_material()
	return RoomGeometry.wall_material()

func _mean_luma(image: Image) -> float:
	var total := 0.0
	for y: int in range(image.get_height()):
		for x: int in range(image.get_width()):
			var color := image.get_pixel(x, y)
			total += (color.r8 + color.g8 + color.b8) / 3.0
	return total / float(image.get_width() * image.get_height())

func _count_instances(node: Node, native_type: Variant) -> int:
	var total := 0
	if is_instance_of(node, native_type):
		total += 1
	for child: Node in node.get_children():
		total += _count_instances(child, native_type)
	return total
