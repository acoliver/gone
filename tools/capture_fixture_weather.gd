extends "res://tools/capture_ship_surfaces.gd"
## Native production scene; only fixture finishes change between effect controls.
const FINISHES := {"OliveSteel_StructuredWeather": "body", "DarkArmouredSteel": "grille", "RaisedRailSteel": "hardware", CeilingFixture.GLASS: "glass"}
var finishes: Dictionary = {}
var surroundings: Dictionary = {}
var map_dir: String

static func surrounding_geometry(node: Node, fixture_finishes: Dictionary) -> Dictionary:
	var result: Dictionary = {}
	for piece: GeometryInstance3D in node.find_children("*", "GeometryInstance3D", true, false):
		if not fixture_finishes.has(piece): result[piece] = piece.material_override
	return result

func _run() -> void:
	if DisplayServer.get_name() == "headless":
		printerr("native renderer required")
		quit(2)
		return
	map_dir = OS.get_environment("GONE_FIXTURE_MAPS")
	if map_dir.is_empty() or not DirAccess.dir_exists_absolute(map_dir):
		printerr("supply an existing effect-isolation map directory in GONE_FIXTURE_MAPS")
		quit(2)
		return
	DirAccess.make_dir_recursive_absolute(output_dir)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.content_scale_size = Vector2i(2304, 1296)
	root.size = root.content_scale_size
	DisplayServer.window_set_size(root.size)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_2X
	game = Game.new(SEED)
	game.light_hallway()
	game.press_console()
	for tick: int in range(BayVentilation.CLEAR_TICKS): game.ventilation.tick(true)
	world = Node3D.new()
	root.add_child(world)
	scene = ShipScene.build_into(world, game)
	scene.hazards.auto_bursts = false
	scene.prepare_near(Vector3(10, 0, 0))
	scene.prepare_near(Vector3(26, 0, 0))
	camera = Camera3D.new()
	world.add_child(camera)
	camera.current = true
	await _settle(36)
	var targets: Array[Vector3] = []
	for mesh: MeshInstance3D in world.find_children("*", "MeshInstance3D", true, false):
		if mesh.get_parent().name == "CeilingFixture" and FINISHES.has(mesh.get_active_material(0).resource_name):
			finishes[mesh] = mesh.get_active_material(0)
			if mesh.get_active_material(0).resource_name == CeilingFixture.GLASS:
				var centre := mesh.to_global(mesh.mesh.get_aabb().get_center())
				if absf(centre.x - 21.0) < .01 and absf(centre.z) < .01: targets.append(centre)
	surroundings = surrounding_geometry(world, finishes)
	assert(targets.size() == 1, "the capture tracks the actual target fixture, including source-seating changes")
	var target := targets[0]
	var variants := PackedStringArray(["weathered", "control", "no_dust", "no_rust", "no_streak", "zones", "dustmask", "topmask", "shellmask", "rust", "soot"])
	if not OS.get_environment("GONE_FIXTURE_VARIANTS").is_empty():
		variants = OS.get_environment("GONE_FIXTURE_VARIANTS").split(",")
	for variant: String in variants:
		_apply(variant)
		camera.fov = 55
		await _shot(variant, "2p5m", &"D14-S-041", target + Vector3(0, -sqrt(2.5 * 2.5 - 0.025 * 0.025), 0.025), target)
		await _shot(variant, "close", &"D14-S-041", target + Vector3(-0.40, -0.64, 0.65), target)
		await _shot(variant, "ledge", &"D14-S-041", target + Vector3(-.7, -.038, .70), target + Vector3(0, .047, 0))
		camera.fov = 76
		await _shot(variant, "corridor", &"D14-S-041", Vector3(18.8, 1.5, 0.25), Vector3(23.0, target.y - .063, 0))
	var manifest := "captures.json" if OS.get_environment("GONE_FIXTURE_VARIANTS").is_empty() else "captures-extra.json"
	var identity := capture_identity()
	identity.merge({"captures": records, "circuit": "secondary-white", "source_energy": Lighting.regular_energy(), "effect_maps": map_dir, "display_server": DisplayServer.get_name(), "seed": SEED})
	FileAccess.open(output_dir.path_join(manifest), FileAccess.WRITE).store_string(JSON.stringify(identity, "\t") + "\n")
	print("FIXTURE CAPTURES COMPLETE count=", records.size())
	quit()

func _texture(path: String) -> ImageTexture:
	var image := Image.load_from_file(path)
	if image == null:
		push_error("missing effect map: " + path)
		quit(1)
		return null
	image.generate_mipmaps()
	return ImageTexture.create_from_image(image)

func _apply(variant: String) -> void:
	var masking := variant in ["zones", "dustmask", "topmask", "shellmask", "rust", "soot"]
	var black := StandardMaterial3D.new()
	black.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	black.albedo_color = Color.BLACK
	for mesh: GeometryInstance3D in surroundings:
		mesh.material_override = black if masking else surroundings[mesh]
	for mesh: MeshInstance3D in finishes:
		var original: StandardMaterial3D = finishes[mesh]
		var material := original.duplicate() as StandardMaterial3D
		var prefix: String = FINISHES[original.resource_name]
		if variant in ["zones", "dustmask", "topmask", "shellmask", "rust", "soot"]:
			material = StandardMaterial3D.new()
			material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
			if prefix == "glass": material.albedo_color = Color.BLACK
			else: material.albedo_texture = _texture(map_dir.path_join(prefix + "_" + variant + ".png"))
		elif variant != "weathered":
			if prefix != "glass":
				material.albedo_texture = _texture(map_dir.path_join(prefix + "_" + variant + ".png"))
				if variant == "control":
					material.roughness_texture = _texture(map_dir.path_join(prefix + "_control_orm.png"))
					material.metallic_texture = material.roughness_texture
			elif variant == "control" and FileAccess.file_exists(map_dir.path_join("glass_control.png")):
				material.emission_texture = _texture(map_dir.path_join("glass_control.png"))
		mesh.set_surface_override_material(0, material)
