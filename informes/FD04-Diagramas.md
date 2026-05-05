<center>

![./media/logo-upt.png](./media/logo-upt.png)

**UNIVERSIDAD PRIVADA DE TACNA**

**FACULTAD DE INGENIERIA**

**Escuela Profesional de Ingeniería de Sistemas**

**Proyecto RustGuard — Diagramas de Ingeniería Inversa**

Curso: *Calidad y Pruebas de Software*

Docente: *Mag. Patrick Cuadros Quiroga*

Integrantes:

***LLica Mamani, Jimmy Mijair (2023076789)***

***Sierra Ruiz, Iker Alberto (2023077090)***

**Tacna – Perú**

***2026***

</center>

<div style="page-break-after: always; visibility: hidden"></div>

Sistema *RustGuard Antivirus*

Diagramas de Arquitectura (Ingeniería Inversa) — FD04

Versión *1.0*

| CONTROL DE VERSIONES | | | | | |
|:---:|:---|:---|:---|:---|:---|
| Versión | Hecha por | Revisada por | Aprobada por | Fecha | Motivo |
| 1.0 | LLica Mamani, Jimmy Mijair | Sierra Ruiz, Iker Alberto | LLica Mamani, Jimmy Mijair | 28/03/2026 | Versión Original |

<div style="page-break-after: always; visibility: hidden"></div>

# ÍNDICE GENERAL

- [1. Diagrama de Clases](#1-diagrama-de-clases)
- [2. Diagrama de Base de Datos](#2-diagrama-de-base-de-datos)
- [3. Diagrama de Componentes](#3-diagrama-de-componentes)
- [4. Diagrama de Despliegue](#4-diagrama-de-despliegue)
- [5. Diagrama de Arquitectura](#5-diagrama-de-arquitectura)
- [6. Diagrama de Infraestructura](#6-diagrama-de-infraestructura)

<div style="page-break-after: always; visibility: hidden"></div>

> **Nota metodológica**: Todos los diagramas de este documento han sido generados mediante **ingeniería inversa** del código fuente del repositorio. Los elementos representados corresponden exclusivamente a clases, módulos, entidades y relaciones presentes en el código real.

---

## 1. Diagrama de Clases

El siguiente diagrama representa las clases Python del módulo `gui/` y las estructuras Rust del módulo `scan_engine/`, inferidas directamente del código fuente.

```mermaid
classDiagram
    %% ── ENUMERACIONES ──────────────────────────────────────────────
    class ScanType {
        <<enumeration>>
        QUICK = "quick"
        FULL = "full"
        CUSTOM = "custom"
        SINGLE = "single"
    }

    class ThreatStatus {
        <<enumeration>>
        DETECTED = "detected"
        QUARANTINED = "quarantined"
        DELETED = "deleted"
        IGNORED = "ignored"
    }

    class DetectionMethod {
        <<enumeration>>
        SIGNATURE = "signature"
        SIGNATURE_MD5 = "signature_md5"
        HEURISTIC = "heuristic"
        CLEAN = "clean"
        ERROR = "error"
        INFO_ONLY = "info_only"
    }

    class ScanStatus {
        <<enumeration>>
        IDLE
        RUNNING
        CANCELLED
        COMPLETE
        ERROR
    }

    %% ── ENTIDADES DE DOMINIO ────────────────────────────────────────
    class ThreatRecord {
        +str path
        +str sha256
        +str md5
        +str threat_name
        +DetectionMethod detection_method
        +int file_size
        +datetime detected_at
        +ThreatStatus status
        +str original_path
        +str quarantine_path
        +filename() str
        +size_human() str
    }

    class ScanSession {
        +str session_id
        +ScanType scan_type
        +str target_path
        +datetime started_at
        +datetime finished_at
        +int total_files
        +int threats_count
        +int skipped_files
        +ScanStatus status
        +list~ThreatRecord~ threats
        +was_cancelled() bool
        +duration_seconds() float
        +duration_human() str
    }

    class QuarantineEntry {
        +str entry_id
        +str original_path
        +str quarantine_path
        +str threat_name
        +str sha256
        +datetime quarantined_at
        +int file_size
        +filename() str
    }

    %% ── INTERFACES (PUERTOS) ────────────────────────────────────────
    class IScanEngine {
        <<interface>>
        +scan_directory(path, callback, token) ScanSummary
        +scan_single_file(path) FileScanResult
        +import_signatures(json_path) int
        +create_token() CancellationToken
    }

    class IScanRepository {
        <<interface>>
        +save_session(session) None
        +load_all_sessions() list~ScanSession~
        +delete_session(session_id) None
    }

    class IQuarantineRepository {
        <<interface>>
        +quarantine_file(threat) QuarantineEntry
        +restore_file(entry_id) bool
        +delete_quarantined(entry_id) bool
        +list_quarantined() list~QuarantineEntry~
    }

    %% ── CASOS DE USO ────────────────────────────────────────────────
    class ScanUseCase {
        -IScanEngine _engine
        -IScanRepository _scan_repo
        -CancellationToken _active_token
        +start_scan(type, path, progress_cb, on_complete) None
        +scan_single_file(path) ScanSession
        +cancel_scan() None
        -_map_to_threat(raw) ThreatRecord
    }

    class QuarantineUseCase {
        -IQuarantineRepository _repo
        +quarantine_threat(threat) QuarantineEntry
        +restore_file(entry_id) bool
        +delete_quarantined(entry_id) bool
        +list_quarantined() list~QuarantineEntry~
    }

    class HistoryUseCase {
        -IScanRepository _repo
        +get_all_sessions() list~ScanSession~
        +clear_history() None
    }

    %% ── INFRAESTRUCTURA ─────────────────────────────────────────────
    class RustScanEngineAdapter {
        -str _db_path
        +scan_directory(path, callback, token)
        +scan_single_file(path)
        +import_signatures(json_path) int
        +create_token()
    }

    class JsonScanRepository {
        -Path _path
        +save_session(session) None
        +load_all_sessions() list~ScanSession~
        +delete_session(session_id) None
        -_load_raw() list~dict~
        -_atomic_write(data) None
        -_serialize(session) dict
        -_deserialize(d) ScanSession
    }

    class JsonQuarantineRepository {
        -Path _qdir
        -Path _registry_path
        +quarantine_file(threat) QuarantineEntry
        +restore_file(entry_id) bool
        +delete_quarantined(entry_id) bool
        +list_quarantined() list~QuarantineEntry~
        -_xor_file(src, dst) None
        -_dexor_file(src, dst) None
        -_load_registry() list~QuarantineEntry~
        -_write_registry(entries) None
    }

    %% ── RUST STRUCTS (via PyO3) ─────────────────────────────────────
    class FileScanResult {
        <<Rust/PyO3>>
        +str path
        +str sha256
        +str md5
        +bool is_threat
        +str threat_name
        +str detection_method
        +u64 file_size
        +str error
    }

    class ScanSummary {
        <<Rust/PyO3>>
        +u64 total_files
        +u64 threats_found
        +u64 skipped_files
        +bool was_cancelled
        +Vec~FileScanResult~ threats
    }

    class CancellationToken {
        <<Rust/PyO3>>
        -Arc~AtomicBool~ flag
        +cancel() None
        +reset() None
        +is_cancelled() bool
    }

    %% ── RELACIONES ──────────────────────────────────────────────────
    ScanSession "1" *-- "0..*" ThreatRecord : contains
    ThreatRecord --> ThreatStatus
    ThreatRecord --> DetectionMethod
    ScanSession --> ScanType
    ScanSession --> ScanStatus

    ScanUseCase --> IScanEngine : uses
    ScanUseCase --> IScanRepository : uses
    QuarantineUseCase --> IQuarantineRepository : uses
    HistoryUseCase --> IScanRepository : uses

    RustScanEngineAdapter ..|> IScanEngine : implements
    JsonScanRepository ..|> IScanRepository : implements
    JsonQuarantineRepository ..|> IQuarantineRepository : implements

    RustScanEngineAdapter --> FileScanResult : returns
    RustScanEngineAdapter --> ScanSummary : returns
    RustScanEngineAdapter --> CancellationToken : creates
```

---

## 2. Diagrama de Base de Datos

RustGuard utiliza dos mecanismos de persistencia: **SQLite** para la base de firmas de malware y **archivos JSON** para historial de escaneos y registro de cuarentena.

### 2.1. Esquema SQLite — Base de Firmas

```mermaid
erDiagram
    SIGNATURES {
        INTEGER id PK "PRIMARY KEY AUTOINCREMENT"
        TEXT sha256 "UNIQUE — hash SHA-256 del archivo malicioso"
        TEXT md5 "hash MD5 (fallback) — puede ser NULL"
        TEXT name "Nombre de la amenaza (ej: Trojan.Agent)"
        TEXT severity "Nivel: low | medium | high | critical (DEFAULT medium)"
    }
```

**Índices definidos en el código** (`scan_engine/src/lib.rs`):
- `idx_sha256` ON `signatures(sha256)` — Búsqueda O(log n) por SHA-256
- `idx_md5` ON `signatures(md5)` — Búsqueda O(log n) por MD5

**Archivo en disco**: `signatures/signatures.db`

---

### 2.2. Esquema JSON — Historial de Sesiones

**Archivo**: `logs/scan_history.json`

```json
[
  {
    "session_id": "a1b2c3d4",
    "scan_type": "quick | full | custom | single",
    "target_path": "/ruta/escaneada",
    "started_at": "2026-03-28T10:00:00.000000",
    "finished_at": "2026-03-28T10:02:30.000000",
    "total_files": 1500,
    "threats_count": 2,
    "skipped_files": 3,
    "status": "COMPLETE | CANCELLED | ERROR",
    "threats": [
      {
        "path": "/ruta/archivo.exe",
        "sha256": "abc123...",
        "md5": "def456...",
        "threat_name": "EICAR-Test-File",
        "detection_method": "signature | signature_md5 | heuristic",
        "file_size": 68,
        "detected_at": "2026-03-28T10:01:15.000000",
        "status": "detected | quarantined | deleted | ignored",
        "original_path": "",
        "quarantine_path": ""
      }
    ]
  }
]
```

---

### 2.3. Esquema JSON — Registro de Cuarentena

**Archivo**: `quarantine/registry.json`

```json
[
  {
    "entry_id": "abc123def456",
    "original_path": "/home/user/downloads/virus.exe",
    "quarantine_path": "/app/quarantine/abc123def456.quar",
    "threat_name": "EICAR-Test-File",
    "sha256": "275a021b...",
    "quarantined_at": "2026-03-28T10:01:20.000000",
    "file_size": 68
  }
]
```

---

## 3. Diagrama de Componentes

```mermaid
graph TB
    subgraph "RustGuard Application"
        subgraph "Presentation Layer"
            MW["MainWindow\n(CustomTkinter GUI)\nmain_window.py"]
        end

        subgraph "Application Layer"
            SUC["ScanUseCase\nscan_use_case.py"]
            QUC["QuarantineUseCase\nscan_use_case.py"]
            HUC["HistoryUseCase\nscan_use_case.py"]
        end

        subgraph "Domain Layer"
            ENT["Entities\nmodels.py\n(ThreatRecord, ScanSession,\nQuarantineEntry, Enums)"]
            PRT["Ports/Interfaces\nports.py\n(IScanEngine, IScanRepository,\nIQuarantineRepository)"]
        end

        subgraph "Infrastructure Layer"
            RSA["RustScanEngineAdapter\nrust_engine_adapter.py"]
            JSR["JsonScanRepository\nscan_repository.py"]
            JQR["JsonQuarantineRepository\nquarantine_repository.py"]
        end

        subgraph "Shared"
            CONST["constants.py\n(colors, quick scan paths)"]
            LOG["logging_config.py\n(RotatingFileHandler)"]
        end
    end

    subgraph "Rust Core (Compiled Binary)"
        RE["scan_engine\n(cdylib / .so / .pyd)\nsrc/lib.rs"]
        subgraph "Rust Internals"
            HC["compute_hashes()\nSHA-256 + MD5"]
            SDB["SignatureDb\n(rusqlite / SQLite)"]
            HE["HeuristicEngine\n(regex rules)"]
            CT["CancellationToken\n(Arc<AtomicBool>)"]
            WD["WalkDir\n(walkdir crate)"]
        end
    end

    subgraph "Persistent Storage"
        SIGDB[("signatures.db\n(SQLite)")]
        HIST[("scan_history.json\n(JSON)")]
        QREG[("quarantine/registry.json\n(JSON)")]
        QFILES[("quarantine/*.quar\n(XOR-obfuscated files)")]
        LOGS[("logs/rustguard.log\n(Rotating log file)")]
    end

    MW --> SUC
    MW --> QUC
    MW --> HUC

    SUC --> PRT
    QUC --> PRT
    HUC --> PRT

    SUC --> RSA
    SUC --> JSR
    QUC --> JQR
    HUC --> JSR

    RSA -->|"PyO3 FFI"| RE

    RE --> HC
    RE --> SDB
    RE --> HE
    RE --> CT
    RE --> WD

    SDB --> SIGDB
    JSR --> HIST
    JQR --> QREG
    JQR --> QFILES
    LOG --> LOGS

    MW --> CONST
    MW --> LOG
```

---

## 4. Diagrama de Despliegue

```mermaid
graph LR
    subgraph "Equipo del Usuario (Desktop)"
        subgraph "Python Runtime (3.10+)"
            PYAPP["RustGuard GUI\n(gui/main.py)"]
            CTKT["CustomTkinter\n5.2+"]
            PYAPP --> CTKT
        end

        subgraph "Rust Extension Module"
            SO["scan_engine.so / scan_engine.pyd\n(Compilado con maturin + cargo)"]
        end

        subgraph "Persistent Data (Local)"
            SQLITE[("signatures/signatures.db\n(SQLite)")]
            JSON1[("logs/scan_history.json")]
            JSON2[("quarantine/registry.json")]
            QUAR[("quarantine/*.quar")]
            LOGF[("logs/rustguard.log")]
        end

        PYAPP -->|"import scan_engine\n(PyO3 cdylib)"| SO
        PYAPP --> SQLITE
        PYAPP --> JSON1
        PYAPP --> JSON2
        PYAPP --> QUAR
        PYAPP --> LOGF
    end

    subgraph "Build Environment (Development)"
        RUST["Rust Toolchain\n(cargo 1.75+)"]
        MATURIN["maturin 1.5+"]
        PYINST["PyInstaller 6.x"]
        MATURIN -->|"cargo build --release"| RUST
        MATURIN -->|"Genera .so/.pyd"| SO
        PYINST -->|"Empaqueta todo en\nRustGuard.exe / RustGuard"| PYAPP
    end

    subgraph "Optional: External Signature Sources"
        MB["MalwareBazaar\nbazaar.abuse.ch"]
        NSRL["NSRL (NIST)\nnist.gov"]
        MB -->|"JSON export"| SQLITE
        NSRL -->|"Hash list"| SQLITE
    end

    style SO fill:#d4531c,color:#fff
    style PYAPP fill:#3776ab,color:#fff
    style SQLITE fill:#003B57,color:#fff
```

---

## 5. Diagrama de Arquitectura

### 5.1. Arquitectura Limpia (Clean Architecture)

```mermaid
graph TD
    subgraph "🖥️ Presentation Layer\n(gui/presentation/)"
        UI["MainWindow\nmain_window.py\n• Eventos de usuario\n• Barra de progreso\n• Tabla de amenazas\n• CustomTkinter"]
    end

    subgraph "⚙️ Application Layer\n(gui/application/use_cases/)"
        SUC["ScanUseCase\n• Orquesta el ciclo de escaneo\n• Crea ScanSession\n• Mapea resultados Rust → Python"]
        QUC["QuarantineUseCase\n• Gestiona cuarentena/restaurar/eliminar"]
        HUC["HistoryUseCase\n• Carga y ordena sesiones"]
    end

    subgraph "📐 Domain Layer\n(gui/domain/)"
        ENT["Entities\nThreatRecord, ScanSession\nQuarantineEntry\n(Dataclasses puros)"]
        PRT["Interfaces / Ports\nIScanEngine\nIScanRepository\nIQuarantineRepository\n(ABCs)"]
    end

    subgraph "🔧 Infrastructure Layer\n(gui/infrastructure/)"
        ADAPTER["RustScanEngineAdapter\n• Implementa IScanEngine\n• Wraps PyO3 Rust module\n• Fallback Python stub"]
        SCANREPO["JsonScanRepository\n• Implementa IScanRepository\n• Historial en scan_history.json\n• Escritura atómica"]
        QREPO["JsonQuarantineRepository\n• Implementa IQuarantineRepository\n• XOR obfuscation\n• registry.json"]
    end

    subgraph "🦀 Rust Core\n(scan_engine/src/lib.rs)"
        RUST["scan_engine (cdylib)\n• scan_file()\n• scan_directory()\n• import_signatures_json()\n• CancellationToken\n• HeuristicEngine\n• SignatureDb (SQLite)"]
    end

    UI -->|"Llama use cases\ndesde hilo separado"| SUC
    UI --> QUC
    UI --> HUC

    SUC -->|"Usa interfaces"| PRT
    QUC --> PRT
    HUC --> PRT

    ADAPTER ..|"Implementa"| PRT
    SCANREPO ..|"Implementa"| PRT
    QREPO ..|"Implementa"| PRT

    ADAPTER -->|"PyO3 FFI\n(import scan_engine)"| RUST

    SUC --> ENT
    QUC --> ENT
    HUC --> ENT

    style UI fill:#2d5a8e,color:#fff
    style SUC fill:#5a8e2d,color:#fff
    style QUC fill:#5a8e2d,color:#fff
    style HUC fill:#5a8e2d,color:#fff
    style ENT fill:#8e6d2d,color:#fff
    style PRT fill:#8e6d2d,color:#fff
    style ADAPTER fill:#8e2d2d,color:#fff
    style SCANREPO fill:#8e2d2d,color:#fff
    style QREPO fill:#8e2d2d,color:#fff
    style RUST fill:#d4531c,color:#fff
```

---

### 5.2. Flujo de Datos — Pipeline de Detección

```mermaid
flowchart LR
    A[📁 Archivo\nen disco] --> B[compute_hashes\nLeer en bloques 64KB]
    B --> C{SHA-256\nen DB?}
    C -->|Sí| D[✅ DETECTADO\ndetection_method=signature]
    C -->|No| E{MD5\nen DB?}
    E -->|Sí| F[✅ DETECTADO\ndetection_method=signature_md5]
    E -->|No| G[HeuristicEngine.analyze]
    G --> H{Doble extensión\n.pdf.exe etc?}
    H -->|Sí| I[✅ SOSPECHOSO\ndetection_method=heuristic]
    H -->|No| J{Ejecutable\noculto?}
    J -->|Sí| I
    J -->|No| K{Ejecutable grande\nen directorio temp?}
    K -->|Sí| I
    K -->|No| L{Ejecutable\nde 0 bytes?}
    L -->|Sí| I
    L -->|No| M{Ejecutable en\nAppData/Roaming?}
    M -->|Sí| I
    M -->|No| N[✅ LIMPIO\ndetection_method=clean]

    style D fill:#c0392b,color:#fff
    style F fill:#c0392b,color:#fff
    style I fill:#e67e22,color:#fff
    style N fill:#27ae60,color:#fff
```

---

## 6. Diagrama de Infraestructura

### 6.1. Infraestructura Actual (v1.0 — Local)

```mermaid
graph TD
    subgraph "Estación de Trabajo del Usuario"
        subgraph "Sistema Operativo (Windows / Linux / macOS)"
            APP["RustGuard.exe / RustGuard\n(PyInstaller bundle)\n\nIncluye:\n• Python 3.10 runtime\n• CustomTkinter 5.2\n• scan_engine.so/.pyd\n• Todas las dependencias"]
        end
        subgraph "Almacenamiento Local"
            DB1[("signatures/signatures.db\nSQLite — Firmas de malware")]
            DB2[("logs/scan_history.json\nHistorial de sesiones")]
            DB3[("quarantine/registry.json\nRegistro cuarentena")]
            DB4[("quarantine/*.quar\nArchivos XOR-ofuscados")]
            DB5[("logs/rustguard.log\nLog rotativo 5MB×3")]
        end
        APP <--> DB1
        APP <--> DB2
        APP <--> DB3
        APP <--> DB4
        APP --> DB5
    end

    subgraph "GitHub (CI/CD — sin costo)"
        REPO["Repository\nIkerASierraR/antivirus_claude"]
        GHA["GitHub Actions\n• Compilación Rust\n• Linting Python\n• Tests\n• Security scan (Semgrep)"]
        REL["GitHub Releases\nBinarios compilados\n(.exe, AppImage)"]
        REPO --> GHA
        GHA --> REL
    end

    DEV["👨‍💻 Desarrollador"] -->|"git push"| REPO
    USER["👤 Usuario Final"] -->|"Descarga release"| REL
    REL --> APP

    style APP fill:#3776ab,color:#fff
    style REPO fill:#24292e,color:#fff
    style GHA fill:#2088ff,color:#fff
    style REL fill:#28a745,color:#fff
```

---

### 6.2. Infraestructura Propuesta (v2.0 — Terraform / AWS)

La siguiente infraestructura es referencial para la versión futura v2.0, alineada con el código Terraform presente en el informe FD01.

```mermaid
graph TD
    subgraph "AWS Cloud (IaC — Terraform)"
        subgraph "CDN Layer"
            CF["Amazon CloudFront\n(CDN para firmas)"]
        end
        subgraph "Storage Layer"
            S3["Amazon S3\nsecureguard-signatures-prod\nVersionado habilitado\nBloqueo acceso público"]
        end
        subgraph "Compute Layer"
            LAMBDA["AWS Lambda\nAPI de actualización de firmas\n1M invocaciones/mes"]
        end
        subgraph "Database Layer"
            RDS["Amazon RDS\nPostgreSQL db.t3.micro\nRegistro de versiones y estadísticas"]
        end

        CF --> S3
        LAMBDA --> S3
        LAMBDA --> RDS
    end

    subgraph "Estaciones de Usuario"
        APP1["RustGuard v2.0\n(Cliente Desktop)"]
        APP2["RustGuard v2.0\n(Cliente Desktop)"]
    end

    subgraph "GitHub"
        REPO["Repositorio\nIkerASierraR/antivirus_claude"]
        TF["Terraform config\n(main.tf)"]
        REPO --> TF
        TF -->|"terraform apply"| CF
    end

    APP1 -->|"HTTPS — Descargar firmas actualizadas"| CF
    APP2 -->|"HTTPS — Descargar firmas actualizadas"| CF

    style CF fill:#ff9900,color:#000
    style S3 fill:#7aa116,color:#fff
    style LAMBDA fill:#ff9900,color:#000
    style RDS fill:#1a9c3e,color:#fff
    style APP1 fill:#3776ab,color:#fff
    style APP2 fill:#3776ab,color:#fff
```

### 6.3. Tabla de Recursos Terraform

| Recurso Terraform | Tipo AWS | Función | Costo Estimado |
|:------------------|:---------|:--------|:--------------:|
| `aws_s3_bucket.signatures` | S3 Bucket | Almacenar base de firmas y actualizaciones | $1.50/mes |
| `aws_s3_bucket_versioning` | S3 Versioning | Rollback de versiones de firmas | incluido |
| `aws_s3_bucket_public_access_block` | S3 Policy | Seguridad: bloqueo acceso público | incluido |
| `aws_cloudfront_distribution.signatures_cdn` | CloudFront | CDN global para distribución rápida | $9.00/mes |
| `aws_lambda_function` | Lambda | API de actualización (serverless) | $0.20/mes |
| `aws_db_instance.signatures_db` | RDS PostgreSQL t3.micro | Registro de versiones y estadísticas | $15.00/mes |
| **Total estimado** | | | **~$25.70/mes** |

**Archivo de configuración**: `informes/FD01-Informe-Factibilidad.md` → Sección 4.2.7
