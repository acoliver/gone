//! Calibration protocol (issue #6 slice B): the scenario parameters and the
//! report evidence for the calibration-evidence lane.
//!
//! The lane produces capture-based evidence that discriminates functioning
//! auto exposure from changed lighting: the scenario predeclares one luminance
//! step, an equal-area bright-patch placement plan, a metering-mask selection,
//! and the auto-exposure on/off arm; the app renders the real post chain into
//! the harness capture target and records the run's setup identity as a
//! tick-stamped report event ([`CalibrationEvidence`]). Bevy fact (verified in
//! vendored source): computed exposure stays GPU-side (a storage buffer read
//! by tonemapping) and is not readable as an app-world component, so evidence
//! about exposure behavior is measured by the runner from the capture PNGs;
//! the app's job is to make the captures and parameters possible and
//! reportable, never to fake measurements.
//!
//! The pinned capture sample ticks are the scenario's `beats` (the existing
//! capture lane requests them exactly as before); [`CalibrationEvidence::
//! sample_ticks`] echoes them so the evidence event is self-contained.
//!
//! Like the rest of `harness`, this module is std + serde only.

/// Upper bound on the light-level parameters and the patch area fraction
/// enforced at parse time. Levels are the wall's linear radiance (see the
/// calibration lane's module docs); the bound keeps the patch's fixed
/// multiple of the wall level finite and the captures inside the tonemapper's
/// responsive range, and the area bound keeps the patch fully on-screen in
/// the edge slot of the fixed calibration camera.
pub const LEVEL_MAX: f32 = 100.0;

/// Upper bound on [`CalibrationParams::patch_area_fraction`]: the largest
/// equal-area patch that still fits fully on screen in the edge slot at the
/// lane's fixed camera geometry (see `bootstrap::calibration`).
pub const PATCH_AREA_FRACTION_MAX: f32 = 0.03;

/// Which metering-mask asset the calibration camera binds on its
/// `AutoExposure` component.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MaskSelection {
    /// The center-weighted radial mask (`post/metering_mask.png`): histogram
    /// weight falls off radially from a fully weighted center to ignored
    /// corners.
    CenterWeighted,
    /// The uniform mask (`post/metering_mask_uniform.png`): every pixel
    /// contributes at full weight. The control that must remove the
    /// center/edge metering difference.
    Uniform,
}

/// Where the equal-area bright patch sits in the frame.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PatchSlot {
    /// Centered on the optical axis: full metering weight under the
    /// center-weighted mask.
    Center,
    /// The lane's fixed upper-right edge position: reduced metering weight
    /// under the center-weighted mask, unchanged weight under the uniform
    /// mask.
    Edge,
}

/// The patch placement plan: fixed in one slot, or moved center-to-edge at a
/// pinned tick on the scenario clock.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PatchPlan {
    /// The patch sits centered for the whole run.
    FixedCenter,
    /// The patch sits at the edge for the whole run.
    FixedEdge,
    /// The patch starts centered and moves to the edge at the pinned tick.
    CenterThenEdge {
        /// Logical tick of the move.
        at_tick: u64,
    },
}

impl PatchPlan {
    /// The tick the plan moves the patch at, if it moves at all.
    #[must_use]
    pub const fn move_tick(&self) -> Option<u64> {
        match *self {
            Self::CenterThenEdge { at_tick } => Some(at_tick),
            Self::FixedCenter | Self::FixedEdge => None,
        }
    }
}

/// One luminance step: the wall radiance changes to `level` on `tick`.
#[derive(Clone, Copy, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct LuminanceStep {
    /// Logical tick of the step (at least 1, so the initial level is sampled
    /// first).
    pub tick: u64,
    /// Linear radiance the wall takes on at the step.
    pub level: f32,
}

/// The calibration lane's scenario parameters (the `calibration` scenario
/// section). Everything the lane renders and records is predeclared here;
/// the scenario describes the scene and never calls gameplay internals.
#[derive(Clone, Copy, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct CalibrationParams {
    /// Linear radiance of the calibration wall before the step.
    pub initial_level: f32,
    /// The one luminance step the run applies.
    pub step: LuminanceStep,
    /// The bright patch's area as a fraction of the frame area at the wall
    /// plane (both placements show the same area).
    pub patch_area_fraction: f32,
    /// The patch placement plan.
    pub patch: PatchPlan,
    /// Which metering mask the camera binds.
    pub mask: MaskSelection,
    /// Whether the camera's `AutoExposure` component is bound at all: bevy's
    /// only switch for computed exposure.
    pub auto_exposure: bool,
}

impl CalibrationParams {
    /// Validate the parameter invariants parse time enforces: positive finite
    /// levels under [`LEVEL_MAX`], a step at tick 1 or later, a patch area in
    /// `(0, PATCH_AREA_FRACTION_MAX)`, and a patch move at tick 1 or later.
    ///
    /// # Errors
    /// A message naming the first violated invariant.
    pub fn validate(&self) -> Result<(), String> {
        validate_level("initial_level", self.initial_level)?;
        validate_level("step level", self.step.level)?;
        if self.step.tick == 0 {
            return Err("calibration step tick must be at least 1 (the initial \
                        level is sampled first)"
                .to_owned());
        }
        if !self.patch_area_fraction.is_finite() || self.patch_area_fraction <= 0.0 {
            return Err(format!(
                "calibration patch_area_fraction must be finite and positive, got {}",
                self.patch_area_fraction
            ));
        }
        if self.patch_area_fraction >= PATCH_AREA_FRACTION_MAX {
            return Err(format!(
                "calibration patch_area_fraction must stay below {PATCH_AREA_FRACTION_MAX} \
                 (the patch must fit fully on screen in the edge slot), got {}",
                self.patch_area_fraction
            ));
        }
        if self.patch.move_tick() == Some(0) {
            return Err("calibration patch move tick must be at least 1 (the \
                        initial placement is sampled first)"
                .to_owned());
        }
        Ok(())
    }
}

/// Check one light-level value against the documented bounds.
fn validate_level(name: &str, level: f32) -> Result<(), String> {
    if !level.is_finite() || level <= 0.0 {
        return Err(format!(
            "calibration {name} must be finite and positive, got {level}"
        ));
    }
    if level > LEVEL_MAX {
        return Err(format!(
            "calibration {name} must not exceed {LEVEL_MAX}, got {level}"
        ));
    }
    Ok(())
}

/// The auto-exposure settings in force on the calibration camera. The fields
/// mirror the `AutoExposure` component's range/filter/speeds as authored.
#[derive(Clone, Copy, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct AutoExposureSettings {
    /// Lower bound of the metered exposure range (`AutoExposure::range`).
    pub range_min: f32,
    /// Upper bound of the metered exposure range.
    pub range_max: f32,
    /// Lower bound of the metering filter (`AutoExposure::filter`).
    pub filter_min: f32,
    /// Upper bound of the metering filter.
    pub filter_max: f32,
    /// Adaptation speed dark-to-bright in F-stops per second.
    pub speed_brighten: f32,
    /// Adaptation speed bright-to-dark in F-stops per second.
    pub speed_darken: f32,
}

/// The auto-exposure arm of the calibration evidence: whether the component
/// was bound, and the settings bound with it (`None` when disabled — no
/// `AutoExposure` component exists, so nothing is in force).
#[derive(Clone, Copy, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct AutoExposureEvidence {
    /// Whether the camera carried the `AutoExposure` component.
    pub enabled: bool,
    /// The bound settings, present exactly when `enabled`.
    pub settings: Option<AutoExposureSettings>,
}

/// One recorded patch placement: which slot the patch occupies from `tick` on.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct PatchPlacement {
    /// First logical tick the patch occupies `slot` (0 for the initial
    /// placement, the pinned tick for a move).
    pub tick: u64,
    /// The slot the patch occupies from `tick` on.
    pub slot: PatchSlot,
}

/// The calibration run's setup evidence, recorded once as a
/// `TimedEvent::Calibration` before any dynamics run: which mask the GPU
/// histogram samples (identified by the sha256 of the loaded asset's pixel
/// bytes, not the file path), the auto-exposure and authored-exposure state,
/// the patch plan, the light levels, and the pinned sample ticks.
#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct CalibrationEvidence {
    /// The metering-mask selection the scenario predeclared.
    pub mask: MaskSelection,
    /// sha2-256 (lowercase hex) of the loaded mask asset's pixel bytes at
    /// runtime — the `Image` data the histogram pass samples.
    pub mask_sha256: String,
    /// The auto-exposure arm: enabled flag plus the settings in force.
    pub auto_exposure: AutoExposureEvidence,
    /// The authored exposure value in force (the camera's `Exposure::ev100`).
    /// Governs the captured brightness when auto exposure is disabled.
    pub authored_exposure_ev100: f32,
    /// The patch's area as a fraction of the frame area at the wall plane.
    pub patch_area_fraction: f32,
    /// The placements in tick order: the initial slot at tick 0, then the
    /// move slot at its pinned tick when the plan moves the patch.
    pub patch_placements: Vec<PatchPlacement>,
    /// The wall radiance before the step.
    pub initial_level: f32,
    /// Tick of the luminance step.
    pub step_tick: u64,
    /// Wall radiance from the step tick on.
    pub step_level: f32,
    /// The pinned capture sample ticks (the scenario's beat ticks, ascending).
    pub sample_ticks: Vec<u64>,
}

/// The patch placements a plan produces, in tick order.
#[must_use]
pub fn patch_placements(plan: PatchPlan) -> Vec<PatchPlacement> {
    match plan {
        PatchPlan::FixedCenter => vec![PatchPlacement {
            tick: 0,
            slot: PatchSlot::Center,
        }],
        PatchPlan::FixedEdge => vec![PatchPlacement {
            tick: 0,
            slot: PatchSlot::Edge,
        }],
        PatchPlan::CenterThenEdge { at_tick } => vec![
            PatchPlacement {
                tick: 0,
                slot: PatchSlot::Center,
            },
            PatchPlacement {
                tick: at_tick,
                slot: PatchSlot::Edge,
            },
        ],
    }
}

#[cfg(test)]
mod tests {
    use super::{
        AutoExposureEvidence, AutoExposureSettings, CalibrationEvidence, CalibrationParams,
        LEVEL_MAX, LuminanceStep, MaskSelection, PATCH_AREA_FRACTION_MAX, PatchPlacement,
        PatchPlan, PatchSlot, patch_placements,
    };

    /// A valid parameter set other tests perturb.
    fn valid_params() -> CalibrationParams {
        CalibrationParams {
            initial_level: 0.18,
            step: LuminanceStep {
                tick: 30,
                level: 0.36,
            },
            patch_area_fraction: 0.02,
            patch: PatchPlan::CenterThenEdge { at_tick: 60 },
            mask: MaskSelection::CenterWeighted,
            auto_exposure: true,
        }
    }

    #[test]
    fn params_roundtrip_through_json() {
        let params = valid_params();
        let json = serde_json::to_string(&params).expect("serializes");
        let parsed: CalibrationParams = serde_json::from_str(&json).expect("parses");
        assert_eq!(parsed, params);
    }

    #[test]
    fn params_parse_from_the_documented_json_shape() {
        let json = r#"{
            "initial_level": 0.18,
            "step": {"tick": 30, "level": 0.36},
            "patch_area_fraction": 0.02,
            "patch": {"center_then_edge": {"at_tick": 60}},
            "mask": "uniform",
            "auto_exposure": false
        }"#;
        let params: CalibrationParams = serde_json::from_str(json).expect("parses");
        assert!((params.initial_level - 0.18).abs() < 1e-6);
        assert_eq!(
            params.step,
            LuminanceStep {
                tick: 30,
                level: 0.36
            }
        );
        assert_eq!(params.patch, PatchPlan::CenterThenEdge { at_tick: 60 });
        assert_eq!(params.mask, MaskSelection::Uniform);
        assert!(!params.auto_exposure);
    }

    #[test]
    fn snake_case_variant_names_parse() {
        for (text, expected) in [
            (r#""center_weighted""#, MaskSelection::CenterWeighted),
            (r#""uniform""#, MaskSelection::Uniform),
        ] {
            let parsed: MaskSelection = serde_json::from_str(text).expect("parses");
            assert_eq!(parsed, expected);
        }
        let center: PatchSlot = serde_json::from_str(r#""center""#).expect("parses");
        let edge: PatchSlot = serde_json::from_str(r#""edge""#).expect("parses");
        assert_eq!((center, edge), (PatchSlot::Center, PatchSlot::Edge));
        let fixed: PatchPlan = serde_json::from_str(r#""fixed_center""#).expect("parses");
        assert_eq!(fixed, PatchPlan::FixedCenter);
    }

    #[test]
    fn unknown_variant_names_are_rejected() {
        let mask: Result<MaskSelection, _> = serde_json::from_str(r#""spot""#);
        assert!(mask.is_err());
        let plan: Result<PatchPlan, _> = serde_json::from_str(r#""diagonal""#);
        assert!(plan.is_err());
    }

    #[test]
    fn valid_params_validate_clean() {
        assert!(valid_params().validate().is_ok());
    }

    #[test]
    fn zero_and_negative_and_nonfinite_levels_are_rejected() {
        for level in [0.0, -1.0, f32::NAN, f32::INFINITY] {
            let mut params = valid_params();
            params.initial_level = level;
            let err = params.validate().expect_err("must fail");
            assert!(err.contains("initial_level"), "{err}");
        }
        let mut params = valid_params();
        params.step.level = 0.0;
        let err = params.validate().expect_err("must fail");
        assert!(err.contains("step level"), "{err}");
    }

    #[test]
    fn levels_above_the_cap_are_rejected() {
        let mut params = valid_params();
        params.initial_level = LEVEL_MAX * 1.5;
        assert!(params.validate().is_err());
        params.initial_level = LEVEL_MAX;
        assert!(params.validate().is_ok(), "the cap itself is allowed");
    }

    #[test]
    fn step_at_tick_zero_is_rejected() {
        let mut params = valid_params();
        params.step.tick = 0;
        let err = params.validate().expect_err("must fail");
        assert!(err.contains("step tick"), "{err}");
    }

    #[test]
    fn patch_area_out_of_range_is_rejected() {
        for fraction in [0.0, -0.01, PATCH_AREA_FRACTION_MAX, 0.5, f32::NAN] {
            let mut params = valid_params();
            params.patch_area_fraction = fraction;
            let err = params.validate().expect_err("must fail");
            assert!(
                err.contains("patch_area_fraction"),
                "fraction {fraction}: {err}"
            );
        }
        let mut params = valid_params();
        params.patch_area_fraction = PATCH_AREA_FRACTION_MAX * 0.5;
        assert!(params.validate().is_ok(), "well under the cap is allowed");
    }

    #[test]
    fn patch_move_at_tick_zero_is_rejected() {
        let mut params = valid_params();
        params.patch = PatchPlan::CenterThenEdge { at_tick: 0 };
        let err = params.validate().expect_err("must fail");
        assert!(err.contains("patch move tick"), "{err}");
    }

    #[test]
    fn fixed_placements_never_report_a_move_tick() {
        assert_eq!(PatchPlan::FixedCenter.move_tick(), None);
        assert_eq!(PatchPlan::FixedEdge.move_tick(), None);
        assert_eq!(
            PatchPlan::CenterThenEdge { at_tick: 7 }.move_tick(),
            Some(7)
        );
    }

    #[test]
    fn placements_follow_the_plan_in_tick_order() {
        assert_eq!(
            patch_placements(PatchPlan::FixedCenter),
            vec![PatchPlacement {
                tick: 0,
                slot: PatchSlot::Center
            }]
        );
        assert_eq!(
            patch_placements(PatchPlan::FixedEdge),
            vec![PatchPlacement {
                tick: 0,
                slot: PatchSlot::Edge
            }]
        );
        assert_eq!(
            patch_placements(PatchPlan::CenterThenEdge { at_tick: 60 }),
            vec![
                PatchPlacement {
                    tick: 0,
                    slot: PatchSlot::Center
                },
                PatchPlacement {
                    tick: 60,
                    slot: PatchSlot::Edge
                },
            ]
        );
    }

    #[test]
    fn evidence_roundtrips_through_json() {
        let evidence = CalibrationEvidence {
            mask: MaskSelection::Uniform,
            mask_sha256: "ab12".repeat(32),
            auto_exposure: AutoExposureEvidence {
                enabled: true,
                settings: Some(AutoExposureSettings {
                    range_min: -8.0,
                    range_max: 8.0,
                    filter_min: 0.10,
                    filter_max: 0.90,
                    speed_brighten: 3.0,
                    speed_darken: 1.0,
                }),
            },
            authored_exposure_ev100: 0.0,
            patch_area_fraction: 0.02,
            patch_placements: patch_placements(PatchPlan::CenterThenEdge { at_tick: 60 }),
            initial_level: 0.18,
            step_tick: 30,
            step_level: 0.36,
            sample_ticks: vec![5, 20, 35, 80],
        };
        let json = serde_json::to_string(&evidence).expect("serializes");
        let parsed: CalibrationEvidence = serde_json::from_str(&json).expect("parses");
        assert_eq!(parsed, evidence);
    }

    #[test]
    fn disabled_auto_exposure_evidence_has_no_settings() {
        let evidence = AutoExposureEvidence {
            enabled: false,
            settings: None,
        };
        let json = serde_json::to_string(&evidence).expect("serializes");
        let parsed: AutoExposureEvidence = serde_json::from_str(&json).expect("parses");
        assert_eq!(parsed, evidence);
        assert!(!parsed.enabled);
        assert!(parsed.settings.is_none());
    }
}
