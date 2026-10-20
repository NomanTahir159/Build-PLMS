use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::Mutex;
use serde_json::Value;
use tauri::{AppHandle, Manager, WebviewWindow};

pub struct Worker { child: Child, input: ChildStdin, output: BufReader<ChildStdout> }
impl Drop for Worker { fn drop(&mut self) { let _ = self.child.kill(); let _ = self.child.wait(); } }
pub struct NativeBackend(pub Mutex<Worker>);
impl NativeBackend {
    pub fn start(app: &AppHandle) -> Result<Self, String> {
        let db = super::storage_root(app)?.join("Database").join("plms.sqlite3");
        let mut command = if cfg!(debug_assertions) {
            let mut c = Command::new(if cfg!(windows) { "python" } else { "python3" });
            c.arg(std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../backend/server.py")); c
        } else {
            Command::new(app.path().resource_dir().map_err(|_| "Backend resources unavailable")?.join("Root/plms-backend.exe"))
        };
        command.env("TMP", super::storage_root(app)?.join("Root/Temp")).env("TEMP", super::storage_root(app)?.join("Root/Temp"));
        let log = std::fs::OpenOptions::new().create(true).append(true).open(super::storage_root(app)?.join("Log/diagnostics.log")).map_err(|e| e.to_string())?;
        command.arg(db).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::from(log));
        #[cfg(windows)] { use std::os::windows::process::CommandExt; command.creation_flags(0x08000000); }
        let mut child = command.spawn().map_err(|_| "The PLMS database worker could not start")?;
        let input = child.stdin.take().ok_or("Backend input unavailable")?;
        let output = BufReader::new(child.stdout.take().ok_or("Backend output unavailable")?);
        Ok(Self(Mutex::new(Worker { child, input, output })))
    }
}
#[tauri::command]
pub async fn plms_backend(window: WebviewWindow, backend: tauri::State<'_, NativeBackend>, request: Value) -> Result<Value, String> {
    if window.label() != "main" { return Err("Unexpected application window".into()); }
    let url = window.url().map_err(|_| "Window origin unavailable")?;
    let trusted = url.scheme() == "tauri" || ((url.scheme() == "http" || url.scheme() == "https") && url.host_str() == Some("tauri.localhost"));
    if !trusted { return Err("Untrusted application origin".into()); }
    let payload = serde_json::to_vec(&request).map_err(|_| "Invalid request")?;
    if payload.len() > 64 * 1024 * 1024 { return Err("Request is too large".into()); }
    let mut worker = backend.0.lock().map_err(|_| "Database worker unavailable")?;
    worker.input.write_all(&payload).and_then(|_| worker.input.write_all(b"\n")).and_then(|_| worker.input.flush()).map_err(|_| "Database connection closed")?;
    let mut line = String::new();
    worker.output.read_line(&mut line).map_err(|_| "Database response failed")?;
    if line.is_empty() || line.len() > 128 * 1024 * 1024 { return Err("Database response unavailable".into()); }
    serde_json::from_str(&line).map_err(|_| "Invalid database response".into())
}
