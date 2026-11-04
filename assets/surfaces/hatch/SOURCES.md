# Hatch weather mask

`leaf-weather.png` is our procedurally generated round-7 leaf mask, promoted from the accepted hatch prototype. No concept-image pixels or third-party texture data are used in this mask.

Reproduce from the repository root with Python, NumPy, SciPy and Pillow:

```sh
python3 tools/generate_hatch_weather.py
```

The generator uses NumPy seed 73041 and writes a unique 1024 × 2048 RGBA data texture. Channels are surviving paint, grain, hardware runoff and flake-edge rust bleed. Sampling is clamped in the leaf's local frame. Alpha is data, not transparency. The source mask is losslessly imported without alpha-border processing; mipmaps are enabled.

The surrounding steel scans retain their existing provenance in `../steel/SOURCES.md`. The hatch shader adds the round-7 treatment to the existing steel shader family. Wheel weathering follows the wheel's frame independently of the leaf.

Production keeps the generated mask, spatial relief and full rust colour. Wall roles retain their approved round-5 finish. White-light harness checks sample the fixture lenses rather than treating the hatch's rust colour as evidence of emergency illumination.
