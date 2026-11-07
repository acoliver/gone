extends SimTestCase
## #88: transmission and reflection are independent of the pane's dark fallback.

func test_canopy_uses_the_shared_lit_thin_glass_shader() -> void:
	var material: Material = PodMesh.canopy_material()
	assert_true(material is ShaderMaterial, "glTF opaque fallback must be replaced with thin glass")
	if not material is ShaderMaterial:
		return
	assert_true(material.resource_name == "WindowTint", "surface identity survives replacement")
	var code: String = material.shader.code
	for setting: String in ["blend_premul_alpha", "depth_draw_never", "cull_disabled", "specular_schlick_ggx", "fog_disabled", "specular_occlusion_disabled", "PREMUL_ALPHA_FACTOR = 1.0", "SPECULAR = 0.5", "ROUGHNESS = 0.07"]:
		assert_true(setting in code, "glass contract includes " + setting)
	for forbidden: String in ["hint_screen_texture", "hint_depth_texture", "unshaded", "ambient_light_disabled", "depth_prepass_alpha"]:
		assert_false(forbidden in code, "glass does not use " + forbidden)

func test_fresnel_transfer_matches_the_declared_table() -> void:
	var material: Material = PodMesh.canopy_material()
	assert_true(material is ShaderMaterial, "Fresnel transfer requires the production shader")
	if not material is ShaderMaterial:
		return
	var samples := {0.0: 0.0592, 60.0: 0.0886, 75.0: 0.269635, 80.0: 0.421712, 85.0: 0.655522, 90.0: 1.0}
	for angle: float in samples:
		var fresnel := 0.04 + 0.96 * pow(1.0 - cos(deg_to_rad(angle)), 5.0)
		assert_true(absf(1.0 - 0.98 * (1.0 - fresnel) - samples[angle]) < 1e-5, "alpha table at %s degrees" % angle)

func test_pane_has_one_broad_sheet_and_explicit_edge_mask() -> void:
	var shell := PodMesh.make_shell(Pods.PodState.SEALED)
	var pane: MeshInstance3D = shell.get_node("PodLid/WindowPane")
	assert_int_equal(pane.mesh.get_surface_count(), 1, "one pane surface")
	var arrays := pane.mesh.surface_get_arrays(0)
	var colors: PackedColorArray = arrays[Mesh.ARRAY_COLOR]
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	assert_int_equal(colors.size(), vertices.size(), "missing COLOR_0 must not select the opaque skirt")
	if colors.size() == vertices.size():
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var skirt := 0
		for i: int in range(0, indices.size(), 3):
			var r := colors[indices[i]].r
			assert_true(absf(r) < 1e-5 or absf(r - 1.0) < 1e-5, "mask is binary")
			assert_true(absf(colors[indices[i + 1]].r - r) < 1e-5 and absf(colors[indices[i + 2]].r - r) < 1e-5, "no mask interpolation into viewing area")
			if r > 0.5:
				skirt += 1
		assert_true(skirt > 0, "pane retains a seated cut edge")
	assert_int_equal(pane.cast_shadow, GeometryInstance3D.SHADOW_CASTING_SETTING_OFF, "glass adds no opaque shadow")
	assert_true(pane.sorting_use_aabb_center and pane.sorting_offset == 0.0, "transparent depth uses the pane center, not hinge origin")
	shell.free()

func test_glass_scene_contract_has_no_global_fog() -> void:
	assert_true(ProjectSettings.get_setting("rendering/environment/defaults/default_clear_color") == Color.BLACK, "interior probes omit the Environment background; uncovered directions must stay black")
	var world := Lighting._world_environment()
	assert_false(world.environment.fog_enabled, "thin glass has no depth-fog compositor")
	assert_false(world.environment.volumetric_fog_enabled, "thin glass has no volumetric-fog compositor")
	world.free()

func test_red_wall_lenses_are_reflection_sources() -> void:
	var lighting := Lighting.build(Game.new(0))
	assert_true(lighting.lens_material().emission_enabled, "#88: assigning emission without enabling its feature leaves the red probe source dark")
	lighting.free()
