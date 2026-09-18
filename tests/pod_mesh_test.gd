extends SimTestCase
## Pins for the realistic pod mesh inventory (issue #37): the per-state
## merged meshes exist and are shared, the material set is pinned, the
## blanket variant lands exactly on the pods whose authored greybox
## solids carry a blanket, construction is deterministic, geometry stays
## inside the pod silhouette, and the frozen exit aperture mouth stays
## visually clear above the traversal band except for the authored
## indicator dressing.

func test_every_state_has_a_merged_mesh() -> void:
	for state: int in [
		Pods.PodState.SEALED,
		Pods.PodState.EMPTY_OPEN,
		Pods.PodState.PLAYER,
	]:
		var mesh := PodMesh.for_state(state)
		assert_true(mesh != null, "state %d has a pod mesh" % state)
		assert_true(mesh is ArrayMesh, "state %d mesh is a merged ArrayMesh" % state)
		assert_true(mesh.get_surface_count() >= 3, "state %d mesh has at least three surfaces" % state)

func test_state_meshes_are_shared_and_distinct() -> void:
	var sealed := PodMesh.for_state(Pods.PodState.SEALED)
	var empty_open := PodMesh.for_state(Pods.PodState.EMPTY_OPEN)
	var player := PodMesh.for_state(Pods.PodState.PLAYER)
	assert_true(sealed != empty_open and empty_open != player and sealed != player, "the three pod states carry distinct meshes")
	assert_true(PodMesh.for_state(Pods.PodState.SEALED) == sealed, "for_state caches one shared mesh per state")

func test_scene_builder_instances_the_state_meshes() -> void:
	var registry := Pods.PodRegistry.frozen()
	var pods := StasisPods.build(registry)
	var groups: Array[Node] = pods.get_children()
	assert_int_equal(groups.size(), Pods.POD_COUNT, "every registry pod gets a group")
	var state_meshes := {}
	for group: Node in groups:
		var meshes: Array[Mesh] = []
		var plates: Array[MeshInstance3D] = []
		for child: Node in group.get_children():
			var instance := child as MeshInstance3D
			if instance == null or instance.mesh == null:
				continue
			if instance.mesh is ArrayMesh:
				meshes.append(instance.mesh)
			elif instance.position == Placement.indicator_plate().center:
				plates.append(instance)
		assert_int_equal(meshes.size(), 1, "each pod carries exactly one merged body mesh")
		assert_int_equal(plates.size(), 1, "each pod keeps its authored indicator plate instance")
		state_meshes[group.name] = meshes[0]
	for pod: Pods.Pod in registry.pods():
		assert_true(
			state_meshes["Pod%d" % pod.id().index()] == PodMesh.for_state(pod.state()),
			"pod %d's mesh is its state's shared mesh" % pod.id().index()
		)

func test_shared_material_count_is_pinned() -> void:
	var ids := {}
	for state: int in [
		Pods.PodState.SEALED,
		Pods.PodState.EMPTY_OPEN,
		Pods.PodState.PLAYER,
	]:
		var mesh := PodMesh.for_state(state)
		for surface: int in range(mesh.get_surface_count()):
			var material := mesh.surface_get_material(surface)
			assert_true(material != null, "every surface carries its shared material")
			ids[material.get_instance_id()] = true
	assert_int_equal(ids.size(), PodMesh.slot_count(), "the three meshes share exactly the pinned material set")
	for slot: int in range(PodMesh.slot_count()):
		var material: StandardMaterial3D = PodMesh.material_for_slot(slot)
		assert_false(material.emission_enabled, "no pod material emits: the beat is unpowered")

func test_material_values_separate_under_dim_red_light() -> void:
	# The follow-up review's diagnosis: modeled detail only reads when
	# the values separate under dim red light. The pod palette is a
	# strict lightness ladder — rubber, chassis, lid, latch, couch stop,
	# mattress, blanket — and the shared steel stays glinty so crowns
	# and hinge barrels catch the fixtures.
	var rubber: float = PodMesh.RUBBER_ALBEDO.get_luminance()
	var chassis: float = (PodMesh.HULL_ALBEDO * PodMesh.CHASSIS_TINT).get_luminance()
	var lid: float = (PodMesh.HULL_ALBEDO * PodMesh.LID_TINT).get_luminance()
	var latch: float = PodMesh.HULL_ALBEDO.get_luminance()
	var stop: float = (PodMesh.COUCH_ALBEDO * PodMesh.COUCH_STOP_TINT).get_luminance()
	var couch: float = PodMesh.COUCH_ALBEDO.get_luminance()
	var blanket: float = PodMesh.BLANKET_ALBEDO.get_luminance()
	assert_true(rubber < chassis, "the gasket rubber stays darkest so it outlines the mouth")
	assert_true(chassis < lid, "the lid slab sits lighter than the hull so a sealed pod reads closed")
	assert_true(lid < latch, "the latch blocks sit a touch lighter than the lid")
	assert_true(latch < stop, "the interior ladder starts above the hardware values")
	assert_true(stop < couch, "the foot stop sits slightly darker than the mattress")
	assert_true(couch < blanket, "the blanket is the lightest read on the pods")
	assert_true(PodMesh.SEALED_LID_BOW >= 0.06 and PodMesh.SEALED_LID_BOW <= 0.08,
		"the sealed crown bow stays inside the deepened 6-8 cm band")
	var steel: StandardMaterial3D = PodMesh.material_for_slot(PodMesh.Slot.HULL)
	assert_true(steel.vertex_color_use_as_albedo,
		"the steel splits chassis, lid, and latch values by vertex tint")
	assert_true(steel.roughness <= 0.45, "the steel stays glinty enough for the crown highlight band")
	assert_true(steel.metallic >= 0.65, "the hinge barrels glint under the red fixtures")
	var couch_material: StandardMaterial3D = PodMesh.material_for_slot(PodMesh.Slot.COUCH)
	assert_true(couch_material.vertex_color_use_as_albedo,
		"the couch splits mattress and stop values by vertex tint")

func test_blanket_variant_matches_authored_registry() -> void:
	var registry := Pods.PodRegistry.frozen()
	var blanket_mesh := PodMesh.for_state(Pods.PodState.EMPTY_OPEN)
	for pod: Pods.Pod in registry.pods():
		var authored_blanket := false
		for solid: PodBody.PodSolid in PodBody.pod_solids(pod.state()):
			if solid.kind == PodBody.SolidKind.BLANKET:
				authored_blanket = true
		var uses_blanket_mesh: bool = PodMesh.for_state(pod.state()) == blanket_mesh
		assert_true(
			authored_blanket == uses_blanket_mesh,
			"pod %d blanket dressing matches its authored solids" % pod.id().index()
		)
	var blanket_material := PodMesh.material_for_slot(PodMesh.Slot.BLANKET)
	var carries_blanket := {}
	for state: int in [
		Pods.PodState.SEALED,
		Pods.PodState.EMPTY_OPEN,
		Pods.PodState.PLAYER,
	]:
		var mesh := PodMesh.for_state(state)
		for surface: int in range(mesh.get_surface_count()):
			if mesh.surface_get_material(surface) == blanket_material:
				carries_blanket[state] = true
	assert_true(carries_blanket.has(Pods.PodState.EMPTY_OPEN), "the empty-open mesh carries blanket fabric")
	assert_false(carries_blanket.has(Pods.PodState.SEALED), "the sealed mesh carries no blanket")
	assert_false(carries_blanket.has(Pods.PodState.PLAYER), "the player mesh carries no blanket")

func test_vertex_counts_stay_within_sanity_bounds() -> void:
	# PodMesh surfaces are non-indexed triangle soup: the vertex array
	# IS the triangle stream, three vertices per triangle.
	for state: int in [
		Pods.PodState.SEALED,
		Pods.PodState.EMPTY_OPEN,
		Pods.PodState.PLAYER,
	]:
		var mesh := PodMesh.for_state(state)
		var vertices := 0
		for surface: int in range(mesh.get_surface_count()):
			var arrays := mesh.surface_get_arrays(surface)
			var surface_vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			vertices += surface_vertices.size()
			assert_int_equal(surface_vertices.size() % 3, 0, "state %d surface %d is pure triangles" % [state, surface])
			for triangle: int in range(0, surface_vertices.size(), 3):
				var a := surface_vertices[triangle]
				var b := surface_vertices[triangle + 1]
				var c := surface_vertices[triangle + 2]
				assert_true((b - a).cross(c - a).length_squared() > 1e-12, "state %d surface %d has no degenerate triangle" % [state, surface])
		assert_true(vertices >= 500, "state %d mesh is nontrivial (>= 500 vertices), got %d" % [state, vertices])
		assert_true(vertices <= 5000, "state %d mesh stays cheap (<= 5000 vertices), got %d" % [state, vertices])

func test_construction_is_deterministic() -> void:
	for state: int in [
		Pods.PodState.SEALED,
		Pods.PodState.EMPTY_OPEN,
		Pods.PodState.PLAYER,
	]:
		var first := PodMesh.build_state_mesh(state)
		var second := PodMesh.build_state_mesh(state)
		assert_int_equal(
			first.get_surface_count(),
			second.get_surface_count(),
			"state %d rebuild keeps its surface count" % state
		)
		for surface: int in range(first.get_surface_count()):
			var first_arrays := first.surface_get_arrays(surface)
			var second_arrays := second.surface_get_arrays(surface)
			var first_vertices: PackedVector3Array = first_arrays[Mesh.ARRAY_VERTEX]
			var second_vertices: PackedVector3Array = second_arrays[Mesh.ARRAY_VERTEX]
			assert_int_equal(
				first_vertices.size(),
				second_vertices.size(),
				"state %d surface %d vertex count is stable" % [state, surface]
			)
			for vertex: int in range(first_vertices.size()):
				assert_vec3_equal(
					first_vertices[vertex],
					second_vertices[vertex],
					"state %d surface %d vertex %d is identical across builds" % [state, surface, vertex]
				)
			assert_true(
				first.surface_get_material(surface) == second.surface_get_material(surface),
				"state %d surface %d keeps its shared material across builds" % [state, surface]
			)

func test_geometry_stays_inside_the_pod_silhouette() -> void:
	for state: int in [
		Pods.PodState.SEALED,
		Pods.PodState.EMPTY_OPEN,
		Pods.PodState.PLAYER,
	]:
		var mesh := PodMesh.for_state(state)
		var bounds := mesh.get_aabb()
		assert_true(bounds.position.x >= PodMesh.BOUND_MIN.x, "state %d stays inside the -X silhouette" % state)
		assert_true(bounds.position.y >= PodMesh.BOUND_MIN.y, "state %d stays above the floor" % state)
		assert_true(bounds.position.z >= PodMesh.BOUND_MIN.z, "state %d stays inside the -Z silhouette" % state)
		assert_true(bounds.end.x <= PodMesh.BOUND_MAX.x, "state %d stays inside the +X silhouette" % state)
		assert_true(bounds.end.y <= PodMesh.BOUND_MAX.y, "state %d stays under the authored lid heights" % state)
		assert_true(bounds.end.z <= PodMesh.BOUND_MAX.z, "state %d stays inside the +Z dressing slack" % state)

func test_exit_mouth_stays_visually_clear() -> void:
	# Above the traversal band and past the wall line, the exit apertures
	# (player and open pods) carry only the authored indicator dressing
	# (plate plus lens around the plate mount). The sealed pod's strip is
	# legitimately covered by its authored closed lid slab, so there the
	# intrusion must stay inside that lid's envelope.
	var band_bottom := PodBody.TRAY_FLOOR_Y
	var wall_line := Pods.POD_LENGTH / 2.0 - PodBody.CAVITY_WALL
	# Vertex storage is float32: parts that end exactly on the wall line
	# or the authored footprint may sit a few ulps past it, so both
	# comparisons carry slack.
	var mouth_line: float = wall_line + 1e-5
	var foot_line: float = Pods.POD_LENGTH / 2.0 + 1e-5
	var dressing_max_z := Placement.indicator_plate().center.z + Placement.PLATE_THICKNESS / 2.0 + 0.02
	for state: int in [
		Pods.PodState.SEALED,
		Pods.PodState.EMPTY_OPEN,
		Pods.PodState.PLAYER,
	]:
		var mesh := PodMesh.for_state(state)
		for surface: int in range(mesh.get_surface_count()):
			var arrays := mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			for vertex: Vector3 in vertices:
				if vertex.z <= mouth_line or vertex.y <= band_bottom:
					continue
				var dressing := absf(vertex.x) <= 0.11 \
					and vertex.y >= 0.49 \
					and vertex.y <= 0.61 \
					and vertex.z <= dressing_max_z
				if state == Pods.PodState.SEALED:
					# The authored sealed lid: full footprint, one slab
					# thick, sitting on the rim, with the deepened crown
					# bow inside the slack. The foot-face indicator
					# dressing (plate plus lens) rides every pod, sealed
					# included.
					assert_true(
						dressing or (
							absf(vertex.x) <= Pods.POD_WIDTH / 2.0 + 0.01
								and vertex.y >= Pods.POD_HEIGHT - 0.02
								and vertex.y <= Pods.POD_HEIGHT + PodBody.LID_THICKNESS \
									+ PodMesh.SEALED_LID_BOW + 0.01
								and vertex.z <= foot_line
						),
						"state %d's mouth strip is covered only by the authored sealed lid and indicator dressing" % state
					)
				else:
					assert_true(
						dressing,
						"state %d dresses the mouth only with the indicator lens" % state
					)
