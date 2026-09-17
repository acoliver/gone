extends Node3D
## The stasis-room root: builds the greybox scene procedurally at runtime
## and owns the Game container, ticking the sim at the fixed 60 Hz
## physics rate. No lights belong to this build stage: the room renders
## dark until the emergency-lighting chunk lands.

var game: Game

func _ready() -> void:
	game = Game.new()
	add_child(RoomGeometry.build())
	add_child(StasisPods.build(game.registry))
	add_child(Hatch.build())
	_add_observer_camera()

func _physics_process(_delta: float) -> void:
	game.tick()

## A static observer camera until the player rig chunk lands: at the
## hatch end of the room, aimed down the central aisle.
func _add_observer_camera() -> void:
	var camera := Camera3D.new()
	camera.position = Vector3(Pods.ROOM_LENGTH / 2.0 - 1.0, 1.6, 0.0)
	add_child(camera)
	camera.look_at(Vector3(-4.0, 1.0, 0.0))
