//! The wake eyelid fullscreen pass (issue #8, render primitive slice).
//!
//! A [`FullscreenMaterial`] that composites the authored wake presentation
//! over the finished LDR frame: opaque top and bottom eyelids, a blur whose
//! radius follows the authored smear, and the authored dark-to-neutral
//! exposure ramp (the WGSL side of the contract lives at
//! `crates/gone_app/assets/post/wake_eyelid.wgsl`). The material component
//! is the camera effect: a camera carries [`WakeEyelidMaterial`], the value
//! is extracted to the render world as its uniform, and the pass samples the
//! camera's `ViewTarget` main texture — which at this pass's position in the
//! chain is display-referred sRGB output, matching the shader's authored
//! display-space colors.
//!
//! # Chain position (declared per bevy 0.19 source; see below for what is
//! actually validated)
//!
//! Bevy 0.19's `Core3d` schedule registers (bevy_core_pipeline 0.19.1,
//! `core_3d/mod.rs`): `tonemapping.in_set(Core3dSystems::PostProcess)` and
//! `upscaling.after(Core3dSystems::PostProcess)`. The pass overrides
//! [`FullscreenMaterial::schedule_configs`] to declare exactly the two edges
//! that position it: `.after(tonemapping).before(upscaling)` — compositing
//! over the finished LDR image, beneath the final upscale. Auto exposure
//! metering stays upstream of the eyelid transitively through tonemapping:
//! bevy's `AutoExposurePlugin` declares
//! `before(tonemapping).in_set(Core3dSystems::PostProcess)`
//! (bevy_post_process 0.19.1, `auto_exposure/mod.rs`), and the histogram
//! reads the HDR main texture that a post-tonemapping pass never writes, so
//! eyelid occlusion cannot run the exposure away.
//!
//! # What is validated where
//!
//! * Unit-tested, GPU-free: the uniform mapping from
//!   [`gone_sim::WakeSample`] (closed / partial / neutral), the extraction
//!   skip of the neutral hold, the 16-byte uniform layout against the WGSL
//!   struct, the checked-in shader asset, plugin/material registration, the
//!   *built* `Core3d` schedule's topological order (the test constructs the
//!   real render sub-app, adds the real `Core3dPlugin`, and asserts the
//!   initialized schedule runs the pass after `tonemapping` and before
//!   `upscaling`), and the readiness aggregation contract.
//! * Not yet validated: an actual GPU frame. Pipeline compilation, bind
//!   groups, and on-screen compositing need a device; the production driver
//!   must gate on [`WakeEyelidPipelineReadiness`] (below) rather than on
//!   frames-since-start.
//!
//! # Pipeline identity and readiness evidence
//!
//! Bevy's [`FullscreenMaterialPlugin`] owns the pipeline: at `RenderStartup`
//! it inserts the render-world resource
//! `FullscreenMaterialPipeline<WakeEyelidMaterial>` — bind group layout
//! `{ texture_2d<float> (filterable), filtering sampler, uniform buffer
//! (min binding size 16) }`, fragment entry `fragment` of
//! [`WAKE_EYELID_SHADER_ASSET`], pipeline label
//! `fullscreen_material_pipeline<gone_app::wake_pass::WakeEyelidMaterial>`,
//! color target specialized per view from the view's target format. Per view
//! carrying the material, its prepare systems specialize the pipeline into
//! the `PipelineCache` and insert the view's
//! `FullscreenMaterialPipelineId`.
//!
//! [`WakeEyelidPlugin`] mirrors that render-world state into the main world
//! as [`WakeEyelidPipelineReadiness`] every extraction, using only real
//! facilities (the pipeline resource, the per-view pipeline ids bound to
//! this material, `PipelineCache::get_render_pipeline_state`), with the
//! first fatal specialization error's own text beside it as
//! [`WakeEyelidPipelineFailure`]. Until a camera carries the material, bevy
//! specializes no pipeline variant, so the honest state is
//! [`WakeEyelidPipelineReadiness::AwaitingView`]: the pass is registered,
//! not compiled. Attaching the component on the production camera, gating
//! the wake timeline on the extracted readiness, and advancing the
//! timeline are the production driver's job ([`crate::wake`], the
//! normal-game wiring).
//!
//! # What each lane decides
//!
//! The normal windowed game and the gameplay harness lane both add the
//! production driver ([`crate::wake::GameWakePlugin`], which adds this
//! plugin): the game runs the authored opening in the window, and the
//! gameplay lane runs the same timeline on its scenario clock. The
//! calibration and smoke lanes build their own plugin sets and are
//! untouched; adding this plugin to a lane is an explicit decision each
//! lane makes.

use bevy::app::{App, Plugin};
use bevy::camera::Camera;
use bevy::core_pipeline::fullscreen_material::{
    FullscreenMaterial, FullscreenMaterialPipeline, FullscreenMaterialPipelineId,
    FullscreenMaterialPlugin,
};
use bevy::core_pipeline::tonemapping::tonemapping;
use bevy::core_pipeline::upscaling::upscaling;
use bevy::ecs::component::Component;
use bevy::ecs::query::{QueryItem, With};
use bevy::ecs::resource::Resource;
use bevy::ecs::schedule::{IntoScheduleConfigs, ScheduleConfigs};
use bevy::ecs::system::{BoxedSystem, Query, Res, ResMut, lifetimeless::Read};
use bevy::render::extract_component::ExtractComponent;
use bevy::render::render_resource::{CachedPipelineState, PipelineCache, ShaderType};
// `bevy::shader` is the facade's re-export of the `bevy_shader` crate, where
// `PipelineCache`'s error type lives; the render_resource module imports it
// privately and offers no re-export of its own.
use bevy::render::sync_component::SyncComponent;
use bevy::render::{ExtractSchedule, MainWorld, RenderApp};
use bevy::shader::ShaderCacheError;
use bevy::shader::ShaderRef;
use gone_sim::WakeSample;

/// The checked-in WGSL asset the pass runs, relative to the app's asset root
/// (`crates/gone_app/assets`). The file's uniform struct is the byte-level
/// twin of [`WakeEyelidMaterial`]; the layout test pins the footprint.
pub const WAKE_EYELID_SHADER_ASSET: &str = "post/wake_eyelid.wgsl";

/// The wake eyelid pass's uniform and camera effect component: the three
/// scalars the WGSL samples, mapped 1:1 from a [`gone_sim::WakeSample`].
///
/// Field order is the WGSL `WakeEyelid` struct's field order; the trailing
/// [`Self::_padding`] rounds the buffer entry to the uniform's 16-byte
/// footprint. The sample's sway offset is deliberately unmapped — it is
/// camera motion for the rig, not a post-pass parameter.
#[derive(Component, Clone, Copy, Debug, PartialEq, ShaderType)]
pub struct WakeEyelidMaterial {
    /// Normalized lid openness: 0 fully shut, 1 fully open.
    pub lid_openness: f32,
    /// Normalized blur: 0 sharp, 1 fully smeared.
    pub blur: f32,
    /// The authored exposure ramp: 0 the authored dark floor, 1 neutral.
    pub exposure_ramp: f32,
    /// Uniform buffers round struct size up to 16 bytes; one float pads.
    _padding: f32,
}

impl WakeEyelidMaterial {
    /// The fully closed uniform: opaque lids, full smear, the dark floor.
    /// The byte-level twin of [`WakeSample::CLOSED`].
    pub const CLOSED: Self = Self {
        lid_openness: 0.0,
        blur: 1.0,
        exposure_ramp: 0.0,
        _padding: 0.0,
    };

    /// The neutral passthrough: open lids, sharp, no authored adjustment.
    /// The byte-level twin of [`WakeSample::NEUTRAL`], and the value an
    /// unconfigured material carries ([`Default`]) so a bare component can
    /// never darken the frame.
    pub const NEUTRAL: Self = Self {
        lid_openness: 1.0,
        blur: 0.0,
        exposure_ramp: 1.0,
        _padding: 0.0,
    };

    /// Map a simulation sample onto the pass's uniform. The sway offset is
    /// ignored (see the struct docs); every other field is copied verbatim.
    #[must_use]
    pub fn from_sample(sample: WakeSample) -> Self {
        Self {
            lid_openness: sample.lid_openness,
            blur: sample.blur,
            exposure_ramp: sample.exposure_ramp,
            _padding: 0.0,
        }
    }
}

impl Default for WakeEyelidMaterial {
    fn default() -> Self {
        Self::NEUTRAL
    }
}

impl SyncComponent for WakeEyelidMaterial {
    type Target = Self;
}

impl ExtractComponent for WakeEyelidMaterial {
    type QueryData = Read<Self>;
    type QueryFilter = With<Camera>;
    type Out = Self;

    fn extract_component(material: QueryItem<'_, '_, Self::QueryData>) -> Option<Self> {
        // The neutral hold skips the pass outright (the shader would be a
        // passthrough): between wake completion and the production driver's
        // removal of the component, no fullscreen draw is spent on it.
        if *material == Self::NEUTRAL {
            None
        } else {
            Some(*material)
        }
    }
}

impl FullscreenMaterial for WakeEyelidMaterial {
    fn fragment_shader() -> ShaderRef {
        ShaderRef::Path(WAKE_EYELID_SHADER_ASSET.into())
    }

    // Bevy's default pins a fullscreen material before tonemapping (in the
    // PostProcess set). The eyelid composites over the finished LDR frame,
    // so it re-pins exactly the two edges that matter: after the
    // tonemapping system, before the upscaling system. See the module docs
    // for the bevy-source lines these names resolve to.
    fn schedule_configs(system: ScheduleConfigs<BoxedSystem>) -> ScheduleConfigs<BoxedSystem> {
        system.after(tonemapping).before(upscaling)
    }
}

/// The main-world mirror of the eyelid pass's render-world pipeline state,
/// refreshed by [`WakeEyelidPlugin`] every extraction from real facilities
/// (`FullscreenMaterialPipeline<WakeEyelidMaterial>`, the per-view
/// `FullscreenMaterialPipelineId`s bound to this material, and
/// `PipelineCache::get_render_pipeline_state`). The production driver gates
/// on this resource, never on frames elapsed.
///
/// Aggregation across the views currently carrying the material is
/// worst-state-wins ([`fold_readiness`]): any errored specialization
/// reports [`Self::Errored`], otherwise [`Self::Ready`] only when every
/// specialized view's pipeline is compiled, otherwise
/// [`Self::Compiling`]. When extraction drops the material (the neutral
/// hold skips it), a previously ready pass reports
/// [`Self::AwaitingView`] again — at wake completion the driver removes
/// the component anyway.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Resource)]
pub enum WakeEyelidPipelineReadiness {
    /// No `FullscreenMaterialPipeline<WakeEyelidMaterial>` in the render
    /// world: the render sub-app is absent (a headless test app), the plugin
    /// is not added, or `RenderStartup` has not run yet.
    #[default]
    NotStarted,
    /// The pipeline resource exists, but no extracted view carries the
    /// material, so bevy has specialized no pipeline variant: registered,
    /// not compiled. The state before the production driver attaches the
    /// effect.
    AwaitingView,
    /// At least one view carries the material and its pipeline variant is
    /// queued or compiling in the `PipelineCache`.
    Compiling,
    /// Every specialized view's pipeline variant is compiled and usable.
    Ready,
    /// At least one specialization failed (shader compile error). The pass
    /// will silently skip its views; the driver must fail loudly instead.
    Errored,
}

/// One specialized view's pipeline compile state, reduced from
/// `CachedPipelineState` (whose variants carry non-`Copy` GPU objects and
/// creation tasks the fold must not need).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum SpecializedPipelineState {
    /// `CachedPipelineState::Ok`: the variant is compiled and usable.
    Compiled,
    /// `CachedPipelineState::Queued` or `Creating`: compilation in flight,
    /// including the two shader-asset waits bevy itself re-queues (see
    /// [`classify_pipeline_error`]).
    Pending,
    /// `CachedPipelineState::Err`: specialization or compilation failed in
    /// a way retrying cannot fix.
    Failed,
}

/// The main-world mirror of the first fatal eyelid pipeline error's text,
/// refreshed by [`WakeEyelidPlugin`] every extraction beside
/// [`WakeEyelidPipelineReadiness`]: `Some` exactly while the readiness is
/// [`WakeEyelidPipelineReadiness::Errored`], carrying bevy's own
/// `ShaderCacheError` display for the production driver to name on its
/// hard exit. The two resources are written together by one system, so an
/// `Errored` verdict always has its text beside it.
#[derive(Clone, Debug, Default, PartialEq, Eq, Resource)]
pub struct WakeEyelidPipelineFailure(pub Option<String>);

/// Sort one cached pipeline error into the bridge's states. Bevy's
/// `PipelineCache` re-queues the two shader-asset variants itself
/// (`ShaderNotLoaded`, `ShaderImportNotYetAvailable` — the pipeline
/// descriptor is waiting on the asset server, not broken), so they are a
/// wait ([`SpecializedPipelineState::Pending`]), never a failure. Only the
/// two fatal variants — the shader could not be processed or the module
/// could not be created — report [`SpecializedPipelineState::Failed`],
/// carrying the error's own display text for the failure mirror.
fn classify_pipeline_error(error: &ShaderCacheError) -> (SpecializedPipelineState, Option<String>) {
    match error {
        ShaderCacheError::ShaderNotLoaded(_) | ShaderCacheError::ShaderImportNotYetAvailable => {
            (SpecializedPipelineState::Pending, None)
        }
        fatal @ (ShaderCacheError::ProcessShaderError(_)
        | ShaderCacheError::CreateShaderModule(_)) => {
            (SpecializedPipelineState::Failed, Some(fatal.to_string()))
        }
    }
}

/// The readiness aggregation, pure so the whole state machine is testable
/// without a device: no pipeline resource is [`WakeEyelidPipelineReadiness::
/// NotStarted`]; a resource with no specialized views is
/// [`WakeEyelidPipelineReadiness::AwaitingView`]; any failed view dominates
/// every other state; readiness requires every specialized view compiled.
fn fold_readiness(
    pipeline_resource_present: bool,
    views: impl Iterator<Item = SpecializedPipelineState>,
) -> WakeEyelidPipelineReadiness {
    if !pipeline_resource_present {
        return WakeEyelidPipelineReadiness::NotStarted;
    }
    let mut any_specialized = false;
    let mut all_compiled = true;
    let mut any_errored = false;
    for state in views {
        any_specialized = true;
        match state {
            SpecializedPipelineState::Compiled => {}
            SpecializedPipelineState::Failed => any_errored = true,
            SpecializedPipelineState::Pending => all_compiled = false,
        }
    }
    if any_errored {
        WakeEyelidPipelineReadiness::Errored
    } else if any_specialized && all_compiled {
        WakeEyelidPipelineReadiness::Ready
    } else if any_specialized {
        WakeEyelidPipelineReadiness::Compiling
    } else {
        WakeEyelidPipelineReadiness::AwaitingView
    }
}

/// Registers the wake eyelid pass: bevy's [`FullscreenMaterialPlugin`] for
/// [`WakeEyelidMaterial`] (extraction, uniform buffering, the render-world
/// pipeline resource, and the pass system ordered against tonemapping and
/// upscaling) plus the [`WakeEyelidPipelineReadiness`] extraction bridge.
///
/// Deliberately attaches nothing: no camera receives the material and no
/// wake phase advances from this plugin. A lane opts into the effect by
/// adding this plugin and inserting the material on its own camera, then
/// gates on the readiness resource.
pub struct WakeEyelidPlugin;

impl Plugin for WakeEyelidPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<WakeEyelidPipelineReadiness>();
        app.init_resource::<WakeEyelidPipelineFailure>();
        app.add_plugins(FullscreenMaterialPlugin::<WakeEyelidMaterial>::default());
        if let Some(render_app) = app.get_sub_app_mut(RenderApp) {
            render_app.add_systems(ExtractSchedule, extract_eyelid_pipeline_readiness);
        }
    }
}

/// Mirror the render world's eyelid pipeline state into the main world. The
/// query pairs the pipeline id with this material so the ids reported can
/// only be the ones bevy's prepare system specialized for views carrying it
/// (other fullscreen materials' ids sit on views without this component).
/// See [`fold_readiness`] for the aggregation contract and
/// [`classify_pipeline_error`] for the error sorting; the readiness and the
/// failure text are written together so an `Errored` verdict never lacks
/// its message.
fn extract_eyelid_pipeline_readiness(
    mut main_world: ResMut<MainWorld>,
    pipeline_cache: Res<PipelineCache>,
    pipeline: Option<Res<FullscreenMaterialPipeline<WakeEyelidMaterial>>>,
    views: Query<(&WakeEyelidMaterial, &FullscreenMaterialPipelineId)>,
) {
    // Bevy hands these read guards by value and offers no reference-typed
    // system params; `into_inner` consumes each guard into the plain
    // borrow the fold below works with.
    let pipeline_present = pipeline.map(Res::into_inner).is_some();
    let pipeline_cache = pipeline_cache.into_inner();
    let mut error_text = None;
    let states = views.iter().map(|(_material, pipeline_id)| {
        match pipeline_cache.get_render_pipeline_state(pipeline_id.0) {
            CachedPipelineState::Ok(_) => SpecializedPipelineState::Compiled,
            CachedPipelineState::Queued | CachedPipelineState::Creating(_) => {
                SpecializedPipelineState::Pending
            }
            CachedPipelineState::Err(error) => {
                let (state, text) = classify_pipeline_error(error);
                error_text = text;
                state
            }
        }
    });
    let readiness = fold_readiness(pipeline_present, states);
    *main_world.resource_mut::<WakeEyelidPipelineReadiness>() = readiness;
    *main_world.resource_mut::<WakeEyelidPipelineFailure>() = WakeEyelidPipelineFailure(error_text);
}

#[cfg(test)]
mod tests {
    use super::{
        SpecializedPipelineState, WAKE_EYELID_SHADER_ASSET, WakeEyelidMaterial,
        WakeEyelidPipelineFailure, WakeEyelidPipelineReadiness, WakeEyelidPlugin,
        classify_pipeline_error, fold_readiness,
    };
    use bevy::app::{App, SubApp};
    use bevy::core_pipeline::core_3d::Core3dPlugin;
    use bevy::core_pipeline::fullscreen_material::FullscreenMaterial;
    use bevy::core_pipeline::schedule::Core3d;
    use bevy::ecs::schedule::ScheduleLabel;
    use bevy::ecs::system::lifetimeless::Read;
    use bevy::ecs::world::World;
    use bevy::math::Vec2;
    use bevy::render::extract_component::ExtractComponent;
    use bevy::render::render_resource::ShaderType;
    use bevy::render::sync_world::SyncToRenderWorld;
    use bevy::render::{ExtractSchedule, MainWorld, RenderApp};
    use bevy::shader::{ShaderCacheError, ShaderRef};
    use gone_sim::WakeSample;

    /// An authored mid-timeline state: the first opening's end state, a
    /// narrow peek through heavy smear with the ramp partway up.
    fn partial_sample() -> WakeSample {
        WakeSample {
            lid_openness: 0.35,
            blur: 0.85,
            exposure_ramp: 0.35,
            sway_offset: Vec2::new(0.012, 0.008),
        }
    }

    /// Asserts two scalars are the same bits: the mapping is a verbatim
    /// copy of the sample's fields, so any rounding at all is a break.
    fn assert_same_bits(actual: f32, expected: f32, label: &str) {
        assert_eq!(actual.to_bits(), expected.to_bits(), "{label}");
    }

    #[test]
    fn closed_sample_maps_to_the_closed_uniform() {
        let uniform = WakeEyelidMaterial::from_sample(WakeSample::CLOSED);
        assert_eq!(uniform, WakeEyelidMaterial::CLOSED);
        assert_same_bits(uniform.lid_openness, 0.0, "closed lid openness");
        assert_same_bits(uniform.blur, 1.0, "closed blur");
        assert_same_bits(uniform.exposure_ramp, 0.0, "closed exposure ramp");
    }

    #[test]
    fn partial_sample_maps_field_for_field() {
        let uniform = WakeEyelidMaterial::from_sample(partial_sample());
        assert_same_bits(uniform.lid_openness, 0.35, "partial lid openness");
        assert_same_bits(uniform.blur, 0.85, "partial blur");
        assert_same_bits(uniform.exposure_ramp, 0.35, "partial exposure ramp");
    }

    #[test]
    fn the_mapping_ignores_the_sway_offset() {
        // The sway offset is camera motion for the rig, never a post-pass
        // parameter: samples differing only in sway must map identically.
        let still = WakeEyelidMaterial::from_sample(partial_sample());
        let swayed = WakeEyelidMaterial::from_sample(WakeSample {
            sway_offset: Vec2::new(-0.04, 0.05),
            ..partial_sample()
        });
        assert_eq!(still, swayed);
    }

    #[test]
    fn neutral_sample_maps_to_the_neutral_uniform() {
        let uniform = WakeEyelidMaterial::from_sample(WakeSample::NEUTRAL);
        assert_eq!(uniform, WakeEyelidMaterial::NEUTRAL);
        assert_same_bits(uniform.lid_openness, 1.0, "neutral lid openness");
        assert_same_bits(uniform.blur, 0.0, "neutral blur");
        assert_same_bits(uniform.exposure_ramp, 1.0, "neutral exposure ramp");
        // An unconfigured material defaults to the neutral passthrough so a
        // bare component can never darken the frame.
        assert_eq!(WakeEyelidMaterial::default(), WakeEyelidMaterial::NEUTRAL);
    }

    #[test]
    fn extraction_skips_only_the_neutral_hold() {
        // The real extraction decision, called on a real query item from a
        // real world: neutral (the completed wake) extracts None so the pass
        // is not scheduled; every non-neutral state extracts Some.
        let extract = |material: WakeEyelidMaterial| {
            let mut world = World::new();
            world.spawn(material);
            let mut query = world.query::<Read<WakeEyelidMaterial>>();
            let item = query.single(&world).expect("exactly one material");
            WakeEyelidMaterial::extract_component(item)
        };
        assert!(extract(WakeEyelidMaterial::NEUTRAL).is_none());
        assert_eq!(
            extract(WakeEyelidMaterial::CLOSED),
            Some(WakeEyelidMaterial::CLOSED)
        );
        assert_eq!(
            extract(WakeEyelidMaterial::from_sample(partial_sample())),
            Some(WakeEyelidMaterial::from_sample(partial_sample()))
        );
    }

    #[test]
    fn uniform_layout_matches_the_wgsl_struct() {
        // The WGSL WakeEyelid struct is four f32s: a 16-byte footprint. The
        // Rust side must agree with that byte layout or the GPU reads a
        // shuffled uniform, and the struct must satisfy WGSL's uniform
        // address-space layout constraints (encase checks both).
        assert_eq!(WakeEyelidMaterial::min_size().get(), 16);
        <WakeEyelidMaterial as ShaderType>::assert_uniform_compat();
    }

    #[test]
    fn the_shader_asset_is_checked_in_at_the_declared_path() {
        // The pipeline loads exactly this asset path at startup; the file
        // must sit in the checked-in asset tree and carry the uniform and
        // binding names the Rust side maps (a drift guard against renaming
        // one side without the other, not a shader compile check).
        match WakeEyelidMaterial::fragment_shader() {
            ShaderRef::Path(path) => {
                assert_eq!(path.path(), std::path::Path::new(WAKE_EYELID_SHADER_ASSET));
            }
            ShaderRef::Default | ShaderRef::Handle(_) => {
                panic!("the eyelid pass must declare its asset path")
            }
        }
        let source = std::fs::read_to_string(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("assets")
                .join(WAKE_EYELID_SHADER_ASSET),
        )
        .expect("the checked-in eyelid shader exists");
        assert!(!source.is_empty(), "the shader is not empty");
        for name in [
            "lid_openness",
            "blur",
            "exposure_ramp",
            "_padding",
            "screen_texture",
            "screen_sampler",
        ] {
            assert!(
                source.contains(name),
                "the shader must name its uniform/binding member `{name}`"
            );
        }
    }

    #[test]
    fn the_plugin_registers_the_material_and_readiness_headless() {
        // No render sub-app (the headless test shape): the extract machinery
        // still registers on the main world — every entity carrying the
        // material is marked for render-world sync — and the readiness
        // resource holds its NotStarted default, honestly naming that no
        // render world has produced pipeline state. The failure mirror
        // holds no error text beside it.
        let mut app = App::new();
        app.add_plugins(WakeEyelidPlugin);
        let entity = app.world_mut().spawn(WakeEyelidMaterial::CLOSED).id();
        assert!(
            app.world().get::<SyncToRenderWorld>(entity).is_some(),
            "the material must carry the render-world sync marker"
        );
        assert_eq!(
            app.world().resource::<WakeEyelidPipelineReadiness>(),
            &WakeEyelidPipelineReadiness::NotStarted
        );
        assert_eq!(
            app.world().resource::<WakeEyelidPipelineFailure>(),
            &WakeEyelidPipelineFailure(None)
        );
    }

    /// Initialize a registered schedule on the render world through bevy's
    /// own schedule scope and return its system names in built run order.
    /// The scope lifts only the schedule out of the `Schedules`
    /// collection, leaving the resource itself in the world, which
    /// `Schedule::initialize` requires (it reads
    /// `ignored_scheduling_ambiguities` from it). A raw
    /// `World::resource_scope::<Schedules>` would remove the resource and
    /// force `initialize` to re-insert it, which the scope guard rejects
    /// in debug builds.
    fn built_system_names(
        world: &mut World,
        label: impl ScheduleLabel,
        context: &str,
    ) -> Vec<String> {
        world
            .try_schedule_scope(label, |world, schedule| {
                schedule.initialize(world).unwrap_or_else(|err| {
                    panic!("{context}: the schedule graph must build: {err}")
                });
                schedule
                    .systems()
                    .expect("initialize made the schedule's systems readable")
                    .map(|(_key, system)| system.name().to_string())
                    .collect()
            })
            .unwrap_or_else(|err| panic!("{context}: the schedule must be registered: {err}"))
    }

    #[test]
    fn core3d_builds_with_the_pass_after_tonemapping_and_before_upscaling() {
        // Real registration and real order evidence, no GPU: a bare render
        // sub-app, bevy's own Core3dPlugin (which registers the tonemapping
        // and upscaling systems production runs), then this slice's plugin.
        // Initializing each schedule builds its topological order; the pass
        // must sit between the two systems its configs pin against, and the
        // readiness extractor must be registered in the render app's
        // ExtractSchedule. What this cannot prove: that a GPU executes the
        // order in a rendered frame.
        let mut app = App::new();
        app.insert_sub_app(RenderApp, SubApp::new());
        // Production inserts `MainWorld` into the render world at the start
        // of every extract, before any extract system can initialize;
        // bevy's real `Extract` system params panic at schedule-initialize
        // time without it.
        app.get_sub_app_mut(RenderApp)
            .expect("the render sub-app was just inserted")
            .world_mut()
            .insert_resource(MainWorld::default());
        // Core3dPlugin must build on the main app: it registers the Core3d
        // schedule and its tonemapping/upscaling systems (bevy_core_pipeline
        // 0.19.1, core_3d/mod.rs: `tonemapping.in_set(Core3dSystems::
        // PostProcess)`, `upscaling.after(Core3dSystems::PostProcess)`) in
        // its render-app half, behind `App::get_sub_app_mut(RenderApp)` —
        // which finds nothing when the plugin is built against the render
        // sub-app itself (a sub-app runs its plugins as the empty app's
        // main sub-app). This is the registration shape production runs:
        // the render sub-app exists as a labeled sub-app and the pipeline
        // plugin builds on the main app. SkyboxPlugin (pulled in by
        // Core3dPlugin) embeds a shader at build time, which requires this
        // registry in the app world the plugin builds against (AssetPlugin
        // owns it in a real app).
        app.insert_resource(bevy::asset::io::embedded::EmbeddedAssetRegistry::default());
        app.add_plugins(Core3dPlugin);
        app.add_plugins(WakeEyelidPlugin);

        let world = app
            .get_sub_app_mut(RenderApp)
            .expect("render sub-app")
            .world_mut();
        let core3d_names = built_system_names(world, Core3d, "Core3d");
        let extract_names = built_system_names(world, ExtractSchedule, "the ExtractSchedule");

        let position = |names: &[String], needle: &str| {
            names
                .iter()
                .position(|name| name.contains(needle))
                .unwrap_or_else(|| panic!("no `{needle}` system in {names:?}"))
        };
        // The tonemapping and upscaling system functions live in each
        // module's `node` submodule in bevy 0.19 (re-exported at the module
        // root), so their full system paths carry the segment.
        let tonemapping_position = position(
            &core3d_names,
            "bevy_core_pipeline::tonemapping::node::tonemapping",
        );
        let eyelid_position = position(
            &core3d_names,
            "fullscreen_material_system<gone_app::wake_pass::WakeEyelidMaterial>",
        );
        let upscaling_position = position(
            &core3d_names,
            "bevy_core_pipeline::upscaling::node::upscaling",
        );
        assert!(
            tonemapping_position < eyelid_position,
            "the eyelid pass must run after tonemapping: {core3d_names:?}"
        );
        assert!(
            eyelid_position < upscaling_position,
            "the eyelid pass must run before upscaling: {core3d_names:?}"
        );
        assert!(
            extract_names
                .iter()
                .any(|name| name.contains("extract_eyelid_pipeline_readiness")),
            "the readiness extractor must be in the render app's ExtractSchedule: \
             {extract_names:?}"
        );
    }

    #[test]
    fn the_readiness_fold_reports_not_started_without_a_pipeline_resource() {
        // Absent resource: NotStarted regardless of any view states — the
        // honest shape before RenderStartup (or without a render app).
        assert_eq!(
            fold_readiness(false, std::iter::empty()),
            WakeEyelidPipelineReadiness::NotStarted
        );
        assert_eq!(
            fold_readiness(false, [SpecializedPipelineState::Compiled].into_iter()),
            WakeEyelidPipelineReadiness::NotStarted
        );
    }

    #[test]
    fn the_readiness_fold_reports_awaiting_view_before_any_specialization() {
        // Resource present, no view carries the material yet: registered,
        // not compiled — the state this slice leaves production in.
        assert_eq!(
            fold_readiness(true, std::iter::empty()),
            WakeEyelidPipelineReadiness::AwaitingView
        );
    }

    #[test]
    fn the_readiness_fold_reports_compiling_while_any_view_pends() {
        let views = [
            SpecializedPipelineState::Compiled,
            SpecializedPipelineState::Pending,
        ];
        assert_eq!(
            fold_readiness(true, views.into_iter()),
            WakeEyelidPipelineReadiness::Compiling
        );
    }

    #[test]
    fn the_readiness_fold_reports_ready_only_when_every_view_compiled() {
        assert_eq!(
            fold_readiness(true, [SpecializedPipelineState::Compiled].into_iter()),
            WakeEyelidPipelineReadiness::Ready
        );
        let views = [SpecializedPipelineState::Compiled; 3];
        assert_eq!(
            fold_readiness(true, views.into_iter()),
            WakeEyelidPipelineReadiness::Ready
        );
    }

    #[test]
    fn the_readiness_fold_lets_any_failure_dominate() {
        // Worst-state-wins: one failed specialization among many must name
        // Errored whether the others are pending or compiled, so the driver
        // fails loudly instead of waiting on a pass that will never run.
        for views in [
            [SpecializedPipelineState::Failed].as_slice(),
            [
                SpecializedPipelineState::Pending,
                SpecializedPipelineState::Failed,
            ]
            .as_slice(),
            [
                SpecializedPipelineState::Compiled,
                SpecializedPipelineState::Failed,
            ]
            .as_slice(),
        ] {
            assert_eq!(
                fold_readiness(true, views.iter().copied()),
                WakeEyelidPipelineReadiness::Errored,
                "views {views:?} must aggregate to Errored"
            );
        }
    }

    #[test]
    fn a_shader_asset_wait_classifies_as_pending_without_error_text() {
        // Bevy's own cache re-queues the two shader-asset variants, so the
        // first extracted frames of a boot (shader still loading) must read
        // as a wait, never as the fatal Errored the driver exits on.
        let unloaded = ShaderCacheError::ShaderNotLoaded(bevy::asset::AssetId::<
            bevy::shader::Shader,
        >::invalid());
        for error in [unloaded, ShaderCacheError::ShaderImportNotYetAvailable] {
            let (state, text) = classify_pipeline_error(&error);
            assert_eq!(state, SpecializedPipelineState::Pending, "{error}");
            assert_eq!(text, None, "{error} carries no failure text");
        }
    }

    #[test]
    fn a_fatal_shader_failure_classifies_as_failed_naming_the_error() {
        let (state, text) = classify_pipeline_error(&ShaderCacheError::CreateShaderModule(
            "the wgsl was rejected".to_owned(),
        ));
        assert_eq!(state, SpecializedPipelineState::Failed);
        let text = text.expect("a fatal failure carries its message");
        assert!(
            text.contains("the wgsl was rejected"),
            "the message names the underlying error: {text}"
        );
    }
}
