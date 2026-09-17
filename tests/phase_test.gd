extends SimTestCase
## Port of the phase.rs inline test module.

func all_phases() -> Array[int]:
	return [Phase.Wake.WAKING, Phase.Wake.AWAKE_IN_POD, Phase.Wake.EXITING_POD, Phase.Wake.STANDING]

func test_spawn_phase_is_waking_with_look_and_locomotion_locked() -> void:
	var machine := Phase.Machine.new()
	assert_true(machine.in_phase(Phase.Wake.WAKING), "spawn phase is Waking")
	assert_false(machine.look_allowed(), "look locked at spawn")
	assert_false(machine.locomotion_allowed(), "locomotion locked at spawn")

func test_wake_complete_advances_waking_to_awake_in_pod() -> void:
	var machine := Phase.Machine.new()
	assert_true(machine.wake_complete().equals(Phase.Transition.advanced(Phase.Wake.WAKING, Phase.Wake.AWAKE_IN_POD)), "wake-complete advances Waking to AwakeInPod")
	assert_true(machine.in_phase(Phase.Wake.AWAKE_IN_POD), "machine sits in AwakeInPod")

func test_exit_intent_advances_awake_in_pod_to_exiting_pod() -> void:
	var machine := Phase.Machine.new(Phase.Wake.AWAKE_IN_POD)
	assert_true(machine.request_pod_exit(Phase.InputEdge.RISING).equals(Phase.Transition.advanced(Phase.Wake.AWAKE_IN_POD, Phase.Wake.EXITING_POD)), "a fresh press advances AwakeInPod to ExitingPod")
	assert_true(machine.in_phase(Phase.Wake.EXITING_POD), "machine sits in ExitingPod")

func test_get_up_complete_advances_exiting_pod_to_standing() -> void:
	var machine := Phase.Machine.new(Phase.Wake.EXITING_POD)
	var result := machine.get_up_complete()
	assert_true(result.is_ok() and result.transition.equals(Phase.Transition.advanced(Phase.Wake.EXITING_POD, Phase.Wake.STANDING)), "get-up-complete advances ExitingPod to Standing")
	assert_true(machine.in_phase(Phase.Wake.STANDING), "machine sits in Standing")

func test_full_progression_reaches_standing_through_every_boundary() -> void:
	var machine := Phase.Machine.new()
	assert_false(machine.look_allowed() and machine.locomotion_allowed(), "both policies locked in Waking")
	assert_true(machine.wake_complete().equals(Phase.Transition.advanced(Phase.Wake.WAKING, Phase.Wake.AWAKE_IN_POD)), "wake boundary")
	assert_true(machine.look_allowed() and not machine.locomotion_allowed(), "look only after the wake boundary")
	assert_true(machine.request_pod_exit(Phase.InputEdge.RISING).equals(Phase.Transition.advanced(Phase.Wake.AWAKE_IN_POD, Phase.Wake.EXITING_POD)), "exit boundary")
	assert_true(machine.look_allowed() and not machine.locomotion_allowed(), "look composes with the get-up, locomotion still locked")
	var result := machine.get_up_complete()
	assert_true(result.is_ok() and result.transition.equals(Phase.Transition.advanced(Phase.Wake.EXITING_POD, Phase.Wake.STANDING)), "get-up boundary")
	assert_true(machine.look_allowed() and machine.locomotion_allowed(), "both unlocked at Standing")
	assert_true(machine.in_phase(Phase.Wake.STANDING), "machine sits in Standing")

func test_early_exit_intent_during_waking_is_ignored() -> void:
	var machine := Phase.Machine.new()
	assert_true(machine.request_pod_exit(Phase.InputEdge.RISING).equals(Phase.Transition.ignored()), "a fresh press during Waking is dropped")
	for _poll: int in range(4):
		assert_true(machine.request_pod_exit(Phase.InputEdge.HELD).equals(Phase.Transition.ignored()), "holds during Waking are dropped")
		assert_true(machine.in_phase(Phase.Wake.WAKING), "phase holds")
	assert_true(machine.wake_complete().equals(Phase.Transition.advanced(Phase.Wake.WAKING, Phase.Wake.AWAKE_IN_POD)), "the dropped intent must not queue")
	assert_true(machine.in_phase(Phase.Wake.AWAKE_IN_POD), "waking still stops at AwakeInPod")

func test_get_up_complete_during_waking_is_rejected() -> void:
	var machine := Phase.Machine.new()
	var result := machine.get_up_complete()
	assert_true(result.error != null and result.error.equals(Phase.PhaseError.get_up_before_exiting_pod(Phase.Wake.WAKING)), "get-up-complete during Waking is a rejected skip")
	assert_true(machine.in_phase(Phase.Wake.WAKING), "phase unchanged")

func test_get_up_complete_during_awake_in_pod_is_rejected() -> void:
	var machine := Phase.Machine.new(Phase.Wake.AWAKE_IN_POD)
	var result := machine.get_up_complete()
	assert_true(result.error != null and result.error.equals(Phase.PhaseError.get_up_before_exiting_pod(Phase.Wake.AWAKE_IN_POD)), "get-up-complete during AwakeInPod is a rejected skip")
	assert_true(machine.in_phase(Phase.Wake.AWAKE_IN_POD), "phase unchanged")

func test_exit_intent_during_exiting_pod_cannot_re_trigger() -> void:
	var machine := Phase.Machine.new(Phase.Wake.EXITING_POD)
	assert_true(machine.request_pod_exit(Phase.InputEdge.RISING).equals(Phase.Transition.ignored()), "a fresh press during ExitingPod is dropped")
	for _poll: int in range(4):
		assert_true(machine.request_pod_exit(Phase.InputEdge.HELD).equals(Phase.Transition.ignored()), "holds during ExitingPod are dropped")
		assert_true(machine.in_phase(Phase.Wake.EXITING_POD), "the authored get-up owns the body")

func test_exit_intent_during_standing_is_ignored() -> void:
	var machine := Phase.Machine.new(Phase.Wake.STANDING)
	for _poll: int in range(3):
		assert_true(machine.request_pod_exit(Phase.InputEdge.RISING).equals(Phase.Transition.ignored()), "exit intent at Standing is unbound")
		assert_true(machine.in_phase(Phase.Wake.STANDING), "phase holds")

func test_wake_complete_re_delivery_is_idempotent_in_every_later_phase() -> void:
	for start: int in all_phases().slice(1):
		var machine := Phase.Machine.new(start)
		assert_true(machine.wake_complete().equals(Phase.Transition.already_delivered()), "re-delivery in a later phase is a no-op")
		assert_true(machine.in_phase(start), "phase holds")

func test_get_up_complete_re_delivery_is_idempotent_in_standing() -> void:
	var machine := Phase.Machine.new(Phase.Wake.STANDING)
	var result := machine.get_up_complete()
	assert_true(result.is_ok() and result.transition.equals(Phase.Transition.already_delivered()), "re-delivery at Standing is a no-op")
	assert_true(machine.in_phase(Phase.Wake.STANDING), "phase holds")

func test_held_exit_intent_crossing_the_wake_boundary_does_not_exit() -> void:
	var machine := Phase.Machine.new()
	assert_true(machine.request_pod_exit(Phase.InputEdge.RISING).equals(Phase.Transition.ignored()), "the input went down before the boundary")
	for _poll: int in range(3):
		assert_true(machine.request_pod_exit(Phase.InputEdge.HELD).equals(Phase.Transition.ignored()), "the hold continues while waking runs")
	assert_true(machine.wake_complete().equals(Phase.Transition.advanced(Phase.Wake.WAKING, Phase.Wake.AWAKE_IN_POD)), "wake boundary")
	for _poll: int in range(5):
		assert_true(machine.request_pod_exit(Phase.InputEdge.HELD).equals(Phase.Transition.ignored()), "the post-boundary hold never fires")
		assert_true(machine.in_phase(Phase.Wake.AWAKE_IN_POD), "machine waits in AwakeInPod")
	assert_true(machine.request_pod_exit(Phase.InputEdge.RISING).equals(Phase.Transition.advanced(Phase.Wake.AWAKE_IN_POD, Phase.Wake.EXITING_POD)), "a fresh press after the boundary exits, exactly once")
	for _poll: int in range(3):
		assert_true(machine.request_pod_exit(Phase.InputEdge.RISING).equals(Phase.Transition.ignored()), "repeated presses cannot re-trigger")
		assert_true(machine.request_pod_exit(Phase.InputEdge.HELD).equals(Phase.Transition.ignored()), "holds cannot re-trigger")
	assert_true(machine.in_phase(Phase.Wake.EXITING_POD), "machine sits in ExitingPod")
	assert_false(machine.locomotion_allowed(), "the held intent never skips the get-up")

func test_held_intent_polled_in_awake_in_pod_is_dropped() -> void:
	var machine := Phase.Machine.new(Phase.Wake.AWAKE_IN_POD)
	assert_true(machine.wake_complete().equals(Phase.Transition.already_delivered()), "wake signal already consumed")
	assert_true(machine.request_pod_exit(Phase.InputEdge.HELD).equals(Phase.Transition.ignored()), "a hold first polled in AwakeInPod is a hold, not a press")
	assert_true(machine.in_phase(Phase.Wake.AWAKE_IN_POD), "phase holds")

func test_repeated_exit_intent_cannot_skip_the_get_up() -> void:
	var machine := Phase.Machine.new(Phase.Wake.AWAKE_IN_POD)
	assert_true(machine.request_pod_exit(Phase.InputEdge.RISING).equals(Phase.Transition.advanced(Phase.Wake.AWAKE_IN_POD, Phase.Wake.EXITING_POD)), "the first press exits")
	for _poll: int in range(10):
		assert_true(machine.request_pod_exit(Phase.InputEdge.RISING).equals(Phase.Transition.ignored()), "repeated presses stop at ExitingPod")
	assert_true(machine.in_phase(Phase.Wake.EXITING_POD), "machine waits for the authored motion")
	var result := machine.get_up_complete()
	assert_true(result.is_ok(), "get-up signal is legal here")
	assert_true(machine.in_phase(Phase.Wake.STANDING), "machine stands")

func test_standing_phase_never_regresses() -> void:
	var machine := Phase.Machine.new(Phase.Wake.STANDING)
	assert_true(machine.wake_complete().equals(Phase.Transition.already_delivered()), "wake re-delivery is a no-op")
	assert_true(machine.request_pod_exit(Phase.InputEdge.RISING).equals(Phase.Transition.ignored()), "exit intent is unbound")
	var result := machine.get_up_complete()
	assert_true(result.is_ok() and result.transition.equals(Phase.Transition.already_delivered()), "get-up re-delivery is a no-op")
	assert_true(machine.in_phase(Phase.Wake.STANDING), "Standing is terminal")

func test_look_policy_per_phase() -> void:
	var expected: Array = [
		[Phase.Wake.WAKING, false],
		[Phase.Wake.AWAKE_IN_POD, true],
		[Phase.Wake.EXITING_POD, true],
		[Phase.Wake.STANDING, true],
	]
	for entry: Array in expected:
		var phase: int = entry[0]
		var allowed: bool = entry[1]
		assert_true(Phase.look_allowed(phase) == allowed, "look in %s" % Phase.phase_name(phase))

func test_locomotion_policy_per_phase() -> void:
	for phase: int in all_phases():
		assert_true(Phase.locomotion_allowed(phase) == (phase == Phase.Wake.STANDING), "locomotion in %s" % Phase.phase_name(phase))

func test_in_phase_matches_only_itself() -> void:
	for phase: int in all_phases():
		for candidate: int in all_phases():
			assert_true(Phase.in_phase(phase, candidate) == (phase == candidate), "%s against %s" % [Phase.phase_name(phase), Phase.phase_name(candidate)])

func test_rejection_names_the_phase_and_leaves_the_machine_put() -> void:
	for start: int in all_phases().slice(0, 2):
		var machine := Phase.Machine.new(start)
		var result := machine.get_up_complete()
		assert_true(result.error != null and result.error.equals(Phase.PhaseError.get_up_before_exiting_pod(start)), "rejection names the offending phase")
		assert_true(machine.in_phase(start), "machine stays put")
		if result.error != null:
			var text := result.error._to_string()
			assert_true(text.contains("get-up-complete"), "display: " + text)
			assert_true(text.contains(Phase.phase_name(start)), "display: " + text)
