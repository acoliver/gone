extends SceneTree
## Production scene and circuits only. Neutral inspection belongs to capture_steel_probe.
## Run: godot --path . -s tools/capture_ship_surfaces.gd -- <output-dir>
const Protocol := preload("res://harness/protocol.gd")

static func capture_identity() -> Dictionary:
	var hashes: Dictionary = {}
	for file: String in Surfaces.IMAGES:
		for suffix: String in ["", ".import"]:
			var path := "assets/surfaces/steel/" + file + suffix
			hashes[path] = FileAccess.get_sha256("res://" + path)
	for path: String in ["app/surfaces.gd", "app/lighting.gd", "app/hallway.gd", "app/power_room.gd", "app/ship_scene.gd", "tools/capture_ship_surfaces.gd", "app/shaders/weathered_steel.gdshader", "app/shaders/steel_sampling.gdshaderinc", "app/shaders/weathered_tape.gdshader", "assets/surfaces/steel/manifest.json", "assets/surfaces/hatch/leaf-weather.png", "assets/surfaces/hatch/leaf-weather.png.import"]:
		hashes[path] = FileAccess.get_sha256("res://" + path)
	return {"app_hash": Protocol.app_hash(ProjectSettings.globalize_path("res://")), "resources": hashes, "lighting": {
		"key_color": [Lighting.EMERGENCY_RED.r, Lighting.EMERGENCY_RED.g, Lighting.EMERGENCY_RED.b],
		"fill_color": [Lighting.EMERGENCY_FILL_COLOR.r, Lighting.EMERGENCY_FILL_COLOR.g, Lighting.EMERGENCY_FILL_COLOR.b],
		"lens_base_color": str(Lighting.LENS_BASE_COLOR), "lens_emission": str(Lighting.emergency_emission(1.0)),
		"key_energy": Lighting.emergency_energy(), "fill_energy": Lighting.emergency_energy() * Lighting.EMERGENCY_FILL_SHARE,
		"fill_counts": [6, 4, 6],
		"no_fill_multiplier": Lighting.EMERGENCY_NO_FILL_KEY_MULTIPLIER, "fill_range": Lighting.EMERGENCY_FILL_RANGE,
		"fill_ceiling_drop": Lighting.EMERGENCY_FILL_CEILING_DROP,
		"key_shadows": false, "fill_shadows": false,
		"fill_masks": [Lighting.BAY_FILL_MASK, Lighting.HALL_FILL_MASK, Lighting.POWER_FILL_MASK],
		"fill_rooms": "D14 bay/hall/power only; remote connectors remain independent under secondary power",
	}}


const SEED: int = 91
var output_dir: String
var world: Node3D
var scene: ShipScene
var game: Game
var camera: Camera3D
var records: Array[Dictionary] = []

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 1 or args[0].strip_edges().is_empty():
		printerr("usage: godot --path . -s tools/capture_ship_surfaces.gd -- <output-dir>")
		quit(2)
		return
	output_dir = args[0]
	_run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name() != "headless", "windowed native captures required")
	DirAccess.make_dir_recursive_absolute(output_dir)
	root.size = Vector2i(2304, 1296)
	DisplayServer.window_set_size(root.size)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_2X
	var identity := capture_identity()
	for white: bool in [false, true]:
		game = Game.new(SEED)
		game.light_hallway()
		if white:
			game.press_console()
			for tick: int in range(BayVentilation.CLEAR_TICKS): game.ventilation.tick(true)
		world = Node3D.new()
		root.add_child(world)
		scene = ShipScene.build_into(world, game, false)
		scene.prepare_near(Vector3(10, 0, 0))
		scene.prepare_near(Vector3(26, 0, 0))
		camera = Camera3D.new()
		world.add_child(camera)
		camera.current = true
		camera.fov = 76
		await _settle(36)
		var circuit := "secondary-white" if white else "emergency-red-orange"
		await _shot(circuit, "section41-corridor", &"D14-S-041", Vector3(18, 1.6, 0.25), Vector3(29.6, 1.5, 0))
		await _shot(circuit, "section41-detail", &"D14-S-041", Vector3(18, 1.6, -0.4), Vector3(18.2, 1.5, -1.5))
		await _shot(circuit, "section41-end-hatch", &"D14-C-001-H-FORE", Vector3(27.5, 1.6, 0), Vector3(30, 1.4, 0))
		camera.fov = 86
		await _shot(circuit, "hatch-close", &"D14-C-001-H-FORE", Vector3(28.45, 1.30, 0.03), Vector3(29.92, 1.30, 0))
		camera.fov = 76
		await _shot(circuit, "hatch-three-quarter", &"D14-C-001-H-FORE", Vector3(28.05, 1.40, -1.16), Vector3(29.92, 1.30, 0))
		var bay_frame := game.layout.bay_to_world()
		await _shot(circuit, "bay", ShipLayout.BAY_ID, bay_frame * Vector3(-0.4, 1.6, 1.49), bay_frame * Vector3(5.8, 1.5, 0))
		await _shot(circuit, "power-doorway", ShipLayout.POWER_ID, Vector3(25.5, 1.6, -0.1), Vector3(27, 1.4, -1.6))
		await _shot(circuit, "connector-aft", &"D14-C-001", Vector3(32.8, 1.6, 0), Vector3(30, 1.4, 0))
		await _shot(circuit, "connector-fore", &"D14-C-000", Vector3(3.5, 1.6, 0), Vector3(6, 1.4, 0))
		await _shot(circuit, "section40", &"D14-S-040", Vector3(-12, 1.6, 0.25), Vector3(-0.2, 1.5, 0))
		await _shot(circuit, "section42", &"D14-S-042", Vector3(46, 1.6, 0.25), Vector3(59.8, 1.5, 0))
		for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-000-H-AFT", &"D14-C-001-H-FORE"]:
			await _faces(circuit, id, "closed")
		var id := &"D14-C-001-H-FORE"
		var context := Doors.Context.new()
		context.face_id = game.layout.door(id).face_ids()[0]
		game.doors.press(id, context)
		for tick: int in range(3): game.advance_doors()
		_present()
		await _faces(circuit, id, "cranking")
		while game.doors.snapshot(id).state != Doors.State.OPENING:
			for tick: int in range(Doors.WHEEL_TICKS): game.advance_doors()
			if game.doors.snapshot(id).state != Doors.State.OPENING: game.doors.press(id, context)
		for tick: int in range(Doors.SWING_TICKS / 2): game.advance_doors()
		_present()
		await _faces(circuit, id, "swing")
		for tick: int in range(Doors.SWING_TICKS): game.advance_doors()
		_present()
		await _faces(circuit, id, "parked")
		for deck: int in [1, 30]:
			var spec := game.layout.connector(ShipLayout.connector_id(deck, 1))
			var remote := scene.build_remote(spec)
			var bounds := spec.bounds()
			await _shot(circuit, "deck%02d-connector" % deck, spec.id(), bounds.get_center() + Vector3(0.6, 0, 0), Vector3(bounds.position.x, bounds.position.y + 1.4, 0))
			scene.remove_remote(spec, remote)
		world.free()
		await process_frame
	if identity != capture_identity():
		push_error("Capture inputs changed during rendering; capture set is inconsistent")
		quit(1)
		return
	identity.merge({"seed": SEED, "material": "round5-steel-v1", "captures": records})
	FileAccess.open(output_dir.path_join("captures.json"), FileAccess.WRITE).store_string(JSON.stringify(identity, "\t") + "\n")
	print("SHIP SURFACES COMPLETE captures=", records.size())
	quit(0)

func _present() -> void:
	for view: DoorView in scene.door_views: view.present(game.doors.snapshot(view.door_id()))

func _faces(circuit: String, id: StringName, pose: String) -> void:
	var spec := game.layout.door(id)
	var view: DoorView
	for candidate: DoorView in scene.door_views:
		if candidate.door_id() == id: view = candidate
	assert(view != null, "capture door exists")
	var frame := Surfaces.world_frame(view.label_leaf())
	for side: int in [-1, 1]:
		var center := frame * Vector3(spec.leaf_aperture().x / 2, 1.25, side * 0.1)
		await _shot(circuit, "%s-%s-%s" % [id, "fore" if side < 0 else "aft", pose], id, center + frame.basis.z * side * 1.85, center)

func _shot(circuit: String, name: String, owner: StringName, eye: Vector3, target: Vector3) -> void:
	camera.position = eye
	camera.look_at(target)
	await _settle(12)
	var path := output_dir.path_join("%s-%s.png" % [circuit, name])
	var image := root.get_texture().get_image()
	assert(image.get_size() == Vector2i(2304, 1296), "native capture resolution")
	assert(image.save_png(path) == OK, "capture saved: " + path)
	var state: Dictionary = {}
	if owner in game.layout.door_ids():
		var snapshot := game.doors.snapshot(owner)
		state = {"state": snapshot.state, "wheel_degrees": snapshot.wheel_angle, "leaf_fraction": snapshot.leaf_fraction, "rest_radians": snapshot.open_radians}
	records.append({"path": path, "owner": owner, "circuit": circuit, "eye": [eye.x, eye.y, eye.z], "camera_transform": str(camera.transform), "fov": camera.fov, "snapshot": state})
	print("SHIP CAPTURE ", path)

func _settle(count: int) -> void:
	for index: int in range(count): await process_frame
	await RenderingServer.frame_post_draw
