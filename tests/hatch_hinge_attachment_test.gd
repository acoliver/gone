extends SimTestCase

const IDS: Array[StringName] = [ShipLayout.BAY_DOOR_ID, &"D14-C-000-H-FORE", &"D14-C-000-H-AFT", &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]

func test_barrel_axes_coincide_with_the_real_swing_axis_on_both_signs() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var checked := 0
		for group: HatchParts.Group in HatchParts.leaf(spec):
			for part: HatchParts.Part in group.parts:
				if not "/barrel-" in String(part.id): continue
				var local := group.transform * part.transform
				var portal := spec.hinge_frame() * local
				var axis := spec.hinge_frame().origin
				var error := Vector2(portal.origin.x - axis.x, portal.origin.z - axis.z).length()
				print("HINGE_AXIS id=%s part=%s error_m=%.6f" % [id, part.id, error])
				assert_true(error <= 0.002, "barrel lies within 2 mm of the real pivot: %s %s" % [id, part.id])
				assert_true(absf(local.basis.y.dot(Vector3.UP)) >= 0.999999, "barrel axis is vertical")
				checked += 1
		assert_true(checked >= 2, "both hinge stations have physical barrels")

func test_frame_recipe_contains_fixed_hinge_mounts_and_free_edge_keepers() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var mounts := 0
		var keepers := 0
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(layout.door(id)):
			if "/HINGE/" in String(solid.id): mounts += 1
			if "/KEEPER/" in String(solid.id): keepers += 1
		assert_true(mounts >= 2, "each hinge joins a fixed, simulation-owned frame mount: " + String(id))
		assert_int_equal(keepers, 3, "three dogs have fixed frame keepers: " + String(id))

func test_dog_pivots_are_on_the_free_edge() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var checked := 0
		for group: HatchParts.Group in HatchParts.leaf(spec):
			for part: HatchParts.Part in group.parts:
				if part.shape != &"generated_latch": continue
				var pivot := part.transform
				pivot.origin -= HatchGeneratedParts.LATCH_CENTER
				var point := (group.transform * pivot).origin
				var pivot_distance := absf(point.x)
				var free_distance := absf(spec.leaf_aperture().x + HatchParts.HINGE_OUTSET - point.x)
				assert_true(free_distance < pivot_distance, "dog is closer to the free edge than to the hinge: " + String(part.id))
				checked += 1
		assert_int_equal(checked, 6, "three dog pivots on each face")

func test_label_rectangles_keep_thirty_mm_from_all_projected_hardware() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		for face_id: StringName in spec.face_ids():
			var face := layout.face(face_id)
			var label := face.leaf_label_frame(spec)
			var rectangle := Rect2(Vector2(label.origin.x, label.origin.y) - face.label_size() / 2, face.label_size())
			var side := 0 if label.basis.z.z < 0 else 1
			for group: HatchParts.Group in HatchParts.leaf(spec):
				if group.side != side or group.steel or String(group.path).ends_with("Contour"): continue
				for part: HatchParts.Part in group.parts:
					var box := group.transform * part.transform * AABB(-part.size / 2, part.size)
					var projected := Rect2(Vector2(box.position.x, box.position.y), Vector2(box.size.x, box.size.y))
					var dx := maxf(0, maxf(projected.position.x - rectangle.end.x, rectangle.position.x - projected.end.x))
					var dy := maxf(0, maxf(projected.position.y - rectangle.end.y, rectangle.position.y - projected.end.y))
					var clearance := Vector2(dx, dy).length()
					if clearance < 0.03 - 0.000001:
						print("LABEL_HARDWARE id=%s face=%s part=%s clearance_m=%.6f label=%s hardware=%s" % [id, face_id, part.id, clearance, rectangle, projected])
					assert_true(clearance >= 0.03 - 0.000001, "label keeps 30 mm from projected hardware: %s %s" % [face_id, part.id])

func test_closed_scene_preserves_round11_collider_ceiling() -> void:
	var layout := ShipLayout.authored().layout
	var count := ShipCollision.opening_set(layout.bay().template(), false, false, layout).size()
	print("ROUND11_CLOSED_COLLIDERS ", count)
	assert_true(count <= 1013, "Round 11 stop rule: never exceed the existing 1013 closed-door colliders")
func test_detail_clearance_query_detects_penetration_without_aabb_false_positives() -> void:
	var query := preload("res://tests/hatch_detail_clearance.gd")
	assert_true(query.penetrates(Transform3D.IDENTITY, Vector3.ONE, Transform3D.IDENTITY, Vector3.ONE), "coincident boxes penetrate")
	assert_false(query.penetrates(Transform3D.IDENTITY, Vector3.ONE, Transform3D(Basis(), Vector3.RIGHT), Vector3.ONE), "touching faces do not penetrate")
	var pose := Transform3D(Basis(Vector3.UP, -PI / 3), Vector3.ZERO)
	assert_true(query.penetrates(pose, Vector3.ONE, Transform3D.IDENTITY, Vector3.ONE), "rotated penetration is detected")
	var spec := ShipLayout.authored().layout.door(ShipLayout.BAY_DOOR_ID)
	for group: HatchParts.Group in HatchParts.leaf(spec):
		for part: HatchParts.Part in group.parts:
			if part.id != &"ForeSteel/plate": continue
			var hinge := spec.hinge_frame()
			hinge.basis = Basis(Vector3.UP, deg_to_rad(-80))
			var slab := hinge * group.transform * part.transform
			var knuckle := Transform3D(Basis(), hinge.origin + Vector3.UP * 0.53)
			assert_true((slab * AABB(-part.size / 2, part.size)).intersects(knuckle * AABB(-Vector3.ONE * 0.008, Vector3.ONE * 0.016)), "whole-slab AABB overlaps empty pivot space")
			assert_false(query.penetrates(slab, part.size, knuckle, Vector3.ONE * 0.016), "oriented slab clears the real pivot")

func test_leaf_reservations_clear_every_fixed_detail_through_the_full_swing() -> void:
	var layout := ShipLayout.authored().layout
	var all_details: Array[ShipGeometry.SolidSpec] = []
	for solid: ShipGeometry.SolidSpec in ShipGeometry.deck_static_solids(layout, 14):
		if solid.collision_role == &"frame_detail": all_details.append(solid)
	for id: StringName in IDS:
		var spec := layout.door(id)
		assert_int_equal(ShipGeometry.hatch_fixed_hardware(spec).size(), 7, "two plates, two fixed knuckles and three keepers")
		var envelope := ShipGeometry.box_aabb(ShipGeometry.door_blockers(spec)[1])
		var swept := AABB(envelope.min_corner(), envelope.max_corner() - envelope.min_corner())
		var details: Array[ShipGeometry.SolidSpec] = []
		for detail: ShipGeometry.SolidSpec in all_details:
			if swept.intersects(detail.transform * AABB(-detail.size / 2, detail.size)): details.append(detail)
		var angles: Array[float] = []
		for degree: int in range(131): angles.append(signf(spec.swing_radians()) * deg_to_rad(degree))
		for seed: int in [0, 7, -913]: angles.append(spec.swing_radians(seed))
		for angle: float in angles:
			var hinge := spec.hinge_frame()
			hinge.basis = Basis(Vector3.UP, angle)
			for group: HatchParts.Group in HatchParts.leaf(spec):
				for part: HatchParts.Part in group.parts:
					var pose := spec.frame() * hinge * group.transform * part.transform
					for detail: ShipGeometry.SolidSpec in details:
						assert_false(preload("res://tests/hatch_detail_clearance.gd").penetrates(pose, part.size, detail.transform, detail.size), "%s angle=%.3f part=%s hits %s" % [id, rad_to_deg(angle), part.id, detail.id])


func test_fixed_hardware_stays_outside_walk_band_and_behind_capsule_standoff() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in layout.door_ids():
		var spec := layout.door(id)
		if spec.animation() != ShipLayout.AnimationRecipe.HINGE: continue
		var fixed := ShipGeometry.hatch_frame_solids(spec)
		var collider_boxes: Array[ColliderSet.Aabb] = []
		for frame: ShipGeometry.SolidSpec in fixed: collider_boxes.append_array(ShipGeometry.collision_boxes(frame))
		var checked := 0
		var local_inverse := spec.frame().affine_inverse()
		for hardware: ShipGeometry.SolidSpec in fixed:
			if not ("/HINGE/" in String(hardware.id) or "/KEEPER/" in String(hardware.id)): continue
			checked += 1
			assert_true(ShipGeometry.collision_boxes(hardware).is_empty(), "fixed hardware adds no collider: " + String(hardware.id))
			var bounds := local_inverse * hardware.transform * AABB(-hardware.size / 2, hardware.size)
			var band := AABB(Vector3(-ShipGeometry.SILL_WALK_WIDTH / 2, ShipGeometry.SILL_HEIGHT, -1), Vector3(ShipGeometry.SILL_WALK_WIDTH, 2, 2))
			assert_false(bounds.intersects(band), "fixed hardware stays outside walk band: " + String(hardware.id))
			var greatest_distance := INF
			# One collider must shield all eight corners. Its radius-expanded
			# volume is convex, so this also proves every point between them.
			for box: ColliderSet.Aabb in collider_boxes:
				var furthest_corner := 0.0
				for x: int in [-1, 1]:
					for y: int in [-1, 1]:
						for z: int in [-1, 1]:
							var point := hardware.transform * (hardware.size * Vector3(x, y, z) / 2)
							furthest_corner = maxf(furthest_corner, point.distance_to(point.clamp(box.min_corner(), box.max_corner())))
				greatest_distance = minf(greatest_distance, furthest_corner)
			print("HINGE_STANDOFF id=%s distance_m=%.6f radius_m=%.6f" % [hardware.id, greatest_distance, Controller.CAPSULE_RADIUS])
			assert_true(greatest_distance <= Controller.CAPSULE_RADIUS, "one existing collider shields every point of the hardware: " + String(hardware.id))
		assert_true(checked >= 7, "two plates, two fixed knuckles and three keepers: " + String(id))

func test_fixed_and_moving_hinge_parts_meet_at_the_closed_seam() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var fixed := ShipGeometry.hatch_frame_solids(spec)
		for group: HatchParts.Group in HatchParts.leaf(spec):
			for part: HatchParts.Part in group.parts:
				if not "/barrel-" in String(part.id): continue
				var moving := spec.hinge_frame() * group.transform * part.transform * AABB(-part.size / 2, part.size)
				var gap := INF
				for solid: ShipGeometry.SolidSpec in fixed:
					if not "/HINGE/" in String(solid.id): continue
					var stationary := spec.frame().affine_inverse() * solid.transform * AABB(-solid.size / 2, solid.size)
					var delta := (stationary.position - moving.end).max(moving.position - stationary.end).max(Vector3.ZERO)
					gap = minf(gap, delta.length())
				assert_true(gap <= 0.001, "fixed mount meets moving barrel within 1 mm: %s %s gap=%.6f" % [id, part.id, gap])

func test_strap_fasteners_are_seated_inside_their_own_straps() -> void:
	var spec := ShipLayout.authored().layout.door(ShipLayout.BAY_DOOR_ID)
	for group: HatchParts.Group in HatchParts.leaf(spec):
		if not String(group.path).begins_with("StrapHinges/"): continue
		for bolt: HatchParts.Part in group.parts:
			if not "/bolt-" in String(bolt.id): continue
			var station := String(bolt.id).get_file().split("-")[1]
			for strap: HatchParts.Part in group.parts:
				if not String(strap.id).ends_with("/strap-" + station): continue
				var a := Rect2(Vector2(strap.transform.origin.x, strap.transform.origin.y) - Vector2(strap.size.x, strap.size.y) / 2, Vector2(strap.size.x, strap.size.y))
				var b := Rect2(Vector2(bolt.transform.origin.x, bolt.transform.origin.y) - Vector2(bolt.size.x, bolt.size.z) / 2, Vector2(bolt.size.x, bolt.size.z))
				assert_true(a.encloses(b), "strap fastener stays fully seated after strap relocation: " + String(bolt.id))
