# 🛡 RustGuard — Antivirus Desktop

Motor de escaneo en **Rust** (PyO3) + Interfaz en **Python** (CustomTkinter)  
Arquitectura limpia, código de nivel profesional, 100% herramientas gratuitas y open-source.

---

## Estructura del Proyecto

```
rustguard/
├── scan_engine/               ← Motor Rust (PyO3 / maturin)
│   ├── Cargo.toml
│   └── src/lib.rs             ← Hashing, heurísticas, DB signatures, token cancelación
│
├── gui/                       ← Aplicación Python
│   ├── main.py                ← Punto de entrada + inyección de dependencias
│   ├── domain/
│   │   ├── entities/models.py ← ThreatRecord, ScanSession, QuarantineEntry, enums
│   │   └── interfaces/ports.py← Interfaces abstractas (IScanEngine, IRepository…)
│   ├── application/
│   │   └── use_cases/
│   │       └── scan_use_case.py ← ScanUseCase, QuarantineUseCase, HistoryUseCase
│   ├── infrastructure/
│   │   ├── scanner/
│   │   │   └── rust_engine_adapter.py  ← Adaptador PyO3 con fallback Python
│   │   └── repositories/
│   │       ├── scan_repository.py      ← Historial en JSON
│   │       └── quarantine_repository.py← Cuarentena XOR + registro JSON
│   ├── presentation/
│   │   └── views/
│   │       └── main_window.py ← GUI CustomTkinter (Scanner, Cuarentena, Historial)
│   └── shared/
│       ├── constants.py       ← Colores, rutas de escaneo rápido
│       └── logging_config.py  ← Logging rotativo a archivo + consola
│
├── signatures/
│   └── sample_signatures.json ← Firmas de ejemplo (formato para importar)
├── pyproject.toml             ← Config maturin
├── requirements.txt
└── rustguard.spec             ← Config PyInstaller
```

---

## Prerrequisitos

| Herramienta | Versión mínima | Instalación |
|---|---|---|
| Python | 3.10+ | python.org |
| Rust + Cargo | 1.75+ | `curl https://sh.rustup.rs -sSf \| sh` |
| maturin | 1.5+ | `pip install maturin` |
| customtkinter | 5.2+ | `pip install customtkinter` |
| PyInstaller | 6.x | `pip install pyinstaller` |

---

## Paso 1 — Compilar el motor Rust

```bash
# Desde la raíz del proyecto (donde está pyproject.toml)
cd rustguard/

# Modo desarrollo (coloca el .so/.pyd directamente en gui/)
pip install maturin
maturin develop --release

# Verificar que funcionó:
python -c "import scan_engine; print('Rust engine OK')"
```

**¿Qué hace maturin?**  
Lee `pyproject.toml`, compila `scan_engine/src/lib.rs` con `cargo build --release`,
genera el archivo `scan_engine.cpython-3XX-*.so` (Linux/macOS) o `scan_engine.pyd` (Windows)
y lo instala como paquete Python editable.

---

## Paso 2 — Instalar dependencias Python

```bash
pip install -r requirements.txt
```

---

## Paso 3 — Ejecutar en desarrollo

```bash
# Desde la raíz del proyecto
python -m gui.main
```

---

## Paso 4 — Importar firmas (opcional)

Puedes usar cualquier base de datos de hashes SHA-256 en formato JSON:

```bash
# Formato esperado:
# [{"sha256": "abc123...", "md5": "...", "name": "Trojan.Agent", "severity": "high"}, ...]

python -c "
import scan_engine
n = scan_engine.import_signatures_json('signatures/sample_signatures.json', 'signatures/signatures.db')
print(f'Importadas {n} firmas')
"
```

**Fuentes de firmas gratuitas:**
- [MalwareBazaar](https://bazaar.abuse.ch/export/) — hashes SHA-256 gratuitos
- [VirusShare](https://virusshare.com/) — requiere registro
- [NSRL (NIST)](https://www.nist.gov/itl/ssd/software-quality-group/national-software-reference-library-nsrl) — hashes de software legítimo (whitelist)

---

## Paso 5 — Empaquetar como ejecutable

### Windows (.exe único)

```bash
# Compilar Rust primero (en Windows, genera .pyd)
maturin develop --release

# Empaquetar con PyInstaller
pyinstaller rustguard.spec

# El ejecutable queda en: dist/RustGuard.exe
```

### Linux/macOS (binario único)

```bash
maturin develop --release
pyinstaller rustguard.spec
# dist/RustGuard
```

### Distribución sin instalación

```bash
# Copia toda la carpeta dist/ al destino
# El ejecutable incluye Python runtime, CustomTkinter y el motor Rust
```

---

## Arquitectura — Flujo de datos

```
[Usuario presiona Escanear]
       ↓
MainWindow._begin_scan()          ← Presentation
       ↓ (hilo separado)
ScanUseCase.start_scan()          ← Application
       ↓
RustScanEngineAdapter             ← Infrastructure
       ↓ (FFI / PyO3)
scan_engine::scan_directory()     ← Rust Core
       ↓ (callback por cada archivo)
_progress_callback → after(0, ui) ← thread-safe Tkinter update
       ↓ (al terminar)
on_scan_complete → render_results ← Presentation
       ↓
JsonScanRepository.save_session() ← Infrastructure
```

---

## Capas de detección (Rust)

| Capa | Método | Descripción |
|---|---|---|
| 1 | SHA-256 | Hash exacto contra DB SQLite |
| 2 | MD5 | Hash MD5 como fallback |
| 3 | Heurística | Extensión doble (`.txt.exe`) |
| 4 | Heurística | Ejecutable oculto (`.hidden.exe`) |
| 5 | Heurística | Ejecutable grande en carpeta temp |
| 6 | Heurística | Ejecutable de 0 bytes (dropper) |
| 7 | Heurística | Ejecutable en AppData/Roaming |

---

## Notas de seguridad

- Los archivos en cuarentena se **XOR** con clave `0xAD` para prevenir ejecución accidental.
- No es cifrado criptográfico; es ofuscación de baja complejidad intencional.
- Para producción real, considera cifrado AES-256 con `cryptography` (Python) o `aes` (Rust).
- El motor Rust no realiza conexiones de red; es completamente offline.
