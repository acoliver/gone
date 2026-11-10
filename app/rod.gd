class_name Rod
extends Node3D
## A detached formed ceiling seat dropped on the stasis-room floor in front of the
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

## Historical logical prop dimensions; pickup geometry and reach remain unchanged.
const ROD_LENGTH: float = 1.0
const ROD_RADIUS: float = 0.022

## The floor-plan center comes from ShipLayout. New pod #88 moves it
## to bay (-0.6, -1.40), clear of the longer pod row. It remains beyond
## the 1.3 m pickup reach from the aisle center and the exit walking line;
## a deliberate approach to the row mouth puts it in reach.

## The rod's yaw about +Z: near-along the pod row, skewed like it was
## dropped, not squared up with the room.
const YAW_RADIANS: float = deg_to_rad(82.0)

static func build() -> Rod:
	var rod := Rod.new()
	rod.name = "Rod"
	# #110: the user-redrawn source is the actual missing ceiling seat, not a round bar.
	var bar := SeatRailComponent.build(&"middle")
	bar.name = "RodBar"
	bar.transform = SeatRailComponent.floor_pose()
	rod.add_child(bar)
	return rod

## The floor-plan center the pickup reach is measured against.
static func local_floor_center() -> Vector2:
	var center := ShipLayout.authored().layout.bay().rod_local().origin
	return Vector2(center.x, center.z)

static func floor_center() -> Vector2:
	var center := ShipLayout.authored().layout.anchor(&"D14-BAY-ROD").origin
	return Vector2(center.x, center.z)

## Leave the floor: hidden rather than freed, so headless tests and the
## harness can pin the gone-from-the-scene state deterministically.
func pick_up() -> void:
	visible = false
