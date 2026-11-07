extends SimTestCase

const IDS: Array[StringName] = [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]
const Exporter := preload("res://tools/export_hatch_parts.gd")

func _plate(row: Dictionary) -> Dictionary:
	for group: Dictionary in row.groups:
		for part: Dictionary in group.parts:
			if part.id == ("ForeSteel/plate" if row.hinge_sign > 0 else "AftSteel/plate"):
				var result := part.duplicate(true)
				result.group_transform = group.transform
				return result
	assert_true(false, "export contains the solid front slab")
	return {}

func _measure(row: Dictionary, imported: bool) -> Dictionary:
	var ring_front := INF
	var widths: Array[float] = []
	var meshes: Dictionary = {}
	var scene: Node
	if imported:
		scene = (load(HatchAsset.SOURCE) as PackedScene).instantiate()
		_collect(scene, meshes)
	var into := float(row.hinge_sign)
	for solid: Dictionary in row.frame_solids:
		if not "/RING/" in solid.id: continue
		var pose := HatchAsset.pose(solid.transform)
		var a := Vector2(solid.section[0][0], solid.section[0][1])
		var b := Vector2(solid.section[1][0], solid.section[1][1])
		var tangent := (b - a).normalized()
		var points: Array[Vector3] = []
		if imported:
			for name: String in HatchAsset.document().nodes:
				var node: Dictionary = HatchAsset.document().nodes[name]
				if node.kind == "frame" and int(node.variant) == int(row.index) and node.id == solid.id:
					for vertex: Vector3 in meshes[name].surface_get_arrays(0)[Mesh.ARRAY_VERTEX]: points.append(pose * vertex)
		else:
			for vertex: Array in solid.vertices: points.append(pose * HatchAsset.vector(vertex))
		var band_min := INF
		var band_max := -INF
		for point: Vector3 in points:
			var local := pose.affine_inverse() * point
			var across := tangent.cross(Vector2(local.x, local.y) - a)
			band_min = minf(band_min, across)
			band_max = maxf(band_max, across)
			var depth := point.z if into > 0 else ShipLayout.WALL - point.z
			ring_front = minf(ring_front, depth)
		widths.append(band_max - band_min)
	var plate := _plate(row)
	var plate_bounds := AABB(-HatchAsset.vector(plate.size) / 2, HatchAsset.vector(plate.size))
	if imported:
		for name: String in HatchAsset.document().nodes:
			var node: Dictionary = HatchAsset.document().nodes[name]
			if node.kind == "leaf" and int(node.variant) == int(row.index) and node.id == plate.id:
				plate_bounds = meshes[name].get_aabb()
	var plate_pose := HatchAsset.pose(row.hinge_transform) * HatchAsset.pose(plate.group_transform) * HatchAsset.pose(plate.transform)
	var front := (plate_pose * Vector3(0, 0, plate_bounds.position.z)).z
	if into < 0: front = ShipLayout.WALL - front
	var reveal := (float(row.aperture[0]) + 0.01 - plate_bounds.size.x) / 2
	var result := {"band_min": widths.min(), "band_max": widths.max(), "protrusion": -ring_front, "flushness": absf(front - ring_front), "reveal": reveal, "solid_edge": plate_bounds.size.z}
	if scene != null: scene.free()
	return result

func _collect(node: Node, meshes: Dictionary) -> void:
	if node is MeshInstance3D: meshes[String(node.name)] = node.mesh
	for child: Node in node.get_children(): _collect(child, meshes)

func _check(imported: bool) -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var row: Dictionary = HatchAsset.variant(spec) if imported else Exporter.variant(spec, 0)
		var values := _measure(row, imported)
		print("HATCH_PROPORTIONS %s imported=%s %s" % [id, imported, JSON.stringify(values)])
		# Andrew changed the design on 2026-11-05: narrow raised bead and a flush,
		# heavy slab replace the old 160 mm ring and 100 mm face plates.
		assert_float_in_range(values.band_min, 0.08 - 0.000001, 0.10 + 0.000001, "ring minimum band")
		assert_float_in_range(values.band_max, 0.08 - 0.000001, 0.10 + 0.000001, "ring maximum band")
		assert_float_in_range(values.protrusion, 0, 0.06 + 0.000001, "raised ring protrusion")
		assert_true(values.flushness <= 0.03 + 0.000001, "leaf face sits within 30 mm of ring")
		assert_true(values.reveal <= 0.02 + 0.000001, "front-view edge gap is at most 20 mm")
		assert_true(values.solid_edge >= 0.16 - 0.000001, "solid slab, excluding skins and laps, is at least 160 mm")

func test_exported_proportions_match_the_concept_dimensions() -> void: _check(false)
func test_imported_proportions_match_the_concept_dimensions() -> void: _check(true)

func test_generated_ring_uses_only_visible_front_relief() -> void:
	# Driver decision after the contract stop: fit the visible source relief
	# into 22 mm, keeping 2 mm margin inside the unchanged flushness limit.
	assert_float_equal(ShipGeometry.HATCH_RING_FRONT, -0.028, "generated bead stands 28 mm proud")
	var geometry_script: GDScript = load("res://sim/ship_geometry.gd")
	assert_false(geometry_script.get_script_constant_map().has("HATCH_RING_BACK"), "no ring reservation behind its original rear plane")
	assert_float_equal(ShipGeometry.HATCH_RING_REAR, -0.006, "existing pocket sealing seat stays fixed")

func test_unused_fixed_surface_api_is_absent() -> void:
	assert_false(HatchModel.new().has_method("fixed_surface"), "merged surround is the only fixed assembly path")
