class_name LadderShaft
extends Node3D
## Continuous well plus inexpensive instanced landing recesses, with no lights
## or label jobs. Detailed rooms replace their shell instances while resident.

var _shell_instances: Dictionary = {}

static func build(layout: ShipLayout, well: ShipLayout.LadderWellSpec) -> LadderShaft:
	var shaft := LadderShaft.new()
	shaft.name = String(well.id())
	shaft.set_meta(&"continuous_bounds", well.bounds())
	var mask := 0
	var groups: Dictionary = {}
	var closures: Array[ShipGeometry.SolidSpec] = []
	var index := layout.well_ids().find(well.id())
	for deck: int in range(1, 31):
		var spec := layout.connector(ShipLayout.connector_id(deck, index))
		var layer := Lighting.space_mask(layout, spec.id())
		mask |= layer
		shaft.set_meta(StringName("landing_%02d" % deck), spec.port_opening())
		var solids := ShipGeometry.connector_solids(layout, spec)
		# Close the pitch above each vestibule ceiling without spanning the climb lane.
		var landing := well.landing_bounds(deck)
		var gap := ShipLayout.DECK_PITCH - ShipLayout.CLEAR_HEIGHT - ShipLayout.WALL
		if deck > 1:
			var y := landing.end.y + ShipLayout.WALL + gap / 2
			for side: int in [-1, 1]:
				closures.append(ShipGeometry.SolidSpec.new(Vector3(well.bounds().get_center().x + side * (well.bounds().size.x + ShipLayout.WALL) / 2, y, landing.get_center().z), Vector3(ShipLayout.WALL, gap, landing.size.z)))
			closures.append(ShipGeometry.SolidSpec.new(Vector3(landing.get_center().x, y, landing.end.z + ShipLayout.WALL / 2), Vector3(landing.size.x, gap, ShipLayout.WALL)))
		for id: StringName in spec.hatch_ids():
			var door := layout.door(id)
			solids.append_array(ShipGeometry.hatch_wall_solids(door))
			solids.append(ShipGeometry.door_blockers(door)[0])
		var lift := layout.door(layout.lift(spec.lift_id()).door_id())
		solids.append(ShipGeometry.door_blockers(lift)[0])
		for solid: ShipGeometry.SolidSpec in solids:
			var key := "%d/%s" % [layer, solid.material_role]
			if not groups.has(key):
				groups[key] = {"mask": layer, "solids": [], "decks": []}
			groups[key].solids.append(solid)
			groups[key].decks.append(deck)
	for key: String in groups:
		var group: Dictionary = groups[key]
		var solids: Array[ShipGeometry.SolidSpec] = []
		solids.assign(group.solids)
		var view := _boxes(solids, group.mask)
		shaft.add_child(view)
		for i: int in range(solids.size()):
			var deck: int = group.decks[i]
			if not shaft._shell_instances.has(deck):
				shaft._shell_instances[deck] = []
			shaft._shell_instances[deck].append([view.multimesh, i, view.multimesh.get_instance_transform(i)])
	var walls := _boxes(ShipGeometry.well_solids(well), mask)
	walls.name = "ShaftWalls"
	shaft.add_child(walls)
	var pitch_closures := _boxes(closures, mask)
	pitch_closures.name = "PitchClosures"
	shaft.add_child(pitch_closures)
	var bounds := well.bounds()
	var ladder_z := well.climb_line().origin.z - 0.95
	var rails: Array[ShipGeometry.SolidSpec] = []
	for side: int in [-1, 1]:
		rails.append(ShipGeometry.SolidSpec.new(Vector3(bounds.get_center().x + side * 0.38, bounds.get_center().y, ladder_z), Vector3(0.065, bounds.size.y, 0.08), Quaternion.IDENTITY, &"", &"frame"))
	var rail_view := _boxes(rails, mask)
	rail_view.name = "Rails"
	shaft.add_child(rail_view)
	var rungs: Array[ShipGeometry.SolidSpec] = []
	var count := ceili(bounds.size.y / 0.28)
	for rung: int in range(count):
		rungs.append(ShipGeometry.SolidSpec.new(Vector3(bounds.get_center().x, bounds.position.y + rung * 0.28, ladder_z), Vector3(0.76, 0.045, 0.08), Quaternion.IDENTITY, &"", &"frame"))
	var rung_view := _boxes(rungs, mask)
	rung_view.name = "Rungs"
	shaft.add_child(rung_view)
	return shaft

func detail_resident(deck: int, resident: bool) -> void:
	for entry: Array in _shell_instances[deck]:
		var mesh: MultiMesh = entry[0]
		var transform: Transform3D = entry[2]
		mesh.set_instance_transform(entry[1], Transform3D(Basis(Vector3.ZERO, Vector3.ZERO, Vector3.ZERO), transform.origin) if resident else transform)

static func _boxes(solids: Array[ShipGeometry.SolidSpec], mask: int) -> MultiMeshInstance3D:
	var view := MultiMeshInstance3D.new()
	view.layers = mask
	var mesh := BoxMesh.new()
	mesh.size = Vector3.ONE
	var role := solids[0].material_role
	mesh.material = RoomGeometry.wall_material()
	if role == &"floor":
		mesh.material = RoomGeometry.floor_material()
	elif role == &"ceiling":
		mesh.material = RoomGeometry.ceiling_material()
	elif role in [&"frame", &"door"]:
		mesh.material = Hatch._flat_grey(Hatch.HATCH_DOOR_SHADE)
	var instances := MultiMesh.new()
	instances.transform_format = MultiMesh.TRANSFORM_3D
	instances.mesh = mesh
	instances.instance_count = solids.size()
	for i: int in range(solids.size()):
		instances.set_instance_transform(i, solids[i].transform * Transform3D(Basis.from_scale(solids[i].size), Vector3.ZERO))
	view.multimesh = instances
	return view
