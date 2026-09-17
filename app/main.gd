extends Node3D
## The stasis-room root: builds the greybox scene procedurally at runtime
## and owns the Game container, ticking the sim at the fixed 60 Hz
## physics rate. The emergency lighting node reads the sim's power grid
## through its own bridge; ceiling hazards are inert dressing.

var game: Game
var camera: Camera3D
var wake_pass: WakePass
var wake_present: WakePresent

func _ready() -> void:
	game = Game.new()
	add_child(RoomGeometry.build())
	add_child(StasisPods.build(game.registry))
	add_child(Hatch.build())
	add_child(Lighting.build(game))
	add_child(Hazards.build())
	_add_observer_camera()
	_add_wake_presentation()

## The eyelid pass over the presented frame and its driver over the sim's
## wake timeline: the lids exist fully closed from the first frame, and
## the timeline starts only once the window has presented one.
func _add_wake_presentation() -> void:
	wake_pass = WakePass.build()
	add_child(wake_pass)
	wake_present = WakePresent.build(game, camera, wake_pass)
	add_child(wake_present)

func _physics_process(_delta: float) -> void:
	game.tick()

## A static observer camera until the player rig chunk lands: at the
## hatch end of the room, aimed down the central aisle.
func _add_observer_camera() -> void:
	camera = Camera3D.new()
	camera.position = Vector3(Pods.ROOM_LENGTH / 2.0 - 1.0, 1.6, 0.0)
	add_child(camera)
	camera.look_at(Vector3(-4.0, 1.0, 0.0))
