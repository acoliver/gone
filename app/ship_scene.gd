class_name ShipScene
extends RefCounted
## Shared structural construction. Tick, wake, audio and readiness ownership
## remain with the existing entrypoints until their respective slices.

var room: RoomGeometry
var pods_node: StasisPods
var hatch: Hatch
var lighting: Lighting
var rod: Rod
var hallway: Hallway
var power_room: PowerRoom

static func build_into(parent: Node3D, game: Game, production_wires: bool = true) -> ShipScene:
	var scene := ShipScene.new()
	scene.room = RoomGeometry.build(true)
	scene.room.name = "RoomGeometry"
	parent.add_child(scene.room)
	scene.pods_node = StasisPods.build(game.registry)
	parent.add_child(scene.pods_node)
	scene.hatch = Hatch.build()
	scene.hatch.name = "Hatch"
	parent.add_child(scene.hatch)
	scene.lighting = Lighting.build(game)
	parent.add_child(scene.lighting)
	parent.add_child(Hazards.build())
	if production_wires:
		parent.add_child(Wires.build())
	scene.rod = Rod.build()
	parent.add_child(scene.rod)
	scene.hallway = Hallway.build(game)
	parent.add_child(scene.hallway)
	scene.power_room = PowerRoom.build(game)
	parent.add_child(scene.power_room)
	return scene
