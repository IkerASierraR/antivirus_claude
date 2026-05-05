# 🗺️ Roadmap de RustGuard

Este documento describe las versiones planificadas y el estado de desarrollo de RustGuard.

---

## Estado Actual

**Versión**: `v1.0.0`  
**Estado**: ✅ Estable

---

## v1.0.0 — Release Inicial ✅

**Fecha de entrega**: Abril 2026

### Funcionalidades incluidas

| Feature | Estado | Descripción |
|:--------|:------:|:------------|
| Motor de escaneo Rust (PyO3) | ✅ | Biblioteca cdylib compilada con maturin |
| Detección por SHA-256 | ✅ | Comparación exacta contra SQLite |
| Detección por MD5 (fallback) | ✅ | Segunda capa de detección por firma |
| Heurística: extensión doble | ✅ | Detecta `archivo.pdf.exe` |
| Heurística: ejecutable oculto | ✅ | Detecta `.hidden.exe` |
| Heurística: ejecutable grande en temp | ✅ | >50 MB en /tmp o \Temp\ |
| Heurística: ejecutable vacío (dropper) | ✅ | 0 bytes + extensión ejecutable |
| Heurística: ejecutable en AppData | ✅ | .exe/.scr en AppData/Roaming |
| Escaneo rápido (Quick Scan) | ✅ | Rutas predefinidas por SO |
| Escaneo completo (Full Scan) | ✅ | Recorrido recursivo completo |
| Escaneo personalizado (Custom Scan) | ✅ | Directorio elegido por usuario |
| Escaneo de archivo único | ✅ | Drag & drop / single file |
| Cancelación de escaneo | ✅ | Token atómico thread-safe |
| Barra de progreso en tiempo real | ✅ | Callback Python por cada archivo |
| Cuarentena XOR | ✅ | Archivos .quar con ofuscación 0xAD |
| Restauración desde cuarentena | ✅ | XOR inverso + registro JSON |
| Eliminación permanente | ✅ | Borrado físico del archivo .quar |
| Historial de sesiones (JSON) | ✅ | Persistencia en scan_history.json |
| Importación de firmas (JSON→SQLite) | ✅ | Base de datos actualizable |
| GUI CustomTkinter tema oscuro | ✅ | Interfaz desktop moderna |
| Logging rotativo | ✅ | 5 MB × 3 archivos |
| Empaquetado PyInstaller | ✅ | Ejecutable standalone |

---

## v1.1.0 — Mejoras de Detección 🔄

**Fecha estimada**: Q3 2026  
**Estado**: Planificado

### Features planificados

| Feature | Prioridad | Descripción técnica |
|:--------|:---------:|:--------------------|
| Soporte reglas YARA | 🔴 Alta | Integrar crate `yara-rust` para reglas estándar de la industria |
| Whitelist NSRL | 🔴 Alta | Reducir falsos positivos con hashes de software legítimo (NIST) |
| Auto-actualización de firmas | 🟡 Media | Descarga automática desde fuente configurable (MalwareBazaar API) |
| Notificaciones del sistema | 🟢 Baja | Alertas nativas: Windows toast / Linux notify-send / macOS NSAlert |
| Exportación de resultados CSV | 🟢 Baja | Exportar tabla de amenazas a CSV |

---

## v2.0.0 — Arquitectura Distribuida 🔄

**Fecha estimada**: Q1 2027  
**Estado**: Diseño preliminar

### Features planificados

| Feature | Tecnología propuesta | Descripción |
|:--------|:--------------------:|:------------|
| Servidor de firmas en nube | FastAPI + AWS S3 + CloudFront | API REST para distribución de actualizaciones |
| Telemetría opt-in | HTTPS + cifrado | Reporte anónimo de detecciones |
| Modo daemon / servicio del SO | systemd / Windows Service | Proceso en segundo plano |
| Escaneo en tiempo real | `watchdog` Python / inotify | Monitoreo continuo del sistema de archivos |
| Infraestructura como Código | Terraform >= 1.5 (AWS) | Ver `informes/FD01-Informe-Factibilidad.md` |

---

## v2.1.0 — Seguridad Avanzada 🔄

**Fecha estimada**: Q3 2027  
**Estado**: Conceptual

| Feature | Descripción |
|:--------|:------------|
| Cifrado AES-256 en cuarentena | Reemplazar XOR con cifrado criptográfico real (`aes` crate Rust) |
| Sandbox básico | Entorno aislado para ejecutar archivos sospechosos |
| Reporte PDF | Exportación de resultados de escaneo a PDF |
| Soporte multi-idioma | ES / EN / PT |

---

## Cronograma Visual

```
2026 Q1-Q2  ████████████ v1.0.0 (Actual — Entregado)
2026 Q3-Q4  ░░░░░░░░░░░░ v1.1.0 (YARA, Whitelist, Auto-update)
2027 Q1-Q2  ░░░░░░░░░░░░ v2.0.0 (Cloud, Daemon, Real-time scan)
2027 Q3-Q4  ░░░░░░░░░░░░ v2.1.0 (AES-256, Sandbox, PDF reports)
```

---

## Issues relacionados

Las historias de usuario para cada versión están documentadas en el informe **FD03** (`informes/FD03-Historias-de-Usuario.md`) y gestionadas mediante **GitHub Issues** en el repositorio.
