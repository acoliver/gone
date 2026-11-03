# Approved Round 5 steel scans

Downloaded from Poly Haven on 2026-11-03. All four photographic sets and
these derivatives are CC0 1.0. License: https://polyhaven.com/license and
https://creativecommons.org/publicdomain/zero/1.0/. Full legal text is in
CC0-1.0.txt. No concept image is sampled.

Round 5 samples eleven images. Its declared peeling_mask sampler is unused;
the original painted albedo is source-only, not a runtime dependency.
Normal maps are OpenGL tangent normals, imported BC5 (XY, reconstructed Z).
ORM is linear R=AO/G=roughness/B=metallic. Round 5 deliberately uses
procedural metallic (.20 down to .025) rather than ORM.B. Colour samplers
are sRGB; normal/ORM samplers are linear. Imports use full mip chains,
repeat/anisotropic filtering, BC7 colour/ORM and BC5 normals. Expected GPU
block payload is 14.67 MiB for eleven 1K textures, below the unchanged
16.1 MiB cap. This excludes driver allocation and scene resources.

## Reproduce derived albedos

`/Volumes/XS1000/tools/mlximg-venv/bin/python tools/prepare_steel_textures.py --check`
compares exact PNG bytes without writing. Drop --check to regenerate.
Versions used: NumPy 2.3.5, Pillow 12.3.0, SciPy 1.18.1.
Inputs are under art-source/steel, excluded with .gdignore. Decode sRGB;
wrapped sigma-24 Gaussian separates luminance/chroma; clamp detail .72..1.35,
raise detail to .55 and median-normalized broad luminance to .10. Target
luminance is .12; chroma is [1.35,.96,.60] plus .22 times high-frequency
source chroma. Clamp linear RGB and encode sRGB, round to 8-bit RGB PNG.
Round 5 retains these Round 4 prepared scan inputs; its shader supplies
the approved dull-steel colour and localized rust treatment.

## Exact sources and SHA-256

### green_metal_rust

Asset: https://polyhaven.com/a/green_metal_rust
License: CC0 1.0

- `art-source/steel/green_metal_rust_albedo.jpg`
  https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/green_metal_rust/green_metal_rust_diff_1k.jpg
  SHA-256 `4509ab0cb1cf6bf9b9f970450a41f83ebd9bff178006deae568ff34b404856fc`
- `assets/surfaces/steel/green_metal_rust_normal.jpg`
  https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/green_metal_rust/green_metal_rust_nor_gl_1k.jpg
  SHA-256 `8ecb28b0ea4026b740ce492e3f606f61a76bdce1f78cb2e29287bf9a56c54a80`
- `assets/surfaces/steel/green_metal_rust_orm.jpg`
  https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/green_metal_rust/green_metal_rust_arm_1k.jpg
  SHA-256 `c1a48da0c5bba8f490497bbedadf4cb21d5387de8b3d49988c065e4b16805434`
- Derived `r4-green_metal_rust-albedo.png` SHA-256 `9b5de492bdfdf3aa76d2d69c41a0e36350b72371ac8ebf125af219ff64533b7a`

### rusty_painted_metal

Asset: https://polyhaven.com/a/rusty_painted_metal
License: CC0 1.0

- `art-source/steel/rusty_painted_metal_albedo.jpg`
  https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rusty_painted_metal/rusty_painted_metal_diff_1k.jpg
  SHA-256 `b086937b45c3628116a838363364a29bd3c5d2542cff906ec1d92d681ee80e15`
- `assets/surfaces/steel/rusty_painted_metal_normal.jpg`
  https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rusty_painted_metal/rusty_painted_metal_nor_gl_1k.jpg
  SHA-256 `f3372e2f60517df2d0e02c1472eb24071d95182d771c30b7ecd8e1b5142768bb`
- `assets/surfaces/steel/rusty_painted_metal_orm.jpg`
  https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rusty_painted_metal/rusty_painted_metal_arm_1k.jpg
  SHA-256 `cd3ef3750348bd8afa552ac41120310f740cd4bfd3c303d81e68e3100bdf7fdd`
- Derived `r4-rusty_painted_metal-albedo.png` SHA-256 `d3838a76509131ca4bc3d152e9f6b09b3facc22c73a1a653cbef84e4f15adcff`

### rusty_metal_04

Asset: https://polyhaven.com/a/rusty_metal_04
License: CC0 1.0

- `art-source/steel/rusty_metal_04_albedo.jpg`
  https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rusty_metal_04/rusty_metal_04_diff_1k.jpg
  SHA-256 `37c6757c5b6b2229f61423c7e5013f970e4dafb48070d35f53ed6d08958ed288`
- `assets/surfaces/steel/rusty_metal_04_normal.jpg`
  https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rusty_metal_04/rusty_metal_04_nor_gl_1k.jpg
  SHA-256 `9c432bee334e65e73ff0b20676dd3f0efbed3f91d261a13dc03b9c8c1a4f4eec`
- `assets/surfaces/steel/rusty_metal_04_orm.jpg`
  https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rusty_metal_04/rusty_metal_04_arm_1k.jpg
  SHA-256 `b040e35ed5e885d04b465761782a5d0ebd241175f562821f8fba35a12dccb789`
- Derived `r4-rusty_metal_04-albedo.png` SHA-256 `e9cda2b8d6d1b5346c8ed1375b914d06fba311d33e2afa6b0191b3c0a974d418`

### rust_coarse_01

Asset: https://polyhaven.com/a/rust_coarse_01
License: CC0 1.0

- `assets/surfaces/steel/r3-rust_coarse_01-albedo.jpg`
  https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rust_coarse_01/rust_coarse_01_diff_1k.jpg
  SHA-256 `369f69eb86a7dcc4e5b6e30b1f3a4da5ce6ba50cf417de937efb4f09101f88d4`
- `assets/surfaces/steel/r3-rust_coarse_01-normal.jpg`
  https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rust_coarse_01/rust_coarse_01_nor_gl_1k.jpg
  SHA-256 `08ae69576b453b0970f5982d359897f09aae41c7cb18c19c02de37324160625c`
