class_name Rod
extends Node3D
## A plain metal rod dropped on the stasis-room floor in front of the
## empty row-A pod at the room's mid-station — the door's pry bar, and
## deliberate set dressing the player can act on: it sits a full step
## off the aisle, past the pickup reach of every walking line (the
## z = 1.49 lane out of the pod and the z = 0 centerline), so it is
## found only by walking to it. Deliberately quiet — no glow, no
## outline, no prompt. One interact press near it picks it up (the
## carried flag lives on the motion state; the rod node leaves the
## floor). The placement is authored here rather than in Placement
## because the placement table stays frozen with the collider
## derivation, and the rod is dressing outside the collider set like
## the status plates, cable trays, and wire loops.

## Rod length and radius, in meters: a metre of plain round bar.
const ROD_LENGTH: float = 1.0
const ROD_RADIUS: float = 0.022

## The authored floor-plan center (x, z), in meters: on the open floor
## in front of the empty row-A pod's mouth at the room's mid-station,
## past the aisle's far edge. The aisle runs |z| <= 1.5 with the
## scripted lane out of the pod at z = 1.49 and the row's solids start
## at z = -1.8; at z = -1.55 the bar sits outside the pickup reach of
## every walking line (the lane center sits 3.04 m away, the aisle
## centerline 1.55 m, both beyond the 1.3 m reach) while a deliberate
## stand at the row's mouth brings it in reach with the capsule sweep
## still clear of the pod solids.
const FLOOR_CENTER: Vector2 = Vector2(-0.6, -1.55)

## The rod's yaw about +Z: near-along the pod row, skewed like it was
## dropped, not squared up with the room.
const YAW_RADIANS: float = deg_to_rad(82.0)

static func build() -> Rod:
	var rod := Rod.new()
	rod.name = "Rod"
	var bar := MeshInstance3D.new()
	bar.name = "RodBar"
	var mesh := CylinderMesh.new()
	mesh.top_radius = ROD_RADIUS
	mesh.bottom_radius = ROD_RADIUS
	mesh.height = ROD_LENGTH
	mesh.radial_segments = 16
	bar.mesh = mesh
	bar.material_override = _plain_metal()
	bar.position = Vector3(FLOOR_CENTER.x, ROD_RADIUS, FLOOR_CENTER.y)
	# Lay the cylinder's axis into the floor plane first, then skew the
	# yaw; the compose order applies the lay-down first.
	bar.quaternion = Quaternion(Vector3.UP, YAW_RADIANS) * Quaternion(Vector3.RIGHT, PI / 2.0)
	rod.add_child(bar)
	return rod

## The floor-plan center the pickup reach is measured against.
static func floor_center() -> Vector2:
	return FLOOR_CENTER

## Leave the floor: hidden rather than freed, so headless tests and the
## harness can pin the gone-from-the-scene state deterministically.
func pick_up() -> void:
	visible = false

## Plain steel: mid-grey albedo, mostly metallic, half-rough, no
## emission — it reads under the red emergency light without shining
## like a beacon.
static func _plain_metal() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.52, 0.52, 0.54)
	material.metallic = 0.85
	material.roughness = 0.5
	material.emission_enabled = false
	return material
