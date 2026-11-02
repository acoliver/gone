class_name ShipConnector
extends Node3D

var lift_leaf: Node3D

static func build(layout: ShipLayout, spec: ShipLayout.ConnectorSpec) -> ShipConnector:
	var connector := ShipConnector.new()
	connector.name = String(spec.id())
	var mask := Lighting.space_mask(layout, spec.id())
	for solid: ShipGeometry.SolidSpec in ShipGeometry.connector_solids(layout, spec):
		connector.add_child(ShipSection.surface(solid, mask))
	var lift := layout.door(layout.lift(spec.lift_id()).door_id())
	connector.lift_leaf = Node3D.new()
	connector.lift_leaf.name = "LiftDoors"
	connector.lift_leaf.transform = lift.frame()
	connector.add_child(connector.lift_leaf)
	for side: int in [-1, 1]:
		connector.lift_leaf.add_child(DoorView.mesh_piece(Hallway._box_mesh(Vector3(lift.aperture().x / 2 - 0.008, lift.aperture().y, ShipLayout.WALL)), Transform3D(Basis(), Vector3(side * lift.aperture().x / 4, lift.aperture().y / 2, ShipLayout.WALL / 2)), mask))
	var panel := DoorView.control_panel()
	panel.name = "LiftCallPanel"
	panel.transform = lift.frame() * Transform3D(Basis(Vector3.UP, PI), Vector3(lift.aperture().x / 2 + 0.25, 1.25, -0.06))
	Lighting.mesh_layers(panel, mask)
	connector.add_child(panel)
	var bounds := spec.bounds()
	for side: int in [-1, 1]:
		connector.add_child(Lighting.steady_fixture(Vector3(bounds.get_center().x, bounds.position.y + Lighting.WALL_MOUNT_HEIGHT, side * (bounds.size.z / 2 - Lighting.WALL_STANDOFF)), mask, minf(Lighting.FIXTURE_RANGE, bounds.size.x / 2)))
	var landing := layout.well(spec.well_id()).landing_bounds(spec.deck_number())
	connector.add_child(Lighting.steady_fixture(Vector3(landing.get_center().x, landing.position.y + Lighting.WALL_MOUNT_HEIGHT, landing.get_center().z), mask, landing.size.z))
	return connector
