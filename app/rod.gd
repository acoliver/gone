class_name Rod
extends Node3D
## A plain metal rod dropped on the stasis-room floor in front of pod 5,
## the empty-open pod beside the player's: obvious set dressing the
## player can act on, deliberately quiet — no glow, no outline, no
## prompt. One interact press near it picks it up (the carried flag
## lives on the motion state; the rod node leaves the floor). The
## placement is authored here rather than in Placement because the
## placement table stays frozen with the collider derivation, and the
## rod is dressing outside the collider set like the status plates,
## cable trays, and wire loops.

## Rod length and radius, in meters: a metre of plain round bar.
const ROD_LENGTH: float = 1.0
const ROD_RADIUS: float = 0.022

## The authored floor-plan center (x, z), in meters: on the open floor
## in front of pod 5's mouth, one step off the aisle's walking line.
## The scripted walk runs at z = 1.495 with a 0.3 m capsule (swept
## z = 1.195..1.795) and the pod's own solids start at z = 1.8, so the
## whole body at z <= 1.19 can never be walked through nor touch a pod.
const FLOOR_CENTER: Vector2 = Vector2(-3.35, 1.10)

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
