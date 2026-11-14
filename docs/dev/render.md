# Game rendering and screen effects

The game uses Godot's Forward+ renderer, selected in `project.godot`. The root `main.tscn` loads `app/main.gd`, which builds the ship, player camera, wake presentation and smoke-symptom layer. Room and prop geometry is generated or imported through the [asset pipeline](asset-pipeline.md).

## Environment and lighting

`app/lighting.gd` builds the world environment with a black background, disabled ambient lighting, fog off and an authored camera exposure multiplier. Visible illumination comes from room fixtures, local machinery and spark sources. Reflection probes support glossy surfaces without ambient fill. [Fixture mounting](light-fixture-mounting.md) describes the source/housing contract; [emergency lighting](emergency-lighting.md) describes circuit handoff.

The calibration scenes in `app/calibration_mode.gd` have their own metering and exposure loop. Their adaptation checks do not establish automatic exposure behavior in ordinary gameplay.

## Screen-effect order

`app/wake_pass.gd` builds a fullscreen `ColorRect` on CanvasLayer 100. `app/wake_eyelid.gdshader` samples the presented scene for blur, lid occlusion and the wake exposure ramp. It starts fully closed. `app/wake_present.gd` waits for the first rendered frame before starting the simulation-owned wake timeline, then projects its samples onto the shader and camera sway. Completion hides the fullscreen pass.

`app/smoke_vision.gd` uses CanvasLayer 99 and `app/smoke_vision.gdshader`. It is hidden while the wake pass is active, then reads the deterministic symptom sample for peripheral blur, desaturation and haze. [Smoke symptoms](smoke-symptoms.md) defines its protected center, bounds and recovery behavior. Both screen rectangles ignore mouse input.

## Run and verify

From the repository root:

```sh
godot --headless --editor --path . --import
godot --path .
godot --headless --path . -s tests/run_tests.gd
godot --headless --path . -s harness/run.gd -- scenarios/gameplay-full.json
godot --headless --path . -s harness/run.gd -- scenarios/calibration-step.json
```

The harness launches a windowed renderer for captures. `tests/wake_test.gd` and `tests/wake_present_test.gd` cover timing, readiness and presentation mapping. `tests/smoke_vision_test.gd` checks peripheral-effect equations; `tests/lighting_test.gd` and `tests/lighting_policy_test.gd` cover lighting behavior. `tests/calibration_test.gd` covers the separate calibration contract.

## Known limitations

Headless simulation tests cannot establish rendered appearance. Judge exposure, glass, fabric and screen effects with native captures at the actual camera. Point-light shadows are disabled, so receiver layers and room masks affect apparent shading. Symptom comfort and audio/visual quality still need playtesting. Platform-specific GPU behavior and performance require native runs on the target hardware.
