class_name DressingMounts
extends RefCounted

static func ceiling_stem(parent: Node3D, ceiling_y: float, surface: Surfaces.SurfaceFrame) -> void:
	assert(ceiling_y > parent.position.y, "fixture mounting point is below its ceiling")
	vertical_stem(parent, ceiling_y, surface)

static func vertical_stem(parent: Node3D, support_y: float, surface: Surfaces.SurfaceFrame) -> void:
	var height := support_y - parent.position.y
	var stem := MeshInstance3D.new()
	stem.name = "CeilingMount"
	stem.mesh = HatchModel.box_mesh(Vector3(0.045, absf(height), 0.045))
	stem.position.y = height / 2
	Surfaces.bind(stem, &"hardware", surface)
	stem.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(stem)
