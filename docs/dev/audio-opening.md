# Provisional wake respiratory audio trial

This is an in-game listening trial, not an accepted sound. No perceptual approval has been recorded. The clip combines two CC0 preview derivatives, so it carries performer and background-noise mismatch risk. The breath and cough are different performers and their room/background character may not match.

## Sources and processing

- Breath: LindaBarrans (Linda), Freesound sound #800927, CC0 1.0: https://freesound.org/people/LindaBarrans/sounds/800927/ . The source used here is the official HQ MP3 preview derivative, not the original WAV; derivative SHA-256: `5f6c115dcb10550c0da1846cc7e6cb1d5093e9257137691f0b1a33836bda915c`. Used source interval [42.30498866, 43.05498866) seconds, placed at [2.55, 3.30) seconds, with +13 dB static gain.
- Mid-cough: Freesound sound #835646 by neilraouf, CC0 1.0: https://freesound.org/people/neilraouf/sounds/835646/ . The source used here is the official HQ MP3 preview derivative, not the original WAV; derivative SHA-256: `5f74bd5460ea5a470429545bc69438ec25ef49f94eb214c938a7d44e9154df74`. Used source interval [11.22, 12.23) seconds, placed at [3.43, 4.44) seconds, with -6 dB static gain. The active cough is at 4.00-4.37 seconds.
- The recorded breath was resampled from 44.1 kHz to 48 kHz with a 160/147 polyphase resampler. Each stem has a 20 ms sine-squared fade at both ends. The staged 7-second mono 48 kHz PCM24 WAV uses the source cuts and gains above, and a reported total true peak of -6.14 dBTP. PCM24 describes the authored WAV; Godot's WAV importer is configured for uncompressed import (`compress/mode=0`) and imports it as uncompressed PCM16 at runtime, reducing source sample bit depth from 24 to 16 while avoiding lossy codec compression. There is no extra gain or normalization in Godot.

Asset: `res://assets/audio/wake/opening-respiratory-trial.wav`

SHA-256: `90bd15cd466630aa77ca1e91fa19c8f5301142abba8073c10db166f83d3bc004`

The non-positional first-person AudioStreamPlayer starts only after WakePresent crosses the rendered-frame readiness barrier and marks the wake STARTED. The timeline and phase timing are unchanged. A small tick-derived camera tremor accompanies the active cough for players who cannot hear the cue; it returns to zero at its boundary and does not affect control.

Listen in-game before making any sound-design decision. No auditory or visual quality approval is claimed here.

The post-wake smoke continuation uses three separate CC0 preview derivatives and remains provisional. Exact source intervals, hashes, importer configuration, gain ceilings, classifier ambiguity, dose thresholds, and scheduler behavior are recorded in [smoke-symptoms.md](smoke-symptoms.md). The higher-intensity breath cut is a listening trial only. No speech-free or labored-performance claim is made.
