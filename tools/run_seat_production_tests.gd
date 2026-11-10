extends "res://tests/run_tests.gd"
## Focused production seat/pickup contracts retain the inherited child error guard.

func _run_tests() -> void:
	var passed := 0
	var failed := 0
	for path: String in ["res://tests/seat_production_test.gd", "res://tests/bay_ceiling_test.gd", "res://tests/rod_test.gd", "res://tests/click_actions_test.gd", "res://tests/hatch_resistance_test.gd", "res://tests/bay_fixtures_test.gd", "res://tests/ceiling_fixture_test.gd"]:
		var script := load(path) as GDScript
		if script == null or not script.can_instantiate():
			printerr("Cannot load focused production test: ",path)
			quit(1)
			return
		var instance: SimTestCase = script.new()
		for method: Dictionary in script.get_script_method_list():
			var method_name: String = method.name
			if not method_name.begins_with("test_"): continue
			instance.begin_test()
			instance.call(method_name)
			if instance.failure == "": passed += 1
			else:
				failed += 1
				print("FAIL ",path," :: ",method_name," :: ",instance.failure)
	print("passed=%d failed=%d" % [passed,failed])
	quit(1 if failed > 0 else 0)
