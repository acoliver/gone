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

Albedo comes from the selected concept's brass chromaticity after removing luminance. The accepted clean brass color remains the principal reference. Curvature and AO place the brown oxide; they do not supply albedo lighting. Circumferential rim brushing, facet-following star finish and sparse scratches affect normal/roughness. Brass has no coat. Enamel is dielectric, with specular 0.5 and coat weight 0.65. Coat roughness is 0.13 Remembered and 0.23 Present. Runtime integration must apply the coat explicitly and must not multiply final ORM values by the former scalar finishes.

The source tools are `medal_stage2_bake.py`, `medal_stage2_regions.py`, `medal_stage2_texture.py`, `medal_stage2_studio.py`, `medal_stage2_measure.py` and `medal_stage2_verify.py` beside the report. Current candidate blends, settings, raw maps, controls, linear captures and review JPEGs are under `tmp/issue130-photoreal/stage2/`. No Hunyuan Paint experiment was needed. Stage-three runtime binding tests and captures now cover Godot tangents, normal decoding and mipmaps. The additional temporal sweep deliberately uses common uncompressed control textures and does not establish production-compression equivalence.
