# 📋 GitHub Projects — Gestión del Proyecto RustGuard

## Descripción General

RustGuard utiliza **GitHub Projects** (tablero Kanban) para gestionar el flujo de trabajo de desarrollo. Este documento describe la estructura de ramas, el flujo de trabajo y la relación entre issues y tareas del proyecto.

---

## 1. Estrategia de Ramas (Git Flow)

### Estructura de ramas

```
main
├── develop
│   ├── feature/rust-scan-engine
│   ├── feature/heuristic-engine
│   ├── feature/quarantine-xor
│   ├── feature/scan-history-json
│   ├── feature/customtkinter-gui
│   └── fix/cancellation-token-race-condition
└── hotfix/signature-db-corruption
```

### Descripción de cada tipo de rama

| Rama | Propósito | Origen | Destino |
|:-----|:----------|:------:|:-------:|
| `main` | Producción — solo releases estables y etiquetados | — | — |
| `develop` | Integración continua de features | `main` | `main` (merge en release) |
| `feature/<nombre>` | Desarrollo de una historia de usuario específica | `develop` | `develop` |
| `fix/<nombre>` | Corrección de bugs no críticos | `develop` | `develop` |
| `hotfix/<nombre>` | Parches urgentes en producción | `main` | `main` + `develop` |

### Convención de nombres de ramas

```
feature/HU-01-quick-scan
feature/HU-07-quarantine-xor
fix/HU-04-cancel-token-thread-safety
hotfix/v1.0.1-signature-db-index
```

---

## 2. Tablero Kanban (GitHub Projects)

### Columnas del tablero

| Columna | Descripción | Criterio de entrada | Criterio de salida |
|:--------|:------------|:-------------------:|:------------------:|
| 📋 **Backlog** | Issues creados pero no priorizados | Issue abierto | Priorización en sprint |
| 🎯 **Sprint Actual** | Issues del sprint en curso | Asignación en planning | Inicio de desarrollo |
| 🔨 **En Progreso** | Issue asignado, rama creada, desarrollo activo | Branch `feature/` creado | PR abierto |
| 👀 **En Revisión** | Pull Request abierto, esperando review | PR creado | Review aprobado + CI verde |
| ✅ **Completado** | Merge realizado, issue cerrado | PR merged | — |

---

## 3. Estructura de Issues

### Plantilla de Historia de Usuario (Issue)

```markdown
## Historia de Usuario
**Como** [tipo de usuario]  
**Quiero** [funcionalidad]  
**Para** [beneficio]

## Criterios de Aceptación
- [ ] CA-XX-1: descripción
- [ ] CA-XX-2: descripción
- [ ] CA-XX-3: descripción

## Escenarios de Prueba
Ver documento FD03 — Escenario N

## Notas Técnicas
- Referencia de código: `ruta/al/archivo.py`
- Dependencias: HU-XX

## Estimación
Story Points: N
```

### Etiquetas (Labels)

| Label | Color | Uso |
|:------|:-----:|:----|
| `feature` | 🟢 Verde | Nueva funcionalidad |
| `bug` | 🔴 Rojo | Defecto a corregir |
| `documentation` | 🔵 Azul | Documentación |
| `high-priority` | 🟠 Naranja | Crítico para el sprint |
| `rust` | 🟤 Marrón | Requiere cambios en scan_engine |
| `python` | 🟡 Amarillo | Solo requiere cambios en gui/ |
| `security` | 🔴 Rojo oscuro | Relacionado con seguridad |

---

## 4. Relación Issues ↔ Historias de Usuario ↔ Código

| Issue GitHub | Historia de Usuario | Módulo | Rama |
|:-------------|:--------------------|:-------|:-----|
| #1 | HU-01 — Escaneo Rápido | `ScanUseCase`, `constants.py` | `feature/HU-01-quick-scan` |
| #2 | HU-02 — Escaneo Completo | `ScanUseCase`, `lib.rs::scan_directory` | `feature/HU-02-full-scan` |
| #3 | HU-03 — Escaneo Custom | `ScanType.CUSTOM`, `main_window.py` | `feature/HU-03-custom-scan` |
| #4 | HU-04 — Cancelación | `CancellationToken`, `cancel_scan()` | `feature/HU-04-cancellation` |
| #5 | HU-05 — Detección por Firma | `SignatureDb`, `compute_hashes()` | `feature/HU-05-signature-detection` |
| #6 | HU-06 — Heurística | `HeuristicEngine::analyze()` | `feature/HU-06-heuristic-engine` |
| #7 | HU-07 — Cuarentena | `JsonQuarantineRepository`, `_xor_file()` | `feature/HU-07-quarantine` |
| #8 | HU-08 — Restauración | `restore_file()`, `_dexor_file()` | `feature/HU-08-restore` |
| #9 | HU-09 — Eliminar de Cuarentena | `delete_quarantined()` | `feature/HU-09-delete-quarantine` |
| #10 | HU-10 — Historial | `HistoryUseCase`, `JsonScanRepository` | `feature/HU-10-scan-history` |
| #11 | HU-11 — Importar Firmas | `import_signatures_json()` | `feature/HU-11-import-signatures` |
| #12 | HU-12 — Progreso en Tiempo Real | Callback en `scan_directory()` | `feature/HU-12-realtime-progress` |

---

## 5. Flujo de Trabajo Completo

```
1. Crear Issue con plantilla de Historia de Usuario
       ↓
2. Agregar al Backlog del GitHub Project
       ↓
3. Sprint Planning: mover a "Sprint Actual", asignar, estimar story points
       ↓
4. Inicio de desarrollo: crear rama feature/HU-XX-nombre desde develop
       ↓
5. Mover Issue a "En Progreso" y asignarse
       ↓
6. Desarrollo + commits con convención: "feat: descripción (#N)"
       ↓
7. Abrir Pull Request hacia develop
       ↓
8. Mover Issue a "En Revisión"
       ↓
9. GitHub Actions ejecuta: cargo build, ruff lint, semgrep scan
       ↓
10. Code Review por al menos 1 colaborador
       ↓
11. Merge del PR (squash merge recomendado)
       ↓
12. Issue cerrado automáticamente (si PR incluye "Closes #N")
       ↓
13. Mover tarjeta a "Completado"
```

---

## 6. Métricas del Proyecto

### Velocidad por Sprint (Story Points completados)

| Sprint | Semanas | Stories completadas | Points |
|:-------|:-------:|:-------------------:|:------:|
| Sprint 1 | 1-3 | HU-05, HU-06 (motor de detección) | 13 |
| Sprint 2 | 4-6 | HU-01, HU-02, HU-03, HU-04 (tipos de escaneo) | 13 |
| Sprint 3 | 7-10 | HU-07, HU-08, HU-09, HU-12 (cuarentena + progreso) | 13 |
| Sprint 4 | 11-14 | HU-10, HU-11 (historial + firmas) | 6 |
| Sprint 5 | 15-16 | Integración final, documentación, release v1.0.0 | — |

### Definición de "Done"

Un issue se considera **completado** cuando:

- [ ] El código ha sido mergeado a `develop`
- [ ] Los criterios de aceptación están verificados
- [ ] El pipeline CI/CD pasa sin errores
- [ ] La documentación relacionada está actualizada
- [ ] No hay regresiones en funcionalidades existentes
