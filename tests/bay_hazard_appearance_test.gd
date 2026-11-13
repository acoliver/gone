extends SimTestCase

func test_sparks_are_coloured_embers_not_white_billboard_squares() -> void:
	var material := Hazards._spark_material()
	assert_true(material.albedo_color.r > material.albedo_color.g * 2, "spark albedo must be orange, not default white")
	assert_true(material.albedo_color.b < 0.15, "spark base has no white core")
	var quad := Hazards._spark_draw_pass(material)
	assert_true(quad.size.x <= 0.01 and quad.size.y <= 0.04, "sparks are small narrow embers, not 5 cm squares")

func test_surface_capture_stages_quiescent_hazards_before_advancing_frames() -> void:
	var source := FileAccess.get_file_as_string("res://tools/capture_ship_surfaces.gd")
	var build := source.find("scene = ShipScene.build_into")
	var settle := source.find("await _settle(36)", build)
	var staged := source.find("scene.hazards.auto_bursts = false", build)
	assert_true(staged > build and staged < settle, "circuit comparisons must exclude random spark flashes that flood the smoke red")
