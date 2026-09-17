class_name Pods
extends RefCounted
## Stasis pod registry, ported from gone_sim pods.rs.
## The single source of truth for the stasis bay layout: seven pods in two
## rows flanking the central aisle, the player's pod in one row, the jammed
## hatch centered on the +X short wall. Units: meters, up is positive Y,
## the floor plane is X/Z with the room's long axis on X, the room centered
## on the origin. Pure data: no Node, scene, or rendering types.

## How many stasis pods the bay holds. Fixed: the story's seven-pod room.
const POD_COUNT: int = 7

## Room length along X (the long axis), in meters.
const ROOM_LENGTH: float = 12.0

## Room width along Z, in meters.
const ROOM_WIDTH: float = 8.0

## Floor-to-ceiling height, in meters.
const ROOM_CEILING_HEIGHT: float = 3.2

## Pod length along the pod's local Z (out from its wall), in meters.
const POD_LENGTH: float = 2.2

## Pod width along the pod's local X (along its wall), in meters.
const POD_WIDTH: float = 0.9

## Pod height from floor to the top of the body, in meters.
const POD_HEIGHT: float = 0.8

## Half-width of the central aisle: the frozen 3 m walk corridor between
## the two pod rows.
const AISLE_HALF_WIDTH: float = 1.5

## Distance from a long wall to the center line of its pod row.
const ROW_CENTER_FROM_WALL: float = POD_LENGTH / 2.0

## Floor-plan Z of the -Z wall row's pod centers (openings face +Z).
const ROW_A_Z: float = -(ROOM_WIDTH / 2.0 - ROW_CENTER_FROM_WALL)

## Floor-plan Z of the +Z wall row's pod centers (openings face -Z).
const ROW_B_Z: float = ROOM_WIDTH / 2.0 - ROW_CENTER_FROM_WALL

## Yaw that points a pod opening toward +Z (the -Z wall row).
const ROW_A_YAW: float = 0.0

## Yaw that points a pod opening toward -Z (the +Z wall row).
const ROW_B_YAW: float = PI

enum PodState { PLAYER, EMPTY_OPEN, SEALED }

static func is_player(state: int) -> bool:
	return state == PodState.PLAYER

## A pod stands open (open lid and a visible cavity) unless sealed.
static func is_open(state: int) -> bool:
	return state != PodState.SEALED

## Pod centers along X for a row, spaced to leave walking gaps between
## pods. Shared by both rows.
static func row_x_centers() -> Array[float]:
	return [-4.8, -3.4, -2.0, -0.6]

class PodId:
	extends RefCounted

	var _index: int = 0

	func _init(index: int) -> void:
		_index = index

	static func try_new(index: int) -> Pods.PodId:
		if index >= 0 and index < Pods.POD_COUNT:
			return Pods.PodId.new(index)
		return null

	static func all() -> Array[Pods.PodId]:
		var ids: Array[Pods.PodId] = []
		for index: int in range(Pods.POD_COUNT):
			ids.append(Pods.PodId.new(index))
		return ids

	func index() -> int:
		return _index

	func equals(other: Pods.PodId) -> bool:
		return other != null and _index == other._index

class PodPlacement:
	extends RefCounted

	## Floor-plan center of the pod body, in meters: (x, z).
	var center: Vector2 = Vector2.ZERO
	## Yaw about +Y in radians rotating local +Z onto the opening's world
	## direction.
	var yaw_radians: float = 0.0

	func _init(p_center: Vector2, p_yaw_radians: float) -> void:
		center = p_center
		yaw_radians = p_yaw_radians

	func equals(other: Pods.PodPlacement) -> bool:
		return other != null and center == other.center and yaw_radians == other.yaw_radians

class Pod:
	extends RefCounted

	var _id: Pods.PodId
	var _state: int
	var _placement: Pods.PodPlacement

	func _init(id: Pods.PodId, state: int, placement: Pods.PodPlacement) -> void:
		_id = id
		_state = state
		_placement = placement

	func id() -> Pods.PodId:
		return _id

	func state() -> int:
		return _state

	func placement() -> Pods.PodPlacement:
		return _placement

	## The player's pod is occupied from Waking through ExitingPod and
	## vacates exactly at Standing. Every other pod is always empty.
	func occupied(phase: int) -> bool:
		match _state:
			Pods.PodState.PLAYER:
				return phase != Phase.Wake.STANDING
			_:
				return false

	func equals(other: Pods.Pod) -> bool:
		return other != null and _id.equals(other._id) and _state == other._state and _placement.equals(other._placement)

class HatchPlacement:
	extends RefCounted

	## Floor-plan center of the hatch opening, in meters: (x, z).
	var center: Vector2 = Vector2.ZERO
	## Yaw about +Y in radians rotating the hatch's local +Z (its inward
	## face) onto the face's world direction.
	var yaw_radians: float = 0.0

	func _init(p_center: Vector2, p_yaw_radians: float) -> void:
		center = p_center
		yaw_radians = p_yaw_radians

	func equals(other: Pods.HatchPlacement) -> bool:
		return other != null and center == other.center and yaw_radians == other.yaw_radians

class PodRegistryError:
	extends RefCounted

	enum Kind { DUPLICATE_POD_ID, PLAYER_POD_COUNT }

	var kind: int = Kind.DUPLICATE_POD_ID
	var id: Pods.PodId = null
	var found: int = 0

	static func duplicate_pod_id(duplicate: Pods.PodId) -> Pods.PodRegistryError:
		var error: Pods.PodRegistryError = Pods.PodRegistryError.new()
		error.kind = Kind.DUPLICATE_POD_ID
		error.id = duplicate
		return error

	static func player_pod_count(count: int) -> Pods.PodRegistryError:
		var error: Pods.PodRegistryError = Pods.PodRegistryError.new()
		error.kind = Kind.PLAYER_POD_COUNT
		error.found = count
		return error

	func equals(other: Pods.PodRegistryError) -> bool:
		if other == null or kind != other.kind:
			return false
		match kind:
			Kind.DUPLICATE_POD_ID:
				return id != null and id.equals(other.id)
			_:
				return found == other.found

	func _to_string() -> String:
		match kind:
			Kind.DUPLICATE_POD_ID:
				return "duplicate stasis pod id %d: each bay id must appear exactly once" % id.index()
			_:
				return "a stasis registry needs exactly one player pod, found %d" % found

class Result:
	extends RefCounted

	var registry: Pods.PodRegistry = null
	var error: Pods.PodRegistryError = null

	static func with_registry(valid: Pods.PodRegistry) -> Pods.Result:
		var result: Pods.Result = Pods.Result.new()
		result.registry = valid
		return result

	static func with_error(failure: Pods.PodRegistryError) -> Pods.Result:
		var result: Pods.Result = Pods.Result.new()
		result.error = failure
		return result

	func is_ok() -> bool:
		return error == null

class PodRegistry:
	extends RefCounted
	## The stasis bay's pod set: the truth the scene and the scene tests
	## read. Construction is validated: ids are distinct and exactly one
	## pod is the player's. No registry can hold duplicate pod ids.

	var _pods: Array[Pods.Pod] = []
	var _player_index: int = 0

	static func frozen() -> Pods.PodRegistry:
		return Pods._build(Pods._frozen_pods())

	static func try_new(pods: Array[Pods.Pod]) -> Pods.Result:
		assert(pods.size() == Pods.POD_COUNT, "a registry holds exactly POD_COUNT pods")
		var sorted: Array[Pods.Pod] = pods.duplicate()
		sorted.sort_custom(func(a: Pods.Pod, b: Pods.Pod) -> bool: return a.id().index() < b.id().index())
		for window_index: int in range(sorted.size() - 1):
			if sorted[window_index].id().equals(sorted[window_index + 1].id()):
				return Pods.Result.with_error(Pods.PodRegistryError.duplicate_pod_id(sorted[window_index + 1].id()))
		var player_index: int = -1
		var player_count: int = 0
		for index: int in range(sorted.size()):
			if Pods.is_player(sorted[index].state()):
				player_count += 1
				if player_index == -1:
					player_index = index
		if player_count == 0:
			return Pods.Result.with_error(Pods.PodRegistryError.player_pod_count(0))
		if player_count > 1:
			return Pods.Result.with_error(Pods.PodRegistryError.player_pod_count(player_count))
		return Pods.Result.with_registry(Pods._build_with_player(sorted, player_index))

	func pods() -> Array[Pods.Pod]:
		return _pods

	func pod(id: Pods.PodId) -> Pods.Pod:
		return _pods[id.index()]

	func player_pod() -> Pods.Pod:
		return _pods[_player_index]

	func hatch() -> Pods.HatchPlacement:
		return Pods._hatch_placement()

	func occupancy_count(phase: int) -> int:
		var count: int = 0
		for pod: Pods.Pod in _pods:
			if pod.occupied(phase):
				count += 1
		return count

	func zero_non_player_occupancy(phase: int) -> bool:
		for pod: Pods.Pod in _pods:
			if not Pods.is_player(pod.state()) and pod.occupied(phase):
				return false
		return true

	func equals(other: Pods.PodRegistry) -> bool:
		if other == null or _pods.size() != other._pods.size() or _player_index != other._player_index:
			return false
		for index: int in range(_pods.size()):
			if not _pods[index].equals(other._pods[index]):
				return false
		return true

static func _pod(id_index: int, state: int, center: Vector2, yaw: float) -> Pods.Pod:
	return Pods.Pod.new(Pods.PodId.new(id_index), state, Pods.PodPlacement.new(center, yaw))

## The frozen opening-beat pods: four in the -Z wall row (ids 0 to 3),
## three in the +Z wall row (ids 4 to 6), the player's pod id 6 at the end
## farthest from the hatch.
static func _frozen_pods() -> Array[Pods.Pod]:
	var row_x: Array[float] = Pods.row_x_centers()
	var pods: Array[Pods.Pod] = []
	pods.append(Pods._pod(0, PodState.SEALED, Vector2(row_x[0], ROW_A_Z), ROW_A_YAW))
	pods.append(Pods._pod(1, PodState.EMPTY_OPEN, Vector2(row_x[1], ROW_A_Z), ROW_A_YAW))
	pods.append(Pods._pod(2, PodState.SEALED, Vector2(row_x[2], ROW_A_Z), ROW_A_YAW))
	pods.append(Pods._pod(3, PodState.EMPTY_OPEN, Vector2(row_x[3], ROW_A_Z), ROW_A_YAW))
	pods.append(Pods._pod(4, PodState.SEALED, Vector2(row_x[2], ROW_B_Z), ROW_B_YAW))
	pods.append(Pods._pod(5, PodState.EMPTY_OPEN, Vector2(row_x[1], ROW_B_Z), ROW_B_YAW))
	pods.append(Pods._pod(6, PodState.PLAYER, Vector2(row_x[0], ROW_B_Z), ROW_B_YAW))
	return pods

## The jammed hatch's frozen placement: centered on the +X short wall,
## facing into the room (toward -X).
static func _hatch_placement() -> Pods.HatchPlacement:
	return Pods.HatchPlacement.new(Vector2(Pods.ROOM_LENGTH / 2.0, 0.0), -PI / 2.0)

static func _build(pods: Array[Pods.Pod]) -> Pods.PodRegistry:
	var player_index: int = -1
	for index: int in range(pods.size()):
		if Pods.is_player(pods[index].state()):
			player_index = index
			break
	assert(player_index != -1, "frozen pod set carries exactly one player pod")
	return Pods._build_with_player(pods, player_index)

static func _build_with_player(pods: Array[Pods.Pod], player_index: int) -> Pods.PodRegistry:
	var registry: Pods.PodRegistry = Pods.PodRegistry.new()
	registry._pods = pods
	registry._player_index = player_index
	return registry
