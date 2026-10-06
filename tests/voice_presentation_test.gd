extends SimTestCase

const TRACKS: Array[String] = [
	"res://assets/audio/voice/hesitant-tail-c-line-1.wav",
	"res://assets/audio/voice/hesitant-tail-c-line-2.wav",
	"res://assets/audio/voice/hesitant-tail-c-line-3.wav",
]

func test_only_three_trackable_paced_voice_sources_are_installed() -> void:
	assert_int_equal(TRACKS.size(), 3, "production voice has exactly three tracks")
	for path: String in TRACKS:
		assert_true(FileAccess.file_exists(path), "voice track exists: " + path)
		var stream := load(path) as AudioStreamWAV
		assert_true(stream != null, "voice track imports as WAV: " + path)
		if stream != null:
			assert_true(stream.get_length() > 0.0, "voice track has audio: " + path)

func test_voice_wav_bytes_match_the_pinned_paced_candidate() -> void:
	var expected_hashes: Array[String] = [
		"cd35c72ac5c2dfb292e149ddbb5f2e70539691a4d62991058329dc2b915aa0b6",
		"b948dc06a58b740b419cfcaf62a5cfa5bc477eb5f8d26d26ddbc0d9babed1c4e",
		"a0b54c5a203b14f7bafe5ad41ca038d1975c1afd3c6b49aaea2a7c2dab77c560",
	]
	assert_int_equal(expected_hashes.size(), TRACKS.size(), "each installed voice track has one pinned hash")
	for index: int in range(TRACKS.size()):
		var bytes := FileAccess.get_file_as_bytes(TRACKS[index])
		assert_true(bytes.size() > 0, "voice track contains WAV bytes: " + TRACKS[index])
		assert_true(FileAccess.get_sha256(TRACKS[index]) == expected_hashes[index], "installed WAV bytes match pinned line %d" % (index + 1))
