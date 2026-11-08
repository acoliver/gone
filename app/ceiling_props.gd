class_name CeilingProps
extends RefCounted

const ROOT := "res://assets/props/ceiling/"
static var _meshes: Dictionary = {}

static func mesh(shape: StringName) -> Mesh:
	if _meshes.has(shape): return _meshes[shape]
	var scene: PackedScene = load(ROOT + String(shape) + ".glb")
	var node := scene.instantiate()
	var pieces := node.find_children("*", "MeshInstance3D", true, false)
	assert(pieces.size() == 1, "one fitted mesh per prop")
	var source := pieces[0] as MeshInstance3D
	var frame := Surfaces.world_frame(source)
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	tool.append_from(source.mesh, 0, frame)
	var result := tool.commit()
	node.free()
	_meshes[shape] = result
	return result

static func _add(root: Node3D, layout: ShipLayout, id: StringName, family: StringName, source: Mesh, poses: Array[Transform3D], role: StringName, part: StringName) -> void:
	assert(not poses.is_empty(), "service family has placements")
	var batch := MultiMesh.new()
	batch.transform_format = MultiMesh.TRANSFORM_3D
	batch.mesh = source
	batch.instance_count = poses.size()
	var bounds := AABB()
	for index: int in range(poses.size()):
		batch.set_instance_transform(index, poses[index])
		var box := poses[index] * source.get_aabb()
		bounds = box if index == 0 else bounds.merge(box)
	batch.custom_aabb = bounds
	var piece := MultiMeshInstance3D.new()
	piece.name = String(family)
	piece.multimesh = batch
	piece.layers = Lighting.architectural_mask(layout, id)
	piece.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	piece.set_meta(&"role", role)
	piece.set_meta(&"instance_poses", poses.duplicate())
	Surfaces.bind(piece, role, Surfaces.surface_frame(layout, id, part))
	root.add_child(piece)

static func armour(fixture: Node3D, layout: ShipLayout, id: StringName) -> void:
	_add(fixture, layout, id, &"ArmouredModules", mesh(&"module"), CeilingServices.module_poses(), &"ceiling", &"CEILING")
