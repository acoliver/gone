extends SimTestCase

func test_unique_painted_atlas_has_both_faces_frame_and_close_camera_density() -> void:
	var material := Surfaces.material(&"modelled_hatch")
	var texture: Texture2D = material.get_shader_parameter(&"hatch_painted")
	assert_true(texture != null, "generated leaf and frame albedo is bound by the shared material")
	if texture == null: return
	var image := texture.get_image()
	# Andrew's wider, flush leaf needs larger cells to retain the unchanged density gate.
	assert_true(image.get_size() == Vector2i(1088, 2048), "packed generated paint")
	assert_int_equal(image.get_format(), Image.FORMAT_BPTC_RGBA, "albedo and derived height share BC7 RGBA")
	assert_true(image.has_mipmaps(), "paint has a complete mip chain")
	var door := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	# Andrew moved the leaf forward; evaluate the actual face, not the old 100 mm plate.
	var centre := door.frame() * door.hinge_frame() * Vector3(door.leaf_aperture().x / 2 + HatchParts.HINGE_OUTSET, 1.30, -door.leaf_face_depth(0))
	var distance := Vector3(28.45, 1.30, 0.03).distance_to(centre)
	var production_pixels := 1296.0 / (2 * tan(deg_to_rad(86.0 / 2)) * distance)
	var view := DoorView.build(door)
	for side: String in ["ForeSteel", "AftSteel"]:
		var piece: MeshInstance3D = view.label_leaf().get_node(side)
		var colours: PackedColorArray = piece.mesh.surface_get_arrays(0)[Mesh.ARRAY_COLOR]
		assert_true(not colours.is_empty(), "paint ownership travels with imported geometry")
		if not colours.is_empty():
			var plate: Dictionary = piece.mesh.get_meta(&"part_ranges")[StringName(side + "/plate")]
			var id := StringName(side + "/plate")
			var part: Dictionary = preload("res://tests/hatch_mesh_ranges.gd").parts(piece.mesh)[id]
			var dimensions: Vector3 = part.bounds.size
			var density := minf(image.get_width() / 2.0 / dimensions.x, image.get_height() * 0.53125 / dimensions.y)
			var face: Vector3 = door.frame().affine_inverse() * Surfaces.world_frame(piece) * part.pose * Vector3(0, 0, -dimensions.z / 2)
			var lookdev_pixels := 1312.0 / (2 * tan(deg_to_rad(46.0 / 2)) * absf(face.z + 3.65))
			print("HATCH_PAINT_DENSITY side=%s texels_per_metre=%.3f production_pixels_per_metre=%.3f lookdev_pixels_per_metre=%.3f production_texels_per_pixel=%.3f lookdev_texels_per_pixel=%.3f" % [side, density, production_pixels, lookdev_pixels, density / production_pixels, density / lookdev_pixels])
			assert_true(density >= production_pixels and density >= lookdev_pixels, "both texture axes exceed one texel per pixel at both close cameras")
			assert_true(colours[int(plate.vertex_start)].r > 0.99, "leaf plate selects unique paint, hardware retains scan")
			assert_true(colours[int(plate.vertex_start)].g > 0.99 if side == "AftSteel" else colours[int(plate.vertex_start)].g < 0.01, "each face selects its own generated cell")
			var uvs: PackedVector2Array = piece.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV2]
			assert_true(uvs.size() == colours.size(), "paint projection survives import for every vertex")
		var frame: MeshInstance3D = view.get_node("Frame/" + side)
		var frame_colours: PackedColorArray = frame.mesh.surface_get_arrays(0)[Mesh.ARRAY_COLOR]
		assert_true(not frame_colours.is_empty() and frame_colours[0].b > 0.99, "frame selects its independently generated albedo cell")
	view.free()

func test_texture_budget_includes_painted_atlas() -> void:
	var bytes := 0
	for texture: Texture2D in Surfaces.HATCH_TEXTURES.values(): bytes += texture.get_image().get_data().size()
	for texture: Texture2D in Surfaces.HATCH_DETAIL_TEXTURES.values(): bytes += texture.get_image().get_data().size()
	var painted: Texture2D = Surfaces.material(&"modelled_hatch").get_shader_parameter(&"hatch_painted")
	assert_true(painted != null, "paint atlas bound")
	if painted == null: return
	bytes += painted.get_image().get_data().size()
	print("HATCH_PAINTED_PAYLOAD ", bytes)
	assert_true(bytes <= 24000000, "all hatch samplers remain within the unchanged 24 MB budget")
