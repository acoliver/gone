//! Throwaway diagnostic (not committed): discrimination matrix probe.
//! Red clear + full-viewport white sprite + primary-window screenshot.
//! - capture red everywhere -> redirect works, draws are broken (GPU preprocessing?)
//! - capture black          -> camera never writes the redirected attachment
//! - capture white+red      -> everything works
//!
//! Env `CPU_PREPROCESS=1` forces the issue-#25595 CPU-preprocessing workaround.

use bevy::app::{App, AppExit, Plugin, PluginGroup, Startup, Update};
use bevy::asset::{Assets, RenderAssetUsages};
use bevy::camera::visibility::Visibility;
use bevy::camera::{Camera2d, ClearColor};
use bevy::color::Color;
use bevy::ecs::prelude::{Commands, MessageWriter, On, Res, ResMut, Resource};
use bevy::image::Image;
use bevy::math::{UVec2, Vec2};
use bevy::render::RenderPlugin;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};
use bevy::render::settings::{RenderCreation, WgpuSettings};
use bevy::render::view::screenshot::{Screenshot, ScreenshotCaptured};
use bevy::sprite::{Anchor, Sprite};
use bevy::transform::components::Transform;
use bevy::window::{Window, WindowPlugin};

fn main() {
    let mut app = App::new();
    let primary = Window {
        title: "probe3".to_owned(),
        resolution: bevy::window::WindowResolution::new(1920, 1080).with_scale_factor_override(1.0),
        ..Default::default()
    };
    let window_plugin = WindowPlugin {
        primary_window: Some(primary),
        ..Default::default()
    };
    if std::env::var("CPU_PREPROCESS").is_ok_and(|v| v == "1") {
        let settings = WgpuSettings {
            constrained_limits: Some({
                use bevy::render::settings::WgpuLimits;
                WgpuLimits {
                    max_binding_array_elements_per_shader_stage: u32::MAX,
                    max_binding_array_sampler_elements_per_shader_stage: u32::MAX,
                    ..WgpuLimits::downlevel_webgl2_defaults()
                }
                .using_resolution(WgpuLimits::default())
            }),
            ..Default::default()
        };
        app.add_plugins((
            bevy::DefaultPlugins
                .set(RenderPlugin {
                    render_creation: RenderCreation::Automatic(Box::new(settings)),
                    ..Default::default()
                })
                .set(window_plugin),
            ProbePlugin,
        ));
    } else {
        app.add_plugins((bevy::DefaultPlugins.set(window_plugin), ProbePlugin));
    }
    app.run();
}

#[derive(Resource)]
struct Frames(u32);

#[derive(Resource, Default)]
struct Captured(u32);

struct ProbePlugin;
impl Plugin for ProbePlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(Frames(0));
        app.insert_resource(Captured(0));
        app.add_observer(on_captured);
        app.add_systems(Startup, setup);
        app.add_systems(Update, tick);
    }
}

fn setup(mut commands: Commands, mut images: ResMut<Assets<Image>>) {
    commands.insert_resource(ClearColor(Color::srgb(1.0, 0.0, 0.0)));
    commands.spawn((Camera2d, bevy::render::view::Msaa::Off));
    // 1920x1080 white sprite covering the full viewport.
    let (w, h) = (1920u32, 1080u32);
    let data = vec![0xffu8; (w * h * 4) as usize];
    let image = Image::new(
        Extent3d {
            width: w,
            height: h,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        data,
        TextureFormat::Rgba8UnormSrgb,
        RenderAssetUsages::MAIN_WORLD,
    );
    let handle = images.add(image);
    let origin = UVec2::new(w, h).as_vec2() * Vec2::new(-0.5, 0.5);
    commands.spawn((
        Sprite::from_image(handle),
        Anchor::TOP_LEFT,
        Visibility::Visible,
        Transform::from_translation(origin.extend(0.0)),
    ));
}

fn tick(
    mut frames: ResMut<Frames>,
    captured: Res<Captured>,
    mut commands: Commands,
    mut exits: MessageWriter<AppExit>,
) {
    frames.0 += 1;
    let f = frames.0;
    if f == 5 {
        commands.spawn(Screenshot::primary_window());
    }
    if captured.into_inner().0 >= 1 {
        // Stay alive a while so an external screencapture can inspect the window.
        if f > 480 {
            bevy::log::info!("probe3: capture done, exiting");
            exits.write(AppExit::Success);
            frames.0 = 0;
        }
    }
    if f > 600 {
        bevy::log::error!("probe3: captures never completed");
        exits.write(AppExit::Error(std::num::NonZeroU8::new(1).unwrap()));
        frames.0 = 0;
    }
}

fn on_captured(mut captured: On<ScreenshotCaptured>, mut done: ResMut<Captured>) {
    let event = captured.event_mut();
    let img = &event.image;
    let data = img.data.as_deref().unwrap_or(&[]);
    let (mut red, mut white, mut black) = (0u64, 0u64, 0u64);
    for p in data.as_chunks::<4>().0 {
        match (p[0], p[1], p[2]) {
            (0, 0, 0) => black += 1,
            (255 | 254, 0, 0) => red += 1,
            (255, 255, 255) => white += 1,
            _ => {}
        }
    }
    let name = format!("tmp/chipscan/probe3-capture-{}.png", done.0);
    if let Ok(dyn_img) = img.clone().try_into_dynamic() {
        let _ = dyn_img.to_rgb8().save(&name);
    }
    bevy::log::info!(
        "probe3: captured {}x{} red {red} white {white} black {black} -> {name}",
        img.width(),
        img.height()
    );
    done.0 += 1;
}
