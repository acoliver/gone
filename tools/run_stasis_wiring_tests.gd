extends "res://tests/run_tests.gd"
## Retains the production runner's child-process script-error guard while
## selecting only the wiring graph and proof tests. The base has no CLI filter.

func _run_tests() -> void:
	var passed := 0
	var failed := 0
	for path: String in ["res://tests/stasis_wiring_routes_test.gd", "res://tests/stasis_wiring_proof_test.gd", "res://tests/stasis_wiring_production_test.gd", "res://tests/wires_test.gd", "res://tests/hazards_test.gd"]:
		var script := load(path) as GDScript
		if script == null or not script.can_instantiate():
			printerr("Cannot load focused wiring test: ",path)
			quit(1)
			return
		var instance: SimTestCase = script.new()
		for method: Dictionary in script.get_script_method_list():
			var method_name: String = method.name
			if not method_name.begins_with("test_"): continue
			instance.begin_test()
			instance.call(method_name)
			if instance.failure == "":
				passed += 1
			else:
				failed += 1
				print("FAIL ",path," :: ",method_name," :: ",instance.failure)
	print("passed=%d failed=%d" % [passed,failed])
	quit(1 if failed > 0 else 0)
