extends RefCounted
## Cuts the passed source in its own metric frame. No axial scaling or UV remap.

const Source = preload("res://app/seat_rail_component.gd")
static var _sources: Dictionary = {}
static var _cache: Dictionary = {}

static func clipped(part: StringName, low: float, high: float) -> ArrayMesh:
	assert(Source.PARTS.has(part), "known source part")
	assert(is_finite(low) and is_finite(high) and low >= -0.600001 and high <= 0.600001 and high > low, "valid source-local cut interval")
	# Grid arithmetic may differ below float precision; share manufactured lengths.
	low = snappedf(low,0.0000001)
	high = snappedf(high,0.0000001)
	assert(high > low, "cut interval resolves at manufactured precision")
	var key := "%s:%.7f:%.7f" % [part,low,high]
	if not _cache.has(key):
		if not _sources.has(part):
			var source := Source.build(part)
			var triangles: Array = []
			_collect(source,Transform3D.IDENTITY,triangles)
			source.free()
			assert(not triangles.is_empty(), "source contains triangles")
			_sources[part] = triangles
		var triangles: Array = _clip(_sources[part],low,true)
		triangles = _clip(triangles,high,false)
		assert(not triangles.is_empty(), "cut retains source metal")
		var surface := SurfaceTool.new()
		surface.begin(Mesh.PRIMITIVE_TRIANGLES)
		surface.set_material(Source.material())
		for triangle: Array in triangles:
			for vertex: Dictionary in triangle:
				surface.set_normal(vertex.n)
				surface.set_uv(vertex.uv)
				surface.add_vertex(vertex.p)
		surface.generate_tangents()
		surface.index()
		_cache[key] = surface.commit()
	return _cache[key]

static func span(length: float) -> ArrayMesh:
	assert(is_finite(length) and length > 0 and length <= 1.2, "manufactured module span is in (0,1.2] metres")
	return clipped(&"full",-length/2,length/2)

static func cache_size() -> int:
	return _cache.size()

static func _collect(node: Node, parent: Transform3D, triangles: Array) -> void:
	var pose := parent
	if node is Node3D: pose *= (node as Node3D).transform
	if node is MeshInstance3D:
		var mesh := (node as MeshInstance3D).mesh
		for surface in range(mesh.get_surface_count()):
			var arrays := mesh.surface_get_arrays(surface)
			var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			assert(points.size() == normals.size() and points.size() == uvs.size(), "source normals and UVs survive import")
			var count := points.size() if indices.is_empty() else indices.size()
			for offset in range(0,count,3):
				var triangle: Array = []
				for corner in range(3):
					var index := offset+corner if indices.is_empty() else indices[offset+corner]
					triangle.append({"p":pose*points[index],"n":(pose.basis.inverse().transposed()*normals[index]).normalized(),"uv":uvs[index]})
				triangles.append(triangle)
	for child: Node in node.get_children(): _collect(child,pose,triangles)

static func _clip(triangles: Array, plane: float, keep_above: bool) -> Array:
	# Vector storage is float32; use that same plane for boundary classification.
	plane = Vector3(plane,0,0).x
	var result: Array = []
	var segments: Array = []
	for triangle: Array in triangles:
		var polygon: Array = []
		var outside := false
		for i in range(3):
			var a: Dictionary = triangle[i]
			var b: Dictionary = triangle[(i+1)%3]
			var da: float = (a.p.x-plane)*(1 if keep_above else -1)
			var db: float = (b.p.x-plane)*(1 if keep_above else -1)
			if da >= 0: polygon.append(a)
			else: outside = true
			if (da < 0 and db > 0) or (da > 0 and db < 0):
				polygon.append(_intersection(a,b,plane))
		if polygon.size() < 3: continue
		if outside:
			for i in range(polygon.size()):
				var a: Dictionary = polygon[i]
				var b: Dictionary = polygon[(i+1)%polygon.size()]
				if absf(a.p.x-plane)<0.000000001 and absf(b.p.x-plane)<0.000000001 and a.p.distance_to(b.p)>0.000000001:
					segments.append([a,b])
		for i in range(1,polygon.size()-1): result.append([polygon[0],polygon[i],polygon[i+1]])
	if not segments.is_empty(): _caps(segments,Vector3.LEFT if keep_above else Vector3.RIGHT,result)
	return result

static func _intersection(a: Dictionary, b: Dictionary, plane: float) -> Dictionary:
	# Both incident triangles must compute an identical float32 cut vertex.
	if a.p.x > b.p.x:
		var swap := a
		a = b
		b = swap
	var t: float = (plane-a.p.x)/(b.p.x-a.p.x)
	var point: Vector3 = a.p.lerp(b.p,t)
	point.x = plane
	return {"p":point,"n":a.n.lerp(b.n,t).normalized(),"uv":a.uv.lerp(b.uv,t)}

static func _key(point: Vector3) -> Vector3i:
	return Vector3i(roundi(point.x*100000000),roundi(point.y*100000000),roundi(point.z*100000000))

static func _caps(segments: Array, normal: Vector3, triangles: Array) -> void:
	var vertices := {}
	var links := {}
	for segment: Array in segments:
		var a := _key(segment[0].p)

		var b := _key(segment[1].p)
		vertices[a] = segment[0]
		vertices[b] = segment[1]
		if not links.has(a): links[a] = []
		if not links.has(b): links[b] = []
		if not links[a].has(b): links[a].append(b)
		if not links[b].has(a): links[b].append(a)
	for key: Vector3i in links: assert(links[key].size()==2,"source cut is a closed physical sheet boundary")
	while not links.is_empty():
		var start: Vector3i = links.keys()[0]
		var current := start
		var previous := Vector3i(2147483647,0,0)
		var loop: Array = []
		while true:
			loop.append(vertices[current])
			var neighbors: Array = links[current]
			var next: Vector3i = neighbors[0] if neighbors[0] != previous else neighbors[1]
			links.erase(current)
			previous = current
			current = next
			if current == start: break
			assert(links.has(current),"nonbranching source cut contour")
		var contour := PackedVector2Array()
		for vertex: Dictionary in loop: contour.append(Vector2(vertex.p.y,vertex.p.z)*1000.0)
		# Millimetres keep the small bend radii above the triangulator tolerance.
		var indices := Geometry2D.triangulate_polygon(contour)
		assert(indices.size()>0,"concave metal cap triangulates without filling the channel void")
		for i in range(0,indices.size(),3):
			var triangle: Array = []
			for j in range(3):
				var source: Dictionary = loop[indices[i+j]]
				triangle.append({"p":source.p,"uv":source.uv,"n":normal})
			if normal.x > 0: triangle.reverse()
			triangles.append(triangle)
