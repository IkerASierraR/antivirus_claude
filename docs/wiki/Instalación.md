# 🔧 Instalación de RustGuard

## Prerrequisitos

Antes de instalar RustGuard, asegúrese de tener los siguientes componentes:

| Herramienta | Versión mínima | Instalación |
|:------------|:--------------:|:------------|
| Python | 3.10+ | [python.org](https://python.org) |
| Rust + Cargo | 1.75+ | `curl https://sh.rustup.rs -sSf \| sh` |
| maturin | 1.5+ | `pip install maturin` |
| customtkinter | 5.2+ | incluido en `requirements.txt` |
| PyInstaller (opcional) | 6.x | `pip install pyinstaller` |

---

## Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/IkerASierraR/antivirus_claude.git
cd antivirus_claude
```

## Paso 2 — Instalar dependencias Python

```bash
pip install -r requirements.txt
```

`requirements.txt` incluye:
- `customtkinter>=5.2.2` — Interfaz gráfica

> **Nota**: `maturin` se instala por separado ya que solo es necesario para compilar el motor Rust.

## Paso 3 — Compilar el motor Rust

```bash
# Instalar maturin si no está disponible
pip install maturin

# Compilar en modo release (recomendado para uso real)
maturin develop --release

# O en modo debug (compilación más rápida para desarrollo)
maturin develop
```

**¿Qué hace este comando?**
1. Lee `pyproject.toml` para encontrar la configuración de maturin.
2. Compila `scan_engine/src/lib.rs` usando `cargo build --release`.
3. Genera `scan_engine.cpython-3XX-<platform>.so` (Linux/macOS) o `scan_engine.pyd` (Windows).
4. Instala el módulo Python en modo editable.

## Paso 4 — Verificar la instalación

```bash
python -c "import scan_engine; print('✅ Motor Rust cargado correctamente')"
```

Si el motor no está compilado, el adaptador Python (`RustScanEngineAdapter`) caerá automáticamente en el modo stub Python (sin escaneo real).

## Paso 5 — Importar firmas (opcional)

```bash
python -c "
import scan_engine
n = scan_engine.import_signatures_json(
    'signatures/sample_signatures.json',
    'signatures/signatures.db'
)
print(f'{n} firma(s) importada(s)')
"
```

**Fuentes de firmas gratuitas:**

| Fuente | URL | Formato |
|:-------|:----|:-------:|
| MalwareBazaar | [bazaar.abuse.ch/export/](https://bazaar.abuse.ch/export/) | JSON/CSV |
| VirusShare | [virusshare.com](https://virusshare.com/) | MD5 list (requiere registro) |
| NSRL (NIST) | [nist.gov/itl/ssd/software-quality-group/national-software-reference-library-nsrl](https://www.nist.gov/itl/ssd/software-quality-group/national-software-reference-library-nsrl) | SHA-256 whitelist |

## Paso 6 — Ejecutar la aplicación

```bash
python -m gui.main
```

---

## Instalación como ejecutable standalone

### Compilar para distribución (PyInstaller)

```bash
# Compilar motor Rust primero
maturin develop --release

# Empaquetar con PyInstaller
pyinstaller rustguard.spec

# El ejecutable queda en:
# Windows: dist/RustGuard.exe
# Linux/macOS: dist/RustGuard
```

El ejecutable generado incluye:
- Python runtime completo
- CustomTkinter y todas las dependencias
- El módulo `scan_engine` compilado en Rust

---

## Solución de problemas

| Problema | Causa posible | Solución |
|:---------|:-------------|:---------|
| `ModuleNotFoundError: No module named 'scan_engine'` | Motor Rust no compilado | Ejecutar `maturin develop --release` |
| `error: toolchain 'stable' is not installed` | Rust no instalado | Instalar con `rustup` |
| `maturin: command not found` | maturin no instalado | `pip install maturin` |
| La GUI no inicia | customtkinter no instalado | `pip install -r requirements.txt` |
| Error de permisos en cuarentena | Sin permisos de escritura | Ejecutar con permisos adecuados o cambiar `quarantine_dir` |
