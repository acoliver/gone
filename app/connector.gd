class_name ShipConnector
extends Node3D

const FIXTURE_ATTENUATION: float = 0.15

var lift_leaf: Node3D

static func build(layout: ShipLayout, spec: ShipLayout.ConnectorSpec) -> ShipConnector:
	var connector := ShipConnector.new()
	connector.name = String(spec.id())
	var mask := Lighting.space_mask(layout, spec.id())
	for solid: ShipGeometry.SolidSpec in ShipGeometry.connector_solids(layout, spec):
		var piece := ShipSection.surface(solid, mask, layout)
		if solid.id == StringName("%s/FLOOR/000" % spec.id()): piece.visible = false
		connector.add_child(piece)
	connector.add_child(CorridorDressing.build(layout, spec.id()))
	connector.add_child(CeilingProps.build(layout, spec.id()))
	var lift_services := CeilingProps.build(layout, spec.lift_id())
	lift_services.name = "LiftCeilingProps"
	connector.add_child(lift_services)
	var lift := layout.door(layout.lift(spec.lift_id()).door_id())
	connector.lift_leaf = Node3D.new()
	connector.lift_leaf.name = "LiftDoors"
	connector.lift_leaf.transform = lift.frame()
	connector.add_child(connector.lift_leaf)
	for side: int in [-1, 1]:
		var piece := HatchModel.mesh_piece(Hallway._box_mesh(Vector3(lift.aperture().x / 2 - 0.008, lift.aperture().y, ShipLayout.WALL)), Transform3D(Basis(), Vector3(side * lift.aperture().x / 4, lift.aperture().y / 2, ShipLayout.WALL / 2)), mask, Surfaces.material(&"hatch_leaf"))
		Surfaces.bind(piece, &"hatch_leaf", Surfaces.door_frame(lift, &"LEAF"))
		connector.lift_leaf.add_child(piece)
	var panel := HatchModel.control_panel()
	panel.name = "LiftCallPanel"
	panel.transform = lift.frame() * Transform3D(Basis(Vector3.UP, PI), Vector3(lift.aperture().x / 2 + 0.25, 1.25, -HatchModel.CONTROL_SIZE.z / 2))
	Lighting.mesh_layers(panel, mask)
	connector.add_child(panel)
	var bounds := spec.bounds()
	for frame: Transform3D in spec.emergency_fixture_frames():
		connector.add_child(Lighting.steady_fixture(frame.origin, mask, minf(Lighting.FIXTURE_RANGE, bounds.size.x / 2), bounds.position.y if frame.origin == spec.landing_key_position() else bounds.end.y, Surfaces.surface_frame(layout, spec.id(), &"CEILING"), FIXTURE_ATTENUATION))
	RoomReturn.steady(connector, bounds, mask)
	return connector
