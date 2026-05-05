# 🏷️ GitHub Releases y Packages — Estrategia de Versionado RustGuard

## 1. Estrategia de Versionado

RustGuard utiliza **Semantic Versioning 2.0.0** (`MAJOR.MINOR.PATCH`):

| Componente | Cuándo incrementar | Ejemplo |
|:-----------|:-------------------|:-------:|
| **MAJOR** | Cambios incompatibles en la API o arquitectura | 2.0.0 |
| **MINOR** | Nuevas funcionalidades compatibles con versiones anteriores | 1.1.0 |
| **PATCH** | Correcciones de bugs y parches de seguridad | 1.0.1 |

### Etiquetas de versión pre-release

| Sufijo | Descripción | Ejemplo |
|:-------|:------------|:-------:|
| `-alpha.N` | Funcionalidad incompleta, uso interno | `v1.1.0-alpha.1` |
| `-beta.N` | Feature-complete, en pruebas | `v1.1.0-beta.1` |
| `-rc.N` | Release Candidate — lista para producción | `v1.1.0-rc.1` |

---

## 2. Proceso de Release

### Paso a paso para publicar una release

```bash
# 1. Asegurar que develop está actualizado
git checkout develop
git pull origin develop

# 2. Crear rama release desde develop
git checkout -b release/v1.1.0 develop

# 3. Actualizar versión en los archivos de configuración
# - scan_engine/Cargo.toml: version = "1.1.0"
# - pyproject.toml: version = "1.1.0"
# - gui/shared/constants.py: APP_VERSION = "1.1.0"

# 4. Actualizar CHANGELOG.md

# 5. Commit de versión
git add .
git commit -m "chore: bump version to v1.1.0"

# 6. Merge a main y develop
git checkout main
git merge --no-ff release/v1.1.0
git tag -a v1.1.0 -m "Release v1.1.0"

git checkout develop
git merge --no-ff release/v1.1.0

# 7. Eliminar rama release
git branch -d release/v1.1.0

# 8. Push con tags
git push origin main develop --tags
```

El push del tag `v1.1.0` activa automáticamente el job `release` en el pipeline CI/CD (ver `.github/workflows/ci.yml`), que:
1. Compila el motor Rust en Linux y Windows.
2. Empaqueta con PyInstaller.
3. Publica los binarios en la GitHub Release.

---

## 3. Releases Actuales y Planificadas

### v1.0.0 — Release Inicial ✅

**Fecha**: Abril 2026  
**Estado**: Publicada

**Assets incluidos**:

| Asset | Plataforma | Descripción |
|:------|:----------:|:------------|
| `RustGuard-linux` | Linux x86_64 | Binario ELF standalone |
| `RustGuard-windows.exe` | Windows x64 | Ejecutable PE standalone |
| `Source code (zip)` | — | Código fuente automático de GitHub |
| `Source code (tar.gz)` | — | Código fuente automático de GitHub |

**Release Notes v1.0.0**:

```markdown
## 🛡️ RustGuard v1.0.0 — Release Inicial

### ¿Qué incluye?
- ⚡ Motor de escaneo en Rust con PyO3 — máximo rendimiento
- 🔍 Detección por SHA-256 y MD5 contra base de firmas SQLite
- 🧠 Análisis heurístico de 5 capas (extensión doble, ejecutables ocultos, etc.)
- 🔒 Sistema de cuarentena con ofuscación XOR
- 📊 Historial persistente de sesiones de escaneo
- 🖥️ Interfaz gráfica CustomTkinter con tema oscuro
- ❌ Cancelación de escaneo en tiempo real
- 📥 Importación de firmas desde JSON (compatible con MalwareBazaar)

### Instalación
Ver README.md para instrucciones completas.

### Plataformas soportadas
- Windows 10/11 (x64)
- Linux (x86_64, glibc 2.31+)
- macOS (build desde fuente)

### Notas de seguridad
- El motor Rust no realiza conexiones de red — 100% offline
- La cuarentena usa ofuscación XOR (no cifrado criptográfico)
- Para entornos de producción, se recomienda cifrado AES-256 (planificado para v2.1.0)
```

---

### v1.1.0 — Planificada (Q3 2026) 🔄

**Assets previstos**:
- `RustGuard-linux-v1.1.0`
- `RustGuard-windows-v1.1.0.exe`
- Reglas YARA de ejemplo (`.yar`)

---

## 4. GitHub Packages

### Publicación de paquete Python (PyPI / GHCR)

Aunque RustGuard en v1.0.0 no publica en PyPI debido a la dependencia del motor Rust compilado, en versiones futuras se consideran las siguientes estrategias:

#### Opción A — GitHub Container Registry (Docker)

```dockerfile
# Dockerfile (referencial — versión futura)
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar wheel pre-compilado
COPY dist/scan_engine*.whl .
COPY requirements.txt .

RUN pip install scan_engine*.whl customtkinter

COPY gui/ gui/
COPY signatures/ signatures/

CMD ["python", "-m", "gui.main"]
```

#### Opción B — Wheel manylinux (PyPI)

Para una distribución futura vía `pip install rustguard`, se usaría maturin con la opción `--manylinux`:

```bash
# Construir wheel compatible con múltiples distribuciones Linux
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin build --release --manylinux 2014

# El wheel resultante puede instalarse en cualquier Linux:
pip install dist/scan_engine-1.1.0-cp311-cp311-manylinux_2_17_x86_64.mhl
```

---

## 5. CHANGELOG

### Formato del CHANGELOG (Keep a Changelog)

```markdown
# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.
El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/).
Este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

## [1.0.0] - 2026-04-28

### Added
- Motor de escaneo en Rust (PyO3) con SHA-256, MD5 y heurísticas
- Sistema de cuarentena XOR con registro JSON
- Historial de sesiones de escaneo (JSON)
- Interfaz gráfica CustomTkinter (tema oscuro)
- Importación de firmas desde JSON hacia SQLite
- Cancelación de escaneo con token atómico thread-safe
- Quick Scan con rutas predefinidas por SO
- Full Scan del sistema de archivos
- Custom Scan de directorio elegido por usuario
- Empaquetado PyInstaller para Windows y Linux
```

---

## 6. Protección de la rama main

Se recomienda configurar las siguientes **Branch Protection Rules** en GitHub:

| Regla | Valor recomendado |
|:------|:-----------------|
| Require pull request reviews before merging | ✅ 1 reviewer mínimo |
| Require status checks to pass | ✅ rust-build, python-lint, maturin-build |
| Require branches to be up to date | ✅ |
| Do not allow bypassing the above settings | ✅ |
| Restrict who can push to matching branches | Administradores del repositorio |
