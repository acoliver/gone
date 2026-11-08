class_name CeilingFixture
extends RefCounted

const ASSET := preload("res://assets/props/ceiling/fixture.glb")
const GLASS := "RecessedFrostedGlass"

static func glass_material(level: float) -> StandardMaterial3D:
	var asset := ASSET.instantiate()
	var glass := _glass(asset)
	var material := glass.mesh.surface_get_material(0).duplicate() as StandardMaterial3D
	asset.free()
	material.emission = Lighting.REGULAR_WHITE * Lighting.REGULAR_EMISSIVE * level
	return material

static func mount(parent: Node3D, ceiling_y: float, mask: int, material: StandardMaterial3D) -> MeshInstance3D:
	var asset := ASSET.instantiate() as Node3D
	asset.name = "CeilingFixture"
	# Light anchors retain their authored position; only the housing moves to the ceiling.
	asset.position.y = ceiling_y - parent.position.y
	var glass := _glass(asset)
	glass.set_surface_override_material(0, material)
	glass.set_meta(&"lamp_circuit", "white")
	Lighting.mesh_layers(asset, mask)
	for piece: MeshInstance3D in asset.find_children("*", "MeshInstance3D", true, false):
		piece.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(asset)
	return glass

static func _glass(asset: Node3D) -> MeshInstance3D:
	var glasses: Array[MeshInstance3D] = []
	for piece: MeshInstance3D in asset.find_children("*", "MeshInstance3D", true, false):
		assert(piece.mesh.get_surface_count() == 1, "fixture parts retain independent authored finishes")
		if piece.mesh.surface_get_material(0).resource_name == GLASS: glasses.append(piece)
	assert(glasses.size() == 1, "fixture requires exactly one recessed glass surface")
	return glasses[0]
