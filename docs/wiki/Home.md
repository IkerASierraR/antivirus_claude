# 🛡️ RustGuard Wiki — Home

Bienvenido a la documentación oficial de **RustGuard**, un antivirus de escritorio de código abierto que combina un motor de escaneo de alto rendimiento escrito en **Rust** con una interfaz gráfica moderna en **Python (CustomTkinter)**.

---

## 📚 Navegación de la Wiki

| Página | Descripción |
|:-------|:------------|
| [Home](Home) | Esta página — visión general |
| [Instalación](Instalación) | Requisitos y pasos de instalación |
| [Uso](Uso) | Guía de uso de la aplicación |
| [Arquitectura](Arquitectura) | Estructura del código y capas |
| [Contribución](Contribución) | Cómo colaborar en el proyecto |
| [Roadmap](Roadmap) | Versiones futuras y features planificados |
| [GitHub Projects](GitHub-Projects) | Flujo de trabajo y gestión de issues |

---

## 🎯 ¿Qué es RustGuard?

RustGuard es una aplicación antivirus de escritorio **multiplataforma** (Windows, Linux, macOS) que:

- ✅ **Detecta malware conocido** mediante comparación de hashes SHA-256 y MD5 contra una base de datos SQLite de firmas.
- ✅ **Identifica amenazas desconocidas** mediante análisis heurístico de 5 reglas (extensión doble, ejecutables ocultos, ejecutables en directorios sospechosos, etc.).
- ✅ **Aísla amenazas** en una zona de cuarentena con ofuscación XOR para prevenir ejecución accidental.
- ✅ **Mantiene historial** de todas las sesiones de escaneo en formato JSON persistente.
- ✅ **Funciona 100% offline** — el motor Rust no realiza conexiones de red.

## ⚡ ¿Por qué Rust para el motor de escaneo?

El motor de escaneo está implementado como biblioteca Rust (compilada a `.so`/`.pyd`) por las siguientes razones técnicas:

| Característica | Beneficio en RustGuard |
|:---------------|:----------------------|
| **Rendimiento nativo** | Escaneo de archivos a velocidad cercana a C/C++ |
| **Seguridad de memoria** | Sin segfaults, sin buffer overflows, sin use-after-free |
| **Concurrencia segura** | `Arc<AtomicBool>` para cancelación thread-safe sin data races |
| **Zero-cost abstractions** | Iteradores eficientes con WalkDir sin overhead de garbage collection |
| **PyO3 integration** | Exposición directa como módulo Python nativo sin IPC overhead |

---

## 🗂️ Estructura del Proyecto

```
antivirus_claude/
├── scan_engine/               ← Motor Rust (PyO3 / maturin)
│   ├── Cargo.toml             ← Dependencias Rust
│   └── src/lib.rs             ← Hashing, heurísticas, SQLite, cancel token
│
├── gui/                       ← Aplicación Python (Clean Architecture)
│   ├── main.py                ← Punto de entrada + DI wiring
│   ├── domain/
│   │   ├── entities/models.py ← ThreatRecord, ScanSession, QuarantineEntry, Enums
│   │   └── interfaces/ports.py← Interfaces abstractas (IScanEngine, IRepository…)
│   ├── application/
│   │   └── use_cases/scan_use_case.py ← ScanUseCase, QuarantineUseCase, HistoryUseCase
│   ├── infrastructure/
│   │   ├── scanner/rust_engine_adapter.py  ← Adaptador PyO3 con fallback Python
│   │   └── repositories/
│   │       ├── scan_repository.py      ← Historial en JSON (escritura atómica)
│   │       └── quarantine_repository.py← Cuarentena XOR + registro JSON
│   ├── presentation/
│   │   └── views/main_window.py ← GUI CustomTkinter (Scanner, Cuarentena, Historial)
│   └── shared/
│       ├── constants.py       ← Colores, rutas de escaneo rápido por SO
│       └── logging_config.py  ← Logging rotativo a archivo + consola
│
├── signatures/
│   ├── sample_signatures.json ← Firmas de ejemplo (EICAR test file)
│   └── signatures.db          ← Base de datos SQLite (generada en runtime)
│
├── pyproject.toml             ← Configuración maturin
├── requirements.txt           ← Dependencias Python
└── rustguard.spec             ← Configuración PyInstaller
```

---

## 🚀 Inicio Rápido

```bash
# Clonar repositorio
git clone https://github.com/IkerASierraR/antivirus_claude.git
cd antivirus_claude

# Instalar dependencias
pip install maturin customtkinter

# Compilar motor Rust
maturin develop --release

# Ejecutar
python -m gui.main
```

Para instrucciones detalladas, ver la página [Instalación](Instalación).

---

## 📊 Tecnologías

| Tecnología | Versión | Uso |
|:-----------|:-------:|:----|
| Rust | 1.75+ | Motor de escaneo (cdylib) |
| PyO3 | 0.21 | Puente FFI Rust ↔ Python |
| maturin | 1.5+ | Build system para extensión Rust |
| Python | 3.10+ | Lógica de negocio y GUI |
| CustomTkinter | 5.2+ | Interfaz gráfica tema oscuro |
| SQLite (rusqlite) | — | Base de datos de firmas |
| PyInstaller | 6.x | Empaquetado como ejecutable standalone |

---

*Proyecto académico — Universidad Privada de Tacna | Curso: Calidad y Pruebas de Software | 2026*
