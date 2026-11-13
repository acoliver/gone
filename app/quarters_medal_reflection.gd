class_name QuartersMedalReflection
extends RefCounted

static func build(state: Node3D) -> ReflectionProbe:
	var group := state.get_node("Placement_wardrobe") as Node3D
	var wardrobe := group.get_node("wardrobe") as Node3D
	var bounds := AABB()
	for name: String in ["BackPanel", "BottomPanel", "TopPanel", "SidePanel_L", "SidePanel_R"]:
		var panel := wardrobe.find_child(name, true, false) as MeshInstance3D
		var part := ShipScene._world_frame(panel) * panel.get_aabb()
		bounds = part if not bounds.has_volume() else bounds.merge(part)
	var front := (ShipScene._world_frame(wardrobe).basis * Vector3.BACK).normalized()
	var probe := ReflectionProbe.new()
	probe.name = "MedalReflection"
	probe.size = bounds.size
	probe.position = bounds.get_center()
	probe.origin_offset = front * (bounds.size.dot(front.abs()) * .5 - .05)
	probe.max_distance = QuartersLayout.bounds().size.length()
	# Light instances keep layer 1; their receiver mask selects quarters meshes.
	probe.cull_mask = Lighting.QUARTERS_MASK | 1
	probe.reflection_mask = Lighting.QUARTERS_MASK
	probe.interior = true
	probe.box_projection = true
	# Disabled ambient also suppresses native specular on this Metal path.
	# The inherited room environment already has black, disabled ambient light.
	probe.ambient_mode = ReflectionProbe.AMBIENT_ENVIRONMENT
	group.add_child(probe)
	return probe

static func refresh(probe: ReflectionProbe, lighting_changed: bool) -> void:
	probe.update_mode = ReflectionProbe.UPDATE_ALWAYS if lighting_changed else ReflectionProbe.UPDATE_ONCE
