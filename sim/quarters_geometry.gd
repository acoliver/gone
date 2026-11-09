class_name QuartersGeometry
extends RefCounted

static func shell() -> Array[ShipGeometry.SolidSpec]:
	var b := QuartersLayout.bounds()
	var wall := QuartersLayout.WALL
	var result: Array[ShipGeometry.SolidSpec] = []
	for top: bool in [false, true]:
		var point := b.get_center()
		point.y = b.end.y + wall / 2 if top else b.position.y - wall / 2
		result.append(_solid("CEILING" if top else "FLOOR", point, Vector3(b.size.x + 2 * wall, wall, b.size.z + 2 * wall), &"ceiling" if top else &"floor"))
	for side: int in [-1, 1]:
		var x := b.position.x - wall / 2 if side < 0 else b.end.x + wall / 2
		result.append(_solid("FORE" if side < 0 else "AFT", Vector3(x, b.get_center().y, b.get_center().z), Vector3(wall, b.size.y, b.size.z)))
	result.append(_solid("STARBOARD", Vector3(b.get_center().x, b.get_center().y, b.end.z + wall / 2), Vector3(b.size.x + 2 * wall, b.size.y, wall)))
	return result

static func _solid(part: String, center: Vector3, size: Vector3, role: StringName = &"wall") -> ShipGeometry.SolidSpec:
	var solid := ShipGeometry.SolidSpec.new(center, size, Quaternion.IDENTITY, StringName("%s/%s" % [QuartersLayout.ID, part]), role)
	solid.surface_identity(QuartersLayout.ID, StringName(part))
	return solid
