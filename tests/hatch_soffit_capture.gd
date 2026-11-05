extends SceneTree
## Check ray-identified soffit pixels in the unchanged production X=30 close captures.

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 1, "supply production capture directory")
	var probe := HatchBandProbe.from_hatch()
	var door := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	var eye := Vector3(28.45, 1.30, 0.03)
	var camera := Transform3D(Basis.looking_at(Vector3(29.92, 1.30, 0) - eye), eye)
	var local := door.frame().affine_inverse() * camera
	var soffit := PackedVector2Array()
	var leaf := PackedVector2Array()
	var scale := 2 * tan(deg_to_rad(86.0 / 2)) / 1296.0
	for y: int in range(80, 530, 2):
		for x: int in range(1072, 1233, 8):
			var direction := local.basis * Vector3((x + 0.5 - 1152) * scale, -(y + 0.5 - 648) * scale, -1).normalized()
			var hit := probe.cast(local.origin, direction)
			if hit.is_empty(): continue
			if hit.part.begins_with("SURROUND/") and hit.normal.y < -0.9 and hit.normal.dot(-direction) > 0:
				soffit.append(Vector2(x, y))
			if hit.part == "ForeSteel/plate" and hit.position.y > 1.6 and hit.position.y < 2.1:
				leaf.append(Vector2(x, y))
	assert(soffit.size() >= 20 and leaf.size() >= 20, "actual soffit rows and unobstructed upper leaf are sampled")
	var passed := true
	for circuit: String in ["emergency-red-orange", "secondary-white"]:
		var image := Image.load_from_file(args[0].path_join(circuit + "-hatch-close.png"))
		assert(image != null and image.get_size() == Vector2i(2304, 1296), "production capture at unchanged native resolution")
		var result: Dictionary = preload("res://tests/hatch_soffit_samples.gd").evaluate(image, soffit, leaf)
		print("HATCH_SOFFIT circuit=%s %s" % [circuit, JSON.stringify(result)])
		passed = passed and result.passed
	quit(0 if passed else 1)
