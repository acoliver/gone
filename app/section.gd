class_name ShipSection
extends Node3D

var side_leaves: Dictionary = {}

static func build(layout: ShipLayout, spec: ShipLayout.SectionSpec) -> ShipSection:
	assert(spec.number() != 41, "section 41 keeps its opening presentation")
	var section := ShipSection.new()
	section.name = String(spec.id())
	var mask := Lighting.architectural_mask(layout, spec.id())
	for solid: ShipGeometry.SolidSpec in ShipGeometry.section_solids(layout, spec):
		var regular := solid.material_role == &"door"
		var piece := SlidingDoorModel.leaf(layout.door(solid.surface_owner), mask, layout) if regular else surface(solid, mask, layout)
		if regular: section.add_child(SlidingDoorModel.frame(layout.door(solid.surface_owner), mask))
		if solid.material_role == &"floor": piece.visible = false
		section.add_child(piece)
		for id: StringName in spec.side_door_ids():
			if solid.id == StringName("%s/LEAF" % id):
				section.side_leaves[id] = piece
	section.add_child(CorridorDressing.build(layout, spec.id()))
	section.add_child(CeilingProps.build(layout, spec.id()))
	var pitch := spec.bounds().size.x / 4
	for frame: Transform3D in spec.emergency_fixture_frames():
		section.add_child(Lighting.steady_fixture(frame.origin, mask, minf(Lighting.FIXTURE_RANGE, pitch), Surfaces.surface_frame(layout, spec.id(), &"WALL")))
	return section

static func surface(solid: ShipGeometry.SolidSpec, mask: int, layout: ShipLayout = ShipLayout.authored().layout) -> MeshInstance3D:
	var mesh := SlidingDoorModel.wall_mesh(layout, solid) if solid.material_role == &"wall" and solid.hatch_profile == null else Hallway._box_mesh(solid.size)
	var piece := HatchModel.mesh_piece(mesh, solid.transform, mask, Surfaces.material(Surfaces.role_for_solid(solid)))
	Surfaces.bind_solid(piece, layout, solid)
	piece.name = String(solid.id).replace("/", "_")
	piece.set_meta(&"solid_id", solid.id)
	return piece
