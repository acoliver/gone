class_name ShipScene
extends RefCounted
## Shared structural construction. Tick, wake, audio and readiness ownership
## remain with the existing entrypoints until their respective slices.

var bay_root: Node3D
var room: RoomGeometry
var pods_node: StasisPods
var hatch: Hatch
var lighting: Lighting
var rod: Rod
var hallway: Hallway
var power_room: PowerRoom

static func build_into(parent: Node3D, game: Game, production_wires: bool = true) -> ShipScene:
	var scene := ShipScene.new()
	scene.bay_root = Node3D.new()
	scene.bay_root.name = "BayRoot"
	scene.bay_root.transform = game.layout.bay_to_world()
	parent.add_child(scene.bay_root)
	scene.room = RoomGeometry.build(true)
	scene.room.name = "RoomGeometry"
	scene.bay_root.add_child(scene.room)
	scene.pods_node = StasisPods.build(game.registry)
	scene.bay_root.add_child(scene.pods_node)
	scene.hatch = Hatch.build()
	scene.hatch.name = "Hatch"
	scene.bay_root.add_child(scene.hatch)
	scene.lighting = Lighting.build(game)
	scene.bay_root.add_child(scene.lighting)
	scene.bay_root.add_child(Hazards.build())
	if production_wires:
		scene.bay_root.add_child(Wires.build())
	scene.rod = Rod.build()
	scene.bay_root.add_child(scene.rod)
	var environment := scene.lighting.get_node("RoomEnvironment")
	scene.lighting.remove_child(environment)
	parent.add_child(environment)
	scene.hallway = Hallway.build(game)
	parent.add_child(scene.hallway)
	scene.power_room = PowerRoom.build(game)
	parent.add_child(scene.power_room)
	return scene
