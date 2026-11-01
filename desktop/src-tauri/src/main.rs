// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::Command;

const ALLOWED_SUBCOMMANDS: &[&str] = &[
    "scan", "preview", "organize", "undo", "history", "status", "config"
];

const ALLOWED_FLAGS: &[&str] = &[
    "--json", "--dry-run", "--recursive", "--quiet", "--limit", "--all"
];

fn is_safe_arg(arg: &str) -> bool {
    if arg.len() > 128 {
        return false;
    }
    // Reject shell metacharacters and control characters
    for ch in arg.chars() {
        if ch.is_control() || "&|;`$><\r\n\t".contains(ch) {
            return false;
        }
    }
    true
}

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

    // Additional argument validation: only allow known flags or numeric values
    for arg in &args[1..] {
        let is_flag = ALLOWED_FLAGS.contains(&arg.as_str());
        let is_num = arg.parse::<u32>().is_ok();
        if !is_flag && !is_num {
            return Err(format!("Unrecognized or forbidden argument flag: {}", arg));
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

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![run_cleandownloads_cmd])
        .run(tauri::generate_context!())
        .expect("error while running CleanDownloads desktop application");
}
