extends SimTestCase

func test_painted_depth_faces_have_nondegenerate_uv2_within_four_to_one_density() -> void:
	var packed: PackedScene = load(HatchAsset.SOURCE)
	var scene := packed.instantiate()
	var counts := _check(scene)
	scene.free()
	print("HATCH_DEPTH_UV checked=%d invalid=%d" % [counts.x, counts.y])
	assert_true(counts.x > 500, "check painted leaf and fixed-frame depth triangles in both variants")
	assert_int_equal(counts.y, 0, "painted depth UV2 has two nonzero axes and at most 4x texel-density anisotropy")

func _check(node: Node) -> Vector2i:
	var counts := Vector2i.ZERO
	if node is MeshInstance3D:
		var arrays: Array = node.mesh.surface_get_arrays(0)
		var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV2]
		var colours: PackedColorArray = arrays[Mesh.ARRAY_COLOR]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var normal_basis := Surfaces.world_frame(node).basis.inverse().transposed()
		for triangle: int in range(0, indices.size(), 3):
			var a := indices[triangle]
			var b := indices[triangle + 1]
			var c := indices[triangle + 2]
			if maxf(colours[a].r, colours[a].b) < 0.5: continue
			var edge := points[b] - points[a]
			var other := points[c] - points[a]
			var normal := edge.cross(other).normalized()
			if absf((normal_basis * normal).normalized().z) > 0.9: continue
			counts.x += 1
			var tangent := edge.normalized()
			var across := normal.cross(tangent)
			var height := other.dot(across)
			# The wider cells retain density for Andrew's larger, forward leaf.
			var atlas_size := Surfaces.HATCH_PAINTED.get_size()
			var texels := atlas_size * Vector2(0.5, 0.53125) if colours[a].r > 0.5 else atlas_size * Vector2(1, 0.46875)
			var du := (uvs[b] - uvs[a]) * texels / edge.length()
			var dv := ((uvs[c] - uvs[a]) * texels - du * other.dot(tangent)) / height
			var trace := du.length_squared() + dv.length_squared()
			var determinant := du.cross(dv)
			var discriminant := sqrt(maxf(0, trace * trace - 4 * determinant * determinant))
			var largest := (trace + discriminant) / 2
			var smallest := determinant * determinant / maxf(largest, 0.000001)
			if smallest <= 0.000001 or largest / smallest > 16.0001:
				if counts.y < 4: print("HATCH_DEPTH_UV_INVALID node=%s triangle=%d singular_ratio=%.4f" % [node.name, triangle / 3, sqrt(largest / maxf(smallest, 0.000001))])
				counts.y += 1
	for child: Node in node.get_children(): counts += _check(child)
	return counts
