class_name QuartersRoom
extends Node3D

var remembered: Node3D
var present: Node3D
var screens: Array[MeshInstance3D] = []

static func build() -> QuartersRoom:
	var room := QuartersRoom.new()
	room.name = "States"
	room.remembered = QuartersFurnishings.build(&"as_built")
	room.present = QuartersFurnishings.build(&"aged")
	for state: Node3D in [room.remembered, room.present]:
		room.add_child(state)
		var screen := MeshInstance3D.new()
		screen.name = "ConsoleScreen"
		var quad := QuadMesh.new()
		quad.size = Vector2(0.96, 0.48)
		screen.mesh = quad
		screen.transform = QuartersLayout.console_frame()
		screen.position += Vector3(0.015, 0.38, 0)
		var finish := StandardMaterial3D.new()
		finish.albedo_color = Color(0.05, 0.18, 0.24)
		finish.emission_enabled = true
		finish.emission = Color(0.12, 0.45, 0.62)
		finish.emission_energy_multiplier = 0.8
		screen.material_override = finish
		state.add_child(screen)
		room.screens.append(screen)
		Lighting.mesh_layers(state, Lighting.QUARTERS_MASK)
	room.remembered.visible = false
	return room
