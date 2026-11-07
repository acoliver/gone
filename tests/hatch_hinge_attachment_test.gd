extends SimTestCase

const IDS: Array[StringName] = [ShipLayout.BAY_DOOR_ID, &"D14-C-000-H-FORE", &"D14-C-000-H-AFT", &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]

func test_only_the_swing_face_carries_two_door_sized_working_hinges() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var into := signf(spec.hinge_frame().origin.z - ShipLayout.WALL / 2)
		var swing_side := 1 if into > 0 else 0
		var straps := 0
		var barrels := 0
		var bolts := 0
		for group: HatchParts.Group in HatchParts.leaf(spec):
			if not String(group.path).begins_with("StrapHinges/"): continue
			assert_int_equal(group.side, swing_side, "Andrew 2026-11-06: remove duplicate push-side hinges")
			for part: HatchParts.Part in group.parts:
				if "/strap-" in String(part.id):
					straps += 1
					assert_true(part.size.is_equal_approx(Vector3(0.22, 0.22, 0.012)), "Andrew 2026-11-06: concept-proportioned 220 mm leaf, not uniform scaling")
					var station := String(part.id).get_file().get_slice("-", 1).to_int()
					var height: float = [0.48, 2.24][station]
					assert_true(absf(part.transform.origin.y - height) < 0.000001, "upper stack shift does not move the door-side leaf")
				if "/bolt-" in String(part.id):
					bolts += 1
					assert_true(part.size.is_equal_approx(Vector3(0.032, 0.008, 0.032)), "four 32 mm bolt heads seat on each 12 mm leaf")
				if "/barrel-" in String(part.id):
					barrels += 1
					# The moving barrel retains its existing diameter and height.
					assert_true(part.size.is_equal_approx(Vector3(0.056, 0.14, 0.056)), "original 56 mm diameter clears FRAME/LEFT without relaxing the swing gate")
					assert_float_equal(part.radius, 0.028, "barrel diameter stays at the size that clears")
					var station := String(part.id).get_file().get_slice("-", 1).to_int()
					var height: float = [0.46, 2.18][station]
					assert_true(absf(part.transform.origin.y - height) < 0.000001, "only the upper knuckle stack shifts, 40 mm below its previous center")
		assert_int_equal(straps, 2, "only two working straps, no opposite-face duplicates")
		assert_int_equal(barrels, 2, "both working straps carry a coaxial barrel")
		assert_int_equal(bolts, 8, "four seated bolts per working strap, no push-side duplicates")

func test_each_moving_barrel_hangs_between_two_bolted_frame_knuckles() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var fixed: Dictionary = {}
		var rings: Array[AABB] = []
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(spec):
			var box := spec.frame().affine_inverse() * solid.transform * AABB(-solid.size / 2, solid.size)
			if "/RING/" in String(solid.id): rings.append(box)
			fixed[String(solid.id).trim_prefix(String(id) + "/")] = solid
		for station: int in range(2):
			var plate_id := "HINGE/PLATE-%d" % station
			var plate: ShipGeometry.SolidSpec = fixed[plate_id]
			# The crown clips the outer plate corner; integer-grid clipping
			# trims micrometres from its bounds, retaining the 1 um pins.
			var plate_height: float = [0.31899920105934, 0.31899976730347][station]
			assert_true(absf(plate.size.x - 0.07499694824219) < 0.000001 and absf(plate.size.y - plate_height) < 0.000001 and absf(plate.size.z - 0.014) < 0.000001, "75 x 319 x 14 mm frame leaf spans both knuckles and caps inside the crown")
			var plate_box := spec.frame().affine_inverse() * plate.transform * AABB(-plate.size / 2, plate.size)
			var overlaps := false
			for ring: AABB in rings:
				if ring.intersects(plate_box): overlaps = true
			assert_true(overlaps, "frame leaf is seated on the existing frame ring")
			var bolts := 0
			for zone: String in ["LOWER", "UPPER"]:
				var knuckle_id := "HINGE/KNUCKLE-%s-%d" % [zone, station]
				var cap_id := "HINGE/CAP-%s-%d" % [zone, station]
				assert_true(fixed.has(knuckle_id), "frame supports the moving barrel at " + knuckle_id)
				assert_true(fixed.has(cap_id), "pin head terminates " + cap_id)
				if not fixed.has(knuckle_id) or not fixed.has(cap_id): continue
				var knuckle: ShipGeometry.SolidSpec = fixed[knuckle_id]
				assert_true(knuckle.size.is_equal_approx(Vector3(0.0438, 0.075, 0.0438)), "75 mm fixed knuckle uses the largest diameter that clears the unchanged swing gate")
				var pose := spec.frame().affine_inverse() * knuckle.transform
				var axis := spec.hinge_frame().origin
				assert_true(Vector2(pose.origin.x - axis.x, pose.origin.z - axis.z).length() <= 0.000001, "fixed and moving knuckles share the existing pivot")
				var moving_center := HatchParts.HINGE_HEIGHTS[station] + HatchParts.HINGE_STACK_SHIFTS[station] + HatchParts.BARREL_OFFSET
				var gap := pose.origin.y - knuckle.size.y / 2 - moving_center - 0.07 if zone == "UPPER" else moving_center - 0.07 - pose.origin.y - knuckle.size.y / 2
				assert_true(absf(gap - 0.0025) < 0.000001, "2.5 mm axial gap separates each fixed knuckle from the moving barrel")
				var cap: ShipGeometry.SolidSpec = fixed[cap_id]
				assert_true(cap.size.is_equal_approx(Vector3(0.0438, 0.012, 0.0438)), "43.8 x 12 mm pin caps seat above and below the stack")
				var cap_pose := spec.frame().affine_inverse() * cap.transform
				var direction := 1.0 if zone == "UPPER" else -1.0
				assert_true(absf(cap_pose.origin.y - pose.origin.y - direction * 0.0435) < 0.000001, "pin cap seats on the outer end of its knuckle")
				for bolt: int in range(3):
					var bolt_id := "HINGE/BOLT-%s-%d-%d" % [zone, bolt, station]
					assert_true(fixed.has(bolt_id), "three bolt heads anchor each knuckle zone: " + bolt_id)
					if not fixed.has(bolt_id): continue
					var head: ShipGeometry.SolidSpec = fixed[bolt_id]
					var head_box := spec.frame().affine_inverse() * head.transform * AABB(-head.size / 2, head.size)
					assert_true(head.size.is_equal_approx(Vector3(0.018, 0.008, 0.018)), "18 mm frame bolt heads")
					assert_true(head_box.position.x >= plate_box.position.x and head_box.end.x <= plate_box.end.x and head_box.position.y >= plate_box.position.y and head_box.end.y <= plate_box.end.y, "bolt head seats inside its frame leaf")
					bolts += 1
			assert_int_equal(bolts, 6, "six frame bolts per heavy hinge")

func test_frame_knuckle_cutouts_preserve_the_four_remaining_rounded_sealing_strips() -> void:
	var spec := ShipLayout.authored().layout.door(ShipLayout.BAY_DOOR_ID)
	for group: HatchParts.Group in HatchParts.leaf(spec):
		if not (String(group.path) == "BackingLapHinge" or "PivotSeal" in String(group.path) or "HingeSeal" in String(group.path)): continue
		assert_int_equal(group.parts.size(), 4, "rounding removes the fifth strip above the upper knuckle")
		if group.parts.size() != 4: continue
		for index: int in range(3):
			var lower := group.parts[index]
			var upper := group.parts[index + 1]
			var bottom := lower.transform.origin.y + lower.size.y / 2
			var top := upper.transform.origin.y - upper.size.y / 2
			var station := index / 2
			var offset := -0.1795 if index % 2 == 0 else 0.0525
			assert_true(absf(bottom - (HatchParts.HINGE_HEIGHTS[station] + HatchParts.HINGE_STACK_SHIFTS[station] + offset)) < 0.000001, "cutout starts at the fixed hardware boundary")
			assert_true(absf(top - bottom - 0.087) < 0.000001, "cutout equals the 75 mm knuckle and 12 mm cap")

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

func test_closed_latches_align_with_their_fixed_keeper_stations_on_both_signs() -> void:
	var layout := ShipLayout.authored().layout
	var signs: Dictionary = {}
	for id: StringName in [&"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var spec := layout.door(id)
		signs[signf(spec.hinge_frame().origin.z - ShipLayout.WALL / 2)] = true
		var keepers: Dictionary = {}
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_fixed_hardware(spec):
			if not "/KEEPER/" in String(solid.id): continue
			keepers[int(String(solid.id).get_file())] = spec.frame().affine_inverse() * solid.transform * AABB(-solid.size / 2, solid.size)
		assert_int_equal(keepers.size(), 3, "every closed latch has a fixed keeper")
		var checked := 0
		for group: HatchParts.Group in HatchParts.leaf(spec):
			for part: HatchParts.Part in group.parts:
				if part.shape != &"generated_latch": continue
				var station := int(String(part.id).get_file().get_slice("-", 1))
				var closed := spec.hinge_frame() * group.transform * part.transform
				var pivot := closed * -HatchGeneratedParts.LATCH_CENTER
				var keeper: AABB = keepers[station]
				var latch := closed * AABB(-part.size / 2, part.size)
				var error := absf(keeper.get_center().y - pivot.y)
				print("LATCH_KEEPER id=%s part=%s station=%d error_m=%.6f" % [id, part.id, station, error])
				assert_true(error <= 0.000001, "keeper aligns with its closed latch pivot: %s %s" % [id, part.id])
				assert_true(latch.position.y <= keeper.end.y and keeper.position.y <= latch.end.y, "closed latch and keeper overlap vertically")
				checked += 1
		assert_int_equal(checked, 6, "all three latch stations on both leaf faces")
	assert_int_equal(signs.size(), 2, "both hinge signs checked")

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
		# Each frame leaf now supports both ends of the moving barrel.
		assert_int_equal(ShipGeometry.hatch_fixed_hardware(spec).size(), 29, "two plates, four bridges, four knuckles, four caps, twelve bolts and three keepers")
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
				# Round 3 deliberately separates the knuckles instead of overlapping them.
				assert_true(absf(gap - 0.0025) < 0.000001, "fixed knuckle leaves the authored 2.5 mm axial gap: %s %s gap=%.6f" % [id, part.id, gap])

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
