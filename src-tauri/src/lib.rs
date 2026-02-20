use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // In production, launch the sidecar binary.
            // In dev, the Python backend is started manually.
            if !cfg!(debug_assertions) {
                let sidecar_command = app
                    .handle()
                    .shell()
                    .sidecar("vibetaff-backend")
                    .expect("failed to create sidecar command");

                let (mut rx, _child) = sidecar_command
                    .spawn()
                    .expect("Failed to spawn backend sidecar");

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
                            _ => {}
                        }
                    }
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
