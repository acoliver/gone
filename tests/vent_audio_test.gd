extends SimTestCase

const HISS: AudioStreamWAV = preload("res://assets/audio/ventilation/ceiling-clear.wav")
const HASH := "3f4bbe5959e2efde9a86eae1407cf0a1db6bdfb9183b9ad7aba41e09c85d6efa"

func test_original_vent_hiss_is_pinned_and_ends_with_the_clear() -> void:
	assert_true(FileAccess.get_sha256("res://assets/audio/ventilation/ceiling-clear.wav") == HASH, "original PCM bytes are pinned")
	assert_int_equal(HISS.mix_rate, 48000, "48 kHz")
	assert_false(HISS.stereo, "mono positional sound")
	assert_int_equal(HISS.loop_mode, AudioStreamWAV.LOOP_DISABLED, "vent hiss never loops")
	assert_float_equal(HISS.get_length(), BayVentilation.CLEAR_TICKS * Sim.LOGICAL_TICK_SECS, "sound lasts exactly the clear interval")
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/audio/ventilation/manifest.json"))
	assert_true(manifest.sha256 == HASH, "recipe manifest pins the same bytes")
	assert_int_equal(manifest.peak_dbfs, -24, "soft hiss peak")
