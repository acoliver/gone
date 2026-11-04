class_name CorridorDressing
extends RefCounted
## Uploads layout-owned poses. Room roots own all batches and instance buffers;
## only the three unit meshes and finite Surfaces roles are shared globally.

static var _meshes: Dictionary = {}

static func build(layout: ShipLayout, space_id: StringName) -> Node3D:
	var spec := layout.dressing(space_id)
	var root := Node3D.new()
	root.name = "CorridorDressing"
	root.set_meta(&"space_id", space_id)
	var mask := Lighting.space_mask(layout, space_id)
	if space_id == &"D14-S-041": mask |= Lighting.HALL_FILL_MASK
	for family: ShipLayout.DressingBatch in spec.batches:
		assert(not family.poses.is_empty(), "dressing batch has instances")
		var batch := MultiMesh.new()
		batch.transform_format = MultiMesh.TRANSFORM_3D
		batch.mesh = _mesh(family.shape)
		batch.instance_count = family.poses.size()
		var bounds := AABB()
		for index: int in range(family.poses.size()):
			var pose := family.poses[index]
			batch.set_instance_transform(index, pose)
			var box := pose * batch.mesh.get_aabb()
			bounds = box if index == 0 else bounds.merge(box)
		batch.custom_aabb = bounds
		var piece := MultiMeshInstance3D.new()
		piece.name = String(family.family)
		piece.multimesh = batch
		piece.layers = mask
		piece.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		piece.set_meta(&"instance_poses", family.poses.duplicate())
		piece.set_meta(&"role", family.role)
		Surfaces.bind(piece, family.role, Surfaces.surface_frame(layout, space_id, family.surface_part))
		root.add_child(piece)
	return root

static func _mesh(shape: StringName) -> Mesh:
	if _meshes.has(shape): return _meshes[shape]
	var mesh: Mesh
	match shape:
		&"box":
			var box := BoxMesh.new()
			box.size = Vector3.ONE
			mesh = box
		&"cylinder":
			var cylinder := CylinderMesh.new()
			cylinder.top_radius = 0.5
			cylinder.bottom_radius = 0.5
			cylinder.height = 1.0
			cylinder.radial_segments = 12
			mesh = cylinder
		&"ring":
			var ring := TorusMesh.new()
			ring.inner_radius = 0.36
			ring.outer_radius = 0.5
			ring.rings = 12
			ring.ring_segments = 6
			# Normalize the axial thickness to the unit bounds used by layout.
			var tool := SurfaceTool.new()
			tool.begin(Mesh.PRIMITIVE_TRIANGLES)
			tool.append_from(ring, 0, Transform3D(Basis.from_scale(Vector3(1, 1 / 0.14, 1)), Vector3.ZERO))
			mesh = tool.commit()
		_:
			assert(false, "unknown dressing primitive: %s" % shape)
	_meshes[shape] = mesh
	return mesh
