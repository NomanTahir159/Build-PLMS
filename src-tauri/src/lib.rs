mod backend;
use serde::Serialize;
use std::fs;
use std::path::PathBuf;
use tauri::{AppHandle, Manager, WebviewWindow, Theme};
use tauri::window::Color;
use std::sync::atomic::{AtomicBool, Ordering};

#[derive(Default)]
struct StartupState { revealed: AtomicBool }

#[derive(Serialize)]
struct StoragePaths { root: String, data: String, backups: String, templates: String, catalog: String, logs: String, resources: String, system: String, office: String, exports: String }

fn storage_root(app: &AppHandle) -> Result<PathBuf, String> {
    if cfg!(debug_assertions) { return app.path().app_data_dir().map(|p| p.join("Development")).map_err(|e| e.to_string()); }
    #[cfg(windows)] { return std::env::var_os("PROGRAMDATA").map(|p| PathBuf::from(p).join("Medicsoft PLMS")).ok_or_else(|| "Windows ProgramData is unavailable".into()); }
    #[cfg(not(windows))] { app.path().app_data_dir().map_err(|e| e.to_string()) }
}
fn ensure_storage(app: &AppHandle) -> Result<StoragePaths, String> {
    let root=storage_root(app)?;
    for folder in ["Root", "Root/EBWebView", "Root/Temp", "Backup", "Catalog", "Database", "Log", "Presets", "Presets/Word"] {
        fs::create_dir_all(root.join(folder)).map_err(|e| format!("Could not create {folder}: {e}"))?;
    }
    let installed=app.path().resource_dir().map_err(|e| e.to_string())?;
    Ok(StoragePaths { root:root.display().to_string(), data:root.join("Database").display().to_string(), backups:root.join("Backup").display().to_string(), templates:root.join("Presets").display().to_string(),catalog:root.join("Catalog").display().to_string(),logs:root.join("Log").display().to_string(),resources:installed.join("Resources").display().to_string(),system:installed.join("System").display().to_string(),office:root.join("Presets/Word").display().to_string(),exports:root.join("Backup").display().to_string() })
}

#[tauri::command]
fn plms_window_action(window: WebviewWindow, action: String) -> Result<(), String> {
    if window.label()!="main" { return Err("Unexpected window".into()); }
    match action.as_str() {
        "minimize" => window.minimize(),
        "maximize" => if window.is_maximized().map_err(|e| e.to_string())? { window.unmaximize() } else { window.maximize() },
        "drag" => window.start_dragging(),
        "close" => window.destroy(),
        _ => return Err("Unsupported window action".into())
    }.map_err(|e| e.to_string())
}

#[tauri::command]
fn plms_storage_paths(app: AppHandle) -> Result<StoragePaths, String> {
    ensure_storage(&app)
}

fn set_window_background(window: &WebviewWindow, dark: bool, system: Option<bool>) -> Result<(), String> {
    if window.label() != "main" { return Err("Unexpected PLMS window".into()); }
    window.set_theme(if system.unwrap_or(false) { None } else { Some(if dark { Theme::Dark } else { Theme::Light }) }).map_err(|e| e.to_string())?;
    let color = if dark { Color(15, 22, 33, 255) } else { Color(243, 246, 251, 255) };
    window.set_background_color(Some(color)).map_err(|e| e.to_string())
}

#[tauri::command]
fn plms_window_background(window: WebviewWindow, dark: bool, system: Option<bool>) -> Result<(), String> {
    set_window_background(&window, dark, system)
}

#[tauri::command]
fn plms_frontend_ready(window: WebviewWindow, dark: bool, system: Option<bool>, startup: tauri::State<'_, StartupState>) -> Result<(), String> {
    set_window_background(&window, dark, system)?;
    if !startup.revealed.load(Ordering::SeqCst) {
        window.show().map_err(|e| e.to_string())?;
        startup.revealed.store(true, Ordering::SeqCst);
        window.set_focus().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(StartupState::default())
        .setup(|app| {
            if let Err(err) = ensure_storage(app.handle()) {
                eprintln!("PLMS storage initialization warning: {err}");
            }

            app.manage(backend::NativeBackend::start(app.handle()).map_err(std::io::Error::other)?);
            let data=storage_root(app.handle()).map_err(std::io::Error::other)?;
            tauri::WebviewWindowBuilder::from_config(app.handle(), &app.config().app.windows[0])?
                .data_directory(data.join("Root/EBWebView"))
                .build()?;

            // Maximize while hidden; frontend readiness owns normal reveal.
            if let Some(main) = app.get_webview_window("main") {
                let _ = main.maximize();
            }
            // Recovery only: avoid leaving an inaccessible hidden process if
            // frontend initialization fails. Normal startup never uses this.
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                std::thread::sleep(std::time::Duration::from_secs(20));
                let scheduler = handle.clone();
                let _ = scheduler.run_on_main_thread(move || {
                    if !handle.state::<StartupState>().revealed.swap(true, Ordering::SeqCst) {
                        eprintln!("PLMS startup readiness timed out; revealing recovery window");
                        if let Some(main) = handle.get_webview_window("main") {
                            let _ = main.show();
                            let _ = main.set_focus();
                        }
                    }
                });
            });

            Ok(())
        })
        .on_window_event(|window,event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                if let Some(view)=window.app_handle().get_webview_window("main") { let _ = view.eval("window.plmsDesktopRequestClose && window.plmsDesktopRequestClose()"); }
            }
        })
        .invoke_handler(tauri::generate_handler![backend::plms_backend, plms_storage_paths, plms_frontend_ready, plms_window_background, plms_window_action])
        .run(tauri::generate_context!())
        .expect("error while running PLMS");
}
