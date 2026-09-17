# Emergency lighting render slice (#10)

The stasis room now uses red emergency fixtures instead of the greybox's white pod and room-fill lights. All seven pod indicator plates are unpowered. This implements the render bridge portion of [issue #10](https://github.com/acoliver/gone/issues/10), not its light-capacity or visual acceptance work.

## Power authority and timing

`gone_sim::PowerGrid` owns power. The app stores it in a Bevy resource and reads `emergency_fixtures_lit()` to select the emergency circuit's target level. A shared `gone_sim::FixtureFade` interpolates the point-light intensities and the lenses' emissive material. Repeated output with the same target leaves the fade running rather than retargeting it.

The transition settles in 30 logical ticks at the sim's 60 Hz rate. Normal play consumes Bevy virtual time. The bridge runs after scripted input, so the gameplay harness supplies its fixed virtual step on driven updates and zero on loading or capture holds. It does not drain `ScenarioTime` or interfere with player motion. Headless integration tests run the actual gameplay drive at 30, 60 and 120 scenario ticks per second, including delayed readback.

Milestone 1 has no gameplay power-cut trigger and no repair or white-lighting state. Test helpers exercise the sim's Emergency-to-Dead transition. The render bridge never writes the grid.

## Authored fixture inventory

These are scene-authoring values, not measured backend limits.

| Property | Current scene |
| --- | --- |
| Emergency point lights | 8 total: 7 wall-mounted, 1 over the jammed hatch |
| Placement | Wall fixtures use each registry pod's X and wall side; hatch fixture uses the existing lintel placement |
| Wall mounting height | 2.65 m |
| Over-hatch mounting height | 2.70 m |
| Per-light intensity on emergency power | 45 lumens |
| Per-light range | 6 m |
| Per-light source radius | 0.08 m |
| Light color | Linear RGB `(1, 0, 0)` |
| Shadow maps and contact shadows | Explicitly disabled for all 8 lights |
| Lens geometry | 8 instances of one shared 0.42 × 0.16 × 0.12 m cuboid mesh |
| Lens material | One shared material; emissive linear RGB `(2.6, 0, 0)` at full power |
| Pod indicator plates | 7, sharing one non-emissive material |
| Other sustained dynamic lights | None |
| Ambient contribution | Black, brightness 0, both globally and on gameplay cameras |
| Environment contribution | No environment maps, skyboxes, atmosphere or light probes authored |
| Fog contribution | Black with exponential density 0; directional tint black |
| Spark flashes | None in this slice |

The bridge updates the existing lens material only when its emissive value changes. It allocates no materials per tick. Each lens is a child of its point light: putting the mesh on the light entity makes Bevy's visibility system use the lens AABB instead of the light's range sphere, incorrectly culling off-camera illumination. A regression test pins this separation.

Fixture dressing adds no colliders, and existing room, pod, hatch and route placements are unchanged. Tests compare the hatch transforms and full collider set across the power cut and verify that the hatch remains blocking.

The gameplay cameras receive explicit ambient and disabled-fog settings, plus physical exposure EV100 0 for the dim emergency emitters instead of Bevy's default EV100 9.7. Auto-exposure range, filter, metering mask, the post/wake shader sequence and the chip overlay are unchanged. A capture's chip is protocol instrumentation, not scene illumination.

The physical exposure revision makes exposure an explicit scene-authoring choice after removing the white fill and ambient sources. It does not increase fixture lumens, add another source or change a harness acceptance threshold. Its recorded effect is narrower than a visual-quality claim: in the prior exposure capture, the standing frame's mean RGB outside the protocol chip changed from `(0, 0, 0)` to approximately `(100.214, 7.218, 7.233)`. These are final-output channel statistics, not measurements of the auto-exposure histogram. They neither establish that the default exposure fell below the meter's range nor justify EV100 0 as the final artistic choice.

The culling correction is independent of that exposure choice. Its structural regression test failed before the lens was moved to a child and passed afterward. The recorded before/after culling statistics did not change, including the black standing frame. That fix is therefore not established as the cause of the earlier black capture. Neither correction makes an arbitrary nonblack-pixel fraction a lighting requirement.

## Evidence and remaining work

Verification logs and opening-capture records for this slice live under `tmp/issue10-emergency-render/`. This directory is ignored by Git. Capture results must be read with their run manifests; the opening command exercises the actual gameplay scene without a window, display assertion or synthesized input.

This slice does not establish that the room reads correctly to a viewer. Pixel channel statistics can detect all-black images or gross channel dominance, but cannot assess fixture placement, scene readability, exposure quality or the intended mood. No visual acceptance is claimed from those statistics.

Before #10 can close, the remaining work includes backend and adapter capability records, the selected clustering path and device limits, allocation/overflow diagnostics, an explicit simultaneous spark-flash reserve, and a 4K capacity stress run with #9's actual fog and flashes. Red-only inter-spark and spark-active captures still need visual validation. Capacity and the separate performance lane must pass independently; this fixture inventory certifies neither capacity nor 4K60.
