extends SceneTree
## Native main.tscn opening first, then explicitly separate inspection cameras.

var OUT := "res://"+OS.get_environment("STASIS_WIRING_RESULTS")+"/" if OS.has_environment("STASIS_WIRING_RESULTS") else "res://tmp/verify-stasis-wiring/production-corrected/"
var main: Node3D
var inspection: Camera3D
var captures: Array[Dictionary] = []
var ordinary_frames: Array[Dictionary] = []
var activated := false
var activation_frame := -1
var normal_seen: Dictionary = {}
var deadline: int
var fingerprints_before: Dictionary
var verified_snapshot: Dictionary

func _init() -> void:
	_run.call_deferred()

func _v(value: Vector3) -> Array:
	return [value.x,value.y,value.z]

func _write(name: String, value: Variant) -> void:
	var file := FileAccess.open(OUT+name,FileAccess.WRITE)
	assert(file!=null,"capture output is writable")
	file.store_string(JSON.stringify(value,"\t")+"\n")

func _fingerprints(expected: Dictionary) -> Dictionary:
	var result := {}
	for path: String in expected:
		var actual := FileAccess.get_sha256("res://"+path)
		if actual != expected[path]:
			printerr("verified snapshot mismatch: "+path)
			quit(1)
			return {}
		result[path] = actual
	return result

func _snapshot_inputs() -> Dictionary:
	var file := FileAccess.open(OUT+"build-snapshot.json",FileAccess.READ)
	if file==null:
		printerr("required verified production build snapshot")
		quit(1)
		return {}
	var document := JSON.new()
	if document.parse(file.get_as_text())!=OK:
		printerr("invalid production build snapshot JSON")
		quit(1)
		return {}
	verified_snapshot = document.data
	var expected: Dictionary = verified_snapshot.inputs_sha256.duplicate()
	expected.merge(verified_snapshot.outputs_sha256)
	expected.merge(verified_snapshot.protected_before)
	expected[OUT.trim_prefix("res://")+"build-snapshot.json"] = FileAccess.get_sha256(OUT+"build-snapshot.json")
	if _fingerprints(expected).is_empty(): return {}
	var source := "res://assets/props/stasis-wiring/production-installation.glb"
	var imported := ConfigFile.new()
	if imported.load(source+".import")!=OK:
		printerr("production import record required")
		quit(1)
		return {}
	var resource: String = imported.get_value("remap","path")
	var checksum := resource.get_basename()+".md5"
	var checksums := FileAccess.get_file_as_string(checksum)
	if not checksums.contains('source_md5="'+FileAccess.get_md5(source)+'"') or not checksums.contains('dest_md5="'+FileAccess.get_md5(resource)+'"'):
		printerr("production import checksum does not match current GLB/resource")
		quit(1)
		return {}
	for path: String in [source+".import",resource,checksum]:
		expected[path.trim_prefix("res://")] = FileAccess.get_sha256(path)
	return _fingerprints(expected)

func _draw() -> void:
	RenderingServer.call_deferred("force_draw",false)
	await RenderingServer.frame_post_draw

func _sample() -> Dictionary:
	return {"frame":Engine.get_process_frames(),"wall_usec":Time.get_ticks_usec(),"physics_frame":Engine.get_physics_frames(),
		"process_ms":Performance.get_monitor(Performance.TIME_PROCESS)*1000.0,
		"physics_ms":Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS)*1000.0,
		"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
		"objects":Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME),
		"primitives":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)}

func _save(label: String, camera: Camera3D, diagnostic: bool) -> void:
	await _draw()
	var image := root.get_texture().get_image()
	assert(image!=null and image.get_size()==Vector2i(1280,900),"native viewport readback")
	var path := OUT+label+".png"
	assert(image.save_png(path)==OK,"save native capture")
	var row := {"path":ProjectSettings.globalize_path(path),"sha256":FileAccess.get_sha256(path),"diagnostic_only":diagnostic,
		"camera_world_m":_v(camera.global_position),"camera_bay_m":_v(main.game.layout.bay_to_world().affine_inverse()*camera.global_position),
		"forward_world":_v(-camera.global_basis.z),"fov":camera.fov,"additional_lights":0,"material_overrides":0,
		"wake_tick":main.game.wake_state.current_tick(),"phase":Phase.phase_name(main.game.phase.current()),
		"eyes":main.wake_pass.params(),"wake_overlay_visible":main.wake_pass.visible,
		"smoke_density":main.game.ventilation.density(),"performance_frame":_sample()}
	captures.append(row)
	print("CAPTURE_SAVED ",label," tick=",row.wake_tick," phase=",row.phase)
	_write("capture-progress.json",captures)

func _space(pressed: bool) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = KEY_SPACE
	event.keycode = KEY_SPACE
	event.pressed = pressed
	Input.parse_input_event(event)

func _ordinary() -> bool:
	while Time.get_ticks_msec()<deadline:
		await process_frame
		await _draw()
		ordinary_frames.append(_sample())
		var openness: float = main.wake_pass.params().lid_openness
		var tick: int = main.game.wake_state.current_tick()
		if not normal_seen.has("blink-one") and openness>=0.30 and tick<130:
			normal_seen["blink-one"] = true
			await _save("normal-opening-blink-one",main.camera,false)
		if not normal_seen.has("blink-two") and openness>=0.65 and not main.game.wake_state.is_complete():
			normal_seen["blink-two"] = true
			await _save("normal-opening-blink-two",main.camera,false)
		if not normal_seen.has("open-eye") and openness>=0.95:
			normal_seen["open-eye"] = true
			await _save("normal-opening-open-eye",main.camera,false)
		if main.game.phase.current()==Phase.Wake.AWAKE_IN_POD and not normal_seen.has("awake"):
			await _save("normal-opening-awake-in-pod",main.camera,false)
			normal_seen["awake"] = Engine.get_process_frames()
		if normal_seen.has("awake") and not activated and Engine.get_process_frames()>int(normal_seen.awake)+6:
			activated = true
			activation_frame = Engine.get_process_frames()
			_space(true)
		if activated and Engine.get_process_frames()>activation_frame+2:
			_space(false)
		if main.player.motion.state()==PlayerMotion.BodyState.GET_UP and main.player.position.y>main.game.exit_path.poses()[0].head().y+.05 and not normal_seen.has("get-up"):
			normal_seen["get-up"] = true
			await _save("normal-opening-get-up",main.camera,false)
		if main.game.phase.current()==Phase.Wake.STANDING:
			_space(false)
			for i in range(Player.GET_UP_LOOK_TICKS+5):
				await process_frame
				await _draw()
			await _save("normal-opening-standing",main.camera,false)
			return true
	return false

func _shot(label: String, eye: Vector3, target: Vector3, fov: float, world: bool = false) -> void:
	var frame: Transform3D = Transform3D.IDENTITY if world else main.game.layout.bay_to_world()
	inspection.global_position = frame*eye
	inspection.look_at(frame*target)
	inspection.fov = fov
	inspection.current = true
	for i in range(12):
		await process_frame
		await _draw()
	var samples: Array[Dictionary] = []
	var start := Time.get_ticks_usec()
	for i in range(30):
		await process_frame
		await _draw()
		samples.append(_sample())
	await _save(label,inspection,true)
	captures[-1]["fixed_camera_frames"] = samples
	captures[-1]["sample_wall_ms"] = (Time.get_ticks_usec()-start)/1000.0
	captures[-1]["performance_scope"] = "30 native fixed-camera inspection frames, main processing frozen, production effects frozen; includes readback, not isolated GPU time"

func _run() -> void:
	assert(DisplayServer.get_name()!="headless","native GPU required")
	root.size = Vector2i(1280,900)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.content_scale_size = root.size
	DisplayServer.window_set_size(root.size)
	DirAccess.make_dir_recursive_absolute(OUT)
	fingerprints_before = _snapshot_inputs()
	if fingerprints_before.is_empty(): return
	main = (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(main)
	var before_colliders: int = main.game.colliders.size()
	deadline = Time.get_ticks_msec()+120000
	var got_up := await _ordinary()
	_write("normal-frame-performance.json",ordinary_frames)
	_write("normal-opening-result.json",{"ordinary_input":"Input.parse_input_event physical Space press/release, through unmodified Player device adapter",
		"standing_reached":got_up,"captures_seen":normal_seen,"power_calls":0,"teleports":0,"inspection_camera":false,
		"wake_smoke_eyes_unmodified":true,"colliders":main.game.colliders.size(),"frame_samples":ordinary_frames.size()})
	assert(got_up,"ordinary Space input must reach Standing without teleport or phase changes")
	assert(normal_seen.has("get-up"),"capture a naturally rendered elevated get-up pose, not just the phase edge")
	# Only after the ordinary opening is recorded, inspect the installed room.
	main.process_mode = Node.PROCESS_MODE_DISABLED
	main.wake_pass.visible = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	inspection = Camera3D.new()
	inspection.near = .008
	inspection.far = 60.0
	root.add_child(inspection)
	await _shot("diagnostic-emergency-routing",Vector3(1.3,1.7,.4),Vector3(-2.9,2.6,-2.2),85)
	await _shot("diagnostic-emergency-fault",Vector3(-.6,2.13,.1),Vector3(-.6,2.80,-.6),60)
	var lighting := main.find_child("Lighting",true,false) as Lighting
	assert(main.game.press_console(),"diagnostic white circuit uses existing console transition")
	for i in range(60): lighting.process_frame(1.0/60.0)
	await _shot("diagnostic-white-source",Vector3(-5.35,2.53,-2.76),Vector3(-5.86,2.75,-3.10),40)
	await _shot("diagnostic-white-routing",Vector3(-2.5,1.85,-1.0),Vector3(-4.65,2.1,-3.3),74)
	await _shot("diagnostic-white-floor-entry",Vector3(-4.05,.70,-3.12),Vector3(-4.10,.17,-3.95),54)
	await _shot("diagnostic-white-fault",Vector3(-.6,2.18,-.05),Vector3(-.6,2.78,-.61),65)
	await _shot("diagnostic-white-three-tips",Vector3(-.61,2.43,-.31),Vector3(-.61,2.54,-.61),61)
	await _shot("diagnostic-white-tip-one-macro",Vector3(-.752,2.484,-.548),Vector3(-.770,2.491,-.587),28)
	await _shot("diagnostic-white-fallen-fragment",Vector3(-.92,.52,-.68),Vector3(-.6,.022,-1.4),62)
	var hall: AABB = main.game.layout.section(&"D14-S-041").bounds()
	var eye := Vector3(hall.position.x+2, hall.position.y+1.65,hall.get_center().z)
	await _shot("diagnostic-white-non-bay-hallway",eye,eye+Vector3(5,0,0),70,true)
	assert(main.game.colliders.size()==before_colliders,"capture leaves collision inventory unchanged")
	var fingerprints_after := _fingerprints(fingerprints_before)
	if fingerprints_after.is_empty(): return
	var protected_after := {}
	for path: String in verified_snapshot.protected_before:
		protected_after[path] = fingerprints_after[path]
	var readbacks := {}
	for name: String in ["normal-frame-performance.json","normal-opening-result.json"]:
		readbacks[OUT.trim_prefix("res://")+name] = FileAccess.get_sha256(OUT+name)
	_write("capture-manifest.json",{"root":"res://main.tscn","display":DisplayServer.get_name(),"adapter":RenderingServer.get_video_adapter_name(),
		"fingerprints_before":fingerprints_before,"fingerprints_after":fingerprints_after,
		"protected_before":verified_snapshot.protected_before,"protected_after":protected_after,
		"source_preserved":fingerprints_before==fingerprints_after,"readback_sha256":readbacks,
		"size":[1280,900],"captures":captures,"ordinary_opening_precedes_diagnostics":true,"ordinary_space_get_up":got_up,
		"diagnostic_changes":["inspection camera","main processing frozen after normal get-up","eyelid overlay hidden only for inspection","existing secondary-white console circuit"],
		"additional_lights":0,"material_changes":0,"timing_smoke_eyes_power_gameplay_sources_changed":verified_snapshot.protected_before!=protected_after,
		"colliders_before_after":[before_colliders,main.game.colliders.size()],"performance_limit":"Concurrent sibling Godot processes recorded by launcher; no isolated throughput claim; no baseline render comparison.",
		"visual_judgment":"Parent image-comparer required"})
	print("PRODUCTION_CAPTURE_PASS captures=",captures.size()," ordinary_space_get_up=",got_up)
	quit(0)
