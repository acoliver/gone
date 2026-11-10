class_name CeilingFixture
extends RefCounted

const ASSET := preload("res://assets/props/ceiling/fixture.glb")
const GLASS := "RecessedFrostedGlass"
static var _metal_materials: Dictionary[String, StandardMaterial3D] = {}
static var _glass_emission: ImageTexture

static func glass_material(level: float) -> StandardMaterial3D:
	var asset := ASSET.instantiate()
	var glass := _glass(asset)
	var material := glass.mesh.surface_get_material(0).duplicate() as StandardMaterial3D
	asset.free()
	# Retain the glare calibration when seating the source inside the recessed glass.
	material.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
	material.albedo_color = Color(0.06, 0.06, 0.06)
	# Grazing scatter keeps the thin aperture visible under player exposure without brightening its frontal face.
	material.rim_enabled = true
	material.rim = 6.0
	material.rim_tint = 0.0
	material.emission_energy_multiplier = 0.30
	if _glass_emission == null:
		# The circuit supplies the warm-white colour; retain the map's dirt and dim sections.
		var image := material.emission_texture.get_image()
		image.convert(Image.FORMAT_RGBA8)
		image.adjust_bcs(1.0, 1.0, 0.0)
		# Balance red against green without clipping away the circuit's warm blue response.
		var pixels := image.get_data()
		for index: int in range(0, pixels.size(), 4):
			pixels[index] = roundi(pixels[index] * Lighting.REGULAR_WHITE.g / Lighting.REGULAR_WHITE.r)
		image = Image.create_from_data(image.get_width(), image.get_height(), image.has_mipmaps(), Image.FORMAT_RGBA8, pixels)
		_glass_emission = ImageTexture.create_from_image(image)
	material.emission_texture = _glass_emission
	material.emission = Lighting.REGULAR_WHITE * Lighting.REGULAR_EMISSIVE * level
	return material

static func mount(parent: Node3D, ceiling_y: float, mask: int, material: StandardMaterial3D) -> MeshInstance3D:
	var asset := ASSET.instantiate() as Node3D
	asset.name = "CeilingFixture"
	# The imported Y=0 mounting plane, not its fixture anchor, must meet the ceiling.
	asset.position.y = ceiling_y - parent.position.y
	var glass := _glass(asset)
	glass.set_surface_override_material(0, material)
	glass.set_meta(&"lamp_circuit", "white")
	Lighting.mesh_layers(asset, mask)
	for piece: MeshInstance3D in asset.find_children("*", "MeshInstance3D", true, false):
		piece.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var finish := piece.mesh.surface_get_material(0) as StandardMaterial3D
		if finish.resource_name == GLASS: continue
		if not _metal_materials.has(finish.resource_name):
			var matte := finish.duplicate() as StandardMaterial3D
			# Keep dusty paint and oxidized edges matte without replacing their authored maps.
			matte.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
			if finish.resource_name == "DarkArmouredSteel":
				matte.albedo_color = Color(0.35, 0.35, 0.35)
			_metal_materials[finish.resource_name] = matte
		piece.set_surface_override_material(0, _metal_materials[finish.resource_name])
	parent.add_child(asset)
	return glass

static func _glass(asset: Node3D) -> MeshInstance3D:
	var glasses: Array[MeshInstance3D] = []
	for piece: MeshInstance3D in asset.find_children("*", "MeshInstance3D", true, false):
		assert(piece.mesh.get_surface_count() == 1, "fixture parts retain independent authored finishes")
		if piece.mesh.surface_get_material(0).resource_name == GLASS: glasses.append(piece)
	assert(glasses.size() == 1, "fixture requires exactly one recessed glass surface")
	return glasses[0]
