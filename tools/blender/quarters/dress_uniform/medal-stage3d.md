# Medal calibration to photographic references, issue #130

## Measurement decisions

The selected references are the four images named in `medal_photo_measure.REFERENCES`, generated locally in `tmp/issue130-reference/photo-20261111-01/`. They are appearance references, not measured alloy reflectance. `reference-selection.md` contains the separate image review. No image judgment is performed in this pass.

Reference masks combine warm/cool colour clusters with a fitted pendant ellipse. The fit uses the lower pendant's warm-colour boundary, excluding the upper ribbon and bar. Geometry separates the annulus, perimeter, centre star, enamel and surrounding wool. Narrow dark departures from the local annulus select engraved grooves; they do not select the whole shaded hemisphere. Masks and coloured overlays are saved under `tmp/issue130-photoreal/stage3d/baseline-analysis/`. Runtime masks use the existing first-hit geometry, physical hit coordinates and UV-sampled curvature/tarnish maps. Body comparisons exclude the suspension hardware outside the 16.1 mm pendant radius. All regional measurements, including star, edges, recesses and ribbon, remain in the JSON report.

LDR PNGs are decoded to linear Rec.709. Luminance percentiles are divided by median surrounding wool luminance. Brass chroma and hue use D65 Lab after normalizing the sample mean to Y=0.18; raw rendered colour is retained, without white balancing either source. A near-highlight exceeds 2.5 times median broad-face luminance. Clipping means any sRGB channel at least 0.99, and is reported separately from near-highlights.

The 0.5–2 mm mottling measurement filters along the annulus circumference in physical coordinates. This excludes the concentric lathe profile from a measurement of irregular surface finish. A homography fitted to first-hit physical positions supplies the game projection; the reference ellipse supplies the photographic projection. The uncorrected two-dimensional bandpass is also reported. Ribbon fine-texture RMS uses 0.1–0.4 mm Gaussian FWHM scales. Texture differences are normalized by local luminance. This allows the original red ribbon pigment to remain exact even though the reference ribbon has different stripes.

`medal-photo-targets.json` fixes ranges before material tuning: the envelope of the two reference views per state, expanded by 25% of the upper observation for luminance/contrast, 8 Lab chroma units, 8 hue degrees, 3 percentage points for near-highlight area and 0.5 percentage points for clipping. The contrast margin has a 0.01 floor. Clipping has no positive lower bound: a reference glint does not require deliberate clipping in the candidate. These tolerances cover generated-reference and segmentation uncertainty; they do not establish physical optical constants. Every candidate is tested against the same ranges in both views. The existing engineering and code-quality gates are unchanged.

The baseline is `149572f`. Its wool luminance is higher than the photographic wool in both states; matching wool-relative brightness therefore does not imply matching absolute image brightness. This difference is retained in the report rather than altering the room exposure, lighting, environment, probe or camera.

## Status

Reference segmentation and exposure-relative measurement tests pass. Material calibration and final verification are in progress.
