# Smoke symptoms

Smoke exposure produces reversible breath, cough and peripheral-vision symptoms. It does not cause unconsciousness, death, loss of movement or loss of aim. The player can leave the bay to recover.

## Simulation and presentation

`sim/smoke_symptoms.gd` owns dose and deterministic event ids. `app/game_step.gd` advances ventilation before sampling the accepted player eye in the bay frame. Inside the bay bounds, spatial exposure is full up to local X=5.5, then tapers to zero at X=6. It is multiplied by the density from `sim/bay_ventilation.gd`, which clears smoke under secondary power. Full exposure raises dose over 18 seconds; no exposure recovers it over eight seconds. Dose stays within 0..1 and starts only when looking is allowed.

`app/main.gd` plays one non-positional cue at a time. Simulation reserves each WAV's duration and a silent interval; runtime also waits for playback completion and at least 0.2 seconds before another queued cue. Queued events clear when dose reaches zero. Cough takes priority over breath. Higher dose shortens cadence without changing control.

The vision shader protects the center at aspect-corrected radius <=0.52. Peripheral symptoms combine gradual desaturation, ghost offset, blur, bounded attenuation and a neutral veil. Sustained attenuation is capped at 12%; the veil adds at most 0.035 per channel before pulse effects. It vanishes in the protected center and at zero dose. Recovery reduces the persistent veil even over a black scene.

## Audio assets

The WAVs and `.import` sidecars are under `assets/audio/smoke/`:

| File | Source and use |
| --- | --- |
| `wake-breath-mild-reference.wav` | [LindaBarrans #800927](https://freesound.org/people/LindaBarrans/sounds/800927/), source cut 42.30498866..43.05498866 seconds; mild breath |
| `linda-pulse-b-provisional.wav` | Same CC0 preview, source cut 47.45..48.40 seconds; higher-intensity listening trial |
| `cough-mid-isolated.wav` | [neilraouf #835646](https://freesound.org/people/neilraouf/sounds/835646/), source cut 11.22..12.23 seconds; active burst about 0.57..0.94 seconds into the stem |

Godot imports uncompressed PCM16 without normalization, trim or loop. Runtime gain caps are +5 dB for the breath pulse and +1 dB for cough. The [opening-audio guide](audio-opening.md) describes the separate wake composite.

## Run and verify

```sh
godot --headless --editor --path . --import
godot --path .
godot --headless --path . -s tests/run_tests.gd
```

Stay in the bay after waking, then leave through the hatch to inspect recovery. `tests/smoke_symptoms_test.gd` covers dose and scheduling; `tests/smoke_vision_test.gd` covers the presentation equations and center protection. Check timing with the actual audio player as well as simulation tests when changing cadence.

## Known limitations

The sound and visual treatment remain provisional. Listening has not established that the higher-intensity clip conveys labored breathing or contains no speech. Human playtesting must assess visibility and comfort, particularly the veil in the unlit hall. Direct low-frame-rate mixed-audio silence has not been measured. The tracked tree has the WAV outputs but no self-contained rebuild script or original preview cache; recreating stems requires the sources and intervals above.
