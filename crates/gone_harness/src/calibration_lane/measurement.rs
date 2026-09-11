//! Capture measurement: decode each beat PNG and reduce it to the
//! `(tick, frame, mean luminance)` sample the assertions read.

use std::path::Path;

use serde::Serialize;

use crate::report::Report;

/// One measured capture: the report's pinned (tick, frame) plus the mean
/// luminance over the PNG's pixels.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Sample {
    /// Beat (and capture file) name the sample came from.
    pub name: String,
    /// Logical tick the capture shows (the report's pinned value).
    pub tick: u64,
    /// Rendered frame the capture shows (the report's pinned value).
    pub frame: u64,
    /// Mean Rec. 709 luma over the sRGB-decoded-to-linear pixels.
    pub mean_linear: f64,
    /// Mean of the red channel in linear light.
    pub mean_linear_r: f64,
    /// Mean of the green channel in linear light.
    pub mean_linear_g: f64,
    /// Mean of the blue channel in linear light.
    pub mean_linear_b: f64,
    /// Mean of the raw encoded red channel (u8/255).
    pub mean_raw_r: f64,
    /// Mean of the raw encoded green channel (u8/255).
    pub mean_raw_g: f64,
    /// Mean of the raw encoded blue channel (u8/255).
    pub mean_raw_b: f64,
}

/// sRGB encoded u8 to linear light, per IEC 61966-2-1. Applied through a
/// 256-entry LUT so a two-megapixel capture costs one table build plus
/// integer histogramming.
fn srgb_to_linear_lut() -> [f64; 256] {
    let mut lut = [0.0; 256];
    for (linear, value) in lut.iter_mut().zip(0u16..=255) {
        let v = f64::from(value) / 255.0;
        *linear = if v <= 0.040_45 {
            v / 12.92
        } else {
            ((v + 0.055) / 1.055).powf(2.4)
        };
    }
    lut
}

/// Per-channel occurrence histograms over a decoded capture's pixels.
fn channel_histograms(rgb: &image::RgbImage) -> ([u32; 256], [u32; 256], [u32; 256]) {
    let mut red = [0u32; 256];
    let mut green = [0u32; 256];
    let mut blue = [0u32; 256];
    for px in rgb.pixels() {
        red[usize::from(px.0[0])] += 1;
        green[usize::from(px.0[1])] += 1;
        blue[usize::from(px.0[2])] += 1;
    }
    (red, green, blue)
}

/// One channel's (linear mean, raw encoded mean) from its histogram.
fn channel_means(counts: &[u32; 256], lut: &[f64; 256], pixels: f64) -> (f64, f64) {
    let mut linear_sum = 0.0;
    let mut encoded_sum = 0.0;
    for value in 0u16..=255 {
        let count = f64::from(counts[usize::from(value)]);
        linear_sum += lut[usize::from(value)] * count;
        encoded_sum += f64::from(value) * count;
    }
    (linear_sum / pixels, encoded_sum / (pixels * 255.0))
}

/// Measure one decoded capture PNG into a [`Sample`] (tick and frame are
/// filled by the caller from the report's pinned manifest entry).
///
/// # Errors
/// A named error when the capture is not 1920x1080 (the offscreen target's
/// fixed extent; any other extent would make means incomparable).
fn measure_image(img: &image::DynamicImage, name: &str) -> Result<Sample, String> {
    use image::GenericImageView as _;
    let (width, height) = img.dimensions();
    if (width, height) != crate::onscreen::ONSCREEN_SIZE {
        return Err(format!(
            "calibration capture `{name}` is {width}x{height}, expected {}x{}",
            crate::onscreen::ONSCREEN_SIZE.0,
            crate::onscreen::ONSCREEN_SIZE.1
        ));
    }
    let (red, green, blue) = channel_histograms(&img.to_rgb8());
    let lut = srgb_to_linear_lut();
    let pixels = f64::from(width) * f64::from(height);
    let (linear_r, raw_r) = channel_means(&red, &lut, pixels);
    let (linear_g, raw_g) = channel_means(&green, &lut, pixels);
    let (linear_b, raw_b) = channel_means(&blue, &lut, pixels);
    Ok(Sample {
        name: name.to_owned(),
        tick: 0,
        frame: 0,
        mean_linear: 0.2126 * linear_r + 0.7152 * linear_g + 0.0722 * linear_b,
        mean_linear_r: linear_r,
        mean_linear_g: linear_g,
        mean_linear_b: linear_b,
        mean_raw_r: raw_r,
        mean_raw_g: raw_g,
        mean_raw_b: raw_b,
    })
}

/// Measure every beat capture into a tick-ordered sample sequence.
///
/// # Errors
/// A named error when a capture file is missing, is not a PNG, or has the
/// wrong extent.
pub(super) fn measure_samples(report: &Report, run_dir: &Path) -> Result<Vec<Sample>, String> {
    let mut samples: Vec<Sample> = Vec::with_capacity(report.beats.len());
    for (name, entry) in &report.beats {
        let path = run_dir.join(&entry.file);
        let bytes = std::fs::read(&path)
            .map_err(|e| format!("failed to read capture `{name}` {}: {e}", path.display()))?;
        let img = image::load_from_memory(&bytes)
            .map_err(|e| format!("capture `{name}` PNG invalid: {e}"))?;
        let mut sample = measure_image(&img, name)?;
        sample.tick = entry.tick;
        sample.frame = entry.frame;
        samples.push(sample);
    }
    samples.sort_by_key(|sample| sample.tick);
    Ok(samples)
}

#[cfg(test)]
mod tests {
    use super::{measure_image, srgb_to_linear_lut};

    #[test]
    fn srgb_lut_matches_the_standard_at_known_values() {
        let lut = srgb_to_linear_lut();
        assert!(lut[0].abs() < 1e-12);
        assert!((lut[255] - 1.0).abs() < 1e-9);
        // Encoded 188 decodes to ~0.5 linear (the sRGB midpoint).
        assert!((lut[188] - 0.5).abs() < 0.005, "lut[188] = {}", lut[188]);
        // Below the linear segment the decode is the /12.92 line.
        assert!((lut[8] - f64::from(8u8) / 255.0 / 12.92).abs() < 1e-12);
    }

    #[test]
    fn solid_frame_measures_its_exact_color() {
        let img = image::DynamicImage::ImageRgb8(image::RgbImage::from_pixel(
            crate::onscreen::ONSCREEN_SIZE.0,
            crate::onscreen::ONSCREEN_SIZE.1,
            image::Rgb([119, 119, 119]),
        ));
        let sample = measure_image(&img, "solid").expect("extent matches");
        let linear = srgb_to_linear_lut()[119];
        assert!((sample.mean_linear - linear).abs() < 1e-9);
        assert!((sample.mean_raw_r - f64::from(119u8) / 255.0).abs() < 1e-9);
    }

    #[test]
    fn wrong_extent_is_a_named_error() {
        let img = image::DynamicImage::ImageRgb8(image::RgbImage::from_pixel(
            100,
            100,
            image::Rgb([0, 0, 0]),
        ));
        let err = measure_image(&img, "small").expect_err("wrong extent must fail");
        assert!(err.contains("capture `small` is 100x100"), "{err}");
    }
}
