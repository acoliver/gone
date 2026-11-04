extends SimTestCase

func test_imported_leaf_and_frame_fit_the_shared_runtime_budget() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [&"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var view := DoorView.build(layout.door(id))
		var counts := _count(view)
		print("HATCH_BUDGET %s triangles=%d submissions=%d" % [id, counts.x, counts.y])
		assert_true(counts.x <= 40000, "at most 40000 imported triangles per complete hatch")
		assert_true(counts.y <= 12, "at most 12 imported material submissions per complete hatch")
		view.free()

func test_shared_render_maps_are_2048_and_no_more_than_24_mb_with_mips() -> void:
	var bytes := 0
	for kind: String in Surfaces.HATCH_TEXTURES:
		var image: Image = Surfaces.HATCH_TEXTURES[kind].get_image()
		assert_true(image.get_size() == Vector2i(2048, 2048), "2048 " + kind)
		assert_true(image.has_mipmaps() and image.get_mipmap_count() == 11, "full 2048 mip chain")
		bytes += image.get_data().size()
	for parameter: String in Surfaces.HATCH_DETAIL_TEXTURES:
		var image: Image = Surfaces.HATCH_DETAIL_TEXTURES[parameter].get_image()
		assert_true(image.get_size() == Vector2i(512, 512), "512 tiled " + parameter)
		assert_true(image.has_mipmaps() and image.get_mipmap_count() == 9, "full tiled detail mip chain")
		assert_int_equal(image.get_format(), Image.FORMAT_RGTC_RG if parameter.begins_with("normal") else Image.FORMAT_BPTC_RGBA, "compressed tiled detail format")
		bytes += image.get_data().size()
	print("HATCH_TEXTURE_PAYLOAD ", bytes)
	assert_true(bytes <= 24000000, "shared hatch texture payload is at most 24 MB")

func _count(node: Node) -> Vector2i:
	var mesh: Mesh
	var instances := 1
	if node is MeshInstance3D: mesh = node.mesh
	elif node is MultiMeshInstance3D:
		mesh = node.multimesh.mesh
		instances = node.multimesh.instance_count
	var result := Vector2i.ZERO
	if mesh != null and mesh.get_meta(&"imported_source", "") == HatchAsset.SOURCE:
		result.y = mesh.get_surface_count()
		for surface: int in range(mesh.get_surface_count()):
			result.x += mesh.surface_get_array_index_len(surface) / 3 * instances
	for child: Node in node.get_children(): result += _count(child)
	return result
