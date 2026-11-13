class_name QuartersMemory
extends RefCounted
## Temporary message wording, including the fault address, follows ruling 16.

enum State { UNSEEN, REMEMBERED, PLAYING, PRESENT }
const CORRUPT_TICKS := 60
const MESSAGE_TICKS := 180
const FAULT_TICKS := 60
const TOTAL_TICKS := CORRUPT_TICKS + MESSAGE_TICKS + FAULT_TICKS
const PLACEHOLDER := "PLACEHOLDER TEXT (decisions.md ruling 16)"
const MESSAGE := "Hi honey. If you see this then I'm actually waiting for you in astrometrics because I was coming to surprise you but... you decided to slack off early."
const FAULT := "MAIN SYSTEM FAULT AT ADDRESS 14F4:9000 / SYSTEM UNAVAILABLE"

var state: State = State.UNSEEN
var elapsed := 0

func observe_entry(previous: Vector3, current: Vector3, deck: int, walking: bool, door_open: bool) -> void:
	if state != State.UNSEEN or not walking or not door_open or deck != QuartersLayout.DECK: return
	var before := QuartersLayout.from_world(previous)
	var after := QuartersLayout.from_world(current)
	if before.z > 0 or after.z <= 0: return
	var hit := before.lerp(after, -before.z / (after.z - before.z))
	if hit.x >= 3.4 and hit.x <= 4.6 and hit.y >= 0 and hit.y < 2.4:
		state = State.REMEMBERED

func press_console() -> bool:
	if state != State.REMEMBERED: return false
	state = State.PLAYING
	elapsed = 0
	return true

func tick() -> void:
	if state != State.PLAYING: return
	elapsed += 1
	if elapsed == TOTAL_TICKS: state = State.PRESENT

func remembered() -> bool:
	return state in [State.REMEMBERED, State.PLAYING]

func screen_text() -> String:
	if state == State.PLAYING:
		if elapsed < CORRUPT_TICKS: return PLACEHOLDER + "\n\nVIDEO DATA CORRUPTED"
		if elapsed < CORRUPT_TICKS + MESSAGE_TICKS: return PLACEHOLDER + "\n\n" + MESSAGE
		return PLACEHOLDER + "\n\n" + FAULT
	if state == State.PRESENT: return PLACEHOLDER + "\n\n" + FAULT
	return PLACEHOLDER + "\n\nPERSONAL MESSAGE / PRESS TO PLAY"
