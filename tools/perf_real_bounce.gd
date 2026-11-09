extends SceneTree

const Bounce := preload("res://app/real_bounce.gd")
const WARMUP := 120
const SAMPLES := 300
var output: String

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 1, "usage: perf_real_bounce.gd -- output.json")
	output = args[0]
	_run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name() != "headless")
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.content_scale_size = Vector2i(1152, 648)
	root.size = root.content_scale_size
	DisplayServer.window_set_size(root.size)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_2X
	RenderingServer.viewport_set_measure_render_time(root.get_viewport_rid(), true)
	var result := {"mode": OS.get_environment(Bounce.ENVIRONMENT_VARIABLE), "resolution": [1152,648], "warmup": WARMUP, "samples": SAMPLES, "circuits": {}}
	for white: bool in [true, false]:
		var game := Game.new(91)
		game.light_hallway()
		if white: game.press_console()
		for tick: int in range(BayVentilation.CLEAR_TICKS): game.ventilation.tick(true)
		var world := Node3D.new()
		root.add_child(world)
		var ship := ShipScene.build_into(world, game)
		ship.hazards.auto_bursts = false
		ship.prepare_near(Vector3(10,0,0))
		ship.prepare_near(Vector3(26,0,0))
		var camera := Camera3D.new()
		world.add_child(camera)
		camera.current = true
		camera.fov = 76
		camera.position = Vector3(18,1.6,.25)
		camera.look_at(Vector3(30,1.5,0))
		for frame: int in range(WARMUP):
			await process_frame
			await RenderingServer.frame_post_draw
		var elapsed: Array[float] = []
		var gpu: Array[float] = []
		var previous := Time.get_ticks_usec()
		for frame: int in range(SAMPLES):
			var phase := float(frame) / SAMPLES
			camera.position = Vector3(18 + 16 * sin(phase * PI), 1.6, .25)
			camera.look_at(Vector3(36 if phase < .5 else 17,1.5,0))
			await process_frame
			await RenderingServer.frame_post_draw
			var now := Time.get_ticks_usec()
			elapsed.append((now - previous) / 1000.0)
			previous = now
			gpu.append(RenderingServer.viewport_get_measured_render_time_gpu(root.get_viewport_rid()))
		var circuit := "secondary-white" if white else "emergency"
		result.circuits[circuit] = {"frame_ms": elapsed, "gpu_ms": gpu}
		print("GI PERF ", result.mode, " ", circuit, " mean_ms=", _mean(elapsed), " gpu_ms=", _mean(gpu))
		var env := (world.get_node("RoomEnvironment") as WorldEnvironment).environment
		env.sdfgi_enabled = false
		await process_frame
		await RenderingServer.frame_post_draw
		world.free()
		await process_frame
	FileAccess.open(output, FileAccess.WRITE).store_string(JSON.stringify(result, "\t") + "\n")
	quit()

func _mean(values: Array[float]) -> float:
	var total := 0.0
	for value: float in values: total += value
	return total / values.size()
