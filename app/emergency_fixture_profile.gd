class_name EmergencyFixtureProfile
extends RefCounted

# Neutral room output and pod-only key output now share the existing wall source.
# Profiles: neutral share, pod share, range, attenuation.
# Identical row cages retain the bay budget; the hatch lamp preserves doorway spill.
const BAY := Vector4(1.216167, 0.263833, 7.000000, 2.479420)
const BAY_HATCH := Vector4(0.000000, 1.000000, 10.449859, 1.134204)
const HALL: Array[Vector4] = [
	Vector4(0.300000, 0.000000, 10.132588, 3.000000),
	Vector4(0.710000, 0.000000, 4.217218, 2.151898),
	Vector4(0.315000, 0.000000, 10.896189, 3.000000),
	Vector4(0.420000, 0.000000, 3.703507, 0.150000),
	Vector4(0.420000, 0.000000, 3.997807, 0.150000),
	Vector4(0.315000, 0.000000, 4.073337, 0.150000),
	Vector4(0.000000, 0.000000, 8.541920, 3.000000),
	Vector4(0.300000, 0.000000, 6.221070, 3.000000),
]
const POWER: Array[Vector4] = [
	Vector4(0.000000, 0.000000, 3.505193, 0.833968),
	Vector4(0.000000, 0.000000, 3.067586, 0.150000),
	Vector4(0.000000, 0.000000, 2.935641, 0.150000),
	Vector4(0.000000, 0.000000, 2.982841, 0.153711),
	Vector4(0.900000, 0.000000, 5.359976, 2.564869),
	Vector4(0.900000, 0.000000, 3.439738, 2.185305),
	Vector4(0.600000, 0.000000, 12.000000, 2.432394),
	Vector4(0.600000, 0.000000, 11.875833, 1.304751),
	Vector4(0.600000, 0.000000, 2.934144, 0.150000),
]

static func apply(light: OmniLight3D, row: Vector4, level: float, red_share: float = 1.0) -> void:
	var share := red_share + row.x + row.y
	var color := (Lighting.EMERGENCY_RED.srgb_to_linear() * red_share + Lighting.EMERGENCY_FILL_COLOR.srgb_to_linear() * row.x + Lighting.POD_STATUS_RED.srgb_to_linear() * row.y) / share
	light.light_color = color.linear_to_srgb()
	light.set_meta(&"energy_share", share)
	light.omni_range = row.z
	light.omni_attenuation = row.w
	light.light_energy = Lighting.emergency_energy() * share * level
