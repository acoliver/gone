extends SimTestCase

func test_every_imported_triangle_centroid_samples_baked_coverage() -> void:
	var coverage := Image.load_from_file("res://assets/props/hatch/hatch_coverage.png")
	assert_true(coverage != null, "bake coverage is available")
	if coverage == null: return
	var packed: PackedScene = load(HatchAsset.SOURCE)
	var scene := packed.instantiate()
	var counts := _check(scene, coverage)
	scene.free()
	print("HATCH_BAKE_COVERAGE triangles=%d uncovered=%d" % [counts.x, counts.y])
	assert_true(counts.x > 70000, "both complete imported variants checked, including hardware")
	assert_int_equal(counts.y, 0, "every triangle UV centroid samples baked coverage")

func _check(node: Node, coverage: Image) -> Vector2i:
	var counts := Vector2i.ZERO
	if node is MeshInstance3D:
		for surface: int in range(node.mesh.get_surface_count()):
			var arrays: Array = node.mesh.surface_get_arrays(surface)
			var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			for triangle: int in range(0, indices.size(), 3):
				var uv := (uvs[indices[triangle]] + uvs[indices[triangle + 1]] + uvs[indices[triangle + 2]]) / 3
				var pixel := Vector2i(floori(uv.x * coverage.get_width()), floori(uv.y * coverage.get_height()))
				counts.x += 1
				if pixel.x < 0 or pixel.y < 0 or pixel.x >= coverage.get_width() or pixel.y >= coverage.get_height() or coverage.get_pixelv(pixel).r == 0:
					if counts.y < 8: print("UNCOVERED node=%s triangle=%d uv=%s" % [node.name, triangle / 3, uv])
					counts.y += 1
	for child: Node in node.get_children(): counts += _check(child, coverage)
	return counts
