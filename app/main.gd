extends Node3D

const WAKE_AUDIO: AudioStreamWAV = preload("res://assets/audio/wake/opening-respiratory-trial.wav")
const SMOKE_BREATH: AudioStreamWAV = preload("res://assets/audio/smoke/wake-breath-mild-reference.wav")
const SMOKE_PULSE: AudioStreamWAV = preload("res://assets/audio/smoke/linda-pulse-b-provisional.wav")
const SMOKE_COUGH: AudioStreamWAV = preload("res://assets/audio/smoke/cough-mid-isolated.wav")
## The stasis-room root: builds the scene procedurally at runtime (the
## greybox room shell and fixtures around the authored pod-v2 pod
## shells) and owns the Game container, ticking the sim at the fixed
## 60 Hz physics rate. The emergency lighting node reads the sim's
## power grid through its own bridge; ceiling hazards are inert
## dressing.

var game: Game
var camera: Camera3D
var player: Player
var hatch: Hatch
var rod: Rod
var hallway: Hallway
var power_room: PowerRoom
var wake_pass: WakePass
var wake_present: WakePresent
var smoke_symptoms: SmokeSymptoms
var smoke_audio: AudioStreamPlayer
var voice_presentation: VoicePresentation
var _smoke_audio_queue: Array[SmokeSymptoms.Event] = []
var _smoke_audio_in_flight := false
var _smoke_silence_until_usec := 0

func _ready() -> void:
	game = Game.new()
	add_child(RoomGeometry.build(true))
	add_child(StasisPods.build(game.registry))
	hatch = Hatch.build()
	add_child(hatch)
	add_child(Lighting.build(game))
	add_child(Hazards.build())
	add_child(Wires.build())
	rod = Rod.build()
	add_child(rod)
	hallway = Hallway.build(game)
	add_child(hallway)
	power_room = PowerRoom.build(game)
	add_child(power_room)
	_add_player()
	_add_wake_presentation()
	_add_wake_audio()
	_add_smoke_symptoms()
	voice_presentation = VoicePresentation.build(game, player)
	add_child(voice_presentation)

func _physics_process(_delta: float) -> void:
	game.tick()
	var accepted_position := player.motion.eye(game)
	smoke_symptoms.tick(game.phase.look_allowed(), accepted_position)
	if smoke_symptoms.dose() <= 0.0:
		_smoke_audio_queue.clear()
		_smoke_audio_in_flight = false
		return
	_smoke_audio_queue.append_array(smoke_symptoms.drain_events())
	_play_next_smoke_event()

## A first-person, non-positional provisional listening trial. The stream
## is preloaded and its player exists before WakePresent can cross readiness.
func _add_wake_audio() -> void:
	var player_2d := AudioStreamPlayer.new()
	player_2d.name = "WakeRespiratoryTrial"
	player_2d.stream = WAKE_AUDIO
	add_child(player_2d)
	wake_present.wake_started.connect(player_2d.play)

func _add_smoke_symptoms() -> void:
	smoke_symptoms = SmokeSymptoms.new()
	var layer := SmokeVision.build(smoke_symptoms, wake_pass)
	add_child(layer)
	smoke_audio = AudioStreamPlayer.new()
	smoke_audio.name = "SmokeSymptomTrial"
	add_child(smoke_audio)
	smoke_audio.finished.connect(_on_smoke_audio_finished)

func _on_smoke_audio_finished() -> void:
	_smoke_audio_in_flight = false
	_smoke_silence_until_usec = Time.get_ticks_usec() + 200000

func _play_next_smoke_event() -> void:
	if _smoke_audio_in_flight or smoke_audio.playing or _smoke_audio_queue.is_empty() or Time.get_ticks_usec() < _smoke_silence_until_usec:
		return
	_play_smoke_event(_smoke_audio_queue.pop_front())

func _play_smoke_event(event: SmokeSymptoms.Event) -> void:
	match event.kind:
		SmokeSymptoms.COUGH:
			smoke_audio.stream = SMOKE_COUGH
			_smoke_gain(event, 0.0)
		SmokeSymptoms.BREATH_PULSE:
			smoke_audio.stream = SMOKE_PULSE
			_smoke_gain(event, 0.0)
		SmokeSymptoms.BREATH_MILD:
			smoke_audio.stream = SMOKE_BREATH
			_smoke_gain(event, 0.0)
		_:
			assert(false, "smoke event kind is registered")
	_smoke_audio_in_flight = true
	smoke_audio.play()

func _smoke_gain(event: SmokeSymptoms.Event, base_db: float) -> void:
	smoke_audio.volume_db = base_db + event.gain_db

## The eyelid pass over the presented frame and its driver over the sim's
## wake timeline: the lids exist fully closed from the first frame, and
## the timeline starts only once the window has presented one. The player
## rig carries the sway.
func _add_wake_presentation() -> void:
	wake_pass = WakePass.build()
	add_child(wake_pass)
	wake_present = WakePresent.build(game, camera, wake_pass, player)
	add_child(wake_present)

## The first-person player rig: the sim drives the body, the rig
## projects its pose, and the wake presentation sways the same camera.
func _add_player() -> void:
	player = Player.build(game, hatch)
	player.rod = rod
	player.power_room = power_room
	add_child(player)
	camera = player.camera
