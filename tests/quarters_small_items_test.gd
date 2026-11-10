extends SimTestCase

const ITEMS := {
	"photo_frame": "photo_frame", "boots": "boots", "hairbrush": "hairbrush", "jewellery_box": "jewellery_box",
	"medal_case": "medal_case", "data_tablet_1": "data_tablet", "data_tablet_2": "data_tablet",
	"mug_1": "mug", "mug_2": "mug", "plate_1": "plate", "plate_2": "plate",
}
const SUPPORTS := {
	"photo_frame": ["bedside_r", "Top"], "hairbrush": ["bedside_l", "Top"], "jewellery_box": ["bedside_l", "Top"],
	"medal_case": ["desk", "Worktop"], "data_tablet_2": ["desk", "Worktop"], "data_tablet_1": ["sofa", "SeatCushion_C"],
	"mug_1": ["dining_table", "Top"], "mug_2": ["dining_table", "Top"],
	"plate_1": ["dining_table", "Top"], "plate_2": ["dining_table", "Top"],
}

func test_small_items_use_real_state_assets_and_shared_placements() -> void:
	var clean := QuartersFurnishings.build(&"as_built")
	var aged := QuartersFurnishings.build(&"aged")
	for id: String in ITEMS:
		assert_false(clean.has_node("Standin_" + id) or aged.has_node("Standin_" + id), "replaced stand-in removed: " + id)
		var remembered := clean.get_node_or_null("Item_" + id) as Node3D
		var present := aged.get_node_or_null("Item_" + id) as Node3D
		assert_true(remembered != null and present != null, "both real placements: " + id)
		if remembered == null or present == null: continue
		assert_true(remembered.transform == present.transform, "same placement root: " + id)
		if id != "data_tablet_1":
			assert_true(remembered.get_child(0).transform == present.get_child(0).transform, "same rigid-support asset transform: " + id)
		for pair: Array in [[remembered, ".glb"], [present, "_aged.glb"]]:
			var asset := pair[0].get_child(0) as Node3D
			assert_true(asset.scene_file_path == QuartersFurnishings.ROOT + ITEMS[id] + pair[1], "correct state GLB: " + id)
			assert_true(asset.scale.is_equal_approx(Vector3.ONE), "real asset dimensions retained: " + id)
	assert_true(clean.has_node("Standin_her_jacket") and aged.has_node("Standin_her_jacket"), "jacket stand-in retained")
	for root: Node3D in [clean, aged]:
		assert_true(root.has_node("Placement_wardrobe/Standin_her_dress_1") and root.has_node("Placement_wardrobe/Standin_her_dress_2"), "dress stand-ins retain names")
		assert_false(root.find_children("Standin_storage_*", "", true, false).is_empty(), "storage stand-in names retained")
	clean.free()
	aged.free()

func test_small_items_contact_real_support_without_furniture_or_item_clipping() -> void:
	for state: StringName in QuartersProps.STATES:
		var root := QuartersFurnishings.build(state)
		var placed: Array[AABB] = []
		for id: String in ITEMS:
			var item := root.get_node_or_null("Item_" + id) as Node3D
			assert_true(item != null, "real item: " + id)
			if item == null: continue
			var bounds := QuartersFurnishings._bounds(item)
			if id == "boots":
				assert_float_in_range(bounds.position.y - QuartersLayout.FLOOR_Y, 0.0, 0.002, "boots contact floor")
			else:
				var support: Array = SUPPORTS[id]
				var furniture := root.get_node("Placement_" + support[0])
				var mesh := furniture.find_child(support[1], true, false) as MeshInstance3D
				var top := ShipScene._world_frame(mesh) * mesh.get_aabb()
				# Curved cloth requires triangle contact, not its whole-mesh AABB crown.
				var height := _surface_height(mesh, bounds) if id == "data_tablet_1" else top.end.y
				assert_float_in_range(bounds.position.y - height, 0.0, 0.002, "%s %s contacts support" % [state, id])
				assert_true(bounds.position.x >= top.position.x and bounds.end.x <= top.end.x and bounds.position.z >= top.position.z and bounds.end.z <= top.end.z, "item inside support footprint: " + id)
				if support[0] == "dining_table":
					for corner: Vector3 in _bottom_corners(bounds):
						var delta := corner - top.get_center()
						assert_true(Vector2(delta.x, delta.z).length() < top.size.x / 2, "item inside round table: " + id)
			for prop: Node3D in root.get_children():
				if not String(prop.name).begins_with("Placement_"): continue
				for mesh: MeshInstance3D in prop.find_children("*", "MeshInstance3D", true, false):
					if bounds.intersects(ShipScene._world_frame(mesh) * mesh.get_aabb()):
						assert_false(_mesh_intersects_box(mesh, bounds), "%s clears actual triangles of %s/%s" % [id, prop.name, mesh.name])
			for other: AABB in placed: assert_false(bounds.intersects(other), "small items do not overlap: " + id)
			placed.append(bounds)
		root.free()

func test_small_items_keep_their_imported_materials_except_simple_frame_glass() -> void:
	for state: StringName in QuartersProps.STATES:
		var root := QuartersFurnishings.build(state)
		for id: String in ITEMS:
			var item := root.get_node_or_null("Item_" + id)
			assert_true(item != null, "real material source: " + id)
			if item == null: continue
			for mesh: MeshInstance3D in item.find_children("*", "MeshInstance3D", true, false):
				assert_true(mesh.material_override == null, "no whole-mesh override: " + id)
				for surface: int in range(mesh.mesh.get_surface_count()):
					var imported := mesh.mesh.surface_get_material(surface)
					var finish := mesh.get_active_material(surface)
					if id == "photo_frame" and imported.resource_name == "Glass":
						assert_true(finish is StandardMaterial3D, "simple frame glass")
						assert_true(is_equal_approx(finish.roughness, 0.07), "glossy like view screen")
						assert_int_equal(finish.transparency, BaseMaterial3D.TRANSPARENCY_ALPHA, "alpha glass")
					else: assert_true(finish == imported, "authored material preserved: " + id)
		root.free()

func _surface_height(mesh: MeshInstance3D, bounds: AABB) -> float:
	var frame := ShipScene._world_frame(mesh)
	var highest := -INF
	var faces := mesh.mesh.get_faces()
	for z: int in range(11):
		for x: int in range(11):
			var origin := Vector3(lerpf(bounds.position.x, bounds.end.x, x / 10.0), bounds.end.y + 1, lerpf(bounds.position.z, bounds.end.z, z / 10.0))
			for index: int in range(0, faces.size(), 3):
				var hit = Geometry3D.ray_intersects_triangle(origin, Vector3.DOWN, frame * faces[index], frame * faces[index + 1], frame * faces[index + 2])
				if hit != null: highest = maxf(highest, hit.y)
	return highest

func _bottom_corners(bounds: AABB) -> Array[Vector3]:
	return [bounds.position, Vector3(bounds.end.x, bounds.position.y, bounds.position.z), Vector3(bounds.position.x, bounds.position.y, bounds.end.z), Vector3(bounds.end.x, bounds.position.y, bounds.end.z)]

func _mesh_intersects_box(mesh: MeshInstance3D, bounds: AABB) -> bool:
	var frame := ShipScene._world_frame(mesh)
	var faces := mesh.mesh.get_faces()
	var centre := bounds.get_center()
	var half := bounds.size / 2
	for index: int in range(0, faces.size(), 3):
		var a := frame * faces[index] - centre
		var b := frame * faces[index + 1] - centre
		var c := frame * faces[index + 2] - centre
		var axes: Array[Vector3] = [Vector3.RIGHT, Vector3.UP, Vector3.BACK, (b - a).cross(c - a)]
		for edge: Vector3 in [b - a, c - b, a - c]:
			for axis: Vector3 in [Vector3.RIGHT, Vector3.UP, Vector3.BACK]: axes.append(edge.cross(axis))
		var separated := false
		for axis: Vector3 in axes:
			if axis.length_squared() < 1e-16: continue
			axis = axis.normalized()
			var radius := axis.abs().dot(half)
			var low := minf(a.dot(axis), minf(b.dot(axis), c.dot(axis)))
			var high := maxf(a.dot(axis), maxf(b.dot(axis), c.dot(axis)))
			if low > radius or high < -radius:
				separated = true
				break
		if not separated: return true
	return false
