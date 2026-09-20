class_name Game
extends RefCounted
## Root-script-owned container over the sim state instances, mirroring
## the Rust StasisScenePlugin contract: the frozen pod registry, the wake
## phase machine, the power grid, the wake timeline state, the authored
## player exit path, and the static collider set are inserted at their
## spawn state and ticked at the fixed 60 Hz physics rate. The sim is
## authoritative: this container reads it and never writes phases ahead
## of the controllers that own them (the wake driver is a later chunk).

var registry: Pods.PodRegistry
var colliders: ColliderSet
var phase: Phase.Machine
var power: Power.Grid
var wake_state: Wake.WakeState
var exit_path: Exit.ExitPath
## The doorway into the hallway opens on act with the rod carried and
## the hallway's fixtures light on the switch beside the doorway; both
## are authored with the hallway (issue #59's prerequisite milestone)
## and owned here, on the container.
var door_open: bool = false
var hallway_lit: bool = false

func _init() -> void:
	registry = Pods.PodRegistry.frozen()
	colliders = Hallway.scene_collider_set(registry, false)
	phase = Phase.Machine.new()
	power = Power.Grid.new()
	wake_state = Wake.WakeState.new(Wake.WakeTimeline.authored())
	exit_path = PlacementTruth.player_exit_path()

## Open the stasis doorway into the hallway: idempotent (called by the
## body motion the tick the door's opening animation completes), and
## the only writer of the doorway's collider state — the rebuilt set
## drops the closed doorway block and the slid-aside door slab so the
## walk sim can cross.
func open_doorway() -> void:
	if door_open:
		return
	door_open = true
	colliders = Hallway.scene_collider_set(registry, true)

## Light the hallway's emergency circuit: the switch flip's single
## authority. Render-side consumers (the hallway's fixture bridge) read
## this and never write it.
func light_hallway() -> void:
	hallway_lit = true

## The emergency circuit's target fixture level: 1.0 while the grid
## carries the emergency cells, 0.0 once they are dead. Render-side
## consumers read this; they never write the grid.
func emergency_circuit_target() -> float:
	return 1.0 if Power.emergency_fixtures_lit(power.state()) else 0.0

## One fixed logical tick, called from _physics_process at the project's
## 60 Hz physics rate. The wake machine consumes nothing before its
## readiness barrier opens, so the opening-beat state holds exactly as
## authored while proving the fixed-rate wiring.
func tick() -> void:
	wake_state.tick()
