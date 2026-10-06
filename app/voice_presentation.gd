class_name VoicePresentation
extends Node

signal line_started(number: int)
signal line_finished(number: int)

const WAKE_LINE: AudioStreamWAV = preload("res://assets/audio/voice/hesitant-tail-c-line-1.wav")
const HALLWAY_LINE: AudioStreamWAV = preload("res://assets/audio/voice/hesitant-tail-c-line-2.wav")
const SWITCH_LINE: AudioStreamWAV = preload("res://assets/audio/voice/hesitant-tail-c-line-3.wav")
const HALLWAY_ENTRY_X: float = 6.0
const SWITCH_DELAY_USEC: int = 1000000

var game: Game
var player: Player
var audio: AudioStreamPlayer
var clock_usec: Callable = Callable()
var _wake_seen := false
var _previous_x: float = 0.0
var _has_previous_position := false
var _hallway_seen := false
var _switch_seen := false
var _switch_at_usec: int = 0
var _line_playing := 0
var _line2_finished := false
var _line2_pending := false
var _line2_seen := false
var _line3_seen := false

static func build(p_game: Game, p_player: Player) -> VoicePresentation:
	var presentation := VoicePresentation.new()
	presentation.name = "VoicePresentation"
	presentation.game = p_game
	presentation.player = p_player
	return presentation

func _ready() -> void:
	audio = AudioStreamPlayer.new()
	audio.name = "SpanishPlaceholderVoice"
	add_child(audio)
	audio.finished.connect(_on_audio_finished)

func _process(_delta: float) -> void:
	poll_events()

func poll_events() -> void:
	if not _wake_seen and game.phase.look_allowed() and game.wake_state.current_tick() >= 282:
		_wake_seen = true
		_play(1, WAKE_LINE)
	var capsule: Resolve.Capsule = player.motion.capsule()
	if capsule != null:
		var x: float = capsule.foot.x
		if _has_previous_position and not _hallway_seen and game.door_open and game.phase.locomotion_allowed() and _previous_x < HALLWAY_ENTRY_X and x >= HALLWAY_ENTRY_X:
			_hallway_seen = true
			_line2_pending = true
		_previous_x = x
		_has_previous_position = true
	if _line2_pending and not _line2_seen and _line_playing == 0 and not audio.playing:
		_line2_pending = false
		_line2_seen = true
		_play(2, HALLWAY_LINE)
	if not _switch_seen and game.hallway_lit:
		_switch_seen = true
		_switch_at_usec = _now_usec()
	if _switch_seen and _hallway_seen and _line2_finished and not _line3_seen and _line_playing == 0 and _now_usec() - _switch_at_usec >= SWITCH_DELAY_USEC:
		_line3_seen = true
		_play(3, SWITCH_LINE)

func _now_usec() -> int:
	if clock_usec.is_valid():
		return int(clock_usec.call())
	return Time.get_ticks_usec()

func _play(number: int, stream: AudioStreamWAV) -> void:
	assert(_line_playing == 0 and not audio.playing, "voice lines never interrupt")
	_line_playing = number
	audio.stream = stream
	line_started.emit(number)
	audio.play()

func _on_audio_finished() -> void:
	var finished_line := _line_playing
	if _line_playing == 2:
		_line2_finished = true
	_line_playing = 0
	if finished_line != 0:
		line_finished.emit(finished_line)
