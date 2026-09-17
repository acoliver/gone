extends SceneTree
## Auto-discovering test runner. Loads every tests/*_test.gd, runs each
## test_* method, prints per-failure file/function/message plus a final
## "passed=X failed=Y" tally, and exits with code 1 on any failure.
## Run: godot --headless --path . -s tests/run_tests.gd

func _init() -> void:
	var passed := 0
	var failed := 0
	var test_files: Array[String] = []
	var directory := DirAccess.open("res://tests")
	if directory == null:
		push_error("cannot open res://tests")
		quit(1)
		return
	directory.list_dir_begin()
	var entry := directory.get_next()
	while entry != "":
		if entry.ends_with("_test.gd"):
			test_files.append(entry)
		entry = directory.get_next()
	directory.list_dir_end()
	test_files.sort()
	for test_file: String in test_files:
		var script: GDScript = load("res://tests/" + test_file)
		if script == null or not script.can_instantiate():
			print("FAIL %s :: <load> :: cannot load test script" % test_file)
			failed += 1
			continue
		var instance: SimTestCase = script.new()
		var method_names: Array[String] = []
		for method: Dictionary in script.get_script_method_list():
			var method_name: String = method["name"]
			if method_name.begins_with("test_"):
				method_names.append(method_name)
		method_names.sort()
		for method_name: String in method_names:
			instance.begin_test()
			instance.call(method_name)
			if instance.failure == "":
				passed += 1
			else:
				failed += 1
				print("FAIL %s :: %s :: %s" % [test_file, method_name, instance.failure])
	print("passed=%d failed=%d" % [passed, failed])
	quit(1 if failed > 0 else 0)
