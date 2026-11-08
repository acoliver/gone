extends SimTestCase

func test_hazard_band_is_physically_narrow_and_its_contour_fits() -> void:
	var spec := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	for group: HatchParts.Group in HatchParts.leaf(spec):
		if String(group.path) not in ["Wheel", "ReverseWheel"]: continue
		var diameter := 0.0
		# Slice 3 v2 replaces the separate rim with one whole generated wheel;
		# its hub record owns the same radial scale used by the hazard band.
		for part: HatchParts.Part in group.parts:
			if String(part.id).ends_with("/hub"): diameter = part.radius * 2
		assert_true(diameter > 0, "the wheel owns the band scale")
		for part: HatchParts.Part in group.parts:
			if part.shape != &"band": continue
			assert_true(absf(part.size.y / diameter - 0.10) < 1e-6, "physical band height is ten percent of the source wheel diameter")
			var lo := part.contour[0]
			var hi := lo
			for point: Vector2 in part.contour:
				lo = lo.min(point)
				hi = hi.max(point)
				assert_true(absf(point.x) <= part.size.x / 2 + 1e-7 and absf(point.y) <= part.size.y / 2 + 1e-7, "chipped band contour stays inside its source reservation")
			assert_true((hi - lo).distance_to(Vector2(part.size.x, part.size.y)) < 1e-6, "the narrow contour retains its exact physical extents")
