class_name BayCeiling
extends Node3D

const PANEL_DIR := "res://assets/props/bay-ceiling/"
const VARIANTS := [&"intact", &"subtlewarp", &"sag", &"torncorner", &"brokenedge"]
const CELL_X := 1.2
const CELL_Z := 0.6
const PANEL_SCALE := Vector3.ONE
const PANEL_Y := 2.99
const PANEL_LENGTH := 1.18
const PANEL_WIDTH := 0.58
const EMPTY_CELLS := [Vector2i(3, 8)]
const DAMAGE := {
Vector2i(3, 9): &"brokenedge", Vector2i(2, 8): &"sag"
}

static func layout() -> Array[Dictionary]:
	return _layout(service_bounds())

static func _layout(obstacles: Array[AABB]) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for iz in range(12):
		for ix in range(10):
			var cell := Vector2i(ix, iz)
			if EMPTY_CELLS.has(cell): continue
			var variant: StringName = DAMAGE.get(cell, &"intact")
			var position := Vector3(-5.4 + ix * CELL_X, PANEL_Y, -3.3 + iz * CELL_Z)
			var basis := Basis.IDENTITY
			var pose := Transform3D(basis, position)
			# This envelope includes the deepest kit variant and all four hardware heads.
			if not _clear(pose * AABB(Vector3(-PANEL_LENGTH / 2, -0.056, -PANEL_WIDTH / 2), Vector3(PANEL_LENGTH, 0.07, PANEL_WIDTH)), obstacles): continue
			result.append({"cell": cell, "variant": variant, "position": position, "pose": pose})
	return result

static func service_bounds() -> Array[AABB]:
	var ship := ShipLayout.authored().layout
	var services := CeilingServices.build(ship, ship.bay())
	var boxes: Array[AABB] = []
	for pose: Transform3D in services.heads: boxes.append(pose * CeilingProps.mesh(&"sprinkler").get_aabb())
	var pipe_bounds := CeilingProps._pipe_mesh().get_aabb()
	for pose: Transform3D in services.pipes + services.tees: boxes.append(pose * pipe_bounds)
	for pose: Transform3D in services.clips: boxes.append(pose * AABB(-Vector3.ONE / 2, Vector3.ONE))
	for row: Dictionary in services.detectors: boxes.append(row.bounds)
	for fixture: ShipLayout.EmergencyFixtureSpec in ship.bay().emergency_fixtures(ship.bay().template()):
		boxes.append(fixture.frame * AABB(-Lighting.LENS_SIZE / 2, Lighting.LENS_SIZE))
		boxes.append(fixture.frame * AABB(Vector3(-0.0225, 0, -0.0225), Vector3(0.045, 3.2 - fixture.frame.origin.y, 0.045)))
	var fixture_bounds: Array[AABB] = []
	var fixture_asset := CeilingFixture.ASSET.instantiate() as Node3D
	_collect_fixture_bounds(fixture_asset, Transform3D.IDENTITY, fixture_bounds)
	fixture_asset.free()
	assert(not fixture_bounds.is_empty(), "generated ceiling fixture has rendered mesh bounds")
	var fixture_box := fixture_bounds[0]
	for box: AABB in fixture_bounds.slice(1): fixture_box = fixture_box.merge(box)
	for frame: Transform3D in ship.bay().regular_light_frames():
		var mount := frame
		mount.origin.y = Pods.ROOM_CEILING_HEIGHT
		var body := mount * fixture_box
		boxes.append(body)
		# Reserve the sightline beneath the slab-mounted beam as a fitted service aperture.
		boxes.append(AABB(Vector3(body.position.x, PANEL_Y - 0.06, body.position.z), Vector3(body.size.x, body.position.y - PANEL_Y + 0.06, body.size.z)))
	# CeilingVent nodes are audio emitters in the plenum, not solid housings.
	# Air passes through the normal perforated panels at those four cells.
	return boxes

static func _collect_fixture_bounds(node: Node, parent: Transform3D, bounds: Array[AABB]) -> void:
	var pose := parent
	if node is Node3D: pose *= (node as Node3D).transform
	if node is MeshInstance3D:
		var mesh_node := node as MeshInstance3D
		bounds.append(pose * mesh_node.mesh.get_aabb())
	for child: Node in node.get_children(): _collect_fixture_bounds(child, pose, bounds)

static func _clear(box: AABB, obstacles: Array[AABB]) -> bool:
	for obstacle: AABB in obstacles:
		if box.intersects(obstacle.grow(0.003)): return false
	return true

static func build() -> BayCeiling:
	var ceiling := BayCeiling.new()
	ceiling.name = "BayCeiling"
	var panels: Dictionary = {}
	var hardware: Dictionary = {}
	var metal_material := _hardware_material()
	var obstacles := service_bounds()
	var placements := _layout(obstacles)
	for variant: StringName in VARIANTS:
		var packed := load(PANEL_DIR + String(variant) + ".glb") as PackedScene
		assert(packed != null, "bay ceiling panel export must import: " + String(variant))
		var imported := packed.instantiate()
		var meshes: Array[MeshInstance3D] = []
		_collect_meshes(imported, Transform3D.IDENTITY, meshes)
		var panel_arrays := []
		var hardware_arrays := []
		for mesh_node: MeshInstance3D in meshes:
			assert(mesh_node.mesh != null, "imported bay ceiling mesh has mesh data")
			var transform := mesh_node.transform
			var into_hardware := String(mesh_node.name).contains("mount_head")
			var arrays: Array = mesh_node.mesh.surface_get_arrays(0)
			var target: Array = hardware_arrays if into_hardware else panel_arrays
			var at := target.size()
			target.resize(at + 2)
			target[at] = arrays
			target[at + 1] = transform
		assert(meshes.size() == 5 and panel_arrays.size() > 0 and hardware_arrays.size() == 8, "each fitted panel must provide one body and four mount heads")
		panels[variant] = _merge_surfaces(panel_arrays, BayCeilingMaterial.material_for_variant(variant))
		hardware[variant] = _merge_surfaces(hardware_arrays, metal_material)
		for mesh_node: MeshInstance3D in meshes: mesh_node.free()
		imported.free()
	for variant: StringName in VARIANTS:
		var cells := placements.filter(func(row: Dictionary) -> bool: return row.variant == variant)
		_add_instances(ceiling, "Panel_" + String(variant), panels[variant], cells)
		_add_instances(ceiling, "MountHeads_" + String(variant), hardware[variant], cells)
	ceiling.add_child(_carrier(metal_material, placements, obstacles))
	ceiling.add_child(_service_cassettes(metal_material, placements, obstacles))
	return ceiling

static func _collect_meshes(node: Node, parent_transform: Transform3D, result: Array[MeshInstance3D]) -> void:
	var local := parent_transform
	if node is Node3D: local = parent_transform * (node as Node3D).transform
	if node is MeshInstance3D:
		var copy := MeshInstance3D.new()
		copy.name = node.name
		copy.mesh = node.mesh
		copy.transform = local
		result.append(copy)
	for child: Node in node.get_children(): _collect_meshes(child, local, result)

static func _merge_surfaces(parts: Array, material: Material) -> ArrayMesh:
	var output := ArrayMesh.new()
	for part_index in range(0, parts.size(), 2):
		var arrays: Array = parts[part_index]
		var transform: Transform3D = parts[part_index + 1]
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		for index in range(vertices.size()):
			vertices[index] = transform * vertices[index]
			if normals.size() == vertices.size(): normals[index] = transform.basis.inverse().transposed() * normals[index]
		arrays[Mesh.ARRAY_VERTEX] = vertices
		arrays[Mesh.ARRAY_NORMAL] = normals
		output.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		output.surface_set_material(output.get_surface_count() - 1, material)
	assert(output.get_surface_count() > 0, "merged bay ceiling mesh has surfaces")
	return output

static func _add_instances(parent: Node3D, node_name: String, mesh: Mesh, cells: Array[Dictionary]) -> void:
	var poses: Array[Transform3D] = []
	for cell: Dictionary in cells: poses.append(cell.pose)
	_batch(parent, node_name, mesh, poses)

static func _hardware_material() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.95, 0.92, 0.86)
	material.albedo_texture = BayCeilingMaterial.ALBEDO[&"intact"]
	material.metallic = 0.62
	material.roughness = 0.78
	material.roughness_texture = BayCeilingMaterial.ROUGHNESS[&"intact"]
	return material
static func _mount_anchors() -> Dictionary:
	var file := FileAccess.open(PANEL_DIR + "manifest.json", FileAccess.READ)
	assert(file != null, "fitted bay ceiling manifest must be available")
	var manifest: Variant = JSON.parse_string(file.get_as_text())
	assert(manifest is Dictionary and manifest.has("variants"), "fitted bay ceiling manifest has variant metadata")
	var anchors: Dictionary = {}
	for variant: StringName in VARIANTS:
		var row: Dictionary = manifest.variants.get(String(variant), {})
		assert(row.has("attachment_underside_points_gltf_m"), "variant mount anchors exist: " + String(variant))
		var points: Array = row.attachment_underside_points_gltf_m
		assert(points.size() == 4, "variant has four measured mount seats: " + String(variant))
		var converted: Array[Vector3] = []
		for point: Array in points:
			assert(point.size() == 3, "mount seat is a three-axis point")
			converted.append(Vector3(float(point[0]), float(point[1]), float(point[2])))
		anchors[variant] = converted
	return anchors


static func _carrier(material: StandardMaterial3D, placements: Array[Dictionary], obstacles: Array[AABB]) -> Node3D:
	var root := Node3D.new()
	root.name = "CarrierGrid"
	var mesh := BoxMesh.new()
	mesh.material = material
	mesh.size = Vector3.ONE
	var cross: Array[Transform3D] = []
	var longs: Array[Transform3D] = []
	var slab: Array[Transform3D] = []
	var seat_cross_webs: Array[Transform3D] = []
	var seat_long_webs: Array[Transform3D] = []
	var seat_cross_ledges: Array[Transform3D] = []
	var seat_long_ledges: Array[Transform3D] = []
	for iz in range(13):
		var z := -3.6 + iz * CELL_Z
		cross.append_array(_rail_segments(Vector3(0, 3.12, z), Vector3(12, 0.055, 0.055), 0, obstacles))
		seat_cross_webs.append_array(_rail_segments(Vector3(0, 3.04025, z), Vector3(12, 0.1045, 0.016), 0, obstacles))
		var cross_spans: Array[Vector2] = [Vector2(-6.0, 6.0)]
		if iz == 9: cross_spans = [Vector2(-6.0, -2.4), Vector2(-1.2, 6.0)]
		seat_cross_ledges.append_array(_cross_ledge_segments(z, cross_spans, obstacles))
		for ix in range(11):
			var x := clampf(-6.0 + ix * CELL_X, -5.9725, 5.9725)
			var pose := _box_pose(Vector3(x, 3.17375, z), Vector3(0.04, 0.0525, 0.04))
			if _clear(pose * mesh.get_aabb(), obstacles): slab.append(pose)
	for ix in range(11):
		var x := clampf(-6.0 + ix * CELL_X, -5.9725, 5.9725)
		longs.append_array(_rail_segments(Vector3(x, 3.12, 0), Vector3(0.055, 0.055, 7.255), 2, obstacles))
		var boundary := -6.0 + ix * CELL_X
		var edge := ix == 0 or ix == 10
		var inward := 1.0 if ix == 0 else -1.0
		var web_x := boundary + inward * 0.004 if edge else boundary
		var ledge_x := boundary + inward * 0.009 if edge else boundary
		seat_long_webs.append_array(_rail_segments(Vector3(web_x, 3.04025, 0), Vector3(0.008 if edge else 0.016, 0.1045, 7.2), 2, obstacles))
		seat_long_ledges.append_array(_rail_segments(Vector3(ledge_x, 2.9865, 0), Vector3(0.018 if edge else 0.036, 0.003, 7.2), 2, obstacles))
	_batch(root, "SupportedCrossRails", mesh, cross)
	_batch(root, "SupportedLongRails", mesh, longs)
	_batch(root, "RailSlabHangers", mesh, slab)
	_batch(root, "SeatCrossWebs", mesh, seat_cross_webs)
	_batch(root, "SeatLongWebs", mesh, seat_long_webs)
	_batch(root, "PanelSupportLedgersCross", mesh, seat_cross_ledges)
	_batch(root, "PanelSupportLedgersLong", mesh, seat_long_ledges)
	var failure := MeshInstance3D.new()
	failure.name = "BrokenEdgeFrameRail"
	failure.mesh = _failed_ledge(material)
	root.add_child(failure)
	return root

static func _cross_ledge_segments(z: float, spans: Array[Vector2], obstacles: Array[AABB]) -> Array[Transform3D]:
	for ix in range(11):
		var boundary := -6.0 + ix * CELL_X
		var edge := ix == 0 or ix == 10
		var inward := 1.0 if ix == 0 else -1.0
		var ledger_x := boundary + inward * 0.009 if edge else boundary
		var half_width := 0.009 if edge else 0.018
		var cut := Vector2(ledger_x - half_width, ledger_x + half_width)
		var remaining: Array[Vector2] = []
		for span: Vector2 in spans:
			if cut.y <= span.x or cut.x >= span.y:
				remaining.append(span)
				continue
			if cut.x > span.x: remaining.append(Vector2(span.x, cut.x))
			if cut.y < span.y: remaining.append(Vector2(cut.y, span.y))
		spans = remaining
	var result: Array[Transform3D] = []
	for span: Vector2 in spans:
		var center := (span.x + span.y) / 2
		var size := span.y - span.x
		result.append_array(_rail_segments(Vector3(center, 2.9865, z), Vector3(size, 0.003, 0.036), 0, obstacles))
	return result

static func _failed_ledge(material: Material) -> ArrayMesh:
	# A torn lower lip bows between retained ends. The upper carrier stays connected.
	var sections: Array[Vector3] = []
	for index in range(61):
		# Long ledgers own the junction footprint; flat end caps butt against their sides.
		var x := clampf(-0.6 + index * 0.02, -CELL_X / 2 + 0.018, CELL_X / 2 - 0.018)
		var bow := pow(maxf(0.0, 1.0 - pow(x / 0.22, 2)), 2) * 0.038
		for corner: Vector2 in [Vector2(-0.018, 0), Vector2(0.018, 0), Vector2(0.018, -0.003), Vector2(-0.018, -0.003)]:
			sections.append(Vector3(-1.8 + x, 2.988 - bow + corner.y, 1.8 + corner.x))
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	surface.set_material(material)
	for index in range(60):
		for side in range(4):
			var a := index * 4 + side
			var b := index * 4 + (side + 1) % 4
			for vertex: int in [a, b, b + 4, a, b + 4, a + 4]:
				surface.set_uv(Vector2(sections[vertex].x / 1.18, sections[vertex].z / 0.58))
				surface.add_vertex(sections[vertex])
	for vertex: int in [0, 2, 1, 0, 3, 2, 240, 241, 242, 240, 242, 243]:
		surface.set_uv(Vector2(sections[vertex].y, sections[vertex].z))
		surface.add_vertex(sections[vertex])
	surface.generate_normals()
	surface.index()
	return surface.commit()

static func _rail_segments(center: Vector3, size: Vector3, axis: int, obstacles: Array[AABB]) -> Array[Transform3D]:
	var intervals: Array[Vector2] = [Vector2(center[axis] - size[axis] / 2, center[axis] + size[axis] / 2)]
	var full := AABB(center - size / 2, size)
	for obstacle: AABB in obstacles:
		var cut := obstacle.grow(0.006)
		if not full.intersects(cut): continue
		var remaining: Array[Vector2] = []
		for span: Vector2 in intervals:
			if cut.end[axis] <= span.x or cut.position[axis] >= span.y: remaining.append(span); continue
			if cut.position[axis] > span.x: remaining.append(Vector2(span.x, cut.position[axis]))
			if cut.end[axis] < span.y: remaining.append(Vector2(cut.end[axis], span.y))
		intervals = remaining
	var result: Array[Transform3D] = []
	for span: Vector2 in intervals:
		var midpoint := center
		var extent := size
		midpoint[axis] = (span.x + span.y) / 2
		extent[axis] = span.y - span.x
		result.append(_box_pose(midpoint, extent))
	return result

static func _service_cassettes(material: StandardMaterial3D, placements: Array[Dictionary], obstacles: Array[AABB]) -> Node3D:
	var root := Node3D.new()
	root.name = "ServiceCassettes"
	var mesh := BoxMesh.new()
	mesh.size = Vector3.ONE
	mesh.material = material
	var occupied: Dictionary = {}
	for row: Dictionary in placements: occupied[row.cell] = true
	for iz in range(12):
		for ix in range(10):
			var cell := Vector2i(ix, iz)
			if occupied.has(cell) or EMPTY_CELLS.has(cell): continue
			var center := Vector3(-5.4 + ix * CELL_X, 2.989, -3.3 + iz * CELL_Z)
			var plate := AABB(center - Vector3(0.59, 0.001, 0.29), Vector3(1.18, 0.002, 0.58))
			var pieces: Array[Transform3D] = []
			var cuts: Array[AABB] = []
			for obstacle: AABB in obstacles:
				if obstacle.position.y < 3.07 and obstacle.end.y > 2.97:
					cuts.append(AABB(Vector3(obstacle.position.x - 0.003, 2.95, obstacle.position.z - 0.003), Vector3(obstacle.size.x + 0.006, 0.13, obstacle.size.z + 0.006)))
			for box: AABB in _cut_plate(plate, cuts): pieces.append(_box_pose(box.get_center(), box.size))
			# Folded returns stiffen the service sheet inside its flat bearing flange.
			for side: int in [-1, 1]:
				for size: Vector3 in [Vector3(1.136, 0.018, 0.002), Vector3(0.002, 0.018, 0.54)]:
					var offset := Vector3(0, -0.010, side * 0.269) if size.x > 1 else Vector3(side * 0.569, -0.010, 0)
					for box: AABB in _cut_plate(AABB(center + offset - size / 2, size), cuts): pieces.append(_box_pose(box.get_center(), box.size))
			_batch(root, "Cassette_%d_%d" % [ix, iz], mesh, pieces)
	return root

static func _cut_plate(plate: AABB, cuts: Array[AABB]) -> Array[AABB]:
	var pieces: Array[AABB] = [plate]
	for cut: AABB in cuts:
		var remainder: Array[AABB] = []
		for piece: AABB in pieces:
			if not piece.intersects(cut):
				remainder.append(piece)
				continue
			var hole := piece.intersection(cut)
			for limits: Vector4 in [Vector4(piece.position.x, hole.position.x, piece.position.z, piece.end.z), Vector4(hole.end.x, piece.end.x, piece.position.z, piece.end.z), Vector4(hole.position.x, hole.end.x, piece.position.z, hole.position.z), Vector4(hole.position.x, hole.end.x, hole.end.z, piece.end.z)]:
				if limits.y - limits.x > 0.00001 and limits.w - limits.z > 0.00001:
					remainder.append(AABB(Vector3(limits.x, piece.position.y, limits.z), Vector3(limits.y - limits.x, piece.size.y, limits.w - limits.z)))
		pieces = remainder
	return pieces

static func _box_pose(center: Vector3, size: Vector3) -> Transform3D:
	return Transform3D(Basis.from_scale(size), center)

static func _batch(parent: Node3D, node_name: String, mesh: Mesh, poses: Array[Transform3D]) -> void:
	var node := MultiMeshInstance3D.new()
	node.name = node_name
	var data := MultiMesh.new()
	data.transform_format = MultiMesh.TRANSFORM_3D
	data.mesh = mesh
	data.instance_count = poses.size()
	var bounds := AABB()
	for index in range(poses.size()):
		data.set_instance_transform(index, poses[index])
		var box := poses[index] * mesh.get_aabb()
		bounds = box if index == 0 else bounds.merge(box)
	data.custom_aabb = bounds
	node.multimesh = data
	parent.add_child(node)
