class_name SlidingDoorModel
extends RefCounted
## Regular-door presentation projects the sim recipe, including hidden pocket returns.

static var _leaves: Dictionary = {}
static var _walls: Dictionary = {}

static func leaf(spec: ShipLayout.DoorSpec, mask: int = 1, layout: ShipLayout = ShipLayout.authored().layout) -> MeshInstance3D:
	var solid := SlidingDoorParts.leaf_solid(spec)
	var key := spec.aperture()
	if not _leaves.has(key):
		var tool := SurfaceTool.new()
		tool.begin(Mesh.PRIMITIVE_TRIANGLES)
		var center := Vector3(0, spec.aperture().y / 2, ShipLayout.WALL / 2)
		for part: HatchParts.Part in SlidingDoorParts.leaf_parts(spec):
			var pose := part.transform
			pose.origin -= center
			var mesh := HatchModel._part_mesh(part)
			if part.shape == &"cylinder":
				var rivet := CylinderMesh.new()
				rivet.top_radius = part.radius
				rivet.bottom_radius = part.radius
				rivet.height = part.size.y
				rivet.radial_segments = 8
				mesh = rivet
			HatchModel._append(tool, mesh, pose)
		tool.index()
		_leaves[key] = tool.commit()
	var piece := HatchModel.mesh_piece(_leaves[key], solid.transform, mask, Surfaces.material(&"hatch_leaf"))
	Surfaces.bind_solid(piece, layout, solid)
	piece.set_meta(&"solid_id", solid.id)
	return piece

static func frame(spec: ShipLayout.DoorSpec, mask: int = 1) -> Node3D:
	var root := Node3D.new()
	for solid: ShipGeometry.SolidSpec in SlidingDoorParts.fixed_solids(spec):
		var piece := HatchModel.mesh_piece(HatchModel.box_mesh(solid.size), solid.transform, mask, Surfaces.material(&"hatch_leaf"))
		Surfaces.bind(piece, &"hatch_leaf", Surfaces.door_frame(spec, solid.surface_part))
		root.add_child(piece)
	return root

static func wall_mesh(layout: ShipLayout, solid: ShipGeometry.SolidSpec) -> Mesh:
	var cuts := SlidingDoorParts.wall_cuts(layout, solid)
	var key := [solid.id, solid.transform, solid.size, cuts]
	if not _walls.has(key):
		var boxes := SlidingDoorParts.wall_boxes(layout, solid)
		if solid.hatch_profile != null:
			var mesh := HatchModel.solid_mesh(solid)
			for cut: AABB in cuts:
				if mesh.get_aabb().intersection(cut).has_volume(): mesh = cut_mesh(mesh, cut)
			_walls[key] = mesh
			return mesh
		if boxes.size() == 1 and boxes[0] == AABB(-solid.size / 2, solid.size):
			return HatchModel.solid_mesh(solid)
		var tool := SurfaceTool.new()
		tool.begin(Mesh.PRIMITIVE_TRIANGLES)
		for box: AABB in boxes:
			HatchModel._append(tool, HatchModel.box_mesh(box.size), Transform3D(Basis(), box.get_center()))
		tool.index()
		_walls[key] = tool.commit()
	return _walls[key]

static func _clip(points: PackedVector3Array, axis: int, plane: float, greater: bool) -> PackedVector3Array:
	var result := PackedVector3Array()
	if points.is_empty(): return result
	var previous := points[-1]
	var previous_inside := previous[axis] >= plane if greater else previous[axis] <= plane
	for point: Vector3 in points:
		var inside := point[axis] >= plane if greater else point[axis] <= plane
		if inside != previous_inside:
			var crossing := previous.lerp(point, (plane - previous[axis]) / (point[axis] - previous[axis]))
			crossing[axis] = plane
			result.append(crossing)
		if inside: result.append(point)
		previous = point
		previous_inside = inside
	return result

static func _polygon(tool: SurfaceTool, points: PackedVector3Array, normal: Vector3) -> void:
	tool.set_normal(normal)
	for index: int in range(1, points.size() - 1):
		for point: Vector3 in [points[0], points[index], points[index + 1]]: tool.add_vertex(point)

static func cut_mesh(source: Mesh, cut: AABB) -> Mesh:
	# Clip only the regular-door mouth out of an existing rounded wall.
	# Rebuilding that wall from its collision box would erase the hatch opening.
	var arrays := source.surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	for triangle: int in range(0, indices.size(), 3):
		var points := PackedVector3Array([vertices[indices[triangle]], vertices[indices[triangle + 1]], vertices[indices[triangle + 2]]])
		var normal := normals[indices[triangle]]
		var bounds := AABB(points[0], Vector3.ZERO).expand(points[1]).expand(points[2])
		if not bounds.intersects(cut):
			_polygon(tool, points, normal)
			continue
		for axis: int in range(3):
			_polygon(tool, _clip(points, axis, cut.position[axis], false), normal)
			points = _clip(points, axis, cut.position[axis], true)
			_polygon(tool, _clip(points, axis, cut.end[axis], true), normal)
			points = _clip(points, axis, cut.end[axis], false)
	# Ordinary mouths are in the straight wall, away from the hatch crown.
	var bounds := source.get_aabb()
	var hit := bounds.intersection(cut)
	var cap := HatchModel.box_mesh(hit.size).surface_get_arrays(0)
	var cap_points: PackedVector3Array = cap[Mesh.ARRAY_VERTEX]
	var cap_normals: PackedVector3Array = cap[Mesh.ARRAY_NORMAL]
	var cap_indices: PackedInt32Array = cap[Mesh.ARRAY_INDEX]
	for triangle: int in range(0, cap_indices.size(), 3):
		var normal := cap_normals[cap_indices[triangle]]
		var axis := normal.abs().max_axis_index()
		var center := hit.get_center() + cap_points[cap_indices[triangle]]
		if center[axis] <= bounds.position[axis] or center[axis] >= bounds.end[axis]: continue
		var points := PackedVector3Array()
		for corner: int in [0, 2, 1]: points.append(cap_points[cap_indices[triangle + corner]] + hit.get_center())
		_polygon(tool, points, -normal)
	tool.index()
	return tool.commit()
