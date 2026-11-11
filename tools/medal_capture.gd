extends RefCounted
## Runtime provenance and effect isolation for the fixed #130 cameras.

static func _texture(texture: Texture2D) -> Dictionary:
	if texture == null: return {}
	return {"path": texture.resource_path, "pixels_sha256": texture.get_image().get_data().hex_encode().sha256_text(), "mipmaps": texture.get_image().has_mipmaps()}

static func inventory(garment: Node3D, main: Node3D) -> Dictionary:
	var surfaces := []
	for part: String in ["Medal", "TunicBody"]:
		var piece := garment.find_child(part, true, false) as MeshInstance3D
		for slot: int in range(piece.mesh.get_surface_count()):
			var imported := piece.mesh.surface_get_material(slot) as StandardMaterial3D
			var finish := piece.get_active_material(slot) as ShaderMaterial
			var arrays := piece.mesh.surface_get_arrays(slot)
			surfaces.append({"part": part, "slot": slot, "shader": finish.shader.resource_path,
				"albedo": _texture(finish.get_shader_parameter("albedo_texture")),
				"normal": _texture(finish.get_shader_parameter("normal_texture")),
				"orm": _texture(finish.get_shader_parameter("orm_texture")) if part == "Medal" and slot < 2 else {},
				"roughness_channel": imported.roughness_texture_channel, "metallic_channel": imported.metallic_texture_channel,
				"ao_channel": imported.ao_texture_channel, "primary_uv": imported.get_meta("_gltf_primary_texture_coord", 0),
				"vertices": arrays[Mesh.ARRAY_VERTEX].size(), "tangent_floats": arrays[Mesh.ARRAY_TANGENT].size() if arrays[Mesh.ARRAY_TANGENT] != null else 0,
				"layers": piece.layers, "shadow": piece.cast_shadow, "lod_bias": piece.lod_bias})
	var probes := []
	for probe: ReflectionProbe in main.find_children("*", "ReflectionProbe", true, false):
		probes.append({"name": str(probe.get_path()), "visible": probe.is_visible_in_tree(), "position": str(probe.global_position), "size": str(probe.size), "cull_mask": probe.cull_mask, "update_mode": probe.update_mode})
	return {"surfaces": surfaces, "probes": probes}

static func geometry(root: Node3D, path: String) -> void:
	var meshes := []
	for piece: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		if not piece.is_visible_in_tree(): continue
		for slot: int in range(piece.mesh.get_surface_count()):
			var arrays := piece.mesh.surface_get_arrays(slot)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var uv: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV] if arrays[Mesh.ARRAY_TEX_UV] != null else PackedVector2Array()
			var positions := []
			var texcoords := []
			for p: Vector3 in vertices:
				var world := piece.global_transform * p
				positions.append([world.x, world.y, world.z])
			for p: Vector2 in uv: texcoords.append([p.x, p.y])
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			var finish := piece.get_active_material(slot)
			var cull: int = finish.cull_mode if finish is BaseMaterial3D else (BaseMaterial3D.CULL_DISABLED if "cull_disabled" in (finish as ShaderMaterial).shader.code else BaseMaterial3D.CULL_BACK)
			meshes.append({"parity": signf(piece.global_transform.basis.determinant()), "cull_mode": cull, "part": String(piece.name), "slot": slot, "positions": positions, "local_positions": Array(vertices).map(func(v: Vector3) -> Array: return [v.x,v.y,v.z]), "uv": texcoords, "indices": Array(indices)})
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(meshes))

static func camera_record(camera: Camera3D) -> Dictionary:
	var t := camera.global_transform
	var matrix := []
	for v: Vector3 in [t.basis.x, t.basis.y, t.basis.z, t.origin]: matrix.append([v.x,v.y,v.z])
	return {"matrix_columns": matrix, "fov": camera.fov, "keep_aspect": camera.keep_aspect, "near": camera.near, "far": camera.far, "size": [1536,864]}

static func control(garment: Node3D, main: Node3D, lane: String) -> void:
	var medal := garment.find_child("Medal", true, false) as MeshInstance3D
	for slot: int in [0,1]:
		var finish := medal.get_active_material(slot) as ShaderMaterial
		if not finish.has_meta("capture_albedo"):
			finish.set_meta("capture_albedo", finish.get_shader_parameter("albedo_texture"))
			finish.set_meta("capture_orm", finish.get_shader_parameter("orm_texture"))
		for role: String in ["albedo", "orm"]:
			finish.set_shader_parameter(role + "_texture", finish.get_meta("capture_" + role))
		if lane == "age-off":
			var aged := is_equal_approx(float((medal.get_active_material(1) as ShaderMaterial).get_shader_parameter("coat_roughness")), 0.23)
			var prefix := "aged" if aged else "as_built"
			for role: String in ["albedo", "orm"]:
				var image := Image.load_from_file("res://tmp/issue130-photoreal/stage2/%s_untarnished_%s.png" % [prefix, role])
				assert(image != null)
				image.generate_mipmaps()
				finish.set_shader_parameter(role + "_texture", ImageTexture.create_from_image(image))
		finish.set_shader_parameter("flat_normal", lane in ["flat-normal", "flat-normal-buffer"])
		finish.set_shader_parameter("rough_enamel", lane == "rough-enamel" and slot == 1)
		finish.set_shader_parameter("diagnostic", 3 if lane.begins_with("mirror") else (1 if lane in ["normal-buffer", "flat-normal-buffer"] else 0))
	for piece: MeshInstance3D in garment.find_children("TunicBody", "MeshInstance3D", true, false):
		for slot: int in range(piece.mesh.get_surface_count()):
			(piece.get_active_material(slot) as ShaderMaterial).set_shader_parameter("contact_enabled", lane != "contact-off")
	for probe: ReflectionProbe in main.find_children("*", "ReflectionProbe", true, false):
		if String(probe.get_path()).contains("Quarters"):
			probe.visible = not lane.ends_with("probe-off")
			if lane == "mirror-refresh": probe.update_mode = ReflectionProbe.UPDATE_ALWAYS
			if lane in ["refreshed", "full"]: probe.update_mode = ReflectionProbe.UPDATE_ONCE

static func sweep(tree: SceneTree, camera: Camera3D, garment: Node3D, state: String, output: String) -> void:
	var medal := garment.find_child("Medal", true, false) as MeshInstance3D
	var finishes: Array[ShaderMaterial] = [medal.get_active_material(0), medal.get_active_material(1)]
	var originals: Array[Texture2D] = [finishes[0].get_shader_parameter("normal_texture"), finishes[1].get_shader_parameter("normal_texture")]
	var prefix := "aged" if state == "present" else "as_built"
	var textures := {}
	for lane: String in ["full", "fine-off", "strong"]:
		var path := "res://assets/props/quarters/dress_uniform/medal/%s_normal.png" % prefix
		if lane == "fine-off": path = "res://tmp/issue130-photoreal/stage2/geometry_runtime_normal.png"
		if lane == "strong": path = "res://tmp/issue130-photoreal/stage2/overstrong_normal.png"
		var image := Image.load_from_file(path)
		assert(image != null)
		image.generate_mipmaps()
		textures[lane] = ImageTexture.create_from_image(image)
	var saved := camera.global_transform
	var target := saved.origin - saved.basis.z * .18
	for index: int in range(24):
		var angle := -.014 + .028 * index / 23.0
		camera.global_position = target + .18 * (saved.basis.z * cos(angle) + saved.basis.x * sin(angle))
		camera.look_at(target)
		for lane: String in textures:
			for finish: ShaderMaterial in finishes: finish.set_shader_parameter("normal_texture", textures[lane])
			for settle: int in range(3): await tree.process_frame
			RenderingServer.force_draw(false)
			await RenderingServer.frame_post_draw
			var image := tree.root.get_texture().get_image().get_region(Rect2i(0,40,1536,824))
			assert(image.save_png(output.path_join("%s-sweep-%02d-%s.png" % [state,index,lane])) == OK)
	camera.global_transform = saved
	for slot: int in [0,1]: finishes[slot].set_shader_parameter("normal_texture", originals[slot])

static func power_lanes(tree: SceneTree, main: Node3D, state: String, output: String) -> void:
	assert(main.game.power_active)
	main.game.power_active = false
	for lane: String in ["fade", "off"]:
		for tick: int in range(15): main.step.ship_scene.tick_rooms()
		for settle: int in range(3): await tree.process_frame
		RenderingServer.force_draw(false)
		await RenderingServer.frame_post_draw
		var image := tree.root.get_texture().get_image().get_region(Rect2i(0,40,1536,824))
		assert(image.save_png(output.path_join("%s-medal-%s.png" % [state,lane])) == OK)
	main.game.power_active = true
	for tick: int in range(60): main.step.ship_scene.tick_rooms()
