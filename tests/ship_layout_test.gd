extends SimTestCase

func _layout() -> ShipLayout:
	var result := ShipLayout.authored()
	assert_true(result.is_ok(), "authored layout validates")
	return result.layout

func test_axes_floors_and_section_intervals() -> void:
	var layout := _layout()
	assert_vec3_equal(ShipLayout.BOW, Vector3(-1, 0, 0), "bow")
	assert_vec3_equal(ShipLayout.PORT, Vector3(0, 0, -1), "port")
	assert_float_equal(layout.floor_y(1), 71.5, "D01 floor")
	assert_float_equal(layout.floor_y(14), 0.0, "D14 floor")
	assert_float_equal(layout.floor_y(30), -88.0, "D30 floor")
	assert_int_equal(layout.deck_ids().size(), 30, "thirty decks")
	for fixture: Array in [[40, -24.0, 0.0], [41, 6.0, 30.0], [42, 36.0, 60.0]]:
		var section := layout.section(StringName("D14-S-%03d" % fixture[0]))
		assert_int_equal(section.number(), fixture[0], "section number")
		assert_vec3_equal(section.bounds().position, Vector3(fixture[1], 0, -1.5), "section minimum")
		assert_vec3_equal(section.bounds().end, Vector3(fixture[2], 3.2, 1.5), "section maximum")
	assert_int_equal(layout.deck(14).section_ids().size(), 3, "built sections")
	assert_true(layout.deck(13).section_ids().is_empty(), "no remote sections built")

func test_connectors_wells_lifts_and_boundary_spaces() -> void:
	var layout := _layout()
	assert_int_equal(layout.connector_ids().size(), 60, "built connectors")
	for n: int in range(2):
		var connector := layout.connector(StringName("D14-C-%03d" % n))
		assert_int_equal(connector.pitch_index(), n, "connector pitch")
		assert_vec3_equal(connector.bounds().position, Vector3(30 * n, 0, -1.5), "connector minimum")
		assert_vec3_equal(connector.bounds().end, Vector3(30 * n + 6, 3.2, 1.5), "connector maximum")
	assert_vec3_equal(layout.well(&"C-000-LADDER").bounds().position, Vector3(2.15, -88, -5.8), "fore well")
	assert_close(layout.well(&"C-001-LADDER").bounds().end, Vector3(35.35, 74.7, -1.5), "aft well")
	assert_vec3_equal(layout.well(&"C-001-LADDER").climb_line().origin, Vector3(34.5, 0, -4.3), "aft climb line")
	assert_vec3_equal(layout.well(&"C-001-LADDER").landing(14).origin, Vector3(34.5, 0, -2.9), "aft approach")
	assert_vec3_equal(layout.connector(&"D14-C-001").port_opening().origin, Vector3(34.5, 0, -1.5), "aft opening")
	assert_close(layout.lift(&"D14-C-001-LIFT").bounds().position, Vector3(32.1, 0, 1.5), "lift footprint")
	assert_false(layout.connector(&"D14-C-M001").is_built(), "fore boundary is explicit and unbuilt")
	assert_false(layout.connector(&"D14-C-002").is_built(), "aft boundary is explicit and unbuilt")

func test_bay_frame_power_room_and_anchors() -> void:
	var layout := _layout()
	var frame := layout.bay_to_world()
	assert_vec3_equal(frame.basis.x, Vector3(0, 0, -1), "exact cardinal basis")
	assert_vec3_equal(frame.basis.y, Vector3.UP, "up preserved")
	assert_vec3_equal(frame.basis.z, Vector3.RIGHT, "quarter turn")
	assert_vec3_equal(frame.origin, Vector3(15, 0, 7.7), "bay origin")
	assert_close(layout.world_to_bay() * (frame * Vector3(-4.8, 0, 2.9)), Vector3(-4.8, 0, 2.9), "inverse")
	assert_close(frame * Vector3(-4.8, 0, 2.9), Vector3(17.9, 0, 12.5), "player pod")
	assert_true(layout.bay().template().equals(Pods.PodRegistry.frozen()), "one frozen local pod template")
	assert_close(layout.power_room().bounds().position, Vector3(21, 0, -9.7), "unchanged power minimum")
	assert_close(layout.power_room().bounds().end, Vector3(33, 3.2, -1.7), "unchanged power maximum")
	assert_int_equal(layout.power_room().console_stations().size(), 6, "six console stations")
	assert_vec3_equal(layout.anchor(&"D14-POWER-CONSOLE").origin, Vector3(22.05, 0, -7.5), "console reach center")
	assert_vec3_equal(layout.anchor(&"D14-HALL-SWITCH").origin, Vector3(16.2, 1.25, 1.45), "switch anchor")
	var door := layout.door(&"D14-BAY-DOOR")
	assert_vec3_equal(door.frame().origin, Vector3(15, 0, 1.5), "hall face")
	assert_close(door.frame() * layout.face(&"D14-BAY-DOOR/BAY").surface_frame().origin, Vector3(15, 0, 1.7), "bay face")

func test_door_counts_policies_and_reciprocal_faces() -> void:
	var layout := _layout()
	var cranks: Array[StringName] = []
	var side_count := 0
	var lift_count := 0
	var hatch_count := 0
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.policy() == ShipLayout.Policy.CRANK:
			cranks.append(id)
		if door.kind() == ShipLayout.DoorKind.SIDE:
			side_count += 1
			assert_int_equal(door.policy(), ShipLayout.Policy.NEVER_OPENS, "side door stays shut")
		if door.kind() == ShipLayout.DoorKind.LIFT:
			lift_count += 1
		if door.kind() == ShipLayout.DoorKind.HATCH:
			hatch_count += 1
		assert_int_equal(door.face_ids().size(), 2, "two faces")
		for index: int in range(2):
			var face := layout.face(door.face_ids()[index])
			assert_true(face.door_id() == id, "face resolves parent")
			assert_true(face.source_space() == door.spaces()[index], "source resolves endpoint")
			assert_true(layout.has_space(face.source_space()), "endpoint exists")
			if door.kind() == ShipLayout.DoorKind.HATCH:
				var expected := 41 + layout.connector(door.owner_id()).pitch_index()
				assert_int_equal(face.destination_section(), expected - index, "face travel destination")
	assert_true(cranks == [&"D14-C-000-H-AFT", &"D14-C-000-H-FORE", &"D14-C-001-H-AFT", &"D14-C-001-H-FORE"], "exact four crank ids")
	assert_int_equal(side_count, 17, "seventeen shut side leaves")
	assert_int_equal(lift_count, 60, "sixty lifts")
	assert_int_equal(hatch_count, 122, "connector and boundary hatches")
	assert_int_equal(layout.door_ids().size(), 201, "one record per door")
	assert_int_equal(layout.section(&"D14-S-041").side_door_ids().size(), 5, "five shut section41 leaves")

func test_layout_is_repeatable_and_collection_reads_are_copies() -> void:
	var first := _layout()
	assert_true(first.serialize() == _layout().serialize(), "repeatable serialized layout")
	var ids := first.door_ids()
	ids.clear()
	assert_int_equal(first.door_ids().size(), 201, "id collection is a copy")
	var faces := first.door(&"D14-BAY-DOOR").face_ids()
	faces.clear()
	assert_int_equal(first.door(&"D14-BAY-DOOR").face_ids().size(), 2, "record collection is a copy")
	var data := first.door(&"D14-BAY-DOOR").data()
	data["face_ids"].clear()
	assert_int_equal(first.door(&"D14-BAY-DOOR").face_ids().size(), 2, "serialized collection is also a copy")

func test_layout_rejects_duplicate_invalid_deck_reference_and_dimensions() -> void:
	var layout := _layout()
	var records := layout.records()
	records.append(records[0])
	assert_int_equal(ShipLayout.try_new(records).error.kind, ShipLayout.LayoutError.Kind.DUPLICATE_ID, "duplicate rejected")
	records = layout.records()
	records.append(ShipLayout.DeckSpec.new(31, [], []))
	assert_int_equal(ShipLayout.try_new(records).error.kind, ShipLayout.LayoutError.Kind.INVALID_DECK, "deck rejected")
	records = layout.records()
	records.append(ShipLayout.SectionSpec.new(&"BAD", 14, 99, AABB(Vector3.ZERO, Vector3(INF, 3.2, 3)), [], [], &"red", true))
	assert_int_equal(ShipLayout.try_new(records).error.kind, ShipLayout.LayoutError.Kind.INVALID_DIMENSIONS, "nonfinite rejected")
	records = layout.records()
	records.append(ShipLayout.SectionSpec.new(&"BAD", 14, 99, AABB(Vector3.ZERO, Vector3(24, 3.2, 3)), [&"missing"], [], &"red", true))
	assert_int_equal(ShipLayout.try_new(records).error.kind, ShipLayout.LayoutError.Kind.BAD_REFERENCE, "missing opening rejected")

func test_layout_rejects_overlapping_apertures() -> void:
	var layout := _layout()
	var records := layout.records()
	var original := layout.door(&"D14-C-000-H-FORE")
	records.append(ShipLayout.DoorSpec.new(&"OVERLAP", 14, original.kind(), original.policy(), original.frame(), original.aperture(), original.spaces(), [&"OVERLAP/FORE", &"OVERLAP/AFT"], original.owner_id(), original.animation(), true))
	records.append(ShipLayout.FaceSpec.new(&"OVERLAP/FORE", 14, &"OVERLAP", original.spaces()[0], 41, Transform3D.IDENTITY, Transform3D.IDENTITY))
	records.append(ShipLayout.FaceSpec.new(&"OVERLAP/AFT", 14, &"OVERLAP", original.spaces()[1], 40, Transform3D.IDENTITY, Transform3D.IDENTITY))
	assert_int_equal(ShipLayout.try_new(records).error.kind, ShipLayout.LayoutError.Kind.OVERLAPPING_APERTURES, "overlap rejected")

func test_section_openings_include_both_end_hatches() -> void:
	var layout := _layout()
	var openings := layout.section(&"D14-S-041").opening_ids()
	assert_true(&"D14-C-000-H-AFT" in openings and &"D14-C-001-H-FORE" in openings, "section topology includes both end portals")

func test_layout_rejects_reference_with_wrong_record_type() -> void:
	var records := _layout().records()
	records.append(ShipLayout.SectionSpec.new(&"BAD", 14, 99, AABB(Vector3.ZERO, Vector3(24, 3.2, 3)), [&"D14"], [], &"red", false))
	var result := ShipLayout.try_new(records)
	assert_false(result.is_ok(), "a deck is not a wall opening")
	if not result.is_ok():
		assert_int_equal(result.error.kind, ShipLayout.LayoutError.Kind.BAD_REFERENCE, "wrong reference type rejected")

func test_layout_rejects_nonreciprocal_face_and_wrong_openability() -> void:
	var layout := _layout()
	var door := layout.door(&"D14-C-000-H-FORE")
	var records := layout.records()
	for index: int in range(records.size()):
		if records[index].id() == door.face_ids()[1]:
			records[index] = ShipLayout.FaceSpec.new(door.face_ids()[1], 14, door.id(), door.spaces()[0], 40, Transform3D.IDENTITY, Transform3D.IDENTITY)
	var result := ShipLayout.try_new(records)
	assert_false(result.is_ok(), "the reverse face must name the other space")
	assert_int_equal(result.error.kind, ShipLayout.LayoutError.Kind.BAD_FACES, "reciprocal face error")
	records = layout.records()
	for index: int in range(records.size()):
		if records[index].id() == door.id():
			records[index] = ShipLayout.DoorSpec.new(door.id(), 14, door.kind(), ShipLayout.Policy.NEVER_OPENS, door.frame(), door.aperture(), door.spaces(), door.face_ids(), door.owner_id(), door.animation(), true)
	result = ShipLayout.try_new(records)
	assert_false(result.is_ok(), "the four internal D14 hatches must crank")
	assert_int_equal(result.error.kind, ShipLayout.LayoutError.Kind.OPENABILITY, "openability error")
