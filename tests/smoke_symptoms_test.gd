extends SimTestCase

const MILD: AudioStreamWAV = preload("res://assets/audio/smoke/wake-breath-mild-reference.wav")
const PULSE: AudioStreamWAV = preload("res://assets/audio/smoke/linda-pulse-b-provisional.wav")
const COUGH_AUDIO: AudioStreamWAV = preload("res://assets/audio/smoke/cough-mid-isolated.wav")

func test_phase_gate_and_smoke_exposure_recovery() -> void:
	var state := SmokeSymptoms.new()
	var bay := Vector3(0.0, 1.6, 0.0)
	for _i in range(600):
		state.tick(false, bay)
	assert_float_equal(state.dose(), 0.0, "wake cannot accumulate exposure")
	assert_int_equal(state.drain_events().size(), 0, "wake cannot queue events")
	for _i in range(18 * 60):
		state.tick(true, bay)
	assert_true(state.dose() > 0.99, "stationary bay exposure reaches cap")
	assert_true(state.dose() <= 1.0, "dose remains capped")
	for _i in range(8 * 60):
		state.tick(true, Vector3(7.0, 1.6, 0.0))
	assert_float_equal(state.dose(), 0.0, "clean hallway gradually recovers dose")

func test_spatial_exposure_bounds_and_taper() -> void:
	assert_float_equal(SmokeSymptoms.exposure_at(Vector3(5.5, 1.0, 0.0)), 1.0, "bay edge is full exposure")
	assert_float_equal(SmokeSymptoms.exposure_at(Vector3(5.75, 1.0, 0.0)), 0.5, "threshold tapers")
	assert_float_equal(SmokeSymptoms.exposure_at(Vector3(6.0, 1.0, 0.0)), 0.0, "hall is clean air")
	assert_float_equal(SmokeSymptoms.exposure_at(Vector3(2.0, 3.21, 0.0)), 0.0, "above bay has no exposure")
	assert_float_equal(SmokeSymptoms.exposure_at(Vector3(2.0, 1.0, 4.01)), 0.0, "outside width has no exposure")

func test_audio_events_begin_after_unlock_and_are_ordered() -> void:
	var first := SmokeSymptoms.new()
	var second := SmokeSymptoms.new()
	var position := Vector3(0.0, 1.6, 0.0)
	var a: Array[SmokeSymptoms.Event] = []
	var b: Array[SmokeSymptoms.Event] = []
	for tick: int in range(1500):
		first.tick(true, position)
		second.tick(true, position)
		a.append_array(first.drain_events())
		b.append_array(second.drain_events())
	assert_true(a.size() > 4, "continued cough and breaths are scheduled: %d" % a.size())
	if a.is_empty():
		return
	assert_true(a[0].onset_tick >= 21, "first breath starts after the unlock delay")
	assert_int_equal(a.size(), b.size(), "deterministic runs emit equal event counts")
	for i: int in range(a.size()):
		assert_int_equal(a[i].id, b[i].id, "event IDs repeat deterministically")
		assert_int_equal(a[i].onset_tick, b[i].onset_tick, "event ticks repeat deterministically")
		if i > 0:
			assert_true(a[i].id > a[i - 1].id, "event IDs increase")

func test_full_exposure_and_recovery_event_timeline() -> void:
	var state := SmokeSymptoms.new()
	var events: Array[SmokeSymptoms.Event] = []
	var durations := {
		SmokeSymptoms.COUGH: ceili(COUGH_AUDIO.get_length() * 60.0),
		SmokeSymptoms.BREATH_MILD: ceili(MILD.get_length() * 60.0),
		SmokeSymptoms.BREATH_PULSE: ceili(PULSE.get_length() * 60.0),
	}
	var high_dose_kinds: Dictionary = {}
	var gate_ticks := 120
	for _i in range(gate_ticks):
		state.tick(false, Vector3(0.0, 1.6, 0.0))
		assert_int_equal(state.drain_events().size(), 0, "no stems before unlock")
	var first_cough_tick := -1
	var first_active_tick := -1
	var zero_tick := -1
	var min_gap := 100000
	for elapsed: int in range(1, 50 * 60 + 1):
		var in_bay := elapsed <= 40 * 60
		state.tick(true, Vector3(0.0 if in_bay else 7.0, 1.6, 0.0))
		var emitted := state.drain_events()
		var sample := state.sample()
		assert_true(emitted.size() <= 1, "only one stem may start per tick")
		assert_float_in_range(sample.dose, 0.0, 1.0, "dose stays within cap")
		if elapsed == 40 * 60:
			assert_float_equal(sample.dose, 1.0, "sustained bay exposure reaches cap")
		if elapsed > 40 * 60 and sample.dose == 0.0:
			if zero_tick == -1:
				zero_tick = elapsed
			assert_int_equal(emitted.size(), 0, "no events after complete recovery")
		if sample.cough_pulse > 0.0 and first_active_tick == -1:
			first_active_tick = elapsed
		for event: SmokeSymptoms.Event in emitted:
			assert_int_equal(event.onset_tick, sample.tick, "events start immediately on their emitted tick")
			assert_true(event.onset_tick > gate_ticks, "every stem starts after unlock")
			if event.kind == SmokeSymptoms.COUGH and first_cough_tick == -1:
				first_cough_tick = elapsed
			if event.kind != SmokeSymptoms.COUGH:
				assert_true(event.onset_tick >= gate_ticks + 21, "breaths respect the post-unlock delay")
			if sample.dose >= 0.7:
				high_dose_kinds[event.kind] = true
			if not events.is_empty():
				var previous: SmokeSymptoms.Event = events.back()
				assert_true(event.id > previous.id, "event IDs strictly increase")
				assert_true(event.onset_tick > previous.onset_tick, "onsets strictly increase without simultaneous stems")
				var gap: int = event.onset_tick - previous.onset_tick - durations[previous.kind]
				min_gap = mini(min_gap, gap)
				assert_true(gap >= 12, "full WAV plus 12 ticks of silence: %s -> %s gap=%d" % [previous.kind, event.kind, gap])
			events.append(event)
	assert_true(not events.is_empty(), "exposure produces stems")
	for kind: String in durations:
		assert_true(high_dose_kinds.has(kind), "%s is present at high dose" % kind)
	assert_true(first_active_tick >= 114 and first_active_tick <= 126, "first active cough is approximately two seconds after unlock")
	assert_int_equal(first_active_tick - first_cough_tick, roundi(SmokeSymptoms.COUGH_ACTIVE_OFFSET * 60.0), "cough visual cue follows actual onset")
	assert_true(zero_tick > 40 * 60 and zero_tick <= 48 * 60 + 1, "hallway recovers within eight seconds plus rounding tick")
	assert_float_equal(state.dose(), 0.0, "ten clean seconds fully recover")
	print("SMOKE TIMELINE events=%d min_gap_ticks=%d first_cough_tick=%d first_active_tick=%d recovery_tick=%d" % [events.size(), min_gap, first_cough_tick, first_active_tick, zero_tick])

func test_due_cough_waits_for_occupancy_and_keeps_priority() -> void:
	var state := SmokeSymptoms.new()
	var bay := Vector3(0.0, 1.6, 0.0)
	for _i in range(21):
		state.tick(true, bay)
	var initial := state.drain_events()
	assert_int_equal(initial.size(), 1, "initial breath occupies the stem")
	if initial.size() != 1:
		return
	var available_tick := initial[0].onset_tick + ceili(MILD.get_length() * 60.0) + 12
	state._next_cough = 1
	state._until_event = 1
	while state.sample().tick < available_tick - 1:
		state.tick(true, bay)
		assert_int_equal(state.drain_events().size(), 0, "occupied stem queues neither cough nor breath")
		assert_int_equal(state._next_cough, 0, "blocked cough remains due")
	state.tick(true, bay)
	var emitted := state.drain_events()
	assert_int_equal(emitted.size(), 1, "available stem emits one cue")
	if emitted.size() == 1:
		assert_true(emitted[0].kind == SmokeSymptoms.COUGH, "due cough takes priority over due breath")
		assert_int_equal(emitted[0].onset_tick, available_tick, "cough starts on the available tick")

func test_occupied_breath_resets_cadence_without_catch_up() -> void:
	var state := SmokeSymptoms.new()
	var bay := Vector3(0.0, 1.6, 0.0)
	for _i in range(21):
		state.tick(true, bay)
	var initial := state.drain_events()
	assert_int_equal(initial.size(), 1, "initial breath occupies the stem")
	if initial.size() != 1:
		return
	var available_tick := initial[0].onset_tick + ceili(MILD.get_length() * 60.0) + 12
	state._next_cough = 1000
	state._until_event = 1
	state.tick(true, bay)
	assert_int_equal(state.drain_events().size(), 0, "occupied breath is skipped")
	assert_true(state._until_event > 0, "skipped breath resets cadence")
	while state.sample().tick < available_tick:
		state.tick(true, bay)
		assert_int_equal(state.drain_events().size(), 0, "missed breath does not catch up when occupancy clears")

func test_smoke_wavs_import_as_uncompressed_pcm16() -> void:
	for stream: AudioStreamWAV in [MILD, PULSE, COUGH_AUDIO]:
		assert_true(stream != null, "smoke stem imports")
		assert_int_equal(stream.mix_rate, 48000, "smoke stem remains 48 kHz")
		assert_true(not stream.stereo, "smoke stem remains mono")
		assert_int_equal(stream.format, AudioStreamWAV.FORMAT_16_BITS, "smoke stem imports to PCM16")
		assert_true(not stream.data.is_empty(), "smoke stem has imported PCM data")
	assert_float_equal(PULSE.get_length(), 0.95, "pulse stem retains its exact duration")
	assert_float_equal(MILD.get_length(), 0.75, "mild stem retains its exact duration")
	assert_float_equal(COUGH_AUDIO.get_length(), 1.01, "cough stem retains its exact duration")
