extends SceneTree
## Windowed one-shot asset-pipeline probe for issue #45: instantiates the
## Blender-built pod-probe GLB at the origin and renders it twice with the
## same framing — once under one dim red OmniLight (shadows off), once
## under a neutral white OmniLight of equal energy — over a near-black
## environment, saving tmp/pipeline/probe-capsule.png and
## tmp/pipeline/probe-capsule-neutral.png, and exits 0 only if both PNGs
## landed. The camera sits high on the hinge-opposite (opening) side of
## the pod: the GLB carries the canopy hinge at +Z, so viewing from -Z
## three-quarter elevation shows the raised lid wing, the exposed tub
## interior, and the couch instead of hiding them behind the hinge-side
## shell wall. The imported canopy transform is logged each run so a lost
## open angle is visible in the log, not just in the pixels.
## Run: godot --path . --resolution 640x360 -s assets/props/probe/probe_capture.gd

const POD_PATH: String = "res://assets/props/probe/pod-probe.glb"
const CAPTURE_PATH: String = "tmp/pipeline/probe-capsule.png"
const NEUTRAL_CAPTURE_PATH: String = "tmp/pipeline/probe-capsule-neutral.png"
const WARMUP_FRAMES: int = 8
const CAMERA_FOV: float = 40.0
const CAMERA_POSITION: Vector3 = Vector3(2.4, 2.7, -1.9)
const AIM_POINT: Vector3 = Vector3(0.0, 0.15, 0.25)
const LIGHT_POSITION: Vector3 = Vector3(1.6, 2.2, -1.5)
const LIGHT_COLOR: Color = Color(1.0, 0.0, 0.0)
const NEUTRAL_LIGHT_COLOR: Color = Color(1.0, 1.0, 1.0)
const LIGHT_ENERGY: float = 12.0
const LIGHT_RANGE: float = 10.0
const BACKGROUND: Color = Color(0.01, 0.01, 0.012)

func _initialize() -> void:
	var rig := _build_scene()
	if rig == null:
		return
	await _capture(rig.light, LIGHT_COLOR, CAPTURE_PATH)
	await _capture(rig.light, NEUTRAL_LIGHT_COLOR, NEUTRAL_CAPTURE_PATH)
	quit(0)

func _build_scene() -> Rig:
	var pod_scene: PackedScene = load(POD_PATH)
	if pod_scene == null or not pod_scene.can_instantiate():
		print("RESULT FAIL cannot load %s" % POD_PATH)
		quit(1)
		return null
	var scene := Node3D.new()
	scene.name = "ProbeRoot"
	var pod: Node3D = pod_scene.instantiate()
	pod.position = Vector3.ZERO
	scene.add_child(pod)
	var canopy := pod.find_child("Canopy", true, false) as Node3D
	if canopy != null:
		var e := canopy.transform.basis.get_euler()
		print("PROBE canopy origin=(%.6f, %.6f, %.6f) euler_deg=(%.3f, %.3f, %.3f)" % [
			canopy.transform.origin.x, canopy.transform.origin.y, canopy.transform.origin.z,
			rad_to_deg(e.x), rad_to_deg(e.y), rad_to_deg(e.z)])
	var camera := Camera3D.new()
	camera.fov = CAMERA_FOV
	camera.near = 0.05
	camera.far = 50.0
	scene.add_child(camera)
	var light := OmniLight3D.new()
	light.light_color = LIGHT_COLOR
	light.light_energy = LIGHT_ENERGY
	light.omni_range = LIGHT_RANGE
	light.shadow_enabled = false
	light.position = LIGHT_POSITION
	scene.add_child(light)
	scene.add_child(_world_environment())
	root.add_child(scene)
	# look_at refuses before the first frame (the tree is not live yet in
	# _initialize), so aim from an explicit position instead.
	camera.look_at_from_position(CAMERA_POSITION, AIM_POINT)
	camera.make_current()
	var rig := Rig.new()
	rig.light = light
	return rig

func _world_environment() -> WorldEnvironment:
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = BACKGROUND
	var world := WorldEnvironment.new()
	world.environment = environment
	return world

## Node _ready is deferred until the first frame processes, so the capture
## waits for the rig to exist and the renderer to settle before grabbing
## the viewport.
func _capture(light: OmniLight3D, color: Color, path: String) -> void:
	light.light_color = color
	for _i: int in range(WARMUP_FRAMES):
		await process_frame
	var image := root.get_texture().get_image()
	var resolved := ProjectSettings.globalize_path(path)
	DirAccess.make_dir_recursive_absolute(resolved.get_base_dir())
	if image.save_png(resolved) != OK:
		print("RESULT FAIL save_png %s" % resolved)
		quit(1)
		return
	print("RESULT OK path=%s size=%s" % [resolved, str(image.get_size())])

class Rig:
	extends RefCounted
	var light: OmniLight3D
