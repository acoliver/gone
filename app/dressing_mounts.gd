class_name DressingMounts
extends RefCounted

static func ceiling_stem(parent: Node3D, ceiling_y: float) -> void:
	assert(ceiling_y > parent.position.y, "fixture mounting point is below its ceiling")
	vertical_stem(parent, ceiling_y)

static func vertical_stem(parent: Node3D, support_y: float) -> void:
	var height := support_y - parent.position.y
	var stem := MeshInstance3D.new()
	stem.name = "CeilingMount"
	stem.mesh = HatchModel.box_mesh(Vector3(0.045, absf(height), 0.045))
	stem.position.y = height / 2
	stem.material_override = Surfaces.material(&"hardware")
	stem.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(stem)

static func tray_hangers(tray: ShipGeometry.SolidSpec, ceiling_y: float) -> Array[ShipGeometry.SolidSpec]:
	var hangers: Array[ShipGeometry.SolidSpec] = []
	for station: float in [-0.35, 0.35]:
		var bottom := tray.corner(Vector3(tray.size.x * station, tray.size.y / 2 - 0.005, 0))
		var height := ceiling_y - bottom.y
		assert(height > 0, "tray mount reaches upward to the ceiling")
		hangers.append(ShipGeometry.SolidSpec.new(bottom + Vector3.UP * height / 2, Vector3(0.055, height, 0.055)))
	return hangers
