class_name Hatch
extends Node3D
## Bay-local wrapper over the shared hinged hatch and its persistent door view.

var view: DoorView

static func build(layout: ShipLayout = ShipLayout.authored().layout, fore_mask: int = 1, aft_mask: int = 1) -> Hatch:
	var hatch := Hatch.new()
	var spec := layout.door(ShipLayout.BAY_DOOR_ID)
	hatch.view = DoorView.build(spec, fore_mask, aft_mask)
	hatch.view.transform = layout.world_to_bay() * spec.frame()
	hatch.add_child(hatch.view)
	return hatch

func door_piece() -> Node3D:
	return view.label_leaf()
