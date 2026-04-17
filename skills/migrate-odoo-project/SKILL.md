---
name: migrate-odoo-project
description: Orquestador para migrar múltiples módulos Odoo a una versión nueva. Escanea carpeta, construye grafo de dependencias, propone orden topológico, agrupa independientes para paralelizar, y tracklea el progreso. NO ejecuta la migración módulo por módulo — delega al skill migrate-odoo. Uso - /migrate-odoo-project <ruta_carpeta_con_modulos>
---

# Orquestador de migración de proyecto Odoo

Este skill es el **planner a nivel proyecto**. No migra módulos — orquesta la migración de muchos módulos respetando dependencias, paralelizando lo que se puede, y manteniendo disciplina de chat fresco por tarea.

## Cuándo usar este skill vs `migrate-odoo`

| Skill | Usar cuando |
|---|---|
| `/migrate-odoo <ruta_modulo>` | Migrás UN módulo aislado (sin otros módulos tuyos que dependan de él o que dependan suyo). |
| `/migrate-odoo-project <ruta_carpeta>` | Tenés **2+ módulos propios** en un mismo proyecto que hay que migrar juntos, y/o hay dependencias entre ellos. |

Regla práctica: si tenés más de 2 módulos custom, usá este skill. El overhead es mínimo y te ahorra dolores de cabeza de orden.

## Lo que este skill **no** hace

- No modifica código de módulos.
- No ejecuta la migración módulo por módulo — eso lo hace `/migrate-odoo` en chats separados.
- No decide por vos las versiones origen/destino — te las pide.
- No te excusa de revisar el plan antes de arrancar.

## Flujo

Trabajá en español (registro argentino). Usá TodoWrite para las 5 fases.

### Fase A — Intake del proyecto

1. Confirmar ruta: debe contener varias carpetas-módulo (cada una con `__manifest__.py`).
2. Pedir al usuario:
   - Versión origen (ej: 15.0)
   - Versión destino (ej: 18.0)
   - ¿Hay una DB de producción de la que podemos hacer copia para test? (crítico para Fase 4 del skill por-módulo)
   - ¿Restricciones de alcance? (ej: "migrar solo los activos en producción, ignorar `*_old`")
3. **No arrancar el escaneo hasta tener estas respuestas.**

### Fase B — Escaneo e inventario

1. Listar con Glob todas las carpetas bajo `<ruta>` que contengan `__manifest__.py` directamente (primer nivel).
2. Para cada módulo, leer `__manifest__.py` y extraer:
   - `name`, `version`, `depends`, `application` (bool), `installable`, `license`.
   - Módulos Python importados (`__init__.py`) — útil para verificar imports rotos.
3. Clasificar módulos:
   - **Propios del proyecto**: los que están en la carpeta.
   - **Dependencias core/OCA**: los que aparecen en `depends` pero no son propios.
4. Advertir:
   - Módulos con `installable=False` → ¿descartar o migrar igual?
   - Módulos que dependen de otros que **no están en la carpeta** y no son core conocidos → ¿dependencia externa? ¿módulo faltante?

### Fase C — Grafo de dependencias y orden topológico

1. Construir el grafo dirigido: nodos = módulos propios; aristas = `modulo_a` → `modulo_b` si `b` ∈ `a.depends`.
2. **Detección de ciclos**: si hay ciclo, ERROR. Odoo no permite ciclos de carga. Pedir al usuario que revise.
3. **Topological sort**: producir orden de migración. Los módulos sin dependencias entre sí pueden migrarse en **cualquier orden** → oportunidad de paralelización.
4. **Agrupar en "oleadas"** (waves): cada oleada contiene módulos que no dependen entre sí y cuyas dependencias están en oleadas anteriores. Ejemplo:

   ```
   Oleada 1: [modulo_a, modulo_z]           ← sin deps entre nuestros módulos
   Oleada 2: [modulo_b (dep: a), modulo_c (dep: a)]
   Oleada 3: [modulo_d (dep: b, c)]
   ```

   Dentro de una oleada, **los módulos se pueden migrar en chats paralelos**. Entre oleadas, hay que terminar la anterior antes de arrancar la siguiente.

### Fase D — Research cross-módulo

1. Consultar `checklists/odoo-version-deltas.md` del toolkit para los breaking changes entre versión origen y destino.
2. Para cada breaking change, grepear **todos los módulos propios** para ver cuáles se ven afectados. Ejemplo:
   - "En 17.0 `tree` pasó a `list` en XML" → `grep -r "<tree " modulos_propios/` → lista de archivos afectados.
   - "En 16.0 deprecated `@api.multi`" → `grep -r "@api.multi" modulos_propios/` → lista.
3. Agrupar los hallazgos por **tipo de cambio** (no por módulo). Esto identifica patrones repetitivos.
4. Proponer **decisiones globales**: "para este patrón, todos los módulos hacen X". Esto se anota en `PROJECT_MIGRATION.md` §Decisiones globales y se referencia desde cada `MIGRATION.md` individual.
5. Cross-reference con OpenUpgrade: para cada modelo core que tus módulos extienden, verificar si OCA ya portó ese modelo en la versión destino — ahorra horas.

### Fase E — Generación de artefactos

Crear en `<ruta>` o en `<ruta>/../migration/`:

```
migration/
├── PROJECT_MIGRATION.md           ← fuente única de verdad del proyecto
├── project_research.md            ← research cross-módulo
├── dependency-graph.md            ← grafo en ASCII + DOT si es útil
└── modules/
    ├── modulo_a/
    │   └── MIGRATION.md           ← inicializado con §0 Intake + link a decisiones globales
    ├── modulo_b/
    │   └── MIGRATION.md
    └── ...
```

**`PROJECT_MIGRATION.md`** debe contener:

```markdown
# Migración de proyecto: <nombre>

**De:** Odoo X.0 → **A:** Odoo Y.0
**Iniciado:** <fecha>
**Módulos:** N propios detectados

## Decisiones globales
- [Decisión 1]: <patrón> → <solución estándar>
- ...

## Grafo de dependencias

<ver dependency-graph.md>

## Plan de migración por oleadas

### Oleada 1 — paralelizable
- [ ] `modulo_a` → `modules/modulo_a/MIGRATION.md`
- [ ] `modulo_z` → `modules/modulo_z/MIGRATION.md`

### Oleada 2 — paralelizable (bloqueada hasta completar Oleada 1)
- [ ] `modulo_b` (depende: `modulo_a`)
- [ ] `modulo_c` (depende: `modulo_a`)

### Oleada 3
- [ ] `modulo_d` (depende: `modulo_b`, `modulo_c`)

## Gates globales

- [ ] Todas las oleadas completadas (módulo por módulo verificado)
- [ ] `-u all` sobre copia de DB de producción funciona
- [ ] Tests de integración cruzada verdes
- [ ] Smoke test manual sobre los flujos críticos del negocio
```

Cada `modules/<modulo>/MIGRATION.md` se inicializa con:
- §0 Intake precompletado (versiones, ruta, link al research global).
- Recordatorio: "Leé `PROJECT_MIGRATION.md` §Decisiones globales antes de arrancar Fase 2".
- Info de dependencias dentro del grafo ("este módulo depende de: [...] que ya deben estar migrados").

### Fase F — Instrucciones al usuario

Al terminar, imprimí:

```
✅ Proyecto orquestado. N módulos detectados, K oleadas.

**Próximo paso**: arrancá por la Oleada 1.
Podés hacer los módulos de la Oleada 1 **en paralelo** en chats separados:

  Terminal 1: /migrate-odoo migration/modules/modulo_a/
  Terminal 2: /migrate-odoo migration/modules/modulo_z/

Cada invocación correrá el flujo fasado completo (intake → research → plan → execute → verify) para UN módulo.

Cuando toda la Oleada 1 esté verde, volvé acá y decime "oleada 1 lista" — voy a validar y habilitarte la Oleada 2.

PROJECT MIGRATION READY — empezá la Oleada 1.
```

## Loop de seguimiento (invocaciones posteriores)

Cuando el usuario vuelve a invocar `/migrate-odoo-project` en la misma ruta después de haber completado módulos:

1. Leer `PROJECT_MIGRATION.md` y detectar cuántos checkboxes están marcados.
2. Leer cada `modules/*/MIGRATION.md` y detectar cuáles tienen `verification.md` completo → marcarlos como ✅ en `PROJECT_MIGRATION.md`.
3. Informar: oleada actual, módulos pendientes, próxima oleada.
4. Si el usuario terminó una oleada completa → sugerir correr tests de integración cruzada antes de la siguiente.

## Reglas duras

1. **Nunca empezar una oleada sin terminar la anterior.** El orden topológico no es opcional — si migrás `b` (que depende de `a`) antes que `a`, el install falla.
2. **Nunca proponer migrar más de una oleada en el mismo chat.** Dentro de una oleada, cada módulo es un chat separado vía `/migrate-odoo`.
3. **`-u all` sobre DB real es el gate final del proyecto**, no el de cada módulo. Cada módulo tiene su propio `-u <modulo>` en Fase 4.
4. **Decisiones globales se definen UNA vez** en `PROJECT_MIGRATION.md` y se aplican en todos los módulos. No renegociar en cada módulo.
5. **Los ciclos en el grafo son ERROR bloqueante.** No intentar resolverlos automático — pedir al usuario que decida cómo romper el ciclo (normalmente extrayendo un módulo común).
6. **No usar este skill para módulos 100% independientes entre sí.** Si no hay dependencias cruzadas entre tus módulos, conviene `/migrate-odoo` directo por cada uno — este skill agrega overhead.

## Paralelización — cuándo conviene

La paralelización de oleadas es **útil**, pero solo si:
- Tenés tiempo de revisar múltiples `plan.md` en paralelo (la revisión humana es el cuello de botella real).
- Los módulos comparten pocos modelos. Si dos módulos de la misma oleada tocan `res.partner` de formas distintas, el merge puede traer conflictos — mejor serie.

Si no estás seguro, **hacé serie dentro de cada oleada**. Es menos rápido pero menos riesgoso.

## Integración con el resto del toolkit

- **Antes de Fase A**: considerar correr `/audit-odoo <modulo>` sobre cada módulo para identificar deuda técnica que querés limpiar antes de migrar. Una migración sobre código mal estructurado es más difícil.
- **Durante Fase D (research cross)**: apoyate en `checklists/odoo-version-deltas.md` del toolkit.
- **Durante las oleadas**: cada módulo usa `/migrate-odoo` que a su vez usa los prompts de `prompts/`.
- **Después de cada oleada**: correr tests de integración cruzada si existen.
