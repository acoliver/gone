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
	var door := ShipLayout.authored().layout.door(QuartersLayout.DOOR)
	# The corridor owns the structural entrance wall, but its outer lighting
	# must not determine the room-facing finish. Keep this skin past the pocket.
	var lining := AABB(b.position, Vector3(b.size.x, b.size.y, 0.002))
	var passage := AABB(door.frame().origin - Vector3(door.aperture().x / 2, 0, 0), Vector3(door.aperture().x, door.aperture().y, wall + 0.004))
	var index := 0
	for panel: AABB in SlidingDoorParts.subtract(lining, passage):
		var inner := _solid("ENTRANCE-INNER-%d" % index, panel.get_center(), panel.size)
		inner.surface_identity(QuartersLayout.ID, &"PORT")
		result.append(inner)
		index += 1
	# Seal the pocket's head clearance over the passage, while leaving the
	# clearance over the parked leaf behind the jamb untouched.
	var head := _solid("ENTRANCE-HEAD", door.frame() * Vector3(0, door.aperture().y + SlidingDoorParts.POCKET_CLEARANCE / 2, wall / 2), Vector3(door.aperture().x, SlidingDoorParts.POCKET_CLEARANCE, SlidingDoorParts.POCKET_DEPTH))
	head.surface_identity(QuartersLayout.SECTION, &"STARBOARD")
	result.append(head)
	return result

static func furniture() -> Array[ShipGeometry.SolidSpec]:
	var result: Array[ShipGeometry.SolidSpec] = []
	for prop: Dictionary in QuartersInventory.props():
		var box := QuartersInventory.world_bounds(QuartersInventory.prop_bounds(prop))
		result.append(_solid("PROP/" + prop.id, box.get_center(), box.size, &"furniture"))
	for item: Dictionary in QuartersInventory.small_items():
		var box := QuartersInventory.world_bounds(item.bounds)
		result.append(_solid("ITEM/" + item.id, box.get_center(), box.size, &"furniture"))
	var leaf := QuartersInventory.world_bounds(QuartersInventory.wardrobe_door())
	result.append(_solid("WARDROBE-LEAF", leaf.get_center(), leaf.size, &"furniture"))
	return result

static func _solid(part: String, center: Vector3, size: Vector3, role: StringName = &"wall") -> ShipGeometry.SolidSpec:
	var solid := ShipGeometry.SolidSpec.new(center, size, Quaternion.IDENTITY, StringName("%s/%s" % [QuartersLayout.ID, part]), role)
	solid.surface_identity(QuartersLayout.ID, StringName(part))
	return solid
