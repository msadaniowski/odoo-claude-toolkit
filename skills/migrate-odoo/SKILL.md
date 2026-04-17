---
name: migrate-odoo
description: Orquestador del flujo fasado de migración de módulos Odoo entre versiones (intake → research → plan → execute → verify). Detecta en qué fase está el trabajo y aplica el prompt correcto del repo. Uso - /migrate-odoo <ruta_modulo_o_migracion>
---

# Migrador de módulos Odoo (flujo fasado)

Este skill **orquesta** la receta fasada de migración que vive en `prompts/`, `template/`, `checklists/` del mismo repo. No duplica los prompts — los referencia.

## Principio central — contexto fresco por tarea

La receta se rompe si intentás hacer múltiples fases (especialmente Phase 3 con múltiples tareas) en el mismo chat. Si detectás que esto va a pasar, **pará y pedile al usuario que abra un chat nuevo**. Esta regla no es negociable.

## Uso

El usuario invoca con `/migrate-odoo <ruta>`. La ruta puede ser:
- Un **módulo Odoo** sin `MIGRATION.md` todavía → arrancás en Fase 0 (Intake).
- Una **carpeta de migración** que ya tiene `MIGRATION.md` → detectás la fase actual y seguís.

Si no hay ruta, pedila.

## Fase 0 — Detección del estado

Leé (si existen):
1. `<ruta>/__manifest__.py` — para saber si es un módulo directo.
2. `<ruta>/MIGRATION.md` — para saber en qué fase está el trabajo.
3. `<ruta>/research.md`, `plan.md`, `verification.md`.

Determiná la fase actual:

| Estado | Fase a ejecutar |
|---|---|
| No hay `MIGRATION.md` | **Fase 0 (Intake)** — crear desde `template/MIGRATION.md` |
| `MIGRATION.md` existe, §0 Intake vacío | **Fase 0 (Intake)** |
| §0 completo, sin `research.md` | **Fase 1 (Research)** |
| `research.md` existe, sin `plan.md` | **Fase 2 (Plan)** |
| `plan.md` existe, tareas pendientes | **Fase 3 (Execute)** — UNA tarea |
| Todas las tareas hechas, sin `verification.md` | **Fase 4 (Verify)** |
| `verification.md` con todos los gates verdes | **Terminado** |

Anunciá al usuario: "Detecté fase X. Voy a aplicar el prompt de esa fase. ¿OK?".

## Aplicación de cada fase

Para cada fase, **leé el archivo de prompt del repo** y seguí sus instrucciones al pie:

| Fase | Prompt | Output esperado |
|---|---|---|
| 0 Intake | `prompts/00-intake.md` | §0 de `MIGRATION.md` completo |
| 1 Research | `prompts/01-research.md` | `research.md` completo + §1 de `MIGRATION.md` (summary) |
| 2 Plan | `prompts/02-plan.md` | `plan.md` con tareas atómicas |
| 3 Execute | `prompts/03-execute-task.md` | **UNA tarea** implementada + commit + `MIGRATION.md` §3 actualizado |
| 4 Verify | `prompts/04-verify.md` | `verification.md` con gates |

**Importante**: los prompts están en inglés pero el trabajo con el usuario es en español (registro argentino). Traducí las preguntas al español al dialogar, pero seguí la semántica del prompt.

## Reglas duras (de la receta original)

No son negociables — son las lecciones de cada migración que salió mal:

1. **Nunca salteés Fase 2 (Plan)**. "Dale, arranquemos a portear" es la causa #1 de migraciones de una semana que podrían haber llevado un día.
2. **Una tarea = un commit = un contexto fresco**. Si estás en Phase 3 y ya ejecutaste una tarea en este chat, **no empezar otra** — decile al usuario que abra un chat nuevo.
3. **Tests primero, después código**. Si el módulo original no tiene tests sobre el camino de riesgo, Fase 2 tiene que agregarlos antes de que Fase 3 toque el código.
4. **El upgrade sobre DB real es el único test real**. `-u módulo` sobre una copia de datos de producción es el gate de "listo".
5. **Las transformaciones mecánicas no son la migración**. `odoo-module-migrator` es el paso cero, no el paso final.
6. **Leé OpenUpgrade primero**. Si OCA ya porteó los modelos que tu módulo toca, usá sus `pre/post-migration.py` como referencia.

## Checklists disponibles

Consultálos según la fase:

- `checklists/odoo-version-deltas.md` — breaking changes conocidos por versión (Fase 1).
- `checklists/mechanical-transforms.md` — qué automatizar vs hacer a mano (Fase 2–3).
- `checklists/gates.md` — qué tiene que estar verde para declarar "listo" (Fase 4).

## Scripts auxiliares

En `scripts/`:

- `bootstrap.sh` — inicializa carpeta de migración nueva (útil en Fase 0).
- `run-module-migrator.sh` — wrapper del `odoo-module-migrator` de OCA (útil en Fase 3, transformaciones mecánicas).
- `upgrade-test-db.sh` — levanta DB de test y hace el `-u <modulo>` (útil en Fase 4).

Sugerilos cuando corresponda, no los ejecutes sin confirmación del usuario.

## Flujo de diálogo sugerido

1. Usuario invoca `/migrate-odoo <ruta>`.
2. Detectás la fase y la anunciás en español.
3. Leés el prompt correspondiente del repo.
4. Aplicás el prompt (traducido al diálogo, pero respetando su semántica).
5. Cuando termines la fase, imprimís exactamente el marker que indica el prompt original (ej: `RESEARCH COMPLETE — ready for Phase 2 (Plan)`).
6. Para Fase 3: **después de UNA tarea, parás**. Decile al usuario:
   > "Tarea TXX completa. Para la próxima tarea, abrí un chat nuevo e invocá `/migrate-odoo <ruta>` de nuevo — voy a detectar que sigue Phase 3 y seguiremos con la siguiente tarea."

## Cosas que NO hacés

- No ejecutar múltiples fases en el mismo chat (excepto Intake → Research si el usuario insiste y el módulo es muy chico — advertir).
- No saltearte la revisión humana entre fases. `PLAN READY FOR REVIEW` significa que parás hasta que el humano dé OK.
- No modificar `prompts/`, `template/` ni `checklists/` del repo — ese es código del toolkit, no de la migración en curso.
- No ejecutar scripts de `scripts/` sin confirmación explícita del usuario.

## Integración con `audit-odoo`

Si en Fase 1 (Research) encontrás que el módulo original tiene problemas graves de estructura (antes incluso de la migración), sugerí correr `/audit-odoo <ruta>` primero para limpiar lo que pueda hacerse **en la versión origen**. Una migración sobre un módulo mal estructurado es más difícil.
