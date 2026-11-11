extends SceneTree
## Paired wardrobe-local probe cost under the unchanged smoke-policy limits.

func _initialize() -> void:
	_run.call_deferred()

func _stats(values: Array[float]) -> Dictionary:
	var ordered := values.duplicate()
	ordered.sort()
	var total := 0.0
	for value: float in values: total += value
	return {"Count": values.size(), "MeanMs": total / values.size(), "P95Ms": ordered[ceili(values.size() * .95) - 1]}

func _run() -> void:
	assert(DisplayServer.get_name() != "headless")
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 1)
	var policy: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://harness/perf-policy.json"))
	root.size = Vector2i(policy.resolution.width, policy.resolution.height)
	root.content_scale_size = root.size
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	RenderingServer.viewport_set_measure_render_time(root.get_viewport_rid(), true)
	var main := (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(main)
	main.set_physics_process(false)
	DemoStart.quarters(main.game, main.player)
	DemoStart.prepare_ship(main.step.ship_scene, main.player)
	main.player.set_process(false)
	main.player.set_physics_process(false)
	main.camera.current = true
	QuartersCapture.pose(main.camera, "wardrobe")
	var report := {"policy": policy.policy_version, "resolution": policy.resolution, "states": {}}
	for state: String in ["remembered", "present"]:
		main.game.quarters.state = QuartersMemory.State.REMEMBERED if state == "remembered" else QuartersMemory.State.PRESENT
		for tick: int in range(60): main.step.ship_scene.tick_rooms()
		var furnishing: Node3D = main.step.ship_scene.quarters.remembered if state == "remembered" else main.step.ship_scene.quarters.present
		var probe := furnishing.get_node("Placement_wardrobe/MedalReflection") as ReflectionProbe
		var lanes := {}
		for lane: String in ["local-probe-off", "full", "refreshing"]:
			probe.visible = lane != "local-probe-off"
			probe.update_mode = ReflectionProbe.UPDATE_ALWAYS if lane == "refreshing" else ReflectionProbe.UPDATE_ONCE
			for frame: int in range(policy.warmup_frames):
				RenderingServer.force_draw(false)
				await process_frame
			var frames: Array[float] = []
			var gpu: Array[float] = []
			var cpu: Array[float] = []
			for frame: int in range(policy.sample_frames):
				var start := Time.get_ticks_usec()
				RenderingServer.force_draw(false)
				await process_frame
				await RenderingServer.frame_post_draw
				frames.append((Time.get_ticks_usec() - start) / 1000.0)
				gpu.append(RenderingServer.viewport_get_measured_render_time_gpu(root.get_viewport_rid()))
				cpu.append(RenderingServer.viewport_get_measured_render_time_cpu(root.get_viewport_rid()))
			lanes[lane] = {"frame": _stats(frames), "gpu": _stats(gpu), "render_cpu": _stats(cpu),
				"texture_memory_bytes": RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TEXTURE_MEM_USED)}
		var full: Dictionary = lanes.full.frame
		lanes["gpu_timing_available"] = lanes.full.gpu.MeanMs > 0
		lanes["added_mean_frame_ms"] = full.MeanMs - lanes["local-probe-off"].frame.MeanMs
		lanes["added_render_cpu_ms"] = lanes.full.render_cpu.MeanMs - lanes["local-probe-off"].render_cpu.MeanMs
		if lanes.gpu_timing_available:
			lanes["added_mean_gpu_ms"] = lanes.full.gpu.MeanMs - lanes["local-probe-off"].gpu.MeanMs
		lanes["policy_pass"] = full.MeanMs <= policy.thresholds.mean_ms_max and full.P95Ms <= policy.thresholds.p95_ms_max
		report.states[state] = lanes
	var file := FileAccess.open(args[0], FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t") + "\n")
	print(JSON.stringify(report))
	quit(0 if report.states.remembered.policy_pass and report.states.present.policy_pass else 1)
