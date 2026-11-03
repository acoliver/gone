extends SceneTree
## Derived documentation data for the currently built S03 subset only.
const OUTPUT := "res://docs/art/ship/3d/built-layout.json"

func _initialize() -> void:
	var layout := ShipLayout.authored().layout
	var frame := layout.bay_to_world()
	var entries := {}
	entries.bay = {"xyz": _point(frame.origin), "bounds": _bounds(frame * layout.bay().local_bounds().position, frame * layout.bay().local_bounds().end), "clear_height": Pods.ROOM_CEILING_HEIGHT}
	var hall := layout.section(&"D14-S-041").bounds()
	entries.hall = {"xyz": _point(hall.get_center() * Vector3(1, 0, 1)), "bounds": _bounds(hall.position, hall.end), "endcap_x": hall.end.x}
	var power := layout.power_room().bounds()
	entries.power_room = {"xyz": _point(power.get_center() * Vector3(1, 0, 1)), "bounds": _bounds(power.position, power.end)}
	for pair: Array in [["rod", &"D14-BAY-ROD"], ["switch", &"D14-HALL-SWITCH"], ["console", &"D14-POWER-CONSOLE"]]:
		entries[pair[0]] = {"xyz": _point(layout.anchor(pair[1]).origin)}
	for pair: Array in [["hatch", ShipLayout.BAY_DOOR_ID], ["power_door", ShipLayout.POWER_DOOR_ID]]:
		entries[pair[0]] = {"xyz": _point(layout.door(pair[1]).frame().origin)}
	entries.backup = {"xyz": _point(layout.power_room().generator_anchor().origin)}
	for pod: Pods.Pod in layout.bay().template().pods():
		var local := pod.placement().center
		entries["pod_%d" % pod.id().index()] = {"xyz": _point(frame * Vector3(local.x, 0, local.y))}
	var file := FileAccess.open(OUTPUT, FileAccess.WRITE)
	assert(file != null, "export is writable")
	file.store_string(JSON.stringify({"slice": "S03", "source": "sim/ship_layout.gd", "facilities": entries}, "\t") + "\n")
	var atlas_path := "res://docs/art/ship/3d/ship_atlas.json"
	var atlas: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(atlas_path))
	for facility: Dictionary in atlas.facilities:
		if entries.has(facility.id):
			facility.merge(entries[facility.id], true)
			facility.source = "sim/ship_layout.gd via tools/export_ship_layout.gd"
	FileAccess.open(atlas_path, FileAccess.WRITE).store_string(JSON.stringify(atlas, "  ", false) + "\n")
	print("EXPORTED ", OUTPUT)
	quit()

func _point(point: Vector3) -> Array:
	return [snappedf(point.x, 0.00001), snappedf(point.y, 0.00001), snappedf(point.z, 0.00001)]

func _bounds(a: Vector3, b: Vector3) -> Dictionary:
	return {"x": [snappedf(minf(a.x, b.x), 0.00001), snappedf(maxf(a.x, b.x), 0.00001)], "z": [snappedf(minf(a.z, b.z), 0.00001), snappedf(maxf(a.z, b.z), 0.00001)]}
