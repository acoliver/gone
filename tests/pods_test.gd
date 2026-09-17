extends SimTestCase
## Port of the pods.rs inline test module.

func all_phases() -> Array[int]:
	return [Phase.Wake.WAKING, Phase.Wake.AWAKE_IN_POD, Phase.Wake.EXITING_POD, Phase.Wake.STANDING]

func pod_at(index: int, state: int) -> Pods.Pod:
	return Pods.Pod.new(Pods.PodId.try_new(index), state, Pods.PodPlacement.new(Vector2.ZERO, 0.0))

func assert_frozen_row(registry: Pods.PodRegistry, row_z: float, expected_yaw: float, expected_count: int, label: String) -> void:
	var row: Array[Pods.Pod] = []
	for pod: Pods.Pod in registry.pods():
		if absf(pod.placement().center.y - row_z) < 1e-6:
			row.append(pod)
	assert_int_equal(row.size(), expected_count, label)
	for pod: Pods.Pod in row:
		assert_true(absf(pod.placement().yaw_radians - expected_yaw) < 1e-6, label)

func test_frozen_registry_holds_seven_distinct_pods_in_two_rows() -> void:
	var registry := Pods.PodRegistry.frozen()
	assert_int_equal(registry.pods().size(), Pods.POD_COUNT, "seven pods")
	var seen: Array[int] = []
	for pod: Pods.Pod in registry.pods():
		seen.append(pod.id().index())
	seen.sort()
	var distinct: Array[int] = []
	for index: int in seen:
		if distinct.is_empty() or distinct.back() != index:
			distinct.append(index)
	assert_int_equal(distinct.size(), Pods.POD_COUNT, "ids must be distinct")
	var all_ids := Pods.PodId.all()
	for pod: Pods.Pod in registry.pods():
		var is_bay := false
		for id: Pods.PodId in all_ids:
			if id.equals(pod.id()):
				is_bay = true
		assert_true(is_bay, "every id is a bay id")
	assert_frozen_row(registry, Pods.ROW_A_Z, 0.0, 4, "row A faces +Z")
	assert_frozen_row(registry, Pods.ROW_B_Z, Pods.ROW_B_YAW, 3, "row B faces -Z")
	var players: Array[Pods.Pod] = []
	for pod: Pods.Pod in registry.pods():
		if Pods.is_player(pod.state()):
			players.append(pod)
	assert_int_equal(players.size(), 1, "exactly one player pod")
	assert_int_equal(players[0].id().index(), 6, "the player pod is id 6")
	assert_int_equal(registry.player_pod().id().index(), 6, "player_pod lookup")
	assert_true(absf(players[0].placement().center.y - Pods.ROW_B_Z) < 1e-6, "the player pod sits in row B")

func test_frozen_state_split_is_three_sealed_three_open_one_player() -> void:
	var registry := Pods.PodRegistry.frozen()
	var sealed := 0
	var empty_open := 0
	var player := 0
	for pod: Pods.Pod in registry.pods():
		if pod.state() == Pods.PodState.SEALED:
			sealed += 1
		elif pod.state() == Pods.PodState.EMPTY_OPEN:
			empty_open += 1
		elif Pods.is_player(pod.state()):
			player += 1
	assert_int_equal(sealed, 3, "three sealed pods")
	assert_int_equal(empty_open, 3, "three empty-open pods")
	assert_int_equal(player, 1, "exactly one player pod")

func test_frozen_layout_respects_room_aisle_and_hatch() -> void:
	assert_true(Pods.POD_HEIGHT <= Pods.ROOM_CEILING_HEIGHT, "pods fit under the ceiling")
	# Pod backs sit flush against the wall, so the room-bounds check rides
	# the rounding boundary. Vector2 components are f32 (matching the Rust
	# layout's f32 tuples), so |z| carries ~1e-7 of f32 rounding that the
	# f64 constants do not round away the way Rust's f32 sum did.
	const layout_epsilon := 1e-6
	var registry := Pods.PodRegistry.frozen()
	var room_half_length := Pods.ROOM_LENGTH / 2.0
	var room_half_width := Pods.ROOM_WIDTH / 2.0
	for pod: Pods.Pod in registry.pods():
		var placement := pod.placement()
		var x := placement.center.x
		var z := placement.center.y
		assert_true(absf(x) + Pods.POD_WIDTH / 2.0 <= room_half_length + layout_epsilon, "pod inside X")
		assert_true(absf(z) + Pods.POD_LENGTH / 2.0 <= room_half_width + layout_epsilon, "pod inside Z")
		var aisle_face := absf(z) - Pods.POD_LENGTH / 2.0
		assert_true(aisle_face >= Pods.AISLE_HALF_WIDTH + Controller.POD_EXIT_CLEARANCE, "pod clears the aisle: face %s" % str(aisle_face))
	var hatch := registry.hatch()
	assert_true(absf(hatch.center.x - Pods.ROOM_LENGTH / 2.0) < 1e-6, "hatch on the +X wall")
	assert_true(absf(hatch.center.y) < 1e-6, "hatch centered on the wall")
	assert_true(sin(hatch.yaw_radians) < 0.0, "hatch faces -X")
	assert_true(absf(cos(hatch.yaw_radians)) < 1e-6, "hatch faces into the room")

func test_occupancy_counts_follow_the_phase() -> void:
	var registry := Pods.PodRegistry.frozen()
	for phase: int in all_phases():
		assert_true(registry.zero_non_player_occupancy(phase), "non-player pods are empty in %s" % Phase.phase_name(phase))
	assert_int_equal(registry.occupancy_count(Phase.Wake.WAKING), 1, "one occupied pod in Waking")
	assert_int_equal(registry.occupancy_count(Phase.Wake.AWAKE_IN_POD), 1, "one occupied pod in AwakeInPod")
	assert_int_equal(registry.occupancy_count(Phase.Wake.EXITING_POD), 1, "one occupied pod in ExitingPod")
	assert_int_equal(registry.occupancy_count(Phase.Wake.STANDING), 0, "no occupied pods at Standing")
	assert_true(registry.player_pod().occupied(Phase.Wake.EXITING_POD), "the player pod is occupied mid get-up")
	assert_false(registry.player_pod().occupied(Phase.Wake.STANDING), "the player pod vacates at Standing")

func test_duplicate_pod_ids_are_rejected() -> void:
	var pods: Array[Pods.Pod] = [
		pod_at(0, Pods.PodState.PLAYER),
		pod_at(1, Pods.PodState.SEALED),
		pod_at(2, Pods.PodState.EMPTY_OPEN),
		pod_at(3, Pods.PodState.SEALED),
		pod_at(4, Pods.PodState.EMPTY_OPEN),
		pod_at(5, Pods.PodState.SEALED),
		pod_at(6, Pods.PodState.EMPTY_OPEN),
	]
	pods[6] = pods[0]
	var result := Pods.PodRegistry.try_new(pods)
	assert_true(result.error != null and result.error.equals(Pods.PodRegistryError.duplicate_pod_id(pods[0].id())), "duplicate ids must be rejected")
	if result.error != null:
		var text := result.error._to_string()
		assert_true(text.contains("duplicate"), "display: " + text)

func test_player_pod_count_is_enforced() -> void:
	var none: Array[Pods.Pod] = [
		pod_at(0, Pods.PodState.SEALED),
		pod_at(1, Pods.PodState.EMPTY_OPEN),
		pod_at(2, Pods.PodState.SEALED),
		pod_at(3, Pods.PodState.EMPTY_OPEN),
		pod_at(4, Pods.PodState.SEALED),
		pod_at(5, Pods.PodState.EMPTY_OPEN),
		pod_at(6, Pods.PodState.SEALED),
	]
	var none_result := Pods.PodRegistry.try_new(none)
	assert_true(none_result.error != null and none_result.error.equals(Pods.PodRegistryError.player_pod_count(0)), "zero player pods rejected")
	var two: Array[Pods.Pod] = [
		pod_at(0, Pods.PodState.PLAYER),
		pod_at(1, Pods.PodState.SEALED),
		pod_at(2, Pods.PodState.EMPTY_OPEN),
		pod_at(3, Pods.PodState.SEALED),
		pod_at(4, Pods.PodState.EMPTY_OPEN),
		pod_at(5, Pods.PodState.SEALED),
		pod_at(6, Pods.PodState.PLAYER),
	]
	var two_result := Pods.PodRegistry.try_new(two)
	assert_true(two_result.error != null and two_result.error.equals(Pods.PodRegistryError.player_pod_count(2)), "two player pods rejected")

func test_valid_pod_sets_round_trip_through_try_new() -> void:
	var frozen := Pods.PodRegistry.frozen()
	var result := Pods.PodRegistry.try_new(frozen.pods().duplicate())
	assert_true(result.is_ok(), "the frozen set is valid")
	if result.is_ok():
		assert_true(result.registry.equals(frozen), "the rebuilt registry equals frozen")
		for pod: Pods.Pod in frozen.pods():
			assert_true(frozen.pod(pod.id()).equals(pod), "pod lookup by id reads back the stored pod")

func test_permuted_pod_sets_still_look_up_every_id_correctly() -> void:
	var frozen := Pods.PodRegistry.frozen()
	var reversed_pods: Array[Pods.Pod] = frozen.pods().duplicate()
	reversed_pods.reverse()
	var reversed_result := Pods.PodRegistry.try_new(reversed_pods)
	assert_true(reversed_result.is_ok(), "a reversed set is valid")
	if reversed_result.is_ok():
		var reversed := reversed_result.registry
		assert_true(reversed.equals(frozen), "order-independent registry contents")
		for id: Pods.PodId in Pods.PodId.all():
			assert_true(reversed.pod(id).id().equals(id), "reversed input, id %d" % id.index())
		assert_true(reversed.player_pod().id().equals(frozen.player_pod().id()), "the player pod is found by identity")
	var swapped_pods: Array[Pods.Pod] = frozen.pods().duplicate()
	var held := swapped_pods[1]
	swapped_pods[1] = swapped_pods[5]
	swapped_pods[5] = held
	var swapped_result := Pods.PodRegistry.try_new(swapped_pods)
	assert_true(swapped_result.is_ok(), "a swapped set is valid")
	if swapped_result.is_ok():
		var swapped := swapped_result.registry
		assert_true(swapped.equals(frozen), "a swapped input builds the same registry")
		for id: Pods.PodId in Pods.PodId.all():
			assert_true(swapped.pod(id).id().equals(id), "swapped input, id %d" % id.index())
		assert_true(swapped.player_pod().placement().equals(frozen.player_pod().placement()), "the player pod moves with its pod, not its input position")

func test_pod_ids_cover_the_bay_range_only() -> void:
	for index: int in range(Pods.POD_COUNT):
		var id := Pods.PodId.try_new(index)
		assert_true(id != null and id.index() == index, "bay indices are ids")
	assert_true(Pods.PodId.try_new(Pods.POD_COUNT) == null, "the pod count is out of range")
	assert_true(Pods.PodId.try_new(255) == null, "255 is out of range")
	var position := 0
	for id: Pods.PodId in Pods.PodId.all():
		assert_int_equal(id.index(), position, "ALL lists ids in order")
		position += 1
