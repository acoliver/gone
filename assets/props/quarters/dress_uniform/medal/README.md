# Medal PBR masters and mounted cloth contact

The driver accepted the stage-one geometry and stage-two studio materials for #130 integration. These maps now bind the mounted medal in both production tunics. The [stage-three report](../../../../../tools/blender/quarters/dress_uniform/medal-stage3.md) records mounting, runtime tests, measured game controls and the remaining probe/visibility limits. Game image review belongs to the driver. The raw cage misses and scratch-control limitations in the [stage-two report](../../../../../tools/blender/quarters/dress_uniform/medal-stage2.md) remain documented.

Medal atlas maps are 2048 by 2048 and use the accepted low mesh's `MedalUV` atlas, exported as primary `DetailUV`. Remembered uses `as_built_*`; Present uses `aged_*`. Present represents 1000 years of dry, sealed, sterile storage. The two new contact PNGs are 512 by 512 linear RGBA8: R incremental cloth AO, G encoded front-cloth depth, B coverage. `contact-frames.json` records their 48 by 56 mm projection frames. Contact is independently enabled only on TunicBody.

| Files | Role | Encoding |
| --- | --- | --- |
| `as_built_albedo.png`, `aged_albedo.png` | Reflected brass color and deep-blue enamel, without painted lighting | sRGB, RGB8 |
| `as_built_normal.png`, `aged_normal.png` | Selected-to-active high-to-low geometry normal plus fine finish | OpenGL tangent +Y, linear RGB8 |
| `as_built_orm.png`, `aged_orm.png` | R occlusion, G final perceptual roughness, B metallic | Linear RGB8 |
| `geometry_normal.png` | Geometry-only normal master | OpenGL tangent +Y, linear RGBA16 |
| `ao_near.png`, `ao_local.png` | Assembled high-poly AO at 0.3 and 2 mm | Linear RGBA16 |
| `curvature_convex.png`, `curvature_concave.png` | Signed high-poly curvature, filtered at 0.10 and 0.40 mm | Linear RGBA16 |

The standalone stage-two low mesh's positions, topology, corner normals and UVs are unchanged. Mounting applies a common rigid placement and, on Remembered only, a hidden-reverse fit; accepted front/suspension positions and atlas samples are preserved. Feature-isolated projection uses explicit 0.15 mm patch-normal cages with 0.30 mm reach. AO retains the assembled high geometry. Final coverage has no holes after within-feature completion of subtexel seam samples. That completion must not be described as zero missed rays.

The concept supplies restrained chromatic variation after removing luminance. Remembered brass now targets linear conductor F0 `(0.90, 0.64, 0.24)`; the previous fixed-rig darkening factors are removed. Present uses a brown-gold thin film over conducting exposed brass, with darker, rougher oxide in recesses. Curvature and AO place oxide without painting lighting into albedo. Circumferential rim brushing, facet-following star finish and sparse scratches affect normal/roughness. Brass has no coat. Enamel remains dielectric, with specular 0.5, coat weight 0.35 and coat roughness 0.18 Remembered / 0.26 Present. Runtime integration applies coat explicitly and uses final ORM values with unit factors. The [stage-three-c report](../../../../../tools/blender/quarters/dress_uniform/medal-stage3c.md) records the physical-finish experiment and its remaining clipping failure under the fixed room rig.

The source tools are `medal_stage2_bake.py`, `medal_stage2_regions.py`, `medal_stage2_texture.py`, `medal_stage2_studio.py`, `medal_stage2_measure.py` and `medal_stage2_verify.py` beside the report. Current candidate blends, settings, raw maps, controls, linear captures and review JPEGs are under `tmp/issue130-photoreal/stage2/`. No Hunyuan Paint experiment was needed. Stage-three runtime binding tests and captures now cover Godot tangents, normal decoding and mipmaps. The additional temporal sweep deliberately uses common uncompressed control textures and does not establish production-compression equivalence.
