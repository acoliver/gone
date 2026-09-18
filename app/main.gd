extends Node3D
## The stasis-room root: builds the greybox scene procedurally at runtime
## and owns the Game container, ticking the sim at the fixed 60 Hz
## physics rate. The emergency lighting node reads the sim's power grid
## through its own bridge; ceiling hazards are inert dressing.

var game: Game
var camera: Camera3D
var player: Player
var hatch: Hatch
var wake_pass: WakePass
var wake_present: WakePresent

func _ready() -> void:
	game = Game.new()
	add_child(RoomGeometry.build())
	add_child(StasisPods.build(game.registry))
	hatch = Hatch.build()
	add_child(hatch)
	add_child(Lighting.build(game))
	add_child(Hazards.build())
	add_child(Wires.build())
	_add_player()
	_add_wake_presentation()

func _physics_process(_delta: float) -> void:
	game.tick()

## The eyelid pass over the presented frame and its driver over the sim's
## wake timeline: the lids exist fully closed from the first frame, and
## the timeline starts only once the window has presented one. The player
## rig carries the sway.
func _add_wake_presentation() -> void:
	wake_pass = WakePass.build()
	add_child(wake_pass)
	wake_present = WakePresent.build(game, camera, wake_pass, player)
	add_child(wake_present)

## The first-person player rig: the sim drives the body, the rig
## projects its pose, and the wake presentation sways the same camera.
func _add_player() -> void:
	player = Player.build(game, hatch)
	add_child(player)
	camera = player.camera
