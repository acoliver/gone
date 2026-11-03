extends SceneTree
## Windowed production-scene check. All views use Main's actual Player camera.
## Run with --resolution 2304x1296 -s tests/ventilation_scene_checks.gd.

const OUTPUT := "res://tmp/polish/b-captures"
var main: Node3D
var route: HarnessRoute
var hazards: Hazards

func _initialize() -> void:
	assert(DisplayServer.get_name() != "headless", "requires a rendered window")
	_run.call_deferred()

func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT))
	main = load("res://main.tscn").instantiate()
	root.add_child(main)
	main.set_physics_process(false)
	var player: Player = main.player
	player.scripted = true
	player.interpolate_view = false
	player.adapter = InputPlane.ScriptedAdapter.new()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	hazards = main.get_node("BayRoot/Hazards")
	await RenderingServer.frame_post_draw
	var source: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/power-room.json"))
	route = HarnessRoute.new(player, 12000)
	route.stepper = main.step
	route.replay_prefix(source.actions, 1256)
	route.walk_to(main.game.layout.bay_to_world() * Vector3(4.0, 0, 0))
	route.look_at(main.game.layout.bay_to_world() * Vector3(-4, 1.6, 0), 8)
	await _capture("bay-before-smoky-red")
	assert(main.game.ventilation.density() == 1.0)
	assert(main.step.ship_scene.lighting.level() == 1.0)

	# Reach the real console and activate through the player's input channel.
	route.walk_to(route.anchor(ShipLayout.BAY_DOOR_ID, Vector3(0, 0, 1)))
	route.walk_to(route.anchor(ShipLayout.BAY_DOOR_ID, Vector3(0, 0, -1)))
	route.walk_to(route.anchor(&"D14-HALL-SWITCH", Vector3(0, -1.25, 0.8)))
	route.look_at(route.anchor(&"D14-HALL-SWITCH"), 4)
	route.press()
	route.hold(45)
	route.walk_to(route.anchor(ShipLayout.POWER_DOOR_ID, Vector3(0, 0, -1)))
	route.look_at(route.anchor(ShipLayout.POWER_DOOR_ID), -9)
	route.press()
	route.hold(60)
	route.walk_to(route.anchor(ShipLayout.POWER_DOOR_ID, Vector3(0, 0, 1.5)))
	route.walk_to(route.anchor(&"D14-POWER-CONSOLE", Vector3(2.45, 0, 3)))
	route.walk_to(route.anchor(&"D14-POWER-CONSOLE", Vector3(0.35, 0, 0)))
	route.look_at(route.anchor(&"D14-POWER-CONSOLE", Vector3(-1, 1.4, 0)), -1)
	route.press()
	route.hold(30)
	route.press()
	assert(main.game.power_active, "real console interaction activates secondary power")

	# The console is too far away to walk back within two seconds. Stage only
	# the real player's capsule at the hall threshold, then walk into the bay.
	var walk: Walk.WalkState = player.motion.locomotion.get("_walk")
	var capsule: Resolve.Capsule = walk.get("_capsule")
	capsule.foot = main.game.layout.bay_to_world() * Vector3(6.5, 0.385, 0)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	walk._velocity_x = 0.0
	walk._velocity_z = 0.0
	player.adapter.look(InputPlane.wrap_angle(PI - player.look_angles().x), deg_to_rad(8) - player.look_angles().y)
	print("CAPTURE SETUP: capsule staged at bay threshold after real console activation; camera remains the production Player camera")
	for tick: int in range(1, 121):
		await physics_frame
		route.step([{"type": "move", "forward": -1.0, "strafe": 0.0}])
		if tick == 1:
			assert(hazards._vents[0].playing and hazards._vents[1].playing, "both ceiling vents start their hiss")
	assert(main.game.ventilation.density() == 0.75, "two-second density")
	assert(not hazards.get_node("CeilingSmoke").emitting)
	await _capture("bay-return-clearing-2s")
	for _tick in range(780):
		await physics_frame
		route.step()
	assert(main.game.ventilation.density() == 0.0, "fifteen-second bay is clear")
	assert(not hazards.get_node("CeilingSmoke").visible)
	assert(not hazards._vents[0].playing and not hazards._vents[1].playing, "hiss stops with clearing")
	assert(main.step.ship_scene.lighting.level() == 0.0)
	assert(main.step.ship_scene.lighting.white_level() == 1.0)
	assert(main.smoke_symptoms.dose() == 0.0, "production symptom state recovers in bay")
	hazards.fire_burst()
	await _capture("bay-settled-white-15s")
	route.walk_to(route.anchor(ShipLayout.BAY_DOOR_ID, Vector3(0, 0, 1)))
	route.walk_to(route.anchor(ShipLayout.BAY_DOOR_ID, Vector3(0, 0, -1)))
	route.walk_to(route.anchor(ShipLayout.BAY_DOOR_ID, Vector3(3, 0, -1)))
	route.look_at(route.anchor(ShipLayout.POWER_DOOR_ID), 0)
	assert(main.hallway.level() == 0.0 and main.hallway.white_level() == 1.0)
	assert(main.power_room.level() == 0.0 and main.power_room.white_level() == 1.0)
	await _capture("section-41-regular-white")
	print("PASS production ventilation, lights, symptom recovery and positional vent audio")
	quit(0)

func _capture(label: String) -> void:
	main.wake_present.present_frame()
	main.player.present()
	for _frame in range(3):
		await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	assert(image.get_size() == Vector2i(2304, 1296), "capture uses requested resolution")
	var path := OUTPUT.path_join(label + ".png")
	assert(image.save_png(path) == OK, "capture writes")
	print("CAPTURE %s eye=%s density=%f red=%f white=%f dose=%f" % [path, main.player.camera.global_position, main.game.ventilation.density(), main.step.ship_scene.lighting.level(), main.step.ship_scene.lighting.white_level(), main.smoke_symptoms.dose()])
