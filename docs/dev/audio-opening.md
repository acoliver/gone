# Opening respiratory audio

The opening uses a provisional first-person breath and cough clip at `assets/audio/wake/opening-respiratory-trial.wav`. It starts after the rendered-frame readiness barrier marks the wake as started. A tick-derived camera tremor accompanies the active cough and returns to zero at its boundary without changing player control.

## Sources and processing

The clip combines two CC0 1.0 Freesound preview derivatives:

- [LindaBarrans #800927](https://freesound.org/people/LindaBarrans/sounds/800927/): breath cut 42.30498866..43.05498866 seconds, placed at 2.55..3.30 seconds with +13 dB static gain.
- [neilraouf #835646](https://freesound.org/people/neilraouf/sounds/835646/): cough cut 11.22..12.23 seconds, placed at 3.43..4.44 seconds with -6 dB static gain. The active burst is at 4.00..4.37 seconds.

The authored output is seven seconds of mono 48 kHz PCM24. The breath was resampled from 44.1 kHz using a 160/147 polyphase resampler. Each stem has 20 ms sine-squared fades. Godot imports the WAV as uncompressed PCM16 with no extra gain or normalization. The `.wav.import` sidecar holds the import settings.

## Run and verify

From the repository root:

```sh
godot --headless --editor --path . --import
godot --path .
godot --headless --path . -s tests/run_tests.gd
```

Listen through the ordinary wake before deciding on the sound. `app/main.gd` wires playback to wake readiness. The wake timeline and symptom tests cover timing; [smoke symptoms](smoke-symptoms.md) describes the separate continuation after the wake.

## Known limitations

No listening approval is recorded. The breath and cough have different performers and potentially different room noise. The tracked tree contains the exported WAV and importer settings, but no self-contained source-preview-to-WAV rebuild script. The intervals and processing above preserve the editing recipe; rebuilding needs the original preview derivatives. PCM24 export does not restore information lost in their MP3 encoding.
