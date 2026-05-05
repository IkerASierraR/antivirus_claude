/// scan_engine/src/lib.rs
/// 
/// RustGuard - High-Performance Antivirus Scan Engine
/// 
/// Exposes Python bindings via PyO3. Responsible for:
///   - SHA-256 / MD5 hash computation
///   - Signature database lookup (SQLite)
///   - Multi-layer heuristic analysis
///   - Directory traversal with real-time progress callbacks
///   - Thread-safe cancellation via AtomicBool

use pyo3::prelude::*;
use pyo3::exceptions::{PyRuntimeError, PyIOError};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::path::Path;
use std::fs;
use std::io::Read;
use sha2::{Sha256, Digest};
use md5::Md5;
use hex;
use walkdir::WalkDir;
use rusqlite::{Connection, OpenFlags, params};
use regex::Regex;
use serde::{Deserialize, Serialize};

// ────────────────────────────────────────────────
//  Data Structures (mirrored in Python domain layer)
// ────────────────────────────────────────────────

/// Result for a single scanned file
#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileScanResult {
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub sha256: String,
    #[pyo3(get)]
    pub md5: String,
    #[pyo3(get)]
    pub is_threat: bool,
    #[pyo3(get)]
    pub threat_name: String,
    #[pyo3(get)]
    pub detection_method: String, // "signature" | "heuristic" | "clean"
    #[pyo3(get)]
    pub file_size: u64,
    #[pyo3(get)]
    pub error: String,           // empty string if no error
}

#[pymethods]
impl FileScanResult {
    fn __repr__(&self) -> String {
        format!(
            "FileScanResult(path='{}', threat={}, method='{}', error='{}')",
            self.path, self.is_threat, self.detection_method, self.error
        )
    }
}

/// Summary returned after a full scan
#[pyclass]
#[derive(Debug, Clone)]
pub struct ScanSummary {
    #[pyo3(get)]
    pub total_files: u64,
    #[pyo3(get)]
    pub threats_found: u64,
    #[pyo3(get)]
    pub skipped_files: u64,   // permission errors, locked files, etc.
    #[pyo3(get)]
    pub was_cancelled: bool,
    #[pyo3(get)]
    pub threats: Vec<FileScanResult>,
}

#[pymethods]
impl ScanSummary {
    fn __repr__(&self) -> String {
        format!(
            "ScanSummary(total={}, threats={}, skipped={}, cancelled={})",
            self.total_files, self.threats_found, self.skipped_files, self.was_cancelled
        )
    }
}

// ────────────────────────────────────────────────
//  Cancellation Token (Thread-Safe)
// ────────────────────────────────────────────────

/// Shared cancellation flag that Python can set from the UI thread.
/// Rust's scan loop checks this on every iteration for clean stop.
#[pyclass]
pub struct CancellationToken {
    flag: Arc<AtomicBool>,
}

#[pymethods]
impl CancellationToken {
    #[new]
    pub fn new() -> Self {
        CancellationToken {
            flag: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Called by Python UI when user clicks "Cancel"
    pub fn cancel(&self) {
        self.flag.store(true, Ordering::SeqCst);
    }

    /// Reset for a new scan session
    pub fn reset(&self) {
        self.flag.store(false, Ordering::SeqCst);
    }

    pub fn is_cancelled(&self) -> bool {
        self.flag.load(Ordering::SeqCst)
    }
}

// ────────────────────────────────────────────────
//  Signature Database Manager
// ────────────────────────────────────────────────

struct SignatureDb {
    conn: Connection,
}

impl SignatureDb {
    /// Open or create the SQLite signature database
    fn open(db_path: &str) -> Result<Self, rusqlite::Error> {
        let conn = Connection::open_with_flags(
            db_path,
            OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
        )
        .or_else(|_| {
            // DB doesn't exist yet — create it with schema
            let c = Connection::open(db_path)?;
            c.execute_batch(
                "CREATE TABLE IF NOT EXISTS signatures (
                    id       INTEGER PRIMARY KEY,
                    sha256   TEXT UNIQUE NOT NULL,
                    md5      TEXT,
                    name     TEXT NOT NULL,
                    severity TEXT DEFAULT 'medium'
                );
                CREATE INDEX IF NOT EXISTS idx_sha256 ON signatures(sha256);
                CREATE INDEX IF NOT EXISTS idx_md5    ON signatures(md5);",
            )?;
            Ok::<_, rusqlite::Error>(c)
        })?;
        Ok(SignatureDb { conn })
    }

    /// Look up by SHA-256; returns (threat_name, severity) or None
    fn lookup_sha256(&self, hash: &str) -> Option<(String, String)> {
        self.conn
            .query_row(
                "SELECT name, severity FROM signatures WHERE sha256 = ?1",
                params![hash],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .ok()
    }

    /// Look up by MD5 as fallback
    fn lookup_md5(&self, hash: &str) -> Option<(String, String)> {
        self.conn
            .query_row(
                "SELECT name, severity FROM signatures WHERE md5 = ?1",
                params![hash],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .ok()
    }
}

// ────────────────────────────────────────────────
//  Hash Computation
// ────────────────────────────────────────────────

/// Compute SHA-256 and MD5 simultaneously (single file read)
fn compute_hashes(path: &Path) -> Result<(String, String), std::io::Error> {
    let mut file = fs::File::open(path)?;
    let mut sha256_hasher = Sha256::new();
    let mut md5_hasher = Md5::new();
    let mut buffer = [0u8; 65536]; // 64 KB chunks

    loop {
        let n = file.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        sha256_hasher.update(&buffer[..n]);
        md5_hasher.update(&buffer[..n]);
    }

    let sha256 = hex::encode(sha256_hasher.finalize());
    let md5 = hex::encode(md5_hasher.finalize());
    Ok((sha256, md5))
}

// ────────────────────────────────────────────────
//  Heuristic Analysis Engine
// ────────────────────────────────────────────────

struct HeuristicEngine {
    double_ext_pattern: Regex,
    suspicious_exts: Vec<String>,
}

impl HeuristicEngine {
    fn new() -> Self {
        // Pattern: file.pdf.exe, file.txt.bat, document.docx.vbs, etc.
        let double_ext = Regex::new(
            r"(?i)\.(pdf|doc|docx|txt|jpg|png|zip|rar)\.(exe|bat|cmd|vbs|ps1|scr|pif|com|lnk|jar|msi)$"
        ).expect("Invalid heuristic regex");

        HeuristicEngine {
            double_ext_pattern: double_ext,
            suspicious_exts: vec![
                ".exe".into(), ".bat".into(), ".cmd".into(), ".vbs".into(),
                ".ps1".into(), ".scr".into(), ".pif".into(), ".com".into(),
                ".lnk".into(), ".jar".into(), ".msi".into(), ".hta".into(),
                ".js".into(),  ".jse".into(), ".wsf".into(), ".wsh".into(),
            ],
        }
    }

    /// Returns (is_suspicious, reason_string)
    fn analyze(&self, path: &Path, file_size: u64, metadata: &fs::Metadata) -> (bool, String) {
        let filename = path.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("");
        let path_str = path.to_string_lossy();

        // Rule 1: Double extension (high confidence)
        if self.double_ext_pattern.is_match(filename) {
            return (true, format!("Double extension attack: {}", filename));
        }

        // Rule 2: Hidden file with executable extension (Windows-style)
        if filename.starts_with('.') {
            let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
            let ext_with_dot = format!(".{}", ext.to_lowercase());
            if self.suspicious_exts.contains(&ext_with_dot) {
                return (true, format!("Hidden executable: {}", filename));
            }
        }

        // Rule 3: Suspiciously large hidden file (> 50 MB) in temp or appdata
        #[cfg(target_os = "windows")]
        let sensitive_dirs = [r"\Temp\", r"\AppData\Local\Temp\", r"\Windows\Temp\"];
        #[cfg(not(target_os = "windows"))]
        let sensitive_dirs = ["/tmp/", "/var/tmp/", "/dev/shm/"];

        let in_sensitive = sensitive_dirs.iter().any(|d| path_str.contains(d));
        if in_sensitive && file_size > 52_428_800 {  // 50 MB
            let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
            let ext_with_dot = format!(".{}", ext.to_lowercase());
            if self.suspicious_exts.contains(&ext_with_dot) {
                return (
                    true,
                    format!(
                        "Large executable in temp dir: {} ({} MB)",
                        filename,
                        file_size / 1_048_576
                    ),
                );
            }
        }

        // Rule 4: Zero-byte executable (dropper placeholder)
        if file_size == 0 {
            let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
            let ext_with_dot = format!(".{}", ext.to_lowercase());
            if self.suspicious_exts.contains(&ext_with_dot) {
                return (true, format!("Zero-byte executable: {}", filename));
            }
        }

        // Rule 5: Executable in unusual location (user home temp/cache)
        #[cfg(target_os = "windows")]
        let user_suspicious = [r"\AppData\Roaming\", r"\AppData\Local\"];
        #[cfg(not(target_os = "windows"))]
        let user_suspicious = ["/.local/share/", "/.cache/"];

        let in_user_suspicious = user_suspicious.iter().any(|d| path_str.contains(d));
        if in_user_suspicious {
            let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
            if ext.eq_ignore_ascii_case("exe") || ext.eq_ignore_ascii_case("scr") {
                return (
                    true,
                    format!("Executable in user data directory: {}", filename),
                );
            }
        }

        (false, String::new())
    }
}

// ────────────────────────────────────────────────
//  Core Scan Functions (exported to Python)
// ────────────────────────────────────────────────

/// Scan a single file. Returns a FileScanResult.
/// `db_path`: path to the SQLite signatures database
#[pyfunction]
pub fn scan_file(path: String, db_path: String) -> PyResult<FileScanResult> {
    let file_path = Path::new(&path);

    // Gather metadata safely
    let metadata = match fs::metadata(file_path) {
        Ok(m) => m,
        Err(e) => {
            return Ok(FileScanResult {
                path,
                sha256: String::new(),
                md5: String::new(),
                is_threat: false,
                threat_name: String::new(),
                detection_method: "error".into(),
                file_size: 0,
                error: format!("Cannot read metadata: {}", e),
            });
        }
    };

    let file_size = metadata.len();

    // Compute hashes
    let (sha256, md5) = match compute_hashes(file_path) {
        Ok(h) => h,
        Err(e) => {
            return Ok(FileScanResult {
                path,
                sha256: String::new(),
                md5: String::new(),
                is_threat: false,
                threat_name: String::new(),
                detection_method: "error".into(),
                file_size,
                error: format!("Cannot read file: {}", e),
            });
        }
    };

    // Signature lookup
    if let Ok(db) = SignatureDb::open(&db_path) {
        if let Some((name, _severity)) = db.lookup_sha256(&sha256) {
            return Ok(FileScanResult {
                path,
                sha256,
                md5,
                is_threat: true,
                threat_name: name,
                detection_method: "signature".into(),
                file_size,
                error: String::new(),
            });
        }
        if let Some((name, _severity)) = db.lookup_md5(&md5) {
            return Ok(FileScanResult {
                path,
                sha256,
                md5,
                is_threat: true,
                threat_name: name,
                detection_method: "signature_md5".into(),
                file_size,
                error: String::new(),
            });
        }
    }

    // Heuristic analysis
    let heuristic = HeuristicEngine::new();
    let (suspicious, reason) = heuristic.analyze(file_path, file_size, &metadata);
    if suspicious {
        return Ok(FileScanResult {
            path,
            sha256,
            md5,
            is_threat: true,
            threat_name: format!("Heuristic.{}", reason),
            detection_method: "heuristic".into(),
            file_size,
            error: String::new(),
        });
    }

    // Clean
    Ok(FileScanResult {
        path,
        sha256,
        md5,
        is_threat: false,
        threat_name: String::new(),
        detection_method: "clean".into(),
        file_size,
        error: String::new(),
    })
}

/// Scan an entire directory tree.
/// 
/// # Arguments
/// * `root_path`     - Directory to scan
/// * `db_path`       - SQLite signatures DB path
/// * `token`         - CancellationToken (Python object)
/// * `callback`      - Python callable(current_path: str, scanned: int, total: int)
///                     called for each file — enables real-time UI updates
#[pyfunction]
pub fn scan_directory(
    py: Python<'_>,
    root_path: String,
    db_path: String,
    token: &CancellationToken,
    callback: PyObject,
) -> PyResult<ScanSummary> {
    // Reset the cancellation flag for this run
    token.reset();

    // Open signature DB once (reused for all files)
    let sig_db_result = SignatureDb::open(&db_path);
    let heuristic = HeuristicEngine::new();

    // First pass: count files for accurate progress bar
    let total_files: u64 = WalkDir::new(&root_path)
        .follow_links(false)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .count() as u64;

    let mut scanned: u64 = 0;
    let mut skipped: u64 = 0;
    let mut threats: Vec<FileScanResult> = Vec::new();

    // Second pass: actual scan
    for entry in WalkDir::new(&root_path)
        .follow_links(false)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
    {
        // Check cancellation on every file
        if token.is_cancelled() {
            return Ok(ScanSummary {
                total_files: scanned,
                threats_found: threats.len() as u64,
                skipped_files: skipped,
                was_cancelled: true,
                threats,
            });
        }

        let path_str = entry.path().to_string_lossy().to_string();
        scanned += 1;

        // Fire real-time progress callback to Python (releases GIL briefly)
        let cb_result: PyResult<()> = py.allow_threads(|| Ok(())).and_then(|_| {
            callback.call1(py, (path_str.clone(), scanned, total_files))?;
            Ok(())
        });
        // Non-fatal: if callback fails (e.g., widget destroyed), continue
        if cb_result.is_err() {
            // UI may have been closed; respect cancellation
            token.cancel();
            break;
        }

        // --- Metadata ---
        let metadata = match fs::metadata(entry.path()) {
            Ok(m) => m,
            Err(_) => {
                skipped += 1;
                continue;
            }
        };
        let file_size = metadata.len();

        // --- Hash computation ---
        let (sha256, md5) = match compute_hashes(entry.path()) {
            Ok(h) => h,
            Err(_) => {
                skipped += 1;
                continue;
            }
        };

        // --- Signature check ---
        let mut found_threat: Option<(String, String)> = None;

        if let Ok(ref db) = sig_db_result {
            if let Some(hit) = db.lookup_sha256(&sha256) {
                found_threat = Some((hit.0, "signature".into()));
            } else if let Some(hit) = db.lookup_md5(&md5) {
                found_threat = Some((hit.0, "signature_md5".into()));
            }
        }

        // --- Heuristic check (only if signature didn't trigger) ---
        if found_threat.is_none() {
            let (suspicious, reason) = heuristic.analyze(entry.path(), file_size, &metadata);
            if suspicious {
                found_threat = Some((
                    format!("Heuristic.{}", reason),
                    "heuristic".into(),
                ));
            }
        }

        if let Some((threat_name, method)) = found_threat {
            threats.push(FileScanResult {
                path: path_str,
                sha256,
                md5,
                is_threat: true,
                threat_name,
                detection_method: method,
                file_size,
                error: String::new(),
            });
        }
    }

    Ok(ScanSummary {
        total_files: scanned,
        threats_found: threats.len() as u64,
        skipped_files: skipped,
        was_cancelled: token.is_cancelled(),
        threats,
    })
}

/// Import signatures from a JSON file into the SQLite database.
/// JSON format: [{"sha256": "...", "md5": "...", "name": "...", "severity": "high"}, ...]
#[pyfunction]
pub fn import_signatures_json(json_path: String, db_path: String) -> PyResult<u64> {
    let content = fs::read_to_string(&json_path)
        .map_err(|e| PyIOError::new_err(format!("Cannot read JSON: {}", e)))?;

    #[derive(Deserialize)]
    struct SigEntry {
        sha256: Option<String>,
        md5: Option<String>,
        name: String,
        severity: Option<String>,
    }

    let entries: Vec<SigEntry> = serde_json::from_str(&content)
        .map_err(|e| PyRuntimeError::new_err(format!("Invalid JSON: {}", e)))?;

    let conn = Connection::open(&db_path)
        .map_err(|e| PyRuntimeError::new_err(format!("Cannot open DB: {}", e)))?;

    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS signatures (
            id       INTEGER PRIMARY KEY,
            sha256   TEXT UNIQUE,
            md5      TEXT,
            name     TEXT NOT NULL,
            severity TEXT DEFAULT 'medium'
        );
        CREATE INDEX IF NOT EXISTS idx_sha256 ON signatures(sha256);
        CREATE INDEX IF NOT EXISTS idx_md5    ON signatures(md5);",
    )
    .map_err(|e| PyRuntimeError::new_err(format!("DB schema error: {}", e)))?;

    let mut imported: u64 = 0;
    for entry in &entries {
        if entry.sha256.is_none() && entry.md5.is_none() {
            continue;
        }
        let result = conn.execute(
            "INSERT OR IGNORE INTO signatures (sha256, md5, name, severity)
             VALUES (?1, ?2, ?3, ?4)",
            params![
                entry.sha256,
                entry.md5,
                entry.name,
                entry.severity.as_deref().unwrap_or("medium")
            ],
        );
        if result.is_ok() {
            imported += 1;
        }
    }

    Ok(imported)
}

/// Returns basic file info without scanning (for UI preview)
#[pyfunction]
pub fn get_file_info(path: String) -> PyResult<FileScanResult> {
    let file_path = Path::new(&path);
    let metadata = fs::metadata(file_path)
        .map_err(|e| PyIOError::new_err(format!("{}", e)))?;

    let (sha256, md5) = compute_hashes(file_path)
        .map_err(|e| PyIOError::new_err(format!("{}", e)))?;

    Ok(FileScanResult {
        path,
        sha256,
        md5,
        is_threat: false,
        threat_name: String::new(),
        detection_method: "info_only".into(),
        file_size: metadata.len(),
        error: String::new(),
    })
}

// ────────────────────────────────────────────────
//  Module Registration
// ────────────────────────────────────────────────

#[pymodule]
fn scan_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<FileScanResult>()?;
    m.add_class::<ScanSummary>()?;
    m.add_class::<CancellationToken>()?;
    m.add_function(wrap_pyfunction!(scan_file, m)?)?;
    m.add_function(wrap_pyfunction!(scan_directory, m)?)?;
    m.add_function(wrap_pyfunction!(import_signatures_json, m)?)?;
    m.add_function(wrap_pyfunction!(get_file_info, m)?)?;
    Ok(())
}
