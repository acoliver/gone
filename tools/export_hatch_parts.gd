extends SceneTree
## Export simulation-owned reservations, not presentation meshes.

static func vector3(value: Vector3) -> Array:
	return [value.x, value.y, value.z]

static func vector2(value: Vector2) -> Array:
	return [value.x, value.y]

static func pose(value: Transform3D) -> Dictionary:
	return {"basis": [vector3(value.basis.x), vector3(value.basis.y), vector3(value.basis.z)], "origin": vector3(value.origin)}

static func polygon(value: PackedVector2Array) -> Array:
	var result: Array = []
	for point: Vector2 in value: result.append(vector2(point))
	return result

static func frame_geometry(door: ShipLayout.DoorSpec, solid: ShipGeometry.SolidSpec) -> Dictionary:
	var vertices: Array = []
	var faces: Array = []
	if "/HINGE/KNUCKLE-" in String(solid.id) or "/HINGE/CAP-" in String(solid.id) or "/HINGE/BOLT-" in String(solid.id):
		var profile: Array[Vector2] = [Vector2(-0.5, 0.86), Vector2(-0.4, 1), Vector2(0.4, 1), Vector2(0.5, 0.86)]
		if "/HINGE/CAP-" in String(solid.id):
			profile = [Vector2(-0.5, 0.5), Vector2(-0.34, 0.5), Vector2(-0.30, 1), Vector2(0.20, 1), Vector2(0.36, 0.84), Vector2(0.5, 0.42)]
		for ring: Vector2 in profile:
			for index: int in range(8):
				var angle := index * TAU / 8
				vertices.append(vector3(Vector3(cos(angle) * solid.size.x * ring.y / 2, ring.x * solid.size.y, sin(angle) * solid.size.z * ring.y / 2)))
		faces.append([7, 6, 5, 4, 3, 2, 1, 0])
		var last := (profile.size() - 1) * 8
		faces.append([last, last + 1, last + 2, last + 3, last + 4, last + 5, last + 6, last + 7])
		for ring: int in range(profile.size() - 1):
			for index: int in range(8):
				var next := (index + 1) % 8
				faces.append([ring * 8 + index, ring * 8 + next, (ring + 1) * 8 + next, (ring + 1) * 8 + index])
		return {"vertices": vertices, "faces": faces}
	if solid.section.is_empty():
		for z: int in [-1, 1]:
			for y: int in [-1, 1]:
				for x: int in [-1, 1]:
					vertices.append(vector3(ShipGeometry.hatch_frame_vertex(door, solid, solid.size * Vector3(x, y, z) / 2)))
		faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
	else:
		var section := solid.section.duplicate()
		if Geometry2D.is_polygon_clockwise(section): section.reverse()
		var count := section.size()
		for z: int in [-1, 1]:
			for point: Vector2 in section:
				vertices.append(vector3(ShipGeometry.hatch_frame_vertex(door, solid, Vector3(point.x, point.y, z * solid.size.z / 2))))
		var triangles := Geometry2D.triangulate_polygon(section)
		for index: int in range(0, triangles.size(), 3):
			faces.append([triangles[index + 2], triangles[index + 1], triangles[index]])
			faces.append([triangles[index] + count, triangles[index + 1] + count, triangles[index + 2] + count])
		for index: int in range(count):
			var next := (index + 1) % count
			faces.append([index, next, next + count, index + count])
	if String(solid.id).ends_with("/STEP/000"):
		var bridge := ShipGeometry.hatch_floor_bridge(solid)
		var skin := frame_geometry(door, bridge)
		var relative := solid.transform.affine_inverse() * bridge.transform
		var start := vertices.size()
		for point: Array in skin.vertices:
			vertices.append(vector3(relative * Vector3(point[0], point[1], point[2])))
		for face: Array in skin.faces:
			var indices: Array = []
			for index: int in face: indices.append(start + index)
			faces.append(indices)
	return {"vertices": vertices, "faces": faces}

static func fitting_records(door: ShipLayout.DoorSpec, solids: Array[ShipGeometry.SolidSpec]) -> Dictionary:
	var fit := {"schema_version": 1, "coordinate_system": "godot_y_up", "ring": {"inner": [], "outer": [], "reservation_ids": []}, "leaf_faces": [], "wheel_axes": [], "labels": [], "hinge_stations": [], "required_seal_ids": []}
	for solid: ShipGeometry.SolidSpec in solids:
		var id := String(solid.id).trim_prefix(String(door.id()) + "/")
		if "/RING/" in id:
			fit.ring.inner.append(vector3(solid.transform * Vector3(solid.section[0].x, solid.section[0].y, 0)))
			fit.ring.outer.append(vector3(solid.transform * Vector3(solid.section[3].x, solid.section[3].y, 0)))
			fit.ring.reservation_ids.append(id)
		if id.begins_with("HINGE/KNUCKLE-"):
			fit.hinge_stations.append({"reservation_id": id, "transform": pose(solid.transform), "axis": vector3(solid.transform.basis.y), "size": vector3(solid.size)})
		if id.begins_with("FRAME/") or id == "COAMING" or "/LIP/" in id or "/THROAT/" in id or "/STEP/" in id:
			fit.required_seal_ids.append(id)
	for group: HatchParts.Group in HatchParts.leaf(door):
		if String(group.path) in ["Wheel", "ReverseWheel"]:
			fit.wheel_axes.append({"group": String(group.path), "transform": pose(group.transform), "axis": vector3(group.transform.basis.z)})
		for part: HatchParts.Part in group.parts:
			if String(part.id).ends_with("Steel/plate"):
				var local := group.transform * part.transform
				var face := local * Vector3(0, 0, -part.size.z / 2)
				fit.leaf_faces.append({"reservation_id": String(part.id), "side": group.side, "plane_origin": vector3(face), "plane_normal": vector3(-local.basis.z), "transform": pose(local), "size": vector3(part.size), "contour": polygon(part.contour)})
			if "Seal" in String(group.path): fit.required_seal_ids.append(String(part.id))
	var layout := ShipLayout.authored().layout
	for id: StringName in door.face_ids():
		var face := layout.face(id)
		fit.labels.append({"face_id": String(id), "transform": pose(face.leaf_label_frame(door)), "size": vector2(face.label_size())})
	return fit

static func variant(source: ShipLayout.DoorSpec, index: int) -> Dictionary:
	# Evaluate the shared recipe before large-world translation loses local precision.
	var door := ShipLayout.DoorSpec.new(source.id(), source.deck_number(), source.kind(), source.policy(), Transform3D.IDENTITY, source.aperture(), source.spaces(), source.face_ids(), source.owner_id(), source.animation(), source.has_wheel())
	var result := {"index": index, "door_id": String(door.id()), "hinge_sign": int(signf(door.hinge_frame().origin.z - ShipLayout.WALL / 2)), "aperture": vector2(door.aperture()), "leaf_aperture": vector2(door.leaf_aperture()), "hinge_transform": pose(door.hinge_frame()), "groups": [], "frame_solids": [], "frame_rivets": []}
	for group: HatchParts.Group in HatchParts.leaf(door):
		var row := {"index": result.groups.size(), "path": String(group.path), "transform": pose(group.transform), "side": group.side, "steel": group.steel, "parts": []}
		for part: HatchParts.Part in group.parts:
			row.parts.append({"index": row.parts.size(), "id": String(part.id), "shape": String(part.shape), "size": vector3(part.size), "transform": pose(part.transform), "radius": part.radius, "inner_radius": part.inner_radius, "contour": polygon(part.contour), "edge_bevel": part.edge_bevel, "paint_layer_depth": part.paint_layer_depth})
		result.groups.append(row)
	var solids := ShipGeometry.hatch_frame_solids(door)
	for solid: ShipGeometry.SolidSpec in solids:
		var row := frame_geometry(door, solid)
		row.merge({"index": result.frame_solids.size(), "id": String(solid.id).trim_prefix(String(door.id()) + "/"), "size": vector3(solid.size), "transform": pose(solid.transform), "section": polygon(solid.section)})
		result.frame_solids.append(row)
	# Derive both seating faces from the actual shared ring, rather than copying
	# presentation-only depth constants. The shallow inset leaves a domed head.
	var ring_min := INF
	var ring_max := -INF
	for solid: ShipGeometry.SolidSpec in solids:
		if not "/RING/" in String(solid.id): continue
		var relative := solid.transform
		for point: Vector2 in solid.section:
			for z: int in [-1, 1]:
				var portal := relative * Vector3(point.x, point.y, z * solid.size.z / 2)
				ring_min = minf(ring_min, portal.z)
				ring_max = maxf(ring_max, portal.z)
	assert(is_finite(ring_min) and is_finite(ring_max), "shared ring defines rivet seating faces")
	for side: int in range(2):
		for station: Transform3D in ShipGeometry.hatch_frame_rivet_stations(door.aperture()):
			var transform := station
			transform.origin.z = (ring_min + ShipGeometry.HATCH_RIVET_DEPTH * 0.08) if side == 0 else (ring_max - ShipGeometry.HATCH_RIVET_DEPTH * 0.08)
			result.frame_rivets.append({"index": result.frame_rivets.size(), "id": "FRAME/RIVETS/%d/%03d" % [side, result.frame_rivets.size()], "side": side, "size": vector3(Vector3(ShipGeometry.HATCH_RIVET_RADIUS * 2, ShipGeometry.HATCH_RIVET_DEPTH, ShipGeometry.HATCH_RIVET_RADIUS * 2)), "radius": ShipGeometry.HATCH_RIVET_RADIUS, "transform": pose(transform)})
	result["fit"] = fitting_records(door, solids)
	return result

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2 or args[0] != "--output":
		printerr("usage: godot --headless --path . -s tools/export_hatch_parts.gd -- --output <json>")
		quit(2)
		return
	var layout := ShipLayout.authored().layout
	var representatives: Dictionary = {}
	# Explicit ids preserve hinge signs and avoid process-dependent StringName ordering.
	for id: StringName in [&"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var door := layout.door(id)
		var hinge_sign := int(signf(door.hinge_frame().origin.z - ShipLayout.WALL / 2))
		if not representatives.has(hinge_sign): representatives[hinge_sign] = door
	assert(representatives.has(1) and representatives.has(-1), "both physical hatch hinge signs exist")
	var document := {"schema_version": 1, "coordinate_system": "godot_y_up", "variants": [variant(representatives[1], 0), variant(representatives[-1], 1)]}
	var output := FileAccess.open(args[1], FileAccess.WRITE)
	assert(output != null, "export destination writable")
	output.store_string(JSON.stringify(document, "\t", false, true) + "\n")
	output.close()
	print("HATCH_EXPORT ", args[1], " variants=2")
	quit(0)
