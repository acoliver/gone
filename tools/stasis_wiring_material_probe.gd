class_name StasisWiringMaterialProbe
extends RefCounted
## Numeric imported-PBR and real first-hit diagnostics, independent of image judgment.

static func meshes(node: Node, output: Array[MeshInstance3D]) -> void:
	if node is MeshInstance3D: output.append(node as MeshInstance3D)
	for child: Node in node.get_children(): meshes(child, output)

static func vector(value: Vector3) -> Array:
	return [value.x, value.y, value.z]

static func color(value: Color) -> Array:
	return [value.r, value.g, value.b, value.a]

static func material_map(assembly: Node3D) -> Array[Dictionary]:
	var found: Array[MeshInstance3D] = []
	meshes(assembly, found)
	var output: Array[Dictionary] = []
	for mesh: MeshInstance3D in found:
		var world_bounds: AABB = mesh.global_transform * mesh.get_aabb()
		for surface: int in range(mesh.mesh.get_surface_count()):
			var material := mesh.get_active_material(surface)
			var row := {"node":String(assembly.get_path_to(mesh)), "node_id":mesh.get_instance_id(),
				"surface_id":surface, "material_instance_id":material.get_instance_id(),
				"material_name":material.resource_name, "material_class":material.get_class(),
				"material_override":mesh.material_override != null,
				"surface_override":mesh.get_surface_override_material(surface) != null,
				"world_aabb_min":vector(world_bounds.position),
				"world_aabb_end":vector(world_bounds.end)}
			if material is StandardMaterial3D:
				var pbr := material as StandardMaterial3D
				row["albedo_srgb"] = color(pbr.albedo_color)
				row["albedo_linear"] = color(pbr.albedo_color.srgb_to_linear())
				row["metallic"] = pbr.metallic
				row["roughness"] = pbr.roughness
				row["albedo_texture"] = pbr.albedo_texture.resource_path if pbr.albedo_texture != null else ""
				row["uv1_scale"] = vector(pbr.uv1_scale)
			output.append(row)
	return output

static func add_colliders(assembly: Node3D) -> void:
	var found: Array[MeshInstance3D] = []
	meshes(assembly, found)
	for mesh: MeshInstance3D in found:
		mesh.create_trimesh_collision()

static func texture_hashes(assembly: Node3D) -> Dictionary:
	var found: Array[MeshInstance3D] = []
	meshes(assembly, found)
	var result: Dictionary = {}
	for mesh: MeshInstance3D in found:
		for surface: int in range(mesh.mesh.get_surface_count()):
			var material := mesh.get_active_material(surface)
			var textures: Array[Texture2D] = []
			if material is StandardMaterial3D:
				var pbr := material as StandardMaterial3D
				for texture: Texture2D in [pbr.albedo_texture,pbr.normal_texture,pbr.roughness_texture,pbr.metallic_texture,pbr.ao_texture]:
					if texture!=null: textures.append(texture)
			elif material is ShaderMaterial:
				var shader_material := material as ShaderMaterial
				for uniform: Dictionary in shader_material.shader.get_shader_uniform_list():
					var value: Variant = shader_material.get_shader_parameter(uniform.name)
					if value is Texture2D: textures.append(value)
			for texture: Texture2D in textures:
				var path := texture.resource_path.get_slice("::",0)
				assert(FileAccess.file_exists(path),"Missing actual material texture source: "+texture.resource_path)
				result[path] = FileAccess.get_sha256(path)
	return result


static func first_hit(camera: Camera3D, pixel: Vector2) -> Dictionary:
	var origin := camera.project_ray_origin(pixel)
	var direction := camera.project_ray_normal(pixel)
	var query := PhysicsRayQueryParameters3D.create(origin, origin+direction*20.0)
	query.hit_back_faces = true
	var hit := camera.get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty(): return {}
	var mesh := (hit.collider as Node).get_parent() as MeshInstance3D
	return {"mesh":mesh, "position":hit.position, "normal":hit.normal, "face_index":hit.face_index}

static func anchors(assembly: Node3D, camera: Camera3D, image: Image) -> Array[Dictionary]:
	var enclosure := assembly.get_node("PhysicalSourceEnclosure") as Node3D
	var found: Array[MeshInstance3D] = []
	meshes(enclosure, found)
	var output: Array[Dictionary] = []
	for mesh: MeshInstance3D in found:
		var label := String(mesh.name)
		if not (label.contains("compression") or label.contains("collar") or label.begins_with("Cast")): continue
		var faces := mesh.mesh.get_faces()
		var step := maxi(1, ceili(float(faces.size()/3)/180.0))
		var counts: Dictionary = {}
		var samples := 0
		var visible_samples := 0
		var chosen: Dictionary = {}
		var chosen_score := -1.0
		for triangle: int in range(0, faces.size()/3, step):
			var point := mesh.global_transform * ((faces[triangle*3]+faces[triangle*3+1]+faces[triangle*3+2])/3.0)
			if camera.is_position_behind(point): continue
			var pixel := camera.unproject_position(point).floor()+Vector2(0.5, 0.5)
			if pixel.x<1 or pixel.y<1 or pixel.x>=image.get_width()-1 or pixel.y>=image.get_height()-1: continue
			var hit := first_hit(camera, pixel)
			if hit.is_empty(): continue
			samples += 1
			var hit_mesh: MeshInstance3D = hit.mesh
			var hit_id := String(assembly.get_path_to(hit_mesh))
			counts[hit_id] = int(counts.get(hit_id, 0))+1
			if hit_mesh != mesh: continue
			visible_samples += 1
			# Prefer front-facing triangle interiors over glancing silhouette pixels.
			var score := (camera.global_position-(hit.position as Vector3)).normalized().dot(hit.normal)
			if score<=chosen_score: continue
			chosen_score = score
			var value := image.get_pixel(int(pixel.x), int(pixel.y))
			chosen = {"pixel_xy":[int(pixel.x), int(pixel.y)], "rgb_srgb":color(value),
				"actual_first_hit_node":hit_id, "actual_first_hit_node_id":hit_mesh.get_instance_id(),
				"actual_first_hit_face_index":hit.face_index, "hit_world_m":vector(hit.position),
				"normal_world":vector(hit.normal)}
		output.append({"requested_node":String(assembly.get_path_to(mesh)), "node_id":mesh.get_instance_id(),
			"projected_aabb_center_px":_pixel(camera.unproject_position(mesh.global_transform * mesh.get_aabb().get_center())),
			"tested_pixel_rays":samples, "visible_first_hit_samples":visible_samples,
			"first_hit_histogram":counts, "visible_pixel_anchor":chosen})
	return output

static func _pixel(point: Vector2) -> Array:
	return [point.x, point.y]
