extends RefCounted
## A downward outward soffit cannot face the lamp above it. Test fill-lit pixels instead.

static func evaluate(image: Image, soffit: PackedVector2Array, leaf: PackedVector2Array) -> Dictionary:
	var minimum := 1.0
	var soffit_luma := 0.0
	var leaf_luma := 0.0
	for pixel: Vector2 in soffit:
		var colour := image.get_pixelv(Vector2i(pixel))
		minimum = minf(minimum, maxf(colour.r, maxf(colour.g, colour.b)))
		soffit_luma += colour.srgb_to_linear().get_luminance()
	for pixel: Vector2 in leaf: leaf_luma += image.get_pixelv(Vector2i(pixel)).srgb_to_linear().get_luminance()
	if not soffit.is_empty(): soffit_luma /= soffit.size()
	if not leaf.is_empty(): leaf_luma /= leaf.size()
	return {"passed": not soffit.is_empty() and not leaf.is_empty() and minimum > 2.0 / 255.0 and soffit_luma < leaf_luma,
		"soffit_samples": soffit.size(), "leaf_samples": leaf.size(), "minimum_max_channel_255": minimum * 255,
		"soffit_mean_linear_luma": soffit_luma, "leaf_mean_linear_luma": leaf_luma}
