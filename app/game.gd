class_name Game
extends RefCounted
## Root-script-owned container over the sim state instances, mirroring
## the Rust StasisScenePlugin contract: the frozen pod registry, the wake
## phase machine, the power grid, the wake timeline state, the authored
## player exit path, and the static collider set are inserted at their
## spawn state and ticked at the fixed 60 Hz physics rate. The sim is
## authoritative: this container reads it and never writes phases ahead
## of the controllers that own them. GameStep owns logical advancement.

var run_seed: int
var doors: Doors.Store
var collision: ShipCollision
var layout: ShipLayout
var bay_exited: bool = false
var registry: Pods.PodRegistry
var colliders: ColliderSet
var phase: Phase.Machine
var power: Power.Grid
var ventilation := BayVentilation.new()
var wake_state: Wake.WakeState
var exit_path: Exit.ExitPath
## The doorway into the hallway opens on act with the rod carried and
## the hallway's fixtures light on the switch beside the doorway; both
## are authored with the hallway (issue #59's prerequisite milestone)
## and owned here, on the container. Issue #59 adds the emergency power
## room behind the corridor's last port (-Z) door walking aft (+X): its doorway opens
## on act (no rod gate — it is a crew door, not a pry-bar hatch), and
## its working console walks the secondary power's state machine — one
## press activates the generator, and the
## hallway, power room and bay hand their emergency red over to regular
## white, and secondary-powered ventilation clears the bay.
var door_open: bool:
	get: return doors.snapshot(ShipLayout.BAY_DOOR_ID).state == Doors.State.OPEN
var hallway_lit: bool = false
var power_door_open: bool:
	get: return doors.snapshot(ShipLayout.POWER_DOOR_ID).state == Doors.State.OPEN
var console_state: int = ConsoleState.INACTIVE
var power_active: bool = false
var quarters := QuartersMemory.new()
var writing_memory := DisplayPerception.Memory.new()
var label_attention := LabelAttention.new(writing_memory)

## The working console starts labeled inactive; one press activates power.
enum ConsoleState { INACTIVE, ACTIVE }

func _init(seed: int) -> void:
	run_seed = seed
	layout = ShipLayout.authored().layout
	doors = Doors.Store.new(layout, seed)
	collision = ShipCollision.new(layout, seed)
	registry = layout.bay().template()
	colliders = collision.deck_set(14)
	phase = Phase.Machine.new()
	power = Power.Grid.new()
	wake_state = Wake.WakeState.new(Wake.WakeTimeline.authored())
	exit_path = PlacementTruth.player_exit_path(layout)

func advance_doors() -> void:
	var events := doors.tick()
	collision.commit(events)
	for event: Doors.Event in events:
		if event.kind() == Doors.EventKind.OPENED:
			colliders = collision.deck_set(14)

func observe_bay_crossing(previous: Vector3, current: Vector3, walking: bool, deck: int = 14) -> void:
	quarters.observe_entry(previous, current, deck, walking, doors.snapshot(QuartersLayout.DOOR).state == Doors.State.OPEN)
	if not bay_exited and PortalCrossing.exits(previous, current, layout.door(ShipLayout.BAY_DOOR_ID), 14, walking, door_open):
		bay_exited = true

## Light the hallway circuit once its switch receives an accepted press.
func light_hallway() -> void:
	hallway_lit = true

## Advance the working console's state machine exactly one step:
## inactive → active (the generator
## lights, the corridor and the power room go regular white). Returns
## true when a step landed — the caller consumes a press only then.
func press_console() -> bool:
	match console_state:
		ConsoleState.INACTIVE:
			console_state = ConsoleState.ACTIVE
			power_active = true
			return true
		_:
			return false

## The emergency circuit's target fixture level: 1.0 while the grid
## carries the emergency cells, 0.0 once they are dead. Render-side
## consumers read this; they never write the grid.
func emergency_circuit_target() -> float:
	return 1.0 if Power.emergency_fixtures_lit(power.state()) else 0.0
