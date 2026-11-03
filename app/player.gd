class_name Player
extends Node3D
## The first-person player rig, ported from gone_app player/mod.rs and
## motion.rs wiring: this node carries the yaw, a Camera3D child at eye
## height carries the pitch, and the sim owns every motion decision. The
## node integrates look from the shared input plane, projects the sim's
## capsule onto the rig (head sphere through the get-up, standing eye
## height on the floor), translates the device's InputMap actions and
## mouse onto the plane, and projects the sim's deterministic door
## opening onto the hatch's door slab every tick.

var game: Game
var camera: Camera3D
var hatch: Node3D = null
var power_room: PowerRoom = null
var rod: Rod = null
var plane: InputPlane
var interactions: Interactions
var motion: PlayerMotion
var adapter: InputPlane.ScriptedAdapter = null
## Scripted mode: the harness adapter is the only input producer and the
## cursor gate on look is lifted (an unattended window never captures).
var scripted: bool = false
## Live play opts in; deterministic captures retain the exact tick pose.
var interpolate_view: bool = false

var _look_yaw: float = 0.0
var _look_pitch: float = 0.0
var _previous_eye := Vector3.ZERO
var _previous_look := Vector2.ZERO
var _presented_look := Vector2.ZERO
var _mouse_pixels: Vector2 = Vector2.ZERO
var _device_actions: bool = false

static func build(p_game: Game, p_hatch: Node3D) -> Player:
	var player := Player.new()
	player.name = "Player"
	player.game = p_game
	player.hatch = p_hatch
	return player

func _ready() -> void:
	plane = InputPlane.new()
	motion = PlayerMotion.new()
	interactions = Interactions.new(game.layout, ShipCollision.opening_sight_solids(game.registry, game.layout))
	# Authored spawn: lying at the exit path's first pose head, facing
	# the pod's opening, aimed one stop short of the vertical.
	var spawn: Exit.ExitPose = game.exit_path.poses()[0]
	_look_yaw = game.registry.player_pod().placement().yaw_radians + game.layout.bay_to_world().basis.get_euler().y
	_look_pitch = InputPlane.PITCH_LIMIT
	camera = Camera3D.new()
	camera.name = "PlayerPitch"
	add_child(camera)
	camera.make_current()
	position = spawn.head()
	_previous_eye = position
	_previous_look = look_angles()
	_presented_look = look_angles()
	_project_rotation(Vector2.ZERO)
	_device_actions = InputMap.has_action("move_forward")
	if not scripted:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func look_angles() -> Vector2:
	return Vector2(_look_yaw, _look_pitch)

func sim_forward() -> Vector3:
	return -Basis.from_euler(Vector3(_look_pitch, 0, 0)).z.rotated(Vector3.UP, _look_yaw)

func _unhandled_input(event: InputEvent) -> void:
	if scripted or Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		return
	var motion_event := event as InputEventMouseMotion
	if motion_event != null:
		_mouse_pixels += motion_event.relative

func step() -> void:
	_previous_eye = motion.eye(game)
	_previous_look = look_angles()
	_collect_device_input(Sim.LOGICAL_TICK_SECS)
	if scripted and adapter != null:
		adapter.offer_tick(plane)
	_integrate_look()
	var facing := sim_forward()
	motion.advance(plane, game, _look_yaw, Sim.LOGICAL_TICK_SECS, facing)
	var context := Interactions.context_for(game, motion, facing)
	var selected := interactions.process(plane, context)
	if selected == &"D14-BAY-ROD" and rod != null:
		rod.pick_up()
	if not motion.failure().is_empty():
		push_error("halting on player motion failure: " + motion.failure())
		get_tree().quit(1)
		return
	position = motion.eye(game)
	if power_room != null:
		power_room.tick_console_attention(position, facing)
	plane.end_frame()

func present() -> void:
	position = motion.eye(game)
	_presented_look = look_angles()
	_project_rotation(Vector2.ZERO)

func present_interpolated(fraction: float) -> void:
	position = _previous_eye.lerp(motion.eye(game), fraction)
	_presented_look = Vector2(lerp_angle(_previous_look.x, _look_yaw, fraction), lerpf(_previous_look.y, _look_pitch, fraction))
	_project_rotation(Vector2.ZERO)

func _process(_delta: float) -> void:
	# WakePresent owns the authored sway until the logical wake completes.
	if interpolate_view and game.phase.look_allowed():
		present_interpolated(Engine.get_physics_interpolation_fraction())

## The device producer: held InputMap actions become the plane's
## movement intent, fresh presses become its edges, mouse pixels and the
## held look keys (comma/period for yaw, the letters A/D for yaw and W/S
## for pitch) become its radians (all land on the same look channel, so
## a tick's mouse and keyboard deltas sum). Scripted runs skip it: the
## adapter offers the same channels.
func _collect_device_input(delta: float) -> void:
	if scripted or not _device_actions:
		return
	# The rig's camera looks along Godot's -Z at the yaw while the sim's
	# walk frame steps along +Z, so the forward key offers the negative
	# sim axis (strafe already shares signs between the frames): forward
	# walks where the player looks, bridged like the look channel's
	# -turn below. The scripted lane keeps the sim frame's signs.
	if motion.mounted():
		var climb := clampf(Input.get_axis("climb_down", "climb_up") + Input.get_axis("move_back", "move_forward"), -1, 1)
		plane.offer_climb(climb)
	else:
		plane.offer_movement(-Input.get_axis("move_back", "move_forward"), Input.get_axis("move_left", "move_right"))
	if Input.is_action_just_pressed("activate"):
		plane.offer_press(InputPlane.Buttons.ACTIVATE)
	if Input.is_action_just_pressed("interact"):
		plane.offer_press(InputPlane.Buttons.INTERACT)
	if _mouse_pixels != Vector2.ZERO:
		plane.offer_look_pixels(_mouse_pixels)
		_mouse_pixels = Vector2.ZERO
	var turn := Input.get_axis("look_left", "look_right")
	var pitch := 0.0 if motion.mounted() else Input.get_axis("look_down", "look_up")
	if turn != 0.0 or pitch != 0.0:
		plane.offer_look(-turn * InputPlane.TURN_SPEED * delta,
			pitch * InputPlane.PITCH_SPEED * delta)

## Look is armed by the phase gate (from AwakeInPod on) and the cursor
## gate (a captured cursor in device mode; always in scripted mode).
func _integrate_look() -> void:
	var cursor_armed := scripted or Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
	if not cursor_armed or not game.phase.look_allowed():
		return
	var delta := plane.take_look()
	var angles := InputPlane.integrate_look(_look_yaw, _look_pitch, delta)
	_look_yaw = angles.x
	_look_pitch = angles.y
	_presented_look = angles
	_project_rotation(Vector2.ZERO)

## Project the integrated look angles onto the rig, composed with the
## wake sway while the timeline owns the camera.
func _project_rotation(sway: Vector2) -> void:
	rotation.y = _presented_look.x + sway.x
	camera.rotation.x = clampf(_presented_look.y + sway.y, -InputPlane.PITCH_LIMIT, InputPlane.PITCH_LIMIT)

## WakePresent's sway carrier: a pure projection of the sample's sway on
## top of the (look-gated, so static through the wake) angles.
func apply_wake_sway(sway: Vector2) -> void:
	_project_rotation(sway)

func on_wake_complete() -> void:
	_project_rotation(Vector2.ZERO)
