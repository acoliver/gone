extends SceneTree

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name() != "headless", "actual MultiMesh readback requires a renderer, not the dummy server")
	var script := load("res://tests/bay_ceiling_test.gd") as GDScript
	var instance := script.new() as SimTestCase
	var passed := 0
	var failed := 0
	for method: Dictionary in script.get_script_method_list():
		if not String(method.name).begins_with("_check_"): continue
		instance.begin_test()
		instance.call(method.name)
		if instance.failure.is_empty():
			passed += 1
			print("PASS ", method.name)
		else:
			failed += 1
			print("FAIL ", method.name, ": ", instance.failure)
	await process_frame
	print("CEILING RENDER CONTRACTS passed=%d failed=%d" % [passed, failed])
	quit(1 if failed else 0)
