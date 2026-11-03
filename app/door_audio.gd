class_name DoorAudio
extends Node3D
## Independent event cursor and bounded positional voices; no simulation writes.

const VOICE_COUNT: int = 6
const GRINDS: Array[AudioStreamWAV] = [
	preload("res://assets/audio/hatch/grind-01.wav"),
	preload("res://assets/audio/hatch/grind-02.wav"),
	preload("res://assets/audio/hatch/grind-03.wav"),
	preload("res://assets/audio/hatch/grind-04.wav"),
]
const STALLS: Array[AudioStreamWAV] = [
	preload("res://assets/audio/hatch/stall-01.wav"),
	preload("res://assets/audio/hatch/stall-02.wav"),
	preload("res://assets/audio/hatch/stall-03.wav"),
]
const THUDS: Array[AudioStreamWAV] = [
	preload("res://assets/audio/hatch/thud-01.wav"),
	preload("res://assets/audio/hatch/thud-02.wav"),
]
const WHEEL_REFUSED: AudioStreamWAV = preload("res://assets/audio/hatch/wheel-refused-01.wav")
const RELEASE: AudioStreamWAV = preload("res://assets/audio/hatch/release-01.wav")

class Cue:
	extends RefCounted
	var family: StringName
	var stream: AudioStreamWAV
	var position: Vector3
	var pitch: float = 1.0

class Voice:
	extends RefCounted
	var player: AudioStreamPlayer3D
	var active: bool = false
	var release: bool = false
	var sequence: int = 0

var voices: Array[Voice] = []
var last_voice: int = -1
var play_count: int = 0
var _layout: ShipLayout
var _sequence: int = 0

static func build(layout: ShipLayout) -> DoorAudio:
	var audio := DoorAudio.new()
	audio.name = "DoorAudio"
	audio._layout = layout
	for index: int in range(VOICE_COUNT):
		var voice := Voice.new()
		voice.player = AudioStreamPlayer3D.new()
		voice.player.name = "DoorVoice%d" % index
		voice.player.bus = &"Master"
		voice.player.unit_size = 2.0
		voice.player.max_distance = 24.0
		voice.player.volume_db = -5.0
		voice.player.finished.connect(func() -> void:
			voice.active = false
			voice.release = false)
		audio.add_child(voice.player)
		audio.voices.append(voice)
	return audio

func describe(event: Doors.Event) -> Cue:
	if event.kind() == Doors.EventKind.OPENED:
		return null
	var cue := Cue.new()
	var spec := _layout.door(event.door_id())
	match event.kind():
		Doors.EventKind.CRANK_MOVED:
			cue.family = &"grind"
			cue.stream = GRINDS[event.audio_variant() % GRINDS.size()]
			cue.pitch = lerpf(1.4, 0.8, clampf(event.angle_delta() / 90.0, 0.0, 1.0))
		Doors.EventKind.CRANK_STALLED:
			cue.family = &"stall"
			cue.stream = STALLS[event.audio_variant() % STALLS.size()]
		Doors.EventKind.REFUSED:
			cue.family = &"wheel-refused" if spec.has_wheel() else &"thud"
			cue.stream = WHEEL_REFUSED if spec.has_wheel() else THUDS[event.audio_variant() % THUDS.size()]
		Doors.EventKind.RELEASED:
			cue.family = &"release"
			cue.stream = RELEASE
		_:
			assert(false, "door event has an audio mapping")
	var face := spec.frame() * _layout.face(event.face_id()).surface_frame()
	cue.position = face * Vector3(0, spec.aperture().y / 2, 0)
	return cue

func consume(events: Array[Doors.Event]) -> void:
	for event: Doors.Event in events:
		if event.sequence() <= _sequence:
			continue
		_sequence = event.sequence()
		var cue := describe(event)
		if cue == null:
			continue
		var index := _available_voice()
		if index < 0:
			# Six doors can open in this layout. Incidental effects yield if
			# every slot is still playing one of those protected releases.
			assert(cue.family != &"release", "pool covers every openable door")
			continue
		var voice := voices[index]
		voice.player.stop()
		voice.player.stream = cue.stream
		voice.player.global_position = cue.position
		voice.player.pitch_scale = cue.pitch
		voice.sequence = event.sequence()
		voice.release = cue.family == &"release"
		voice.active = true
		voice.player.play()
		last_voice = index
		play_count += 1

func _available_voice() -> int:
	var oldest: int = -1
	for index: int in range(voices.size()):
		var voice := voices[index]
		if not voice.active:
			return index
		if not voice.release and (oldest < 0 or voice.sequence < voices[oldest].sequence):
			oldest = index
	return oldest
