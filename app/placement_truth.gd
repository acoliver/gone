class_name PlacementTruth
extends RefCounted
## Placement-derived gameplay truth shared by the game's own build and
## machine checks, ported from gone_app placement_truth.rs. The gameplay
## lane's runner verifies a run against numbers derived from the frozen
## placement data (the exit waypoint, the hatch placement), never from
## literals, so the game and its verifier cannot drift. Pure data.

## Standing eye height above the capsule foot's ground contact, in
## meters: the controller spec's standing height puts the eye point near
## 1.6 m, and this is that number for the rig.
const STANDING_EYE_HEIGHT: float = 1.6

## The authored get-up path out of the player pod, built exactly as the
## scene wiring builds it: the frozen player pod's placement against the
## tray floor the cavity build actually constructs.
static func player_exit_path() -> Exit.ExitPath:
	var result := Exit.ExitPath.try_new(
		Pods.PodRegistry.frozen().player_pod().placement(),
		PodBody.TRAY_FLOOR_Y
	)
	assert(result.is_ok(), "the frozen player pod authors a valid exit path")
	return result.path
