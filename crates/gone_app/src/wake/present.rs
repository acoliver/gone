//! The primary window's closed-frame acknowledgement (the presentation leg
//! of the wake gate).
//!
//! Issue #27's product gap: the normal windowed game's wake driver started
//! the authored timeline when the asset ledger and the eyelid pipeline
//! bridge agreed, even while the primary window never yielded a drawable
//! (an occluded window's surface acquire fails every frame and bevy renders
//! nothing), so the driver played the whole wake invisibly. This module adds
//! the missing leg: a typed main-world acknowledgement of the primary
//! window's last closed render frame, carried across the render/main
//! boundary in two phases.
//!
//! # The two-phase handoff (why it is two phases)
//!
//! Bevy 0.19 makes the main world available on the render world only during
//! [`ExtractSchedule`]: `ExtractPlugin`'s extract function inserts
//! `MainWorld` immediately before `render_world.run_schedule(ExtractSchedule)`
//! and removes it immediately after (bevy_render 0.19.1,
//! `extract_plugin.rs`, `extract()`), and its doc on `MainWorld` states the
//! resource "is only available during `ExtractSchedule`". A system in the
//! [`Render`] schedule therefore cannot write the main world at all; the
//! first version of this gate requested `ResMut<MainWorld>` there and
//! panicked on every normal launch. The handoff respects the lifetime:
//!
//! * **Phase 1, render:** [`probe_primary_window`] runs in the `Render`
//!   schedule after bevy's own render-and-present system, reads bevy's own
//!   `ExtractedWindows` (never the surface), and records the frame's fact in
//!   a render-local resource ([`WakePresentFrameEvidence`]). Each closed
//!   frame overwrites the record, so no fact outlives its frame.
//! * **Phase 2, extract:** [`extract_present_readiness`] runs in the
//!   `ExtractSchedule`, consumes the record, and folds it into the
//!   main-world mirror ([`WakePresentReadiness`]) through `ResMut<MainWorld>`
//!   — the same window the pipeline bridge's mirror uses
//!   ([`crate::wake_pass`]).
//!
//! Provenance stays one frame: the fact published at an extraction is the
//! frame that closed during the previous render pass, exactly the frame the
//! following main-world update paces its delta against. The record is
//! consumed on publication, so an extraction with no intervening closed
//! render frame folds no success; a stale drawable fact can never be
//! re-published across frames without one, and the sticky ever-seen bit
//! latches only on facts a real closed frame produced.
//!
//! # Evidence contract (what the acknowledgement does and does not prove)
//!
//! The probe reads only state bevy's own render loop already maintains; it
//! never touches the surface (the `get_current_texture` call is bevy's, made
//! in its `prepare_windows`). Bevy 0.19's `render_system` runs the render
//! graph, submits the frame's command encoder, and calls
//! `ExtractedWindow::present` for every window whose view has a swapchain
//! attachment to present. A probe system ordered after that render frame
//! reads `ExtractedWindows` and records two facts about the primary window
//! (published to [`WakePresentReadiness`] at the next extraction):
//!
//! * **Per frame** (`closed_with_drawable`): whether the frame that just
//!   closed drew into the window's frame output. The extracted window's
//!   `swap_chain_texture_view` is present at frame close exactly when bevy
//!   acquired a drawable for this frame and the graph rendered into it, and
//!   absent when the acquire failed (an occluded or recreating surface) or
//!   no surface existed yet.
//! * **Sticky** (`drawable_frame_seen`): whether any render frame has yet
//!   closed over the primary window's drawable. The mirror only ever
//!   latches it, never clears it.
//!
//! With the game's window camera — the loading cover, then the rig camera;
//! the normal game always has one — the frame bevy just closed is also the
//! frame it just submitted and presented. The acknowledgement is frame
//! scheduling evidence from bevy's own loop. It is not a GPU completion
//! fence and not a pixel proof: nothing here reads presented content, and
//! pipeline compilation ([`crate::wake_pass::WakeEyelidPipelineReadiness`]
//! `Ready`) is compile evidence, never drawable evidence — the two legs
//! stay distinct.
//!
//! # Which lane paces on this
//!
//! The normal windowed game inserts [`PresentationPacedWake`]: its timeline
//! starts only once a frame has closed over the primary window's drawable,
//! that acknowledged start update consumes no wake delta, and updates
//! following frames without a drawable bank no time (no catch-up on time
//! the window never presented). The harness lanes never insert it, and
//! their contracts stay untouched: the headless lane has no primary window
//! and takes no presentation leg at all, and the canary's scenario clock is
//! already held by its own screenshot-proven present gate — its windowed
//! hold below is belt-and-suspenders that the first presented frame always
//! precedes.

use bevy::app::{App, Plugin};
use bevy::ecs::prelude::Resource;
use bevy::ecs::schedule::IntoScheduleConfigs;
use bevy::ecs::system::{Res, ResMut};
use bevy::render::view::ExtractedWindows;
use bevy::render::{ExtractSchedule, MainWorld, Render, RenderApp, RenderSystems};

/// Declares that this run paces its wake on the primary window's
/// presentation. Inserted by the windowed game's own wiring and by nothing
/// else: the harness lanes' scenario clocks are already screenshot-proven
/// at 1:1, and their tick contracts must stay byte-identical. See the
/// module docs for the exact pacing this opt-in buys.
#[derive(Resource, Default)]
pub(crate) struct PresentationPacedWake;

/// The main-world mirror of the primary window's closed-frame state,
/// published only by [`extract_present_readiness`] (once per extraction,
/// from the render world's record) and by test fixtures. It holds its
/// honest default — nothing has closed — until an extraction follows a
/// closed render frame, so a windowed gate without any render evidence
/// holds.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Resource)]
pub(crate) struct WakePresentReadiness {
    /// Whether the render frame that just closed drew into the primary
    /// window's frame output. `false` exactly when the window's drawable
    /// was unavailable that frame (occluded or recreating surface, or no
    /// surface yet) — the update following such a frame banks no time in a
    /// paced run.
    pub(crate) closed_with_drawable: bool,
    /// Whether any render frame has yet closed over the primary window's
    /// drawable — sticky once true. The paced start gate holds on this.
    pub(crate) drawable_frame_seen: bool,
}

/// The render world's record of the frame that just closed, written by
/// [`probe_primary_window`] after every closed render frame and consumed by
/// [`extract_present_readiness`] at the next extraction. `Some` only in
/// that window: the probe's per-frame overwrite plus the extractor's take
/// together mean a recorded fact can never outlive the frame it describes.
/// This resource lives in the render world only; the main world never sees
/// it, only the folded mirror.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Resource)]
struct WakePresentFrameEvidence {
    /// Whether the frame that just closed drew into the primary window's
    /// frame output, or `None` between the consumption and the next probe.
    closed_with_drawable: Option<bool>,
}

/// Registers the acknowledgement: the main-world mirror resource, the
/// render-world probe that records each closed frame, and the extraction
/// that publishes the record into the main world. Without a render sub-app
/// (a rendererless test app) only the mirror resource is initialized, and
/// it stays at its default — the honest "nothing closed" shape a
/// rendererless world truly is in.
pub(crate) struct WakePresentProbePlugin;

impl Plugin for WakePresentProbePlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<WakePresentReadiness>();
        if let Some(render_app) = app.get_sub_app_mut(RenderApp) {
            render_app.init_resource::<WakePresentFrameEvidence>();
            render_app.add_systems(Render, probe_primary_window.after(RenderSystems::Render));
            render_app.add_systems(ExtractSchedule, extract_present_readiness);
        }
    }
}

/// Whether the primary window's frame output carried a drawable at this
/// frame's close: the window bevy extracted as primary must hold its
/// swapchain texture view after the render frame ran and presented. Pure so
/// the whole mirror is testable without a device; the field read is the one
/// piece that only a real render world can exercise.
#[must_use]
fn primary_window_drawable(windows: &ExtractedWindows) -> bool {
    windows
        .primary
        .and_then(|entity| windows.get(&entity))
        .is_some_and(|window| window.swap_chain_texture_view.is_some())
}

/// Fold one closed frame's drawable fact into the previous mirror state:
/// the per-frame bit is overwritten, the sticky bit only ever latches.
#[must_use]
fn fold_present(previous: WakePresentReadiness, drawable: bool) -> WakePresentReadiness {
    WakePresentReadiness {
        closed_with_drawable: drawable,
        drawable_frame_seen: previous.drawable_frame_seen || drawable,
    }
}

/// Record this closed render frame's primary-window fact into the
/// render-local evidence channel. Runs after bevy's own render-and-present
/// system every frame, reading only `ExtractedWindows` (bevy's own state —
/// never the surface, never a second acquire). It cannot touch the main
/// world from here: `MainWorld` exists on the render world only during
/// `ExtractSchedule`, long gone by the `Render` schedule (issue #27's
/// normal-startup crash); the next extraction carries the record across.
fn probe_primary_window(
    windows: Res<ExtractedWindows>,
    mut evidence: ResMut<WakePresentFrameEvidence>,
) {
    evidence.closed_with_drawable = Some(primary_window_drawable(windows.into_inner()));
}

/// Publish the recorded frame fact into the main world: the extraction half
/// of the handoff, running inside bevy's `ExtractSchedule` — the only
/// window in which `MainWorld` exists on the render world, and the same
/// window the pipeline bridge's mirror writes in. Consumes the record, so
/// an extraction with no intervening closed render frame folds no success
/// and a stale drawable fact is never re-published.
fn extract_present_readiness(
    mut main: ResMut<MainWorld>,
    mut evidence: ResMut<WakePresentFrameEvidence>,
) {
    let drawable = evidence.closed_with_drawable.take().unwrap_or(false);
    let previous = *main.resource::<WakePresentReadiness>();
    *main.resource_mut::<WakePresentReadiness>() = fold_present(previous, drawable);
}

#[cfg(test)]
mod tests {
    use bevy::app::App;
    use bevy::ecs::system::RunSystemOnce;
    use bevy::render::extract_plugin::ExtractPlugin;
    use bevy::render::view::ExtractedWindows;
    use bevy::render::{MainWorld, Render, RenderApp};

    use super::{
        WakePresentFrameEvidence, WakePresentProbePlugin, WakePresentReadiness,
        extract_present_readiness, fold_present, probe_primary_window,
    };

    /// The real render sub-app over this module's real plugin: bevy's own
    /// `ExtractPlugin` (which registers the `Render` and `ExtractSchedule`
    /// schedules and owns the real extract function that inserts `MainWorld`
    /// around `ExtractSchedule` and removes it after), then
    /// [`WakePresentProbePlugin`]. Production initializes the extracted
    /// windows on the render world (`bevy_window`'s `WindowRenderPlugin`,
    /// `init_gpu_resource::<ExtractedWindows>`); this fixture carries the
    /// schedule machinery without the window plugin, so it performs exactly
    /// that one initialization itself. An `app.update()` on this fixture
    /// runs bevy's genuine per-frame sequence: main schedules, then the real
    /// extract (with `MainWorld` present only inside `ExtractSchedule`).
    fn present_bridge_app() -> App {
        let mut app = App::new();
        app.add_plugins(ExtractPlugin::default());
        app.add_plugins(WakePresentProbePlugin);
        app.get_sub_app_mut(RenderApp)
            .expect("ExtractPlugin creates the render sub-app")
            .world_mut()
            .init_resource::<ExtractedWindows>();
        app
    }

    /// The render world, where the probe and the record live.
    fn render_world(app: &mut App) -> &mut bevy::ecs::world::World {
        app.get_sub_app_mut(RenderApp)
            .expect("ExtractPlugin creates the render sub-app")
            .world_mut()
    }

    /// Record a closed frame's drawable fact in the render-local channel,
    /// the write [`probe_primary_window`] makes once per closed render
    /// frame. The `true` fact's arrival in production is bevy's own
    /// `ExtractedWindow::set_swapchain_texture`; a real texture view needs a
    /// GPU device, so the fixture records the fact directly. The probe path
    /// itself (the no-drawable shape) is exercised through the real
    /// schedule in the tests below.
    fn record_closed_frame(app: &mut App, drawable: bool) {
        render_world(app)
            .resource_mut::<WakePresentFrameEvidence>()
            .closed_with_drawable = Some(drawable);
    }

    /// The main-world mirror as the driver's gate reads it.
    fn mirror(app: &App) -> WakePresentReadiness {
        *app.world().resource::<WakePresentReadiness>()
    }

    #[test]
    fn the_mirror_folds_the_sticky_first_frame_and_the_per_frame_drawable() {
        // A drawable frame latches the sticky bit and sets the per-frame bit;
        // a later frame without the drawable clears only the per-frame bit —
        // the first closed frame is never un-seen.
        let seen = fold_present(WakePresentReadiness::default(), true);
        assert!(seen.closed_with_drawable && seen.drawable_frame_seen);
        let lost = fold_present(seen, false);
        assert!(!lost.closed_with_drawable && lost.drawable_frame_seen);
        // A frame without the drawable over a never-presented window stays
        // at the honest all-false default.
        assert_eq!(
            fold_present(WakePresentReadiness::default(), false),
            WakePresentReadiness::default()
        );
    }

    #[test]
    fn the_plugin_registers_headless_with_the_honest_default() {
        // No render sub-app: only the mirror resource registers, holding its
        // default — the windowed gate must read this as "nothing has closed
        // yet", never as a satisfied leg.
        let mut app = App::new();
        app.add_plugins(WakePresentProbePlugin);
        assert_eq!(
            app.world().resource::<WakePresentReadiness>(),
            &WakePresentReadiness::default()
        );
    }

    /// The issue #27 crash shape, exercised as production runs it: the
    /// render world between extractions carries no `MainWorld` (bevy
    /// inserts it only around `ExtractSchedule`), and the probe runs in the
    /// `Render` schedule. The old probe requested `ResMut<MainWorld>` here,
    /// failed validation every frame, and killed the normal launch ~200 ms
    /// in; the real probe must validate, run, and record the frame's fact
    /// in a world that has no main world at all.
    #[test]
    fn the_probe_validates_and_records_in_a_main_world_less_render_schedule() {
        let mut app = present_bridge_app();
        let world = render_world(&mut app);
        assert!(
            world.get_resource::<MainWorld>().is_none(),
            "the fixture is the production shape: no MainWorld outside extraction"
        );
        // The pre-acquisition extracted shape: bevy has extracted no
        // drawable for any window. Running the real Render schedule (bevy's
        // own systems plus the probe) must not panic.
        world.run_schedule(Render);
        let evidence = render_world(&mut app)
            .resource::<WakePresentFrameEvidence>()
            .closed_with_drawable;
        assert_eq!(
            evidence,
            Some(false),
            "the probe records the honest no-drawable fact for a window-less frame"
        );
        assert!(
            render_world(&mut app).get_resource::<MainWorld>().is_none(),
            "running the render schedule must not conjure a MainWorld"
        );
    }

    /// The extraction half through bevy's genuine per-frame machinery: the
    /// recorded drawable fact is published into the main world's mirror,
    /// the record is consumed (never replayed), and `MainWorld` is gone
    /// again the moment extraction ends.
    #[test]
    fn the_extraction_publishes_the_recorded_frame_through_main_world() {
        let mut app = present_bridge_app();
        record_closed_frame(&mut app, true);
        app.update();
        assert_eq!(
            mirror(&app),
            WakePresentReadiness {
                closed_with_drawable: true,
                drawable_frame_seen: true
            },
            "the first published drawable frame latches both facts"
        );
        let world = render_world(&mut app);
        assert_eq!(
            world.resource::<WakePresentFrameEvidence>(),
            &WakePresentFrameEvidence::default(),
            "the record is consumed at publication, never replayed"
        );
        assert!(
            world.get_resource::<MainWorld>().is_none(),
            "MainWorld is not shared past extraction"
        );
    }

    /// The bridge timeline the paced driver's contract is written against:
    /// publish, then an extraction with no intervening closed frame (no
    /// stale success), then a frame without the drawable recorded through
    /// the real probe path (overwrites, per-frame bit clears, sticky
    /// history holds), then a drawable frame again (pacing re-arms). The
    /// mirror shape after the no-drawable frame,
    /// `closed_with_drawable: false, drawable_frame_seen: true`, is exactly
    /// what the driver tests inject as `lose_drawable`: the sticky bit
    /// gated only the one-time start, the per-frame bit is what continual
    /// pacing banks against.
    #[test]
    fn a_stale_record_never_republishes_and_a_drawable_free_frame_overwrites() {
        let mut app = present_bridge_app();
        record_closed_frame(&mut app, true);
        app.update();
        assert!(mirror(&app).drawable_frame_seen);

        // An extraction with no intervening closed render frame: the record
        // was consumed, so nothing re-publishes the old success, and the
        // sticky first frame is never un-seen.
        app.update();
        assert_eq!(
            mirror(&app),
            WakePresentReadiness {
                closed_with_drawable: false,
                drawable_frame_seen: true
            },
            "no stale success across frames without a drawable"
        );

        // A following frame without the drawable, recorded through the real
        // probe path: the Render schedule over bevy's own extracted windows
        // holding no drawable. The overwrite clears the per-frame bit only.
        render_world(&mut app).run_schedule(Render);
        app.update();
        assert_eq!(
            mirror(&app),
            WakePresentReadiness {
                closed_with_drawable: false,
                drawable_frame_seen: true
            },
            "the occlusion-shaped frame banks nothing but keeps the history"
        );

        // The next drawable frame re-arms the per-frame bit; the sticky bit
        // was already true and stays true.
        record_closed_frame(&mut app, true);
        app.update();
        assert_eq!(
            mirror(&app),
            WakePresentReadiness {
                closed_with_drawable: true,
                drawable_frame_seen: true
            },
            "a drawable frame re-arms pacing"
        );
    }

    /// The rendererless shape the plugin must also serve: no render
    /// sub-app means no probe, no record, no extraction — the mirror holds
    /// its default, and the extract system's fold math is directly
    /// verifiable over a plain world (`take` of an empty record folds no
    /// success).
    #[test]
    fn the_extractor_folds_nothing_from_an_empty_record_over_a_plain_world() {
        let mut world = bevy::ecs::world::World::new();
        world.init_resource::<WakePresentFrameEvidence>();
        world.insert_resource(MainWorld::default());
        world
            .resource_mut::<MainWorld>()
            .insert_resource(WakePresentReadiness::default());
        world
            .run_system_once(extract_present_readiness)
            .expect("the extractor runs over the plain world");
        let readiness = world
            .resource::<MainWorld>()
            .resource::<WakePresentReadiness>();
        assert_eq!(
            *readiness,
            WakePresentReadiness::default(),
            "an empty record folds no success"
        );
        assert_eq!(
            world.resource::<WakePresentFrameEvidence>(),
            &WakePresentFrameEvidence::default(),
        );
    }

    /// The probe's fact is the pure fold input; over a plain world with a
    /// real `ExtractedWindows` resource holding no entries, the probe
    /// records the honest `Some(false)` — the same fact the schedule-level
    /// tests observe in the render world.
    #[test]
    fn the_probe_records_no_drawable_over_window_less_extracted_windows() {
        let mut world = bevy::ecs::world::World::new();
        world.init_resource::<ExtractedWindows>();
        world.init_resource::<WakePresentFrameEvidence>();
        world
            .run_system_once(probe_primary_window)
            .expect("the probe runs over the plain world");
        assert_eq!(
            world
                .resource::<WakePresentFrameEvidence>()
                .closed_with_drawable,
            Some(false),
        );
    }
}
