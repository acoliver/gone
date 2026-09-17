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

func _init() -> void:
	registry = Pods.PodRegistry.frozen()
	colliders = Placement.scene_collider_set(registry)
	phase = Phase.Machine.new()
	power = Power.Grid.new()
	wake_state = Wake.WakeState.new(Wake.WakeTimeline.authored())
	exit_path = PlacementTruth.player_exit_path()

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
