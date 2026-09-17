class_name WakePresent
extends Node
## The wake presentation driver, ported from gone_app wake/mod.rs: the
## sim's WakeState owns every timing decision, this node only projects.
## The readiness leg waits for the window's first presented frame before
## starting the timeline (a compiled effect is not a drawable: the whole
## opening must not play into a window that never presented), then the
## machine start-once contract is the sim's own. Every render frame is a
## pure projection of the current logical tick's sample: shader params
## onto the pass, and the sample's sway offset onto the camera as
## (base pose + sway), recomputed from the base each frame so no
## batching of ticks can accumulate drift into the pose. At the sim's
## completion the driver hands off to the phase machine exactly once
## (Waking -> AwakeInPod, any other outcome is a loud wiring failure),
## settles the camera on the neutral pose, and deactivates the pass.
## Gameplay input stays gated off through the sim's phase machine for
## the whole wake. This node never ticks the sim and never writes a
## phase ahead of the completion signal.

var game: Game
var camera: Camera3D = null
var pass_layer: WakePass = null
## When set, the sway projection and the completion settle go through
## the player rig (its yaw/pitch split owns the rotations) instead of
## writing the observer camera's rotation directly.
var rig: Player = null

var _base_rotation: Vector3 = Vector3.ZERO
var _completed: bool = false
var _begun: bool = false

## Build the driver over the game's own wake machine and observer camera.
## The pass is written the machine's current sample (fully closed until
## readiness), so the camera's first presented frame carries the closed
## lids. Not adding the returned node to the tree keeps the readiness leg
## manual, which is the shape the tests drive.
static func build(p_game: Game, p_camera: Camera3D, p_pass: WakePass, p_rig: Player = null) -> WakePresent:
	var driver := WakePresent.new()
	driver.name = "WakePresent"
	driver.game = p_game
	driver.camera = p_camera
	driver.pass_layer = p_pass
	driver.rig = p_rig
	driver._base_rotation = p_camera.rotation
	driver.pass_layer.apply_sample(p_game.wake_state.sample())
	return driver

func _ready() -> void:
	# The presentation leg: the timeline starts only once the window has
	# presented a frame for the lids to composite over.
	await RenderingServer.frame_post_draw
	begin()

## Open the readiness barrier: the sim's start-once contract, then one
## projection of tick zero's closed rest state. No sim tick is consumed.
func begin() -> int:
	var start: int = game.wake_state.mark_ready()
	_begun = true
	present_frame()
	return start

func is_begun() -> bool:
	return _begun

## One presentation frame: a pure projection of the sim's current sample
## onto the pass params and the camera pose, then the completion handoff
## check. Reads only; never advances the sim.
func present_frame() -> void:
	var sample: Wake.WakeSample = game.wake_state.sample()
	pass_layer.apply_sample(sample)
	if rig != null:
		rig.apply_wake_sway(sample.sway_offset)
	else:
		camera.rotation = sway_rotation(_base_rotation, sample.sway_offset)
	_complete_if_due()

## The camera pose for one sway offset: the captured base pose plus the
## sample's sway (x is yaw, y is pitch). A pure projection, so the same
## tick always lands on the same pose bits.
static func sway_rotation(base: Vector3, sway: Vector2) -> Vector3:
	return base + Vector3(sway.y, sway.x, 0.0)

## Gameplay input through the sim's own phase gate: look and locomotion
## stay locked while the phase machine holds Waking, which is every
## moment of the wake timeline.
func input_allowed() -> bool:
	return game.phase.look_allowed()

func is_complete() -> bool:
	return _completed

## The authored completion handoff, exactly once: the neutral camera pose,
## the phase machine's Waking -> AwakeInPod boundary (any other outcome is
## a wiring failure), and the pass deactivated.
func _complete_if_due() -> void:
	if not game.wake_state.is_complete():
		return
	if _completed:
		return
	_completed = true
	assert(game.phase.wake_complete().kind == Phase.Transition.Kind.ADVANCED)
	if rig != null:
		rig.on_wake_complete()
	else:
		camera.rotation = _base_rotation
	pass_layer.set_active(false)

func _process(_delta: float) -> void:
	present_frame()
