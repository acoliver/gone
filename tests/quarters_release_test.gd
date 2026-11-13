extends SimTestCase

func test_manual_release_selects_at_the_visible_control_and_uses_corridor_policy() -> void:
	var game := Game.new(114)
	var interactions := Interactions.new(game.layout)
	var context := Interactions.Context.new()
	context.game = game
	context.motion = PlayerMotion.new()
	context.walking = true
	context.deck = 16
	context.foot = Vector3(44.1, -10.695, 0.4)
	context.eye = context.foot + Vector3.UP * 1.35
	context.forward = (Vector3(44.1, -9.7, 1.43) - context.eye).normalized()
	var plane := InputPlane.new()
	plane.offer_press(InputPlane.Buttons.INTERACT)
	var selected := interactions.process(plane, context)
	assert_true(selected == &"D16-QUARTERS-RELEASE", "aiming at the release, outside the leaf rectangle, selects its own target")
	assert_int_equal(game.doors.snapshot(QuartersLayout.DOOR).releases, 1, "control dispatches the existing manual-release policy")
	assert_int_equal(plane.pending_edges(), 0, "one input edge consumed")

	var target := interactions.target_for(QuartersLayout.RELEASE, 16, context.foot)
	assert_true(interactions.target_visible(target, context.eye, game.collision), "wall does not hide its corridor-face control")
	context.deck = 14
	assert_true(Interactions.hit_distance(target, context, []) < 0, "D14 cannot operate the D16 release")
	context.deck = 16
	context.foot.z = 2.5
	context.eye.z = 2.5
	context.forward = (Vector3(44.1, -9.7, 1.43) - context.eye).normalized()
	assert_true(Interactions.hit_distance(target, context, []) < 0, "release is not operable through its back")
func test_manual_release_has_recess_handle_and_shared_label() -> void:
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), ["--headless", "--path", ProjectSettings.globalize_path("res://"), "-s", "tests/quarters_release_scene_checks.gd"], output, true)
	var text := "".join(output)
	assert_int_equal(code, 0, text)
	assert_false(text.contains("ERROR:"), text)
	assert_true(text.contains("QUARTERS RELEASE PASS"), "hardware and label checks completed")
