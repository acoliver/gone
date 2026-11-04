extends SimTestCase

func test_close_camera_detail_density_exceeds_two_texels_per_pixel() -> void:
	var material := Surfaces.material(&"modelled_hatch")
	var pitch: Variant = material.get_shader_parameter(&"hatch_detail_pitch")
	var detail: Texture2D = material.get_shader_parameter(&"albedo_a")
	assert_true(pitch is float and detail != null, "modelled hatch binds metre-scaled photographic detail")
	if not pitch is float or detail == null: return
	var camera := Camera3D.new()
	camera.position = Vector3(28.45, 1.30, 0.03)
	camera.fov = 86
	var door := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	var centre := door.frame() * door.hinge_frame() * Vector3(door.leaf_aperture().x / 2, 1.30, -0.10)
	var distance := camera.position.distance_to(centre)
	var pixels_per_metre := 1296.0 / (2 * tan(deg_to_rad(camera.fov / 2)) * distance)
	var detail_density: float = detail.get_width() / pitch
	assert_true(detail_density >= pixels_per_metre * 2, "detail must not magnify at the production close camera")
	var view := DoorView.build(door)
	var mesh: Mesh = view.label_leaf().get_node("ForeSteel").mesh
	var arrays := mesh.surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var row: Dictionary = mesh.get_meta(&"part_ranges")[&"ForeSteel/plate"]
	var densities: Array[float] = []
	for triangle: int in range(int(row.index_start), int(row.index_start + row.index_count), 3):
		var a := indices[triangle]
		var b := indices[triangle + 1]
		var c := indices[triangle + 2]
		if normals[a].z > -0.9999: continue
		var area := (vertices[b] - vertices[a]).cross(vertices[c] - vertices[a]).length()
		var uv_area := absf((uvs[b] - uvs[a]).cross(uvs[c] - uvs[a]))
		if area > 0.000001: densities.append(Surfaces.HATCH_TEXTURES.albedo.get_width() * sqrt(uv_area / area))
	densities.sort()
	assert_true(not densities.is_empty(), "density uses actual imported front-cap UV area")
	if not densities.is_empty():
		print("HATCH_DENSITY mask_texels_per_metre=%.3f detail_texels_per_metre=%.3f close_pixels_per_metre=%.3f detail_texels_per_pixel=%.3f distance_m=%.4f" % [densities[densities.size() / 2], detail_density, pixels_per_metre, detail_density / pixels_per_metre, distance])
	assert_true(Surfaces.STEEL.code.contains("scan_sample(albedo_a") and Surfaces.STEEL.code.contains("hatch_detail_pitch"), "the production shader samples tiled detail separately from UV masks")
	view.free()
	camera.free()
