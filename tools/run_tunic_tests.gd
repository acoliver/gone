extends "res://tests/run_tests.gd"
## The normal child-process error guard, with the tunic integration cohort.

func _run_tests() -> void:
	var passed := 0
	var failed := 0
	for path: String in ["tunic_props", "medal_pbr", "quarters_clothes", "quarters_demo_materials", "fixture_aging"]:
		var script := load("res://tests/%s_test.gd" % path) as GDScript
		assert(script != null and script.can_instantiate())
		var instance: SimTestCase = script.new()
		for method: Dictionary in script.get_script_method_list():
			if not String(method.name).begins_with("test_"): continue
			instance.begin_test()
			instance.call(method.name)
			if instance.failure.is_empty(): passed += 1
			else:
				failed += 1
				print("FAIL %s :: %s :: %s" % [path, method.name, instance.failure])
	print("passed=%d failed=%d" % [passed, failed])
	quit(1 if failed > 0 else 0)
