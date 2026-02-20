use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;
use std::sync::Mutex;

struct SidecarState(Mutex<Option<tauri_plugin_shell::process::CommandChild>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(SidecarState(Mutex::new(None)))
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            if !cfg!(debug_assertions) {
                let sidecar_command = app
                    .handle()
                    .shell()
                    .sidecar("vibetaff-backend")
                    .expect("failed to create sidecar command");

                let (mut rx, child) = sidecar_command
                    .spawn()
                    .expect("Failed to spawn backend sidecar");

                let state = app.state::<SidecarState>();
                *state.0.lock().unwrap() = Some(child);

                tauri::async_runtime::spawn(async move {
                    while let Some(event) = rx.recv().await {
                        match event {
                            CommandEvent::Stdout(line) => {
                                let s = String::from_utf8_lossy(&line);
                                log::info!("[backend] {}", s);
                            }
                            CommandEvent::Stderr(line) => {
                                let s = String::from_utf8_lossy(&line);
                                log::warn!("[backend] {}", s);
                            }
                            CommandEvent::Terminated(payload) => {
                                log::warn!(
                                    "[backend] Process terminated with code: {:?}",
                                    payload.code
                                );
                            }
                            _ => {}
                        }
                    }
                });
            }

            Ok(())
        })
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                log::info!("Window destroyed, sidecar will be cleaned up by OS");
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
