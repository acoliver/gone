class_name RoomReturn
extends ReflectionProbe
## A bounded diffuse return from the room's existing architectural circuits.
## No sky, capture, emission or extra source participates in this approximation.

const RETURN_SHARE := 0.1
var _emergency: Array[OmniLight3D] = []
var _regular: Array[OmniLight3D] = []

static func build(bounds: AABB, emergency: Array[OmniLight3D], regular: Array[OmniLight3D], mask: int) -> RoomReturn:
	var probe := RoomReturn.new()
	probe.name = "RoomReturn"
	probe.position = bounds.get_center()
	probe.size = bounds.size
	probe.interior = true
	probe.blend_distance = 0.0
	probe.ambient_mode = ReflectionProbe.AMBIENT_COLOR
	probe.cull_mask = 0
	probe.reflection_mask = mask
	probe._emergency = emergency.duplicate()
	probe._regular = regular.duplicate()
	probe.refresh()
	return probe

static func steady(parent: Node3D, bounds: AABB, mask: int) -> void:
	var keys: Array[OmniLight3D] = []
	for key: Node in parent.find_children("*", "OmniLight3D", true, false): keys.append(key)
	# The continuous opening hall shell also borders the connector volumes.
	parent.add_child(build(bounds, keys, [], mask | 1))

static func _mean_radiance(keys: Array[OmniLight3D]) -> Color:
	var result := Color(0, 0, 0, 1)
	for key: OmniLight3D in keys:
		result += key.light_color.srgb_to_linear() * key.light_energy
	return result / keys.size() if not keys.is_empty() else Color.BLACK

func refresh() -> void:
	# Average each circuit separately so fixture density does not brighten the
	# return, and a red-to-white crossfade remains linear in emitted radiance.
	var radiance := (_mean_radiance(_emergency) + _mean_radiance(_regular)) * RETURN_SHARE
	var energy := maxf(radiance.r, maxf(radiance.g, radiance.b))
	var colour := (radiance / energy).linear_to_srgb() if energy > 0 else Color.BLACK
	colour.a = 1.0
	if ambient_color != colour: ambient_color = colour
	if ambient_color_energy != energy: ambient_color_energy = energy

func _process(_delta: float) -> void:
	refresh()
