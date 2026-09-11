//! The game-content readiness barrier (review batch 3d).
//!
//! A gameplay run (the harness gameplay lane and the normal game alike) is
//! not started until every required game asset has loaded. The required list
//! is data: one constructor, [`GameAssets::game_required_assets`], lists
//! today's auto-exposure metering mask, and the later passes extend the list
//! there when they add assets of their own.
//!
//! * Harness gameplay lane: the readiness proof (the offscreen readback) is
//!   requested only once the ledger reports every required asset loaded and
//!   the rig camera is bound to the capture target, so the readback that
//!   opens the scenario clock is a rendered game frame and the pipelines
//!   that produce it are compiled. The proof, not the ledger alone, stays
//!   the boundary (see `bootstrap::state::Readiness`).
//! * Normal game: the ledger is polled every update by
//!   [`poll_required_assets_or_exit`]. A pending load holds the game in its
//!   authored initial presentation: the wake phase machine sits in
//!   `Waking`, and the wake progression (the issue #8 wake pass) must
//!   consult [`GameAssets::ready`] before it may drive the machine. A load
//!   error is a hard error: the game names the asset and the underlying
//!   error and exits nonzero instead of rendering with the engine's
//!   placeholder standing in for a required asset.
//!
//! Load errors are tracked, never retried: the first error is sticky and
//! the verdict never improves. A load that stays pending is bounded by the
//! app's existing failure paths (a harness run ends at the runner's process
//! timeout naming the scenario, the same known limit as a readback that
//! never lands); there is no separate polling budget of new shape.

use std::num::NonZeroU8;

use bevy::app::AppExit;
use bevy::asset::{AssetServer, Handle, LoadState};
use bevy::ecs::message::MessageWriter;
use bevy::ecs::prelude::{Res, ResMut, Resource};
use bevy::image::Image;

use crate::post::{MASK_ASSET_PATH, PostChainAssets};

/// One required game asset: the ledger name the failure report carries (the
/// asset path) and the handle the owning game plugin already loaded.
pub(crate) struct RequiredAsset {
    name: &'static str,
    handle: Handle<Image>,
}

/// One required asset's observed load state: the ledger's cached view of the
/// asset server, refreshed by [`GameAssets::poll`].
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum AssetLoad {
    /// The load has not completed (still loading, or not yet started).
    Pending,
    /// The load completed.
    Loaded,
    /// The load failed; the string is the underlying error.
    Failed(String),
}

/// A required asset's load failure: the asset by name plus the underlying
/// error, exactly as the run's failure report carries them.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct AssetFailure {
    /// The asset's ledger name (its path).
    pub(crate) asset: &'static str,
    /// The loader's underlying error text.
    pub(crate) error: String,
}

/// The required-asset ledger for one game run. Built once at wiring from the
/// handles the game plugins already own; polled once per update. The first
/// load error is sticky: after it the ledger stops polling and the verdict
/// never improves.
#[derive(Resource)]
pub(crate) struct GameAssets {
    assets: Vec<RequiredAsset>,
    loads: Vec<AssetLoad>,
    failure: Option<AssetFailure>,
}

impl GameAssets {
    /// A ledger over the given required assets, every load pending.
    #[must_use]
    pub(crate) fn new(assets: Vec<RequiredAsset>) -> Self {
        let loads = vec![AssetLoad::Pending; assets.len()];
        Self {
            assets,
            loads,
            failure: None,
        }
    }

    /// The required assets of today's game content: the auto-exposure
    /// metering mask the post chain loads. The later passes that add game
    /// assets extend this one constructor; the barrier follows the list.
    #[must_use]
    pub(crate) fn game_required_assets(masks: &PostChainAssets) -> Self {
        Self::new(vec![RequiredAsset {
            name: MASK_ASSET_PATH,
            handle: masks.metering_mask.clone(),
        }])
    }

    /// Advance the ledger from the asset server: pending loads are re-read,
    /// loaded ones stay, and the first load error is recorded and stops the
    /// poll. After a failure the ledger is inert; call
    /// [`GameAssets::failure`] for the verdict.
    pub(crate) fn poll(&mut self, server: &AssetServer) {
        if self.failure.is_some() {
            return;
        }
        let mut failure = None;
        for (load, asset) in self.loads.iter_mut().zip(&self.assets) {
            if *load == AssetLoad::Loaded {
                continue;
            }
            match server.load_state(&asset.handle) {
                LoadState::Loaded => *load = AssetLoad::Loaded,
                LoadState::Failed(error) => {
                    let record = AssetFailure {
                        asset: asset.name,
                        error: error.to_string(),
                    };
                    // The entry records the failure too, so the ledger's
                    // per-asset view matches the run's verdict from the
                    // first observation onward.
                    *load = AssetLoad::Failed(record.error.clone());
                    failure = Some(record);
                    break;
                }
                LoadState::Loading | LoadState::NotLoaded => *load = AssetLoad::Pending,
            }
        }
        self.failure = failure;
    }

    /// True when every required asset has loaded and none has failed: the
    /// barrier's asset leg, and the gate the wake progression (issue #8)
    /// must consult before it may drive the phase machine out of `Waking`.
    #[must_use]
    pub(crate) fn ready(&self) -> bool {
        self.failure.is_none() && self.loads.iter().all(|load| *load == AssetLoad::Loaded)
    }

    /// The first required-asset load failure, if any.
    #[must_use]
    pub(crate) fn failure(&self) -> Option<&AssetFailure> {
        self.failure.as_ref()
    }

    /// A ledger with injected load states, for tests that pin the verdict
    /// and the failure paths without racing the asset server's IO tasks.
    /// Injected failures carry their `failure` verdict with them, so
    /// `poll`'s sticky early-out holds from the first call.
    #[cfg(test)]
    #[must_use]
    pub(crate) fn with_loads(states: &[(&'static str, AssetLoad)]) -> Self {
        Self {
            assets: states
                .iter()
                .map(|(name, _)| RequiredAsset {
                    name,
                    handle: Handle::default(),
                })
                .collect(),
            loads: states.iter().map(|(_, state)| state.clone()).collect(),
            failure: states.iter().find_map(|(name, state)| match state {
                AssetLoad::Failed(error) => Some(AssetFailure {
                    asset: name,
                    error: error.clone(),
                }),
                _ => None,
            }),
        }
    }
}

/// The normal game's barrier poll: advance the ledger and, on a required
/// asset's load failure, name the asset and the underlying error and exit
/// nonzero. The game never renders with the engine's placeholder standing
/// in for a required asset. A pending load does nothing here: the scene
/// stays in its authored `Waking` opening because nothing drives the wake
/// machine before this ledger reports ready.
pub(crate) fn poll_required_assets_or_exit(
    mut assets: ResMut<GameAssets>,
    server: Res<AssetServer>,
    mut exits: MessageWriter<AppExit>,
) {
    assets.poll(server.into_inner());
    if let Some(failure) = assets.failure() {
        eprintln!(
            "gone: required asset `{}` failed to load: {}",
            failure.asset, failure.error
        );
        exits.write(AppExit::Error(NonZeroU8::new(1).expect("one is nonzero")));
    }
}

#[cfg(test)]
mod tests {
    use bevy::app::{App, TaskPoolPlugin};
    use bevy::asset::{AssetApp, AssetPlugin, AssetServer};
    use bevy::ecs::message::Messages;
    use bevy::image::ImagePlugin;
    use bevy::input::ButtonInput;
    use bevy::input::keyboard::KeyCode;
    use bevy::input::mouse::AccumulatedMouseMotion;
    use bevy::window::WindowFocused;

    use super::{AppExit, AssetLoad, GameAssets, poll_required_assets_or_exit};
    use crate::player::PlayerLookPlugin;
    use crate::post::GamePostChainPlugin;
    use crate::scene::{SimWakePhase, StasisScenePlugin};
    use gone_sim::WakePhase;

    const MASK: &str = crate::post::MASK_ASSET_PATH;

    /// An app whose only job is to hand out a real [`AssetServer`] for the
    /// poll tests (the IO tasks behind it are never waited on).
    fn server_app() -> App {
        let mut app = App::new();
        app.add_plugins((TaskPoolPlugin::default(), AssetPlugin::default()));
        app
    }

    #[test]
    fn a_pending_load_holds_the_barrier_and_a_full_one_opens_it() {
        let assets = GameAssets::with_loads(&[(MASK, AssetLoad::Pending)]);
        assert!(!assets.ready(), "a pending load holds the barrier");
        assert_eq!(assets.failure(), None);

        // The barrier opens exactly when every entry is loaded, and the
        // empty-ledger shape a game with no required assets would boot
        // with opens trivially.
        let loaded = GameAssets::with_loads(&[(MASK, AssetLoad::Loaded)]);
        assert!(loaded.ready());
        assert!(GameAssets::with_loads(&[]).ready());
    }

    #[test]
    fn poll_keeps_an_untracked_handle_pending_and_an_error_sticky() {
        // A handle the server never tracks reads as NotLoaded forever: the
        // deterministic pending shape the delay tests inject. The poll maps
        // it to Pending and the barrier stays held.
        let app = server_app();
        let server = app.world().resource::<AssetServer>();
        let mut assets = GameAssets::with_loads(&[(MASK, AssetLoad::Pending)]);
        assets.poll(server);
        assert!(!assets.ready());
        assert_eq!(assets.failure(), None);

        // The first load error is sticky: poll becomes inert, the failure
        // verdict never improves, and the error text rides with it.
        let mut failed =
            GameAssets::with_loads(&[(MASK, AssetLoad::Failed("missing file".to_owned()))]);
        failed.poll(server);
        let failure = failed.failure().expect("the injected failure is recorded");
        assert_eq!(failure.asset, MASK);
        assert_eq!(failure.error, "missing file");
        assert!(!failed.ready());
    }

    #[test]
    fn a_failed_required_asset_exits_the_normal_game() {
        let mut app = App::new();
        app.add_plugins((TaskPoolPlugin::default(), AssetPlugin::default()));
        app.init_asset::<bevy::image::Image>();
        app.add_message::<AppExit>();
        app.insert_resource(GameAssets::with_loads(&[(
            MASK,
            AssetLoad::Failed("missing file".to_owned()),
        )]));
        app.add_systems(bevy::app::Update, poll_required_assets_or_exit);
        app.update();
        let exits = app.world().resource::<Messages<AppExit>>();
        let errors = exits
            .iter_current_update_messages()
            .filter(|exit| matches!(exit, AppExit::Error(_)))
            .count();
        assert_eq!(errors, 1, "the hard error exits the game nonzero");
    }

    #[test]
    fn the_normal_game_does_not_advance_the_wake_progression_before_readiness() {
        // The real plugin set the windowed game boots, no renderer: the
        // scene plugin inserts the authored spawn state and nothing in the
        // game drives the wake machine before the ledger reports ready.
        // Regression pin for the loading gate: if a later pass adds a wake
        // driver that skips the barrier, the phase moves and this fails.
        let mut app = App::new();
        app.add_plugins((
            TaskPoolPlugin::default(),
            AssetPlugin::default(),
            ImagePlugin::default(),
        ));
        app.init_asset::<bevy::mesh::Mesh>()
            .init_asset::<bevy::pbr::StandardMaterial>();
        // The look plugin's systems read the input state DefaultPlugins
        // initializes in the real game; a rendererless test app provides it
        // directly.
        app.add_message::<WindowFocused>()
            .init_resource::<ButtonInput<KeyCode>>()
            .init_resource::<AccumulatedMouseMotion>();
        app.add_plugins((GamePostChainPlugin, StasisScenePlugin, PlayerLookPlugin));
        let ledger = {
            let masks = app.world().resource::<crate::post::PostChainAssets>();
            GameAssets::game_required_assets(masks)
        };
        app.insert_resource(ledger);
        app.add_message::<AppExit>();
        app.add_systems(bevy::app::Update, poll_required_assets_or_exit);

        for _ in 0..5 {
            app.update();
        }
        assert_eq!(
            app.world().resource::<SimWakePhase>().phase(),
            WakePhase::Waking,
            "the authored opening holds until the barrier passes"
        );
        let ledger = app.world().resource::<GameAssets>();
        assert!(
            ledger.failure().is_none(),
            "the checked-in mask must not fail its load"
        );
        let exits = app.world().resource::<Messages<AppExit>>();
        assert!(
            exits.iter_current_update_messages().next().is_none(),
            "a loading game does not exit"
        );
    }
}
