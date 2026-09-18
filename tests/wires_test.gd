extends SimTestCase
## Visual-half pins for issue #34: authored hanging-wire meshes under
## the torn ceiling — looped bundles, dangling strands, and split
## frayed ends along authored sag curves, all deterministic, above the
## camera envelope, swinging on S-bends, crossing the lying wake view's
## cone, and sharing one warm dark-grey insulation material.

## No wire dips below this height anywhere (tube surface included).
const CLEARANCE_FLOOR: float = 2.1
## An anchored end sits at least this high: at a torn tray underside.
const ANCHOR_HEIGHT: float = 2.9
## The spark strobes sit this far under their tray centers (Hazards).
const SPARK_DROP: float = 0.2

func test_wire_inventory_is_the_authored_mix() -> void:
	var wires := Placement.hanging_wires()
	assert_int_equal(wires.size(), 12, "the authored strand count stays pinned")
	var loops := 0
	var strands := 0
	var frays := 0
	for wire: Placement.HangingWire in wires:
		assert_int_equal(wire.points.size(), Placement.HANGING_WIRE_SAMPLES,
			"every wire samples the authored centerline resolution")
		assert_float_in_range(wire.radius, 0.008, 0.042,
			"strand radii stay in the authored band")
		var anchored_ends := 0
		for end: Vector3 in [wire.points.front(), wire.points.back()]:
			if end.y >= ANCHOR_HEIGHT:
				anchored_ends += 1
		match anchored_ends:
			2:
				loops += 1
			1:
				strands += 1
			0:
				frays += 1
	assert_int_equal(loops, 5, "looped bundles: both ends anchored at the tear")
	assert_int_equal(strands, 5, "single hanging strands: one anchored end")
	assert_int_equal(frays, 2, "split frayed ends: thin offshoots off parent wires")

func test_every_wire_clears_the_camera_envelope() -> void:
	var wires := Placement.hanging_wires()
	var lowest := INF
	for wire: Placement.HangingWire in wires:
		for point: Vector3 in wire.points:
			lowest = minf(lowest, point.y - wire.radius)
		for end: Vector3 in [wire.points.front(), wire.points.back()]:
			if end.y >= ANCHOR_HEIGHT:
				assert_float_in_range(end.y, ANCHOR_HEIGHT, Pods.ROOM_CEILING_HEIGHT,
					"anchored ends hang from the torn-ceiling band")
	assert_true(lowest >= CLEARANCE_FLOOR,
		"no wire dips below the %.1f m clearance floor, got %s" % [CLEARANCE_FLOOR, str(lowest)])
	assert_true(CLEARANCE_FLOOR - PlacementTruth.STANDING_EYE_HEIGHT >= 0.4,
		"the clearance floor holds margin over the standing eye height")

func test_spark_strobe_positions_carry_wire_anchor_clusters() -> void:
	var trays := Placement.cable_trays()
	var wires := Placement.hanging_wires()
	for index: int in range(trays.size()):
		var spot: Vector3 = trays[index].center + Vector3(0.0, -SPARK_DROP, 0.0)
		var near := 0
		for wire: Placement.HangingWire in wires:
			for end: Vector3 in [wire.points.front(), wire.points.back()]:
				if end.distance_to(spot) <= 0.45:
					near += 1
		assert_true(near >= 2,
			"spark spot %d at %s carries a wire anchor cluster, got %d" % [index, str(spot), near])

## The lying wake view: the exit path's first pose head (the spawn eye),
## at the player pod's yaw and the authored look pitch one stop short of
## vertical, carrying the Camera3D default vertical fov. The authored
## pod-area wires must cross inside that cone so the up-facing beats
## read wires from the first opening blink.
func test_pod_view_cone_carries_three_wire_crossings() -> void:
	var eye: Vector3 = PlacementTruth.player_exit_path().poses()[0].head()
	var yaw: float = Pods.PodRegistry.frozen().player_pod().placement().yaw_radians
	var forward: Vector3 = (Basis(Vector3.UP, yaw) * Basis(Vector3.RIGHT, InputPlane.PITCH_LIMIT)) \
		* Vector3.FORWARD
	var threshold: float = cos(deg_to_rad(Camera3D.new().fov * 0.5))
	var crossings := 0
	var crossing_loops := 0
	var crossing_strands := 0
	var sagging_loop := false
	for wire: Placement.HangingWire in Placement.hanging_wires():
		var anchored_ends := 0
		for end: Vector3 in [wire.points.front(), wire.points.back()]:
			if end.y >= ANCHOR_HEIGHT:
				anchored_ends += 1
		var in_cone := false
		for point: Vector3 in wire.points:
			if point.y > eye.y and (point - eye).normalized().dot(forward) >= threshold:
				in_cone = true
		if not in_cone:
			continue
		crossings += 1
		if anchored_ends == 2:
			crossing_loops += 1
			var anchor_mean: float = 0.5 * (wire.points.front().y + wire.points.back().y)
			var lowest: float = wire.points[0].y
			for point: Vector3 in wire.points:
				lowest = minf(lowest, point.y)
			if anchor_mean - lowest >= 0.6:
				sagging_loop = true
		elif anchored_ends == 1:
			crossing_strands += 1
	assert_true(crossings >= 3,
		"at least three wires cross the lying view's cone, got %d" % crossings)
	assert_true(crossing_loops >= 1 and sagging_loop,
		"a crossing loop sags at least 0.6 m inside the cone")
	assert_true(crossing_strands >= 1,
		"a crossing strand swings inside the cone")

## Every dangling strand bows to one side through its upper hang and the
## opposite side through its lower hang (the signed lateral deviation
## from the anchor-to-tip chord flips between halves), so the hang reads
## as a swinging cable instead of a straight rod.
func test_dangling_strands_carry_s_curves() -> void:
	var wires := Placement.hanging_wires()
	for wire: Placement.HangingWire in wires:
		var anchor: Vector3 = wire.points.front()
		var tip: Vector3 = wire.points.back()
		if not (anchor.y >= ANCHOR_HEIGHT and tip.y < ANCHOR_HEIGHT):
			continue
		var axis := Vector3(tip.x - anchor.x, 0.0, tip.z - anchor.z).normalized()
		var side := axis.cross(Vector3.UP)
		var upper_max := -INF
		var upper_min := INF
		var lower_max := -INF
		var lower_min := INF
		for index: int in range(wire.points.size()):
			var offset: float = (wire.points[index] - anchor).dot(side)
			if index < wire.points.size() / 2:
				upper_max = maxf(upper_max, offset)
				upper_min = minf(upper_min, offset)
			else:
				lower_max = maxf(lower_max, offset)
				lower_min = minf(lower_min, offset)
		var bows_opposite: bool = (upper_max > 0.05 and lower_min < -0.05) \
			or (upper_min < -0.05 and lower_max > 0.05)
		assert_true(bows_opposite,
			"the dangling strand at %s carries opposing bends, got upper [%s, %s] lower [%s, %s]"
			% [str(anchor), str(upper_min), str(upper_max), str(lower_min), str(lower_max)])

func test_wire_surface_is_one_merged_dark_insulation_mesh() -> void:
	var wires := Wires.build()
	var instances: Array[Node] = wires.find_children("*", "MeshInstance3D", true, false)
	assert_int_equal(instances.size(), 1, "every authored wire merges into one mesh instance")
	var instance := instances[0] as MeshInstance3D
	var mesh := instance.mesh as ArrayMesh
	assert_int_equal(mesh.get_surface_count(), 1, "one surface: one draw call for all wires")
	var vertices: PackedVector3Array = mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	assert_true(vertices.size() > 12 * Placement.HANGING_WIRE_SAMPLES * Wires.RADIAL_SEGMENTS,
		"the merged surface carries every ring of every wire")
	var material := instance.material_override as StandardMaterial3D
	assert_true(material != null, "the wires carry a standard insulation material")
	var luminance: float = 0.2126 * material.albedo_color.r \
		+ 0.7152 * material.albedo_color.g + 0.0722 * material.albedo_color.b
	assert_float_in_range(luminance, 0.12, 0.18, "warm dark-grey insulation albedo")
	assert_float_in_range(material.roughness, 0.25, 0.45,
		"low insulation roughness so the red fixtures glint off it")
	assert_float_in_range(material.metallic, 0.35, 0.55,
		"metallic sheen catches the red light and the spark strobes")

func test_wire_builds_are_deterministic() -> void:
	var first := Placement.hanging_wires()
	var second := Placement.hanging_wires()
	assert_int_equal(first.size(), second.size(), "two authorings carry the same strand count")
	for index: int in range(first.size()):
		assert_int_equal(first[index].points.size(), second[index].points.size(),
			"wire %d keeps its sample count across builds" % index)
		for sample: int in range(first[index].points.size()):
			assert_vec3_equal(first[index].points[sample], second[index].points[sample],
				"wire %d sample %d is identical across builds" % [index, sample])
		assert_float_equal(first[index].radius, second[index].radius,
			"wire %d keeps its radius across builds" % index)
	var mesh_a := _merged_mesh(Wires.build())
	var mesh_b := _merged_mesh(Wires.build())
	var vertices_a: PackedVector3Array = mesh_a.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	var vertices_b: PackedVector3Array = mesh_b.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	assert_int_equal(vertices_a.size(), vertices_b.size(),
		"the merged surface keeps its vertex count across builds")
	for index: int in range(vertices_a.size()):
		assert_vec3_equal(vertices_a[index], vertices_b[index],
			"merged vertex %d is identical across builds" % index)

func _merged_mesh(wires: Node) -> ArrayMesh:
	var instance := wires.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D
	return instance.mesh as ArrayMesh
