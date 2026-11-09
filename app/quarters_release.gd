class_name QuartersRelease
extends RefCounted

const LABEL_FRAME := Transform3D(Basis.IDENTITY, Vector3(0, 0.16, 0.041))
const LABEL_SIZE := Vector2(0.20, 0.065)

static func build(layout: ShipLayout) -> Node3D:
	var root := Node3D.new()
	root.name = "ManualRelease"
	root.transform = QuartersLayout.release_frame()
	var steel := Surfaces.material(&"hatch_leaf")
	var frame := Surfaces.door_frame(layout.door(QuartersLayout.DOOR), &"FRAME")
	var mask := Lighting.architectural_mask(layout, QuartersLayout.SECTION)
	var size := QuartersLayout.RELEASE_SIZE
	for part: Array in [
		["Recess", Vector3(size.x, size.y, 0.03), Vector3.ZERO],
		["FrameLeft", Vector3(0.025, size.y, 0.035), Vector3(-(size.x - 0.025) / 2, 0, 0.0225)],
		["FrameRight", Vector3(0.025, size.y, 0.035), Vector3((size.x - 0.025) / 2, 0, 0.0225)],
		["FrameHead", Vector3(size.x - 0.05, 0.085, 0.035), Vector3(0, (size.y - 0.085) / 2, 0.0225)],
		["FrameFoot", Vector3(size.x - 0.05, 0.035, 0.035), Vector3(0, -(size.y - 0.035) / 2, 0.0225)],
		["HandleLeft", Vector3(0.025, 0.11, 0.035), Vector3(-0.065, -0.03, 0.0375)],
		["HandleRight", Vector3(0.025, 0.11, 0.035), Vector3(0.065, -0.03, 0.0375)],
		["PullGrip", Vector3(0.155, 0.026, 0.026), Vector3(0, -0.03, 0.066)],
	]:
		var piece := HatchModel.mesh_piece(HatchModel.box_mesh(part[1]), Transform3D(Basis(), part[2]), mask, HatchModel.material(0.055) if part[0] == "Recess" else steel)
		piece.name = part[0]
		if part[0] != "Recess": Surfaces.bind(piece, &"hatch_leaf", frame)
		root.add_child(piece)
	for x: float in [-0.115, 0.115]:
		for y: float in [-0.20, 0.20]:
			var screw := HatchModel.mesh_piece(HatchModel.cylinder(0.007, 0.004), Transform3D(Basis(Vector3.RIGHT, PI / 2), Vector3(x, y, 0.042)), mask, steel)
			Surfaces.bind(screw, &"hatch_leaf", frame)
			root.add_child(screw)
	return root
