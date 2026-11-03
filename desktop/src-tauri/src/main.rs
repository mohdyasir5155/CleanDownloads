// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use tauri::{
    menu::{MenuBuilder, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, Manager, WindowEvent,
};
use tauri_plugin_notification::NotificationExt;

// ─── Close-to-tray toggle (controlled from Settings) ───────────────────
static CLOSE_TO_TRAY: AtomicBool = AtomicBool::new(true);

// ─── CLI safety layer ──────────────────────────────────────────────────
const ALLOWED_SUBCOMMANDS: &[&str] = &[
    "scan", "preview", "organize", "undo", "history", "status", "config",
];

const ALLOWED_FLAGS: &[&str] = &[
    "--json", "--dry-run", "--recursive", "--quiet", "--limit", "--all",
    "--batch-id",
];

fn is_safe_arg(arg: &str) -> bool {
    if arg.len() > 256 {
        return false;
    }
    for ch in arg.chars() {
        if ch.is_control() || "&|;`$><\r\n\t".contains(ch) {
            return false;
        }
    }
    true
}

// ─── Tauri IPC Commands ────────────────────────────────────────────────

#[tauri::command]
fn run_cleandownloads_cmd(args: Vec<String>) -> Result<String, String> {
    if args.is_empty() || args.len() > 10 {
        return Err("Invalid number of arguments".into());
    }

    let subcommand = &args[0];
    if !ALLOWED_SUBCOMMANDS.contains(&subcommand.as_str()) {
        return Err(format!("Unauthorized subcommand: {}", subcommand));
    }

    for arg in &args {
        if !is_safe_arg(arg) {
            return Err("Argument contains invalid characters or exceeds maximum length".into());
        }
    }

    // Additional argument validation: only allow known flags, uuid-like values, or numbers
    for arg in &args[1..] {
        let is_flag = ALLOWED_FLAGS.contains(&arg.as_str());
        let is_num = arg.parse::<u32>().is_ok();
        let is_uuid = arg.len() <= 64
            && arg
                .chars()
                .all(|c| c.is_ascii_alphanumeric() || c == '-');
        if !is_flag && !is_num && !is_uuid {
            return Err(format!("Unrecognized or forbidden argument: {}", arg));
        }
    }

    let output = Command::new("cleandownloads")
        .args(&args)
        .output()
        .map_err(|e| format!("Failed to execute cleandownloads: {}", e))?;

    if output.status.success() {
        String::from_utf8(output.stdout)
            .map_err(|e| format!("Invalid UTF-8 output: {}", e))
    } else {
        let err = String::from_utf8_lossy(&output.stderr);
        Err(format!("Command failed: {}", err))
    }
}

/// Toggle close-to-tray behavior from the frontend
#[tauri::command]
fn set_close_to_tray(enabled: bool) {
    CLOSE_TO_TRAY.store(enabled, Ordering::Relaxed);
}

/// Get current close-to-tray state
#[tauri::command]
fn get_close_to_tray() -> bool {
    CLOSE_TO_TRAY.load(Ordering::Relaxed)
}

/// Send a native Windows notification from the frontend
#[tauri::command]
fn send_notification(app: tauri::AppHandle, title: String, body: String) -> Result<(), String> {
    app.notification()
        .builder()
        .title(&title)
        .body(&body)
        .show()
        .map_err(|e| format!("Notification failed: {}", e))
}

/// Run a scan and return results, also sends a notification
#[tauri::command]
fn scan_and_notify(app: tauri::AppHandle) -> Result<String, String> {
    let result = run_cleandownloads_cmd(vec!["scan".into(), "--json".into()]);

    match &result {
        Ok(json_str) => {
            // Parse scan result to get file count for notification
            if let Ok(scan_data) = serde_json::from_str::<serde_json::Value>(json_str) {
                let total = scan_data
                    .get("total_ready")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0);

                let body = if total == 0 {
                    "Your Downloads folder is already clean. Zero clutter!".to_string()
                } else {
                    format!(
                        "Scan complete. {} file{} ready to organize.",
                        total,
                        if total == 1 { " is" } else { "s are" }
                    )
                };

                let _ = app
                    .notification()
                    .builder()
                    .title("CleanDownloads")
                    .body(&body)
                    .show();
            }
        }
        Err(e) => {
            let _ = app
                .notification()
                .builder()
                .title("CleanDownloads — Scan Failed")
                .body(&format!("Could not scan Downloads: {}", e))
                .show();
        }
    }

    result
}

/// Run organize and return results, also sends a notification
#[tauri::command]
fn organize_and_notify(app: tauri::AppHandle, dry_run: bool) -> Result<String, String> {
    let mut args = vec!["organize".to_string(), "--json".to_string()];
    if dry_run {
        args.push("--dry-run".to_string());
    }

    let result = run_cleandownloads_cmd(args);

    match &result {
        Ok(json_str) => {
            if let Ok(org_data) = serde_json::from_str::<serde_json::Value>(json_str) {
                let success = org_data
                    .get("successful_moves")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0);
                let failed = org_data
                    .get("failed_moves")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0);

                if dry_run {
                    let _ = app
                        .notification()
                        .builder()
                        .title("CleanDownloads — Dry Run")
                        .body(&format!("{} files would be organized.", success))
                        .show();
                } else if failed == 0 {
                    let _ = app
                        .notification()
                        .builder()
                        .title("Organization Complete")
                        .body(&format!(
                            "{} file{} successfully organized. Zero clutter!",
                            success,
                            if success == 1 { " was" } else { "s were" }
                        ))
                        .show();
                } else {
                    let _ = app
                        .notification()
                        .builder()
                        .title("Organization Complete — With Errors")
                        .body(&format!(
                            "{} files organized, {} failed to move.",
                            success, failed
                        ))
                        .show();
                }
            }
        }
        Err(e) => {
            let _ = app
                .notification()
                .builder()
                .title("CleanDownloads — Organization Failed")
                .body(&format!("Could not organize files: {}", e))
                .show();
        }
    }

    result
}

/// Undo a batch and notify
#[tauri::command]
fn undo_and_notify(app: tauri::AppHandle, batch_id: Option<String>) -> Result<String, String> {
    let mut args = vec!["undo".to_string()];
    if let Some(id) = &batch_id {
        args.push("--batch-id".to_string());
        args.push(id.clone());
    }
    args.push("--json".to_string());

    let result = run_cleandownloads_cmd(args);

    match &result {
        Ok(_) => {
            let _ = app
                .notification()
                .builder()
                .title("CleanDownloads — Undo Complete")
                .body("Files have been restored to their original locations.")
                .show();
        }
        Err(e) => {
            let _ = app
                .notification()
                .builder()
                .title("CleanDownloads — Undo Failed")
                .body(&format!("Could not undo: {}", e))
                .show();
        }
    }

    result
}

/// Open the user's Downloads folder in Windows File Explorer
#[tauri::command]
fn open_downloads_folder() -> Result<(), String> {
    if let Some(user_dirs) = dirs_next() {
        let downloads = user_dirs;
        Command::new("explorer")
            .arg(&downloads)
            .spawn()
            .map_err(|e| format!("Failed to open folder: {}", e))?;
        Ok(())
    } else {
        Command::new("explorer")
            .arg("shell:Downloads")
            .spawn()
            .map_err(|e| format!("Failed to open folder: {}", e))?;
        Ok(())
    }
}

fn dirs_next() -> Option<String> {
    std::env::var("USERPROFILE").ok().map(|p| format!("{}\\Downloads", p))
}

// ─── Helper: show + focus main window ──────────────────────────────────

fn show_main_window(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.set_focus();
    }
}

// ─── Application entry point ───────────────────────────────────────────

fn main() {
    tauri::Builder::default()
        // ── Single instance (MUST be first plugin) ─────────────
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            // If user tries to relaunch, just focus the existing window
            show_main_window(app);
        }))
        // ── Notifications ──────────────────────────────────────
        .plugin(tauri_plugin_notification::init())
        // ── Application setup ──────────────────────────────────
        .setup(|app| {
            // ── Build tray context menu ────────────────────────
            let open_item =
                MenuItem::with_id(app, "open", "Open CleanDownloads", true, None::<&str>)?;
            let sep1 = PredefinedMenuItem::separator(app)?;
            let scan_item =
                MenuItem::with_id(app, "scan", "Scan Downloads", true, None::<&str>)?;
            let preview_item =
                MenuItem::with_id(app, "preview", "Preview Organization", true, None::<&str>)?;
            let organize_item =
                MenuItem::with_id(app, "organize", "Organize Now", true, None::<&str>)?;
            let folder_item =
                MenuItem::with_id(app, "folder", "Open Downloads Folder", true, None::<&str>)?;
            let sep2 = PredefinedMenuItem::separator(app)?;
            let settings_item =
                MenuItem::with_id(app, "settings", "Settings", true, None::<&str>)?;
            let sep3 = PredefinedMenuItem::separator(app)?;
            let exit_item =
                MenuItem::with_id(app, "exit", "Exit CleanDownloads", true, None::<&str>)?;

            let tray_menu = MenuBuilder::new(app)
                .items(&[
                    &open_item,
                    &sep1,
                    &scan_item,
                    &preview_item,
                    &organize_item,
                    &folder_item,
                    &sep2,
                    &settings_item,
                    &sep3,
                    &exit_item,
                ])
                .build()?;

            // ── Build tray icon ────────────────────────────────
            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("CleanDownloads — One command. Zero clutter.")
                .menu(&tray_menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app_handle, event| {
                    match event.id().as_ref() {
                        "open" => {
                            show_main_window(app_handle);
                        }
                        "scan" => {
                            show_main_window(app_handle);
                            // Emit event to frontend to trigger scan
                            let _ = app_handle.emit("tray-action", "scan");
                        }
                        "preview" => {
                            show_main_window(app_handle);
                            let _ = app_handle.emit("tray-action", "preview");
                        }
                        "organize" => {
                            show_main_window(app_handle);
                            let _ = app_handle.emit("tray-action", "organize");
                        }
                        "folder" => {
                            let _ = open_downloads_folder();
                        }
                        "settings" => {
                            show_main_window(app_handle);
                            let _ = app_handle.emit("tray-action", "settings");
                        }
                        "exit" => {
                            // Full application exit — remove tray, close all windows
                            app_handle.exit(0);
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    // Left-click: show/focus the main window
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        show_main_window(app);
                    }
                })
                .build(app)?;

            Ok(())
        })
        // ── Close-to-tray behavior ─────────────────────────────
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                if CLOSE_TO_TRAY.load(Ordering::Relaxed) {
                    // Hide instead of closing — app stays in system tray
                    let _ = window.hide();
                    api.prevent_close();
                }
                // If close_to_tray is false, allow normal close/exit
            }
        })
        // ── Register IPC commands ──────────────────────────────
        .invoke_handler(tauri::generate_handler![
            run_cleandownloads_cmd,
            set_close_to_tray,
            get_close_to_tray,
            send_notification,
            scan_and_notify,
            organize_and_notify,
            undo_and_notify,
            open_downloads_folder,
        ])
        .run(tauri::generate_context!())
        .expect("error while running CleanDownloads desktop application");
}
