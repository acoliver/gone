class_name PortalCrossing
extends RefCounted
## Accepted foot motion through the hall face, from the bay toward -Z.

static func exits(previous: Vector3, current: Vector3, portal: ShipLayout.DoorSpec, deck: int, walking: bool, passage_open: bool) -> bool:
	if not walking or not passage_open or deck != portal.deck_number():
		return false
	var inverse := portal.frame().affine_inverse()
	var before := inverse * previous
	var after := inverse * current
	if before.z <= 0.0 or after.z > 0.0:
		return false
	var fraction := before.z / (before.z - after.z)
	var hit := before.lerp(after, fraction)
	return absf(hit.x) <= portal.aperture().x / 2.0 and hit.y >= 0.0 and hit.y <= portal.aperture().y
