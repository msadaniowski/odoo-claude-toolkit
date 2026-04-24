# Odoo Claude Toolkit

Colección de herramientas para Claude Code orientadas al trabajo diario con Odoo.

Instalable como **plugin de Claude Code**, o usando cada componente por separado.

## Herramientas incluidas

| Herramienta | Estado | Descripción |
|---|---|---|
| **Skill `audit-odoo`** (`skills/audit-odoo/`) | 🆕 Beta | Auditor de módulos Odoo antes de instalarlos: estructura, manifest, código Python/ORM, seguridad, vistas XML. Genera `.audit/AUDIT_REPORT.md`. Ver [`skills/audit-odoo/SKILL.md`](skills/audit-odoo/SKILL.md). |
| **Skill `audit-odoo-fix`** (`skills/audit-odoo-fix/`) | 🆕 Beta | A partir de un `AUDIT_REPORT.md`, genera `FIX_PLAN.md` con oleadas priorizadas y ejecuta los fixes uno a uno (un fix = un commit = chat fresco). Ver [`skills/audit-odoo-fix/SKILL.md`](skills/audit-odoo-fix/SKILL.md). |
| **Skill `enhance-odoo`** (`skills/enhance-odoo/`) | 🆕 Beta | Analiza un módulo Odoo y propone mejoras/nuevas features **validadas end-to-end** (negocio, técnico, UX, seguridad). Cada propuesta incluye trace de flujo, prerequisitos verificados, chequeo de colisiones con lógica existente y test automatizado. Descarta propuestas cuyo flujo no cierre. Genera `.enhance/ENHANCEMENT_REPORT.md`. Ver [`skills/enhance-odoo/SKILL.md`](skills/enhance-odoo/SKILL.md). |
| **Skill `enhance-odoo-fix`** (`skills/enhance-odoo-fix/`) | 🆕 Beta | A partir de `ENHANCEMENT_REPORT.md`, genera `ENHANCEMENT_PLAN.md` con 7 oleadas y ejecuta las mejoras una a una (una mejora = un commit = chat fresco). Oleadas de features requieren **test pasando** antes de marcar ✅. Ver [`skills/enhance-odoo-fix/SKILL.md`](skills/enhance-odoo-fix/SKILL.md). |
| **Skill `deadcode-odoo`** (`skills/deadcode-odoo/`) | 🆕 Beta | Análisis estático de un módulo Odoo: detecta métodos huérfanos, referencias rotas (button/field/compute a métodos/campos inexistentes), modelos aislados, XML IDs y valores de Selection sin uso. Cruza contra TODOS los addons del `addons_path` para no flagggear falsos positivos por herencia cross-module. Genera `.deadcode/DEADCODE_REPORT.md`. Ver [`skills/deadcode-odoo/SKILL.md`](skills/deadcode-odoo/SKILL.md). |
| **Skill `deadcode-odoo-fix`** (`skills/deadcode-odoo-fix/`) | 🆕 Beta | A partir de `DEADCODE_REPORT.md`, genera `DEADCODE_PLAN.md` en 7 oleadas y ejecuta las correcciones una a una (una corrección = un commit = chat fresco). **Gate humano obligatorio** antes de cada eliminación — el análisis estático no puede confirmar al 100% que algo es dead code. Ver [`skills/deadcode-odoo-fix/SKILL.md`](skills/deadcode-odoo-fix/SKILL.md). |
| **Skill `migrate-odoo`** (`skills/migrate-odoo/`) | 🆕 Beta | Orquestador del flujo fasado para **un módulo**. Detecta en qué fase estás y aplica el prompt correcto. Wrapper sobre la receta de `prompts/`. Ver [`skills/migrate-odoo/SKILL.md`](skills/migrate-odoo/SKILL.md). |
| **Skill `migrate-odoo-project`** (`skills/migrate-odoo-project/`) | 🆕 Beta | Orquestador a nivel **proyecto multi-módulo**. Escanea, arma grafo de dependencias, propone orden topológico en oleadas paralelizables, y delega cada módulo al skill `migrate-odoo`. Ver [`skills/migrate-odoo-project/SKILL.md`](skills/migrate-odoo-project/SKILL.md). |
| **Receta de migración** (`prompts/`, `template/`, `checklists/`) | ✅ Estable | Flujo manual por fases para migrar módulos entre versiones. Usable sin el skill, pegando prompts. Ver sección [Receta de migración](#receta-de-migración-de-módulos-odoo). |

## Instalación como plugin de Claude Code

Desde Claude Code:

```
/plugin install msadaniowski/odoo-claude-toolkit
```

O cloná el repo y apuntá tu `settings.json` al path local.

## Comandos rápidos

| Comando | Qué hace | Cuándo usarlo |
|---|---|---|
| `/audit-odoo <ruta_modulo>` | Auditoría estática del módulo (estructura, ORM, seguridad, XML). Produce informe Markdown con severidades en `.audit/AUDIT_REPORT.md`. | Antes de instalar/mergear un módulo, o antes de empezar a migrarlo. |
| `/audit-odoo-fix <ruta_modulo>` | Lee el informe, genera `FIX_PLAN.md` con oleadas priorizadas, y ejecuta los fixes uno a uno (chat fresco por tarea). | Después de `/audit-odoo`, para aplicar las correcciones en forma disciplinada. |
| `/enhance-odoo <ruta_modulo>` | Análisis propositivo: propone mejoras/nuevas features validadas end-to-end (descarta las que no cierran flujo, incluye test por cada una). Produce `.enhance/ENHANCEMENT_REPORT.md`. | Cuando el módulo está saneado y querés saber qué se le podría agregar sin romper nada. Recomendado después de `/audit-odoo-fix`. |
| `/enhance-odoo-fix <ruta_modulo>` | Lee el informe, genera plan en 7 oleadas, ejecuta mejoras una a una. Tests obligatorios en oleadas de features de negocio y UX. | Después de `/enhance-odoo`, para implementar las propuestas en forma disciplinada. |
| `/deadcode-odoo <ruta_modulo>` | Scan estático cross-módulo (AST + XML + CSV) que detecta código muerto/roto/desconectado. Produce `.deadcode/DEADCODE_REPORT.md` con findings 🔴🟡🔵. | Cuando sospechás que el módulo tiene lógica huérfana o vistas apuntando a cosas que no existen. Ideal después de refactors grandes o rondas largas de `/enhance-odoo-fix`. |
| `/deadcode-odoo-fix <ruta_modulo>` | Lee el informe de deadcode, genera plan en 7 oleadas, ejecuta correcciones una a una con gate humano obligatorio antes de eliminar cualquier item. | Después de `/deadcode-odoo`, para limpiar el módulo con disciplina (una eliminación = un commit = un chat fresco). |
| `/migrate-odoo <ruta_modulo>` | Migra UN módulo siguiendo el flujo fasado (intake → research → plan → execute → verify). | Módulo aislado, o invocado por el orquestador por cada módulo de una oleada. |
| `/migrate-odoo-project <ruta_carpeta>` | Orquesta migración de muchos módulos: grafo de dependencias, oleadas paralelizables, decisiones globales. | Tenés 2+ módulos con dependencias cruzadas que hay que migrar juntos. |

---

## Guía de uso paso a paso

Playbook completo para un proyecto multi-módulo. Si tenés UN módulo aislado, saltá al paso 4 invocando `/migrate-odoo` directo.

### 0. Preparar workspace (5 minutos)

```bash
# 1. Verificá que no tenés cambios sin commitear
cd /ruta/a/tu_proyecto_odoo
git status

# 2. Tag de seguridad antes de tocar nada
git tag pre-migration-$(date +%Y%m%d)

# 3. Branch para el trabajo de migración
git checkout -b migration/odoo-XX-to-YY

# 4. Backup reciente de la DB de producción (o una copia)
pg_dump -Fc mi_db_prod > ~/backups/prod-$(date +%Y%m%d).dump
```

**Regla**: nunca migrás sobre la única copia que tenés. Siempre contra una copia.

### 1. Auditoría previa — limpiar deuda técnica en la versión origen

Por cada módulo crítico (o todos si tenés tiempo), abrí Claude Code en la raíz del proyecto y corré:

```
/audit-odoo /ruta/a/tu_proyecto/addons/mi_modulo
```

Vas a obtener un informe con hallazgos clasificados por severidad:

- 🔴 **Crítico**: rompe instalación, vulnerabilidades (SQL injection, XSS), permisos abiertos.
- 🟠 **Alto**: bug funcional probable, N+1 severo, incompatibilidad con la versión declarada.
- 🟡 **Medio**: mala práctica moderada (`sudo()` sin justificar, etc.).
- 🔵 **Bajo** / ℹ️ **Info**: estilo, convenciones, sugerencias.

**Regla**: resolvé 🔴 y 🟠 **en la versión origen**, antes de migrar. Es 10x más barato que arreglarlos durante la migración.

Commits con formato: `audit(<modulo>): fix <descripción>`.

> **Tip**: podés auditar múltiples módulos en paralelo abriendo varios chats/ventanas de Claude Code, uno por módulo.

### 1.5. (Opcional) Mejoras antes de migrar

**Cuándo aplica**: si además de migrar querés aprovechar para sumar features nuevas o hacer refactors de oportunidad, y el módulo ya pasó por audit-fix.

**Cuándo NO aplica**: si el objetivo es solamente migrar versión, saltá este paso. Migrar + agregar features al mismo tiempo es una receta para confundirte sobre qué rompió qué.

```
/enhance-odoo /ruta/a/tu_proyecto/addons/mi_modulo
```

Produce `.enhance/ENHANCEMENT_REPORT.md` con propuestas validadas end-to-end (negocio, técnico, UX, seguridad). Cada propuesta trae:

- **Trace de flujo completo**: trigger → acceso → datos de soporte → procesamiento → salida → reversibilidad.
- **Chequeo de colisiones** con la lógica existente del módulo.
- **Test automatizado diseñado** (TransactionCase o HttpCase).
- **Prerequisitos explícitos**: qué hay que crear, qué ya está.

La skill **descarta** propuestas cuyo flujo no se pueda completar en el módulo actual (ej: un quiz por portal en un módulo sin portal configurado). Las descartadas aparecen en sección aparte del informe con razón explícita — son información útil, no basura.

Después del análisis, corré:

```
/enhance-odoo-fix /ruta/a/tu_proyecto/addons/mi_modulo
```

Genera `ENHANCEMENT_PLAN.md` con 7 oleadas (preparación → groundwork → técnico → seguridad → features de negocio → UX → docs/tests). Las oleadas de features tienen gate obligatorio: **el test diseñado tiene que pasar antes de marcar la tarea ✅**.

**Regla**: completar TODAS las oleadas de enhance-fix antes de arrancar la migración. Features nuevas a medio hacer + cambio de versión Odoo = pesadilla de debugging.

### 2. Orquestación del proyecto

En un chat **nuevo** de Claude Code:

```
/migrate-odoo-project /ruta/a/tu_proyecto/addons
```

El skill te va a pedir:

- Versión origen (ej: `15.0`)
- Versión destino (ej: `18.0`)
- Ruta de una DB de prueba (copia de prod)
- Restricciones de alcance (ej: "ignorá los módulos `*_old`")

**Output**: una carpeta `migration/` con:

```
migration/
├── PROJECT_MIGRATION.md       ← tablero maestro del proyecto
├── project_research.md        ← patrones cross-módulo y decisiones globales
├── dependency-graph.md        ← grafo ASCII + orden topológico
└── modules/
    ├── modulo_a/MIGRATION.md  ← uno por módulo, ya inicializado
    ├── modulo_b/MIGRATION.md
    └── ...
```

Los módulos quedan agrupados en **oleadas**:
- Oleada 1: módulos sin dependencias con otros módulos tuyos — se pueden migrar en **paralelo**.
- Oleada 2: dependen solo de la Oleada 1.
- Oleada N: dependen de oleadas anteriores.

### 3. Gate humano — revisar el plan ⚠️

**No lo saltees.** Abrí `PROJECT_MIGRATION.md` y revisá:

- ¿El orden de oleadas tiene sentido con lo que sabés del negocio?
- ¿Las **decisiones globales** propuestas te convencen? (ej: "todos los `<tree>` → `<list>`, todos los `@api.multi` se eliminan").
- ¿Algún módulo marcado como "dependencia externa" que en realidad es tuyo?
- ¿Ciclos reportados? (Odoo no permite ciclos de carga — hay que romperlos antes de seguir).

Si algo no cierra, pegás tus comentarios en el chat del orquestador y le pedís que ajuste `PROJECT_MIGRATION.md`. **No avanzar hasta que el plan te convenza.**

### 4. Migración por oleadas (ciclo principal)

Por cada módulo de la **Oleada actual**, abrí un chat **fresco** de Claude Code:

```
/migrate-odoo /ruta/a/tu_proyecto/migration/modules/mi_modulo
```

El skill detecta la fase en la que está el trabajo y avanza:

| Fase | Qué hace | Gate |
|---|---|---|
| 0. Intake | Completa `MIGRATION.md` §0 con info básica. | — |
| 1. Research | Investiga el módulo + delta entre versiones. Produce `research.md`. | Revisar `research.md`. |
| 2. Plan | Divide el trabajo en tareas atómicas. Produce `plan.md`. | **Gate principal — revisar `plan.md` antes de avanzar.** |
| 3. Execute | Implementa **UNA tarea** de `plan.md`. | Después de cada tarea, **chat nuevo**. |
| 4. Verify | Corre tests, genera `verification.md`. | Revisar gates manuales. |

**Reglas duras de Fase 3:**

- **Una tarea = un commit = un chat fresco.** Cuando el skill termina una tarea, te dice "abrí un chat nuevo para la próxima". **Hacelo.**
- No batches tareas en el mismo chat — la IA pierde contexto y empieza a tomar atajos.
- Si una tarea no pasa verificación, el skill para y te avisa. No forzar — diagnosticar.

**Paralelización dentro de una oleada**: abrí 2-3 chats simultáneos, cada uno con un módulo distinto de la misma oleada. No más — el cuello de botella real es tu capacidad de revisar planes.

### 5. Fin de oleada — volver al orquestador

Cuando todos los módulos de una oleada tienen ✅ en `PROJECT_MIGRATION.md`, volvé al chat del orquestador (o invocá de nuevo):

```
/migrate-odoo-project /ruta/a/tu_proyecto/addons
```

Detecta el progreso y habilita la próxima oleada. Repetí hasta completar todas.

Entre oleadas es buen momento para correr tests de integración cruzada si existen.

### 6. Verify final (el gate real de "listo")

Con todas las oleadas verdes:

```bash
# Restaurar copia de DB de prod en un entorno de test
pg_restore -d test_db ~/backups/prod-XXXX.dump

# Upgrade de TODOS los módulos
odoo -d test_db -u all --stop-after-init --addons-path=/ruta/a/tu_proyecto/addons,...
```

**Gates finales:**

- [ ] `-u all` corre sin errores sobre copia de DB de producción.
- [ ] Smoke tests manuales de los flujos críticos del negocio pasan.
- [ ] Tests automatizados verdes.
- [ ] Plan de rollback documentado en `verification.md`.

Recién cuando todo esto esté verde, merge a `main` y deploy.

---

## Checklist resumen

- [ ] Backup git + DB de producción
- [ ] Branch `migration/...`
- [ ] `/audit-odoo` en cada módulo, fix 🔴 y 🟠 en versión origen
- [ ] (Opcional) `/enhance-odoo` + `/enhance-odoo-fix` si además vas a sumar features — completar antes de migrar
- [ ] `/migrate-odoo-project` genera plan de oleadas
- [ ] **Revisión humana del `PROJECT_MIGRATION.md`** (gate crítico)
- [ ] Oleada 1 — `/migrate-odoo` por cada módulo en chats frescos
- [ ] Oleada 2, 3, ... — repetir
- [ ] `-u all` sobre copia de DB de producción
- [ ] Smoke tests manuales de flujos críticos
- [ ] Merge a `main` / deploy

---

## Errores comunes que conviene evitar

1. **Saltarse el audit**: "dale, es un módulo simple" → en Fase 3 aparece un `sudo()` mal puesto que rompe algo. El audit previo paga con creces.
2. **Reusar el mismo chat para varias tareas de Fase 3**: la IA pierde contexto y hace atajos silenciosos. **Chat fresco por tarea, siempre.**
3. **Testear solo con demo data**: la mayoría de los bugs aparecen con volúmenes y datos reales. Usar copia de prod es obligatorio.
4. **Migrar cuando estás cansado**: los gates humanos (revisar `research.md`, `plan.md`, `verification.md`) son el único filtro real. Si no vas a revisar bien, pausá.
5. **Ignorar decisiones globales**: si en `PROJECT_MIGRATION.md` decidiste "todos los `<tree>` → `<list>`", todos los módulos siguen eso. No renegociar en cada módulo — ahí perdés coherencia.
6. **Paralelizar demasiado**: tener 5 chats abiertos suena productivo hasta que tenés 5 planes para revisar al mismo tiempo y no revisás ninguno bien. Máximo 2-3 en paralelo.

---

## Recomendación antes de tirarte al proyecto completo

Antes de orquestar 20+ módulos, **probá el flujo con UNO chico** para calibrar:

1. Elegí un módulo de la Oleada 1 (sin dependencias custom).
2. Corré `/audit-odoo` → fixear lo crítico.
3. Corré `/migrate-odoo` → hacé el flujo entero.
4. Anotá dónde se trabó o qué check faltó.

Una vez que viste el flujo en vivo, sabés si el toolkit necesita ajustes antes de escalar.

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
