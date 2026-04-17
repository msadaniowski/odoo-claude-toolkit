# Odoo Claude Toolkit

Colección de herramientas para Claude Code orientadas al trabajo diario con Odoo.

Instalable como **plugin de Claude Code**, o usando cada componente por separado.

## Herramientas incluidas

| Herramienta | Estado | Descripción |
|---|---|---|
| **Skill `audit-odoo`** (`skills/audit-odoo/`) | 🆕 Beta | Auditor de módulos Odoo antes de instalarlos: estructura, manifest, código Python/ORM, seguridad, vistas XML. Ver [`skills/audit-odoo/SKILL.md`](skills/audit-odoo/SKILL.md). |
| **Skill `migrate-odoo`** (`skills/migrate-odoo/`) | 🆕 Beta | Orquestador del flujo fasado de migración — detecta en qué fase estás y aplica el prompt correcto. Wrapper sobre la receta de `prompts/`. Ver [`skills/migrate-odoo/SKILL.md`](skills/migrate-odoo/SKILL.md). |
| **Receta de migración** (`prompts/`, `template/`, `checklists/`) | ✅ Estable | Flujo manual por fases para migrar módulos entre versiones. Usable sin el skill, pegando prompts. Ver sección [Receta de migración](#receta-de-migración-de-módulos-odoo). |

## Instalación como plugin de Claude Code

Desde Claude Code:

```
/plugin install msadaniowski/odoo-claude-toolkit
```

O cloná el repo y apuntá tu `settings.json` al path local.

## Uso de cada skill

- **Auditor**: `/audit-odoo <ruta_al_modulo>` — produce un informe Markdown con severidades (crítico/alto/medio/bajo), adaptado a la versión de Odoo declarada en `__manifest__.py`.
- **Migrador**: `/migrate-odoo <ruta_modulo_o_migracion>` — detecta la fase del trabajo de migración y aplica el prompt correspondiente. Respeta la regla de un chat fresco por tarea en Fase 3.

---

# Receta de Migración de Módulos Odoo

Una **receta guiada por especificación, dividida en fases** para migrar módulos de Odoo entre versiones, diseñada para trabajar con asistentes de IA (Claude Code, Codex, Cursor, etc.).

Inspirada en el flujo de [GSD (Get Shit Done)](https://github.com/gsd-build/get-shit-done), adaptada a las realidades de una migración de Odoo: `OpenUpgrade`, guías de OCA, transformaciones mecánicas, y las decisiones humanas que siempre quedan.

---

## Por qué existe

Migrar un módulo de Odoo **nunca** es un ejercicio puro de "correr el codemod". Siempre hay:

- Cambios mecánicos (renombres de API, atributos deprecados, bump de manifest) → automatizable
- Cambios semánticos (lógica de negocio que depende de comportamiento que cambió) → requiere entender
- Cambios de forma de los datos (campos renombrados, modelos fusionados/divididos) → requiere scripts de OpenUpgrade
- Superficie de regresión (tests, datos demo, vistas) → requiere verificación

Esta receta divide el trabajo en **5 fases** para que la IA trabaje en chunks pequeños y verificables con contexto fresco, en vez de intentar portar un módulo entero de una sola vez (lo cual falla).

---

## Las fases

```
┌───────────┐   ┌──────┐   ┌──────┐   ┌──────────┐   ┌────────────┐
│ 0. Intake │ → │ 1.   │ → │ 2.   │ → │ 3.       │ → │ 4.         │
│           │   │ Inv. │   │ Plan │   │ Ejecutar │   │ Verificar  │
└───────────┘   └──────┘   └──────┘   └──────────┘   └────────────┘
```

| Fase | Objetivo | Output | Quién lidera |
|------|----------|--------|--------------|
| 0. Intake | Capturar la solicitud de migración, alcance, restricciones | semilla de `MIGRATION.md` | Humano |
| 1. Investigación | Entender cambios de la versión target + estado actual del módulo | `research.md` | IA |
| 2. Plan | Dividir el trabajo en tareas atómicas con criterios de aceptación | `plan.md` | IA + revisión humana |
| 3. Ejecutar | Aplicar cambios tarea por tarea, cada una en contexto fresco | Commits por tarea | IA |
| 4. Verificar | Correr tests, QA manual, upgrade sobre copia de DB real | `verification.md` | IA + Humano |

---

## Cómo usarla

1. **Copiá** la carpeta `template/` dentro del repo de tu módulo (o en una carpeta hermana).
2. **Completá** `template/MIGRATION.md` con las 3 cosas que solo vos sabés: versión origen, versión destino, path del módulo.
3. **Abrí** el módulo en Claude Code / Codex y pegá el **prompt de Fase 1** de `prompts/01-research.md`.
4. **Revisá** el `research.md` que generó la IA — este es tu primer gate.
5. **Pegá el prompt de Fase 2** → revisá `plan.md` → **este es el gate principal, no lo saltes**.
6. Para cada tarea del `plan.md`, pegá el **prompt de Fase 3** en una ventana de chat fresca (importante: contexto fresco por tarea).
7. Cuando todas las tareas estén hechas, pegá el **prompt de Fase 4** para correr la suite de verificación.

Ver [`docs/workflow.md`](docs/workflow.md) para el flujo completo con diagramas.

---

## Qué hay en la caja

```
odoo-claude-toolkit/
├── README.md                       ← estás acá
├── template/                       ← copiá esto a tu proyecto
│   ├── MIGRATION.md                ← fuente única de verdad de esta migración
│   ├── research.md                 ← completa la Fase 1
│   ├── plan.md                     ← completa la Fase 2
│   └── verification.md             ← completa la Fase 4
├── prompts/                        ← pegá esto en Claude/Codex
│   ├── 00-intake.md
│   ├── 01-research.md
│   ├── 02-plan.md
│   ├── 03-execute-task.md
│   └── 04-verify.md
├── checklists/
│   ├── odoo-version-deltas.md      ← breaking changes conocidos por versión
│   ├── mechanical-transforms.md    ← qué automatizar vs hacer a mano
│   └── gates.md                    ← checklist de "no avanzar hasta que..."
├── scripts/
│   ├── bootstrap.sh                ← inicializa una nueva migración
│   ├── run-module-migrator.sh      ← wrapper de OCA odoo-module-migrator
│   └── upgrade-test-db.sh          ← levanta DB de test y hace el upgrade
└── docs/
    ├── workflow.md
    ├── tools.md                    ← OpenUpgrade, oca-port, module-migrator
    └── why-phases.md
```

---

## Reglas de la receta

Estas reglas no son negociables — son las lecciones de cada migración de Odoo que salió mal:

1. **Nunca saltes la Fase 2 (Plan).** "Dale, arranquemos a portear" es la causa #1 de migraciones de una semana que podrían haber llevado un día.
2. **Una tarea = un commit = un contexto fresco de IA.** No dejes que la IA batchee tareas.
3. **Tests primero, después código.** Si el módulo original no tiene tests sobre el camino de riesgo, la Fase 2 tiene que agregarlos antes de que la Fase 3 toque el código.
4. **El upgrade sobre DB real es el único test real.** `-u módulo` sobre una copia de datos de producción es el gate de "listo".
5. **Las transformaciones mecánicas no son la migración.** `odoo-module-migrator` es el paso cero, no el paso final.
6. **Leé OpenUpgrade primero.** Si OCA ya porteó los modelos que tu módulo toca, usá sus `pre/post-migration.py` como referencia.

---

## Créditos y referencias

- [OCA OpenUpgrade](https://github.com/OCA/OpenUpgrade) — la referencia para migración a nivel de DB
- [OCA Migration Guidelines](https://github.com/OCA/maintainer-tools/wiki) — el checklist de la comunidad
- [OCA odoo-module-migrator](https://github.com/OCA/odoo-module-migrator) — transformaciones mecánicas
- [OCA oca-port](https://github.com/OCA/oca-port) — portear commits entre versiones
- [GSD: Get Shit Done](https://github.com/gsd-build/get-shit-done) — el enfoque de meta-prompting en el que está modelada esta receta
