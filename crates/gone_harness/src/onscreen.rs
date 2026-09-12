//! Machine verification of the render canary's single onscreen capture.
//!
//! A `--render-check` run opens the app's canary lane: a real (focused)
//! window presents the scene, and the app saves exactly one onscreen capture
//! via `Screenshot::primary_window()`, at the first beat's request, named
//! `beats/<first-beat>.onscreen.png` in the run directory. After the run this
//! module verifies the artifact with named, fail-fast errors: exactly one
//! onscreen PNG under `beats/`, decoded at exactly 1920x1080, not entirely
//! black, and its frame-code chip lattice decodes to the report's frame for
//! that beat (the window renders the same world as the offscreen target, chip
//! included). The checks are pure functions over file paths and decoded pixel
//! buffers, so they unit-test without a GPU and without writing artifacts.

use std::path::{Path, PathBuf};

use image::GenericImageView as _;

use crate::{Scenario, report};

/// The canary window's exact physical capture size: 1920x1080 at the forced
/// scale factor of 1.0, the same extent as the offscreen capture target.
pub const ONSCREEN_SIZE: (u32, u32) = (1920, 1080);

/// The file infix separating the canary's onscreen capture from the beat PNG.
/// Must match the app's onscreen save name (`onscreen_file_name` in the app's
/// bootstrap state): `beats/<beat>.onscreen.png`.
const ONSCREEN_INFIX: &str = ".onscreen.png";

/// The onscreen capture's file for a beat, relative to the run directory
/// (forward-slash, like every report artifact path).
#[must_use]
pub fn onscreen_rel_path(beat: &str) -> String {
    format!("beats/{beat}{ONSCREEN_INFIX}")
}

/// Verify the canary's onscreen artifact for one finished run: exactly one
/// onscreen PNG under `beats/` (named for the scenario's first beat), decoded
/// at exactly [`ONSCREEN_SIZE`], not entirely black, and its frame-code chip
/// decodes to the report's frame for that beat.
///
/// # Errors
/// A named message for each failing check: the missing or duplicated capture
/// (naming the expected file, or listing the extras), an unreadable or
/// non-PNG file, a wrong extent, an entirely black capture, an undecodable
/// chip lattice, or a chip frame that differs from the report's.
pub fn verify_run(
    scenario: &Scenario,
    report: &report::Report,
    run_dir: &Path,
) -> Result<(), String> {
    let beat = scenario.beats.first().ok_or_else(|| {
        "render-check requires a scenario with at least one beat: the canary \
         captures the onscreen frame at the first beat"
            .to_owned()
    })?;
    let entry = report.beats.get(&beat.name).ok_or_else(|| {
        format!(
            "report has no beat `{}`: the onscreen capture has no report frame to verify against",
            beat.name
        )
    })?;
    let path = find_capture(run_dir, &onscreen_rel_path(&beat.name))?;
    let bytes = std::fs::read(&path)
        .map_err(|e| format!("failed to read onscreen capture {}: {e}", path.display()))?;
    let img = image::load_from_memory(&bytes)
        .map_err(|e| format!("onscreen capture `{}` PNG invalid: {e}", path.display()))?;
    verify_image(&beat.name, entry.frame, &img)
}

/// The checks over one decoded onscreen image: exact extent, not entirely
/// black, and a decodable frame-code chip whose frame equals the report's.
///
/// # Errors
/// A named message per failing check, in the offscreen beat-decode wording
/// style but saying onscreen.
pub fn verify_image(
    beat: &str,
    report_frame: u64,
    img: &image::DynamicImage,
) -> Result<(), String> {
    let (width, height) = img.dimensions();
    if (width, height) != ONSCREEN_SIZE {
        return Err(format!(
            "onscreen capture for beat `{beat}` is {width}x{height}, expected {}x{}",
            ONSCREEN_SIZE.0, ONSCREEN_SIZE.1
        ));
    }
    let rgb = img.to_rgb8();
    if is_all_black(rgb.as_raw()) {
        return Err(format!(
            "onscreen capture is entirely black (beat `{beat}`)"
        ));
    }
    let (tick, frame) =
        crate::frame::decode_chip_from_rgb(rgb.as_raw(), 3, rgb.width(), rgb.height())
            .map_err(|e| format!("beat `{beat}` onscreen frame-code decode: {e}"))?;
    if frame != report_frame {
        return Err(format!(
            "beat `{beat}` onscreen frame-code mismatch: capture shows (tick {tick}, frame {frame}), report says frame {report_frame}"
        ));
    }
    Ok(())
}

/// True when every byte of an RGB pixel buffer is zero, i.e. every pixel is
/// exactly (0, 0, 0).
#[must_use]
fn is_all_black(rgb: &[u8]) -> bool {
    rgb.iter().all(|&byte| byte == 0)
}

/// Resolve the canary's single onscreen capture under `run_dir`: exactly one
/// `*.onscreen.png` under `beats/`, and it must be the expected file (the
/// first beat's name).
///
/// # Errors
/// None found names the expected capture; a same-infix file under a different
/// name is named; more than one lists them all.
fn find_capture(run_dir: &Path, expected_rel: &str) -> Result<PathBuf, String> {
    let expected = run_dir.join(expected_rel);
    let mut found = list_onscreen_captures(run_dir)?;
    found.sort();
    choose_capture(&found, &expected)
}

/// The `*.onscreen.png` files under `run_dir/beats`, sorted. A missing beats
/// directory counts as none, so the missing-capture failure names the expected
/// file instead of surfacing an I/O error.
///
/// # Errors
/// An I/O error other than a missing directory.
fn list_onscreen_captures(run_dir: &Path) -> Result<Vec<PathBuf>, String> {
    let beats = run_dir.join("beats");
    let entries = match std::fs::read_dir(&beats) {
        Ok(entries) => entries,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
        Err(e) => return Err(format!("failed to read {}: {e}", beats.display())),
    };
    Ok(entries
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            path.is_file()
                && path
                    .file_name()
                    .and_then(|name| name.to_str())
                    .is_some_and(|name| name.ends_with(ONSCREEN_INFIX))
        })
        .collect())
}

/// Pick the single expected capture out of the found list.
///
/// # Errors
/// An empty list names the expected capture; a single capture under a
/// different name names both; several list them all.
fn choose_capture(found: &[PathBuf], expected: &Path) -> Result<PathBuf, String> {
    match found {
        [] => Err(format!(
            "missing onscreen capture `{}`: render-check requires exactly one \
             *{ONSCREEN_INFIX} under beats/ (the canary saves it at the first beat)",
            expected.display()
        )),
        [one] if one == expected => Ok(expected.to_path_buf()),
        [one] => Err(format!(
            "found onscreen capture `{}` but the canary saves the first beat's \
             capture as `{}`",
            one.display(),
            expected.display()
        )),
        many => {
            let listed = many
                .iter()
                .map(|path| path.display().to_string())
                .collect::<Vec<_>>()
                .join(", ");
            Err(format!(
                "expected exactly one onscreen capture under beats/, found {}: {listed}",
                many.len()
            ))
        }
    }
}

#[cfg(test)]
mod tests {
    use std::path::{Path, PathBuf};

    use super::{
        ONSCREEN_SIZE, choose_capture, find_capture, is_all_black, onscreen_rel_path, verify_image,
        verify_run,
    };
    use crate::frame::{OFF_COLOR, chip_pixel, chip_size};
    use crate::report::{BeatEntry, Identity, Report};
    use crate::{Beat, PROTOCOL_VERSION, Scenario};

    /// A capture scenario whose first beat is `beat-a` at tick 2.
    fn scenario_with_first_beat() -> Scenario {
        Scenario {
            name: "smoke".to_owned(),
            seed: 1234,
            beats: vec![Beat::new("beat-a", 2)],
            ..Scenario::default()
        }
    }

    /// A report carrying exactly the `beat-a` manifest entry.
    fn report_with_beat(frame: u64) -> Report {
        let mut report = Report::new(
            PROTOCOL_VERSION,
            "smoke",
            1234,
            Identity {
                app_hash: "a".to_owned(),
                scenario_hash: "s".to_owned(),
                config_hash: "c".to_owned(),
            },
        );
        report.beats.insert(
            "beat-a".to_owned(),
            BeatEntry {
                file: "beats/beat-a.png".to_owned(),
                tick: 2,
                frame,
                request_id: 1,
            },
        );
        report
    }

    /// A synthetic onscreen frame: the chip at the top-left over the off
    /// palette, elsewhere pure background.
    fn chip_image(tick: u64, frame: u64, width: u32, height: u32) -> image::DynamicImage {
        let (off_r, off_g, off_b) = OFF_COLOR;
        let mut img = image::RgbImage::from_pixel(width, height, image::Rgb([off_r, off_g, off_b]));
        let (chip_w, chip_h) = chip_size();
        for py in 0..chip_h {
            for px in 0..chip_w {
                let (r, g, b) = chip_pixel(tick, frame, px, py);
                img.put_pixel(px, py, image::Rgb([r, g, b]));
            }
        }
        image::DynamicImage::ImageRgb8(img)
    }

    /// A unique scratch run dir for the filesystem tests (created on demand,
    /// removed after the test; the process id keeps sibling sessions apart).
    fn scratch_dir(test: &str) -> PathBuf {
        std::env::temp_dir().join(format!(
            "gone-harness-onscreen-{test}-{}",
            std::process::id()
        ))
    }

    #[test]
    fn onscreen_name_is_the_first_beat_with_the_onscreen_infix() {
        assert_eq!(onscreen_rel_path("beat-a"), "beats/beat-a.onscreen.png");
    }

    #[test]
    fn happy_path_decodes_the_chip_and_matches_the_report_frame() {
        let img = chip_image(2, 5, ONSCREEN_SIZE.0, ONSCREEN_SIZE.1);
        assert_eq!(verify_image("beat-a", 5, &img), Ok(()));
    }

    #[test]
    fn wrong_size_is_rejected_naming_both_extents() {
        let img = chip_image(2, 5, 100, 100);
        let err = verify_image("beat-a", 5, &img).expect_err("wrong size must fail");
        assert!(err.contains("100x100"), "{err}");
        assert!(err.contains("1920x1080"), "{err}");
    }

    #[test]
    fn entirely_black_capture_is_rejected() {
        let img = image::DynamicImage::ImageRgb8(image::RgbImage::from_pixel(
            ONSCREEN_SIZE.0,
            ONSCREEN_SIZE.1,
            image::Rgb([0, 0, 0]),
        ));
        let err = verify_image("beat-a", 5, &img).expect_err("all black must fail");
        assert!(err.contains("onscreen capture is entirely black"), "{err}");
    }

    #[test]
    fn chip_frame_mismatch_is_rejected_naming_both_frames() {
        let img = chip_image(2, 9, ONSCREEN_SIZE.0, ONSCREEN_SIZE.1);
        let err = verify_image("beat-a", 5, &img).expect_err("frame mismatch must fail");
        assert!(err.contains("onscreen frame-code mismatch"), "{err}");
        assert!(err.contains("frame 9"), "{err}");
        assert!(err.contains("frame 5"), "{err}");
    }

    #[test]
    fn nonblack_image_without_a_chip_lattice_is_a_named_onscreen_decode_failure() {
        // The off palette is nonzero, so the capture is not "entirely black",
        // but an all-off lattice matches no digit: the decode must fail by
        // name rather than the black check swallowing it.
        let (off_r, off_g, off_b) = OFF_COLOR;
        let img = image::DynamicImage::ImageRgb8(image::RgbImage::from_pixel(
            ONSCREEN_SIZE.0,
            ONSCREEN_SIZE.1,
            image::Rgb([off_r, off_g, off_b]),
        ));
        assert!(!is_all_black(img.to_rgb8().as_raw()));
        let err = verify_image("beat-a", 5, &img).expect_err("no lattice must fail");
        assert!(err.contains("onscreen frame-code decode"), "{err}");
    }

    #[test]
    fn all_black_is_a_byte_level_predicate() {
        assert!(is_all_black(&[]));
        assert!(is_all_black(&[0, 0, 0, 0, 0, 0]));
        assert!(!is_all_black(&[0, 0, 1]));
    }

    #[test]
    fn choose_capture_requires_the_expected_single_file() {
        let expected = Path::new("/run/beats/beat-a.onscreen.png");
        let missing = choose_capture(&[], expected).expect_err("none found must fail");
        assert!(
            missing.contains("missing onscreen capture `/run/beats/beat-a.onscreen.png`"),
            "{missing}"
        );
        assert_eq!(
            choose_capture(&[expected.to_path_buf()], expected).expect("the one expected file"),
            expected.to_path_buf()
        );
        let other = Path::new("/run/beats/beat-b.onscreen.png");
        let renamed = choose_capture(&[other.to_path_buf()], expected).expect_err("wrong name");
        assert!(renamed.contains("beat-b.onscreen.png"), "{renamed}");
        let both = vec![expected.to_path_buf(), other.to_path_buf()];
        let multiple = choose_capture(&both, expected).expect_err("two captures must fail");
        assert!(multiple.contains("found 2"), "{multiple}");
        assert!(
            multiple.contains("beat-a.onscreen.png") && multiple.contains("beat-b.onscreen.png"),
            "{multiple}"
        );
    }

    #[test]
    fn find_capture_treats_a_missing_run_dir_as_a_missing_capture() {
        let run_dir = scratch_dir("missing-run-dir");
        let err = find_capture(&run_dir, "beats/beat-a.onscreen.png")
            .expect_err("nothing on disk must fail");
        assert!(err.contains("missing onscreen capture"), "{err}");
        assert!(err.contains("beats/beat-a.onscreen.png"), "{err}");
    }

    #[test]
    fn verify_run_happy_path_through_a_real_png_file() {
        let run_dir = scratch_dir("happy");
        let beats = run_dir.join("beats");
        std::fs::create_dir_all(&beats).expect("beats dir");
        chip_image(2, 5, ONSCREEN_SIZE.0, ONSCREEN_SIZE.1)
            .save(beats.join("beat-a.onscreen.png"))
            .expect("png save");
        let outcome = verify_run(&scenario_with_first_beat(), &report_with_beat(5), &run_dir);
        let _ = std::fs::remove_dir_all(&run_dir);
        assert_eq!(outcome, Ok(()));
    }

    #[test]
    fn verify_run_fails_listing_multiple_onscreen_files() {
        let run_dir = scratch_dir("multiple");
        let beats = run_dir.join("beats");
        std::fs::create_dir_all(&beats).expect("beats dir");
        std::fs::write(beats.join("beat-a.onscreen.png"), []).expect("first file");
        std::fs::write(beats.join("beat-b.onscreen.png"), []).expect("second file");
        let outcome = verify_run(&scenario_with_first_beat(), &report_with_beat(5), &run_dir);
        let _ = std::fs::remove_dir_all(&run_dir);
        let err = outcome.expect_err("two captures must fail");
        assert!(err.contains("found 2"), "{err}");
        assert!(
            err.contains("beat-a.onscreen.png") && err.contains("beat-b.onscreen.png"),
            "{err}"
        );
    }
}
