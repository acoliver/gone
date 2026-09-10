//! Throwaway diagnostic (not committed): window-screenshot isolation probe.
//!
//! No camera renders to the window at all. Camera A targets image IA (red clear).
//! Captures: primary window at frame 5, image IA at frame 10, primary window again
//! at frame 120.
//!
//! Verdicts:
//! - window captures black with zero cameras on the window -> the window
//!   screenshot machinery itself never carries content on this stack
//! - IA capture red -> the image-target screenshot path works

use bevy::app::{App, AppExit, Plugin, PluginGroup, Startup, Update};
use bevy::asset::{Assets, Handle, RenderAssetUsages};
use bevy::camera::{Camera, Camera2d, ClearColor, RenderTarget};
use bevy::color::Color;
use bevy::ecs::message::MessageWriter;
use bevy::ecs::prelude::{
    Commands, Component, Entity, Has, On, Query, Res, ResMut, Resource, With,
};
use bevy::image::Image;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat, TextureUsages};
use bevy::render::view::screenshot::{Screenshot, ScreenshotCaptured};
use bevy::window::{PrimaryWindow, Window, WindowPlugin};

fn main() {
    let mut app = App::new();
    let window_plugin = WindowPlugin {
        primary_window: Some(Window {
            title: "probe5".to_owned(),
            resolution: bevy::window::WindowResolution::new(1920, 1080)
                .with_scale_factor_override(1.0),
            ..Default::default()
        }),
        ..Default::default()
    };
    app.add_plugins((bevy::DefaultPlugins.set(window_plugin), ProbePlugin));
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

fn setup(mut commands: Commands, mut images: ResMut<Assets<Image>>) {
    commands.insert_resource(ClearColor(Color::srgb(1.0, 0.0, 0.0)));
    let mut target = Image::new(
        Extent3d {
            width: 512,
            height: 512,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        vec![0; 512 * 512 * 4],
        TextureFormat::Rgba8UnormSrgb,
        RenderAssetUsages::default(),
    );
    target.texture_descriptor.usage |= TextureUsages::RENDER_ATTACHMENT;
    let handle = images.add(target);
    commands.spawn((
        Camera2d,
        bevy::render::view::Msaa::Off,
        Camera {
            order: 0,
            ..Camera::default()
        },
        RenderTarget::Image(handle.clone().into()),
    ));
    commands.insert_resource(ImageTarget(handle));
}

fn tick(
    mut frames: ResMut<Frames>,
    done: Res<Done>,
    target: Res<ImageTarget>,
    windows: Query<(), With<PrimaryWindow>>,
    mut commands: Commands,
    mut exits: MessageWriter<AppExit>,
) {
    frames.0 += 1;
    let f = frames.0;
    if windows.single().is_ok() {
        if f == 5 {
            commands.spawn((Screenshot::primary_window(), Early));
        }
        if f == 10 {
            commands.spawn(Screenshot::image(target.into_inner().0.clone()));
        }
        if f == 120 {
            commands.spawn((Screenshot::primary_window(), Late));
        }
    }
    if done.into_inner().0 >= 3 {
        bevy::log::info!("probe5: all captures done");
        exits.write(AppExit::Success);
        frames.0 = 0;
    }
    if f > 600 {
        bevy::log::error!("probe5: captures never completed");
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
        "image-A"
    };
    let event = captured.event_mut();
    let img = &event.image;
    let (mut red, mut black, mut other) = (0u64, 0u64, 0u64);
    if let Ok(dyn_img) = img.clone().try_into_dynamic() {
        for p in dyn_img.to_rgb8().as_raw().as_chunks::<3>().0 {
            match *p {
                [255 | 254, 0, 0] => red += 1,
                [0, 0, 0] => black += 1,
                _ => other += 1,
            }
        }
        bevy::log::info!(
            "probe5: {what} {}x{} red {red} black {black} other {other}",
            img.width(),
            img.height()
        );
    } else {
        bevy::log::error!(
            "probe5: {what} convert failed (format {:?})",
            img.texture_descriptor.format
        );
    }
    done.0 += 1;
}
