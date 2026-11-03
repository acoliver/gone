class_name ShipSection
extends Node3D

var side_leaves: Dictionary = {}

static func build(layout: ShipLayout, spec: ShipLayout.SectionSpec) -> ShipSection:
	assert(spec.number() != 41, "section 41 keeps its opening presentation")
	var section := ShipSection.new()
	section.name = String(spec.id())
	var mask := Lighting.space_mask(layout, spec.id())
	for solid: ShipGeometry.SolidSpec in ShipGeometry.section_solids(layout, spec):
		var piece := surface(solid, mask)
		section.add_child(piece)
		for id: StringName in spec.side_door_ids():
			if solid.id == StringName("%s/LEAF" % id):
				section.side_leaves[id] = piece
	var bounds := spec.bounds()
	var pitch := bounds.size.x / 4
	for station: int in range(4):
		for side: int in [-1, 1]:
			var origin := Vector3(bounds.position.x + (station + 0.5) * pitch, bounds.position.y + Lighting.WALL_MOUNT_HEIGHT, side * (bounds.size.z / 2 - Lighting.WALL_STANDOFF))
			section.add_child(Lighting.steady_fixture(origin, mask, minf(Lighting.FIXTURE_RANGE, pitch)))
	return section

static func surface(solid: ShipGeometry.SolidSpec, mask: int) -> MeshInstance3D:
	var material := RoomGeometry.wall_material()
	match solid.material_role:
		&"floor": material = RoomGeometry.floor_material()
		&"ceiling": material = RoomGeometry.ceiling_material()
		&"door", &"frame": material = HatchModel.flat_grey(HatchModel.DOOR_SHADE)
	var piece := HatchModel.mesh_piece(Hallway._box_mesh(solid.size), solid.transform, mask, material)
	piece.name = String(solid.id).replace("/", "_")
	piece.set_meta(&"solid_id", solid.id)
	return piece
