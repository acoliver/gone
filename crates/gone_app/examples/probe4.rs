//! Throwaway diagnostic (not committed): render-lane discrimination matrix.
//!
//! Scenes:
//! - window camera: red clear + one 256x256 white sprite (`MAIN_WORLD` | `RENDER_WORLD` usages)
//! - image camera:  green clear, target = its own `Rgba8UnormSrgb` image (same usages)
//!
//! Captures:
//! - window screenshot at frame 5 (early) and frame 120 (late)
//! - image-target screenshot at frame 10
//!
//! Verdicts printed per capture as color histograms over the PNG's RGB pixels:
//! - window late black too  -> window capture path broken, not a first-frame race
//! - image capture green    -> image path works; only the window redirect is broken
//! - white sprite visible   -> `RenderAssetUsages` was the sprite bug

use bevy::app::{App, AppExit, Plugin, PluginGroup, Startup, Update};
use bevy::asset::{Assets, Handle, RenderAssetUsages};
use bevy::camera::visibility::Visibility;
use bevy::camera::{Camera, Camera2d, ClearColor, RenderTarget};
use bevy::color::Color;
use bevy::ecs::message::MessageWriter;
use bevy::ecs::prelude::{
    Commands, Component, Entity, Has, On, Query, Res, ResMut, Resource, With,
};
use bevy::image::Image;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};
use bevy::render::view::screenshot::{Screenshot, ScreenshotCaptured};
use bevy::sprite::{Anchor, Sprite};
use bevy::transform::components::Transform;
use bevy::window::{PrimaryWindow, Window, WindowPlugin};

fn main() {
    let mut app = App::new();
    let window_plugin = WindowPlugin {
        primary_window: Some(Window {
            title: "probe4".to_owned(),
            resolution: bevy::window::WindowResolution::new(1920, 1080)
                .with_scale_factor_override(1.0),
            ..Default::default()
        }),
        ..Default::default()
    };
    app.add_plugins(if std::env::var("CPU_PREPROCESS").is_ok_and(|v| v == "1") {
        let settings = bevy::render::settings::WgpuSettings {
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
        (
            bevy::DefaultPlugins
                .set(bevy::render::RenderPlugin {
                    render_creation: bevy::render::settings::RenderCreation::Automatic(Box::new(
                        settings,
                    )),
                    ..Default::default()
                })
                .set(window_plugin),
            ProbePlugin,
        )
    } else {
        (bevy::DefaultPlugins.set(window_plugin), ProbePlugin)
    });
    app.run();
}

#[derive(Resource, Default)]
struct Frames(u32);

#[derive(Resource, Default)]
struct Done(u32);

#[derive(Resource)]
struct ImageTarget(Handle<Image>);

#[derive(Component)]
struct Early;

#[derive(Component)]
struct Late;

#[derive(Component)]
struct ImageShot;

struct ProbePlugin;
impl Plugin for ProbePlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(Frames(0));
        app.insert_resource(Done(0));
        app.add_observer(on_captured);
        app.add_systems(Startup, setup);
        app.add_systems(Update, tick);
    }
}

fn solid_image(width: u32, height: u32, rgba: [u8; 4]) -> Image {
    let mut image = Image::new(
        Extent3d {
            width,
            height,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        std::iter::repeat_n(rgba, (width * height) as usize)
            .flatten()
            .collect(),
        TextureFormat::Rgba8UnormSrgb,
        RenderAssetUsages::default(),
    );
    image.texture_descriptor.usage |=
        bevy::render::render_resource::TextureUsages::RENDER_ATTACHMENT;
    image
}

fn setup(mut commands: Commands, mut images: ResMut<Assets<Image>>) {
    // Window scene: red clear + white sprite.
    commands.insert_resource(ClearColor(Color::srgb(1.0, 0.0, 0.0)));
    commands.spawn((Camera2d, bevy::render::view::Msaa::Off));
    let white = images.add(solid_image(256, 256, [0xff, 0xff, 0xff, 0xff]));
    commands.spawn((
        Sprite::from_image(white),
        Anchor::CENTER,
        Visibility::Visible,
        Transform::default(),
    ));

    // Image scene: green clear, camera targeting its own texture.
    let target = images.add(solid_image(512, 512, [0, 0, 0, 0xff]));
    commands.spawn((
        Camera2d,
        bevy::render::view::Msaa::Off,
        Camera {
            order: 1,
            ..Camera::default()
        },
        RenderTarget::Image(target.clone().into()),
    ));
    commands.insert_resource(ImageTarget(target));
}

fn tick(
    mut frames: ResMut<Frames>,
    done: Res<Done>,
    target: Res<ImageTarget>,
    windows: Query<&Window, With<PrimaryWindow>>,
    mut commands: Commands,
    mut exits: MessageWriter<AppExit>,
) {
    frames.0 += 1;
    let f = frames.0;
    let window_ready = windows.single().is_ok();
    if window_ready && f == 5 {
        commands.spawn((Screenshot::primary_window(), Early));
    }
    if window_ready && f == 10 {
        commands.spawn((Screenshot::image(target.into_inner().0.clone()), ImageShot));
    }
    if window_ready && f == 120 {
        commands.spawn((Screenshot::primary_window(), Late));
    }
    if done.into_inner().0 >= 3 {
        bevy::log::info!("probe4: all captures done");
        exits.write(AppExit::Success);
        frames.0 = 0;
    }
    if f > 600 {
        bevy::log::error!("probe4: captures never completed");
        exits.write(AppExit::Error(std::num::NonZeroU8::new(1).unwrap()));
        frames.0 = 0;
    }
}

fn on_captured(
    mut captured: On<ScreenshotCaptured>,
    shots: Query<(Entity, Has<Early>, Has<Late>)>,
    mut done: ResMut<Done>,
) {
    let entity = captured.entity;
    let what = if shots.get(entity).is_ok_and(|(_, e, _)| e) {
        "window-early"
    } else if shots.get(entity).is_ok_and(|(_, _, l)| l) {
        "window-late"
    } else {
        "image-target"
    };
    let event = captured.event_mut();
    let img = &event.image;
    let (mut red, mut green, mut white, mut black, mut other) = (0u64, 0u64, 0u64, 0u64, 0u64);
    if let Ok(dyn_img) = img.clone().try_into_dynamic() {
        for p in dyn_img.to_rgb8().as_raw().as_chunks::<3>().0 {
            match *p {
                [255 | 254, 0, 0] => red += 1,
                [0, 255 | 254, 0] => green += 1,
                [255, 255, 255] => white += 1,
                [0, 0, 0] => black += 1,
                _ => other += 1,
            }
        }
        let name = format!("tmp/issue15-render-lane/probe/probe4-{what}.png");
        let _ = dyn_img.to_rgb8().save(&name);
        bevy::log::info!(
            "probe4: {what} {}x{} red {red} green {green} white {white} black {black} other {other}",
            img.width(),
            img.height()
        );
    } else {
        bevy::log::error!(
            "probe4: {what} convert failed (format {:?})",
            img.texture_descriptor.format
        );
    }
    done.0 += 1;
}
