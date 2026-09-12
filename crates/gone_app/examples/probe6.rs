//! Throwaway probe: why does the metering-mask asset not become resident in a
//! bare test app? Prints the server load state per update with logs on.

fn main() {
    let mut app = bevy::app::App::new();
    app.add_plugins((
        bevy::app::TaskPoolPlugin::default(),
        bevy::log::LogPlugin::default(),
        bevy::asset::AssetPlugin::default(),
        bevy::image::ImagePlugin::default(),
    ));
    let server = app.world().resource::<bevy::asset::AssetServer>().clone();
    let handle: bevy::asset::Handle<bevy::image::Image> = server.load("post/metering_mask.png");
    for i in 0..30 {
        app.update();
        let resident = app
            .world()
            .resource::<bevy::asset::Assets<bevy::image::Image>>()
            .get(&handle)
            .is_some();
        println!(
            "update {i}: resident={resident} load_state={:?}",
            server.load_state(handle.id())
        );
        if resident {
            break;
        }
    }
}
