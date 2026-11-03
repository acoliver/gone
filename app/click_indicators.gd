class_name ClickIndicators
extends Control

var player: Player
var marker: MeshInstance3D

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	marker = MeshInstance3D.new()
	marker.name = "WalkObjectiveMarker"
	var ring := TorusMesh.new()
	ring.inner_radius = 0.10
	ring.outer_radius = 0.14
	ring.rings = 16
	ring.ring_segments = 8
	marker.mesh = ring
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = Color(0.85, 0.9, 0.75)
	marker.material_override = material
	player.add_child(marker)
	marker.top_level = true
	marker.visible = false

func _process(_delta: float) -> void:
	var objective := player.motion.objectives.current
	marker.visible = objective != null and objective.kind == ClickObjective.Kind.FLOOR
	if marker.visible:
		marker.global_position = objective.point + Vector3.UP * 0.025
	queue_redraw()

func _draw() -> void:
	if not player.scripted and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		draw_circle(get_viewport_rect().size * 0.5, 2.0, Color(0.9, 0.9, 0.85, 0.85))
