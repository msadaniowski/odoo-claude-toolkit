---
name: deadcode-odoo-fix
description: A partir de un DEADCODE_REPORT.md producido por deadcode-odoo, genera DEADCODE_PLAN.md con oleadas priorizadas y ejecuta las correcciones una a una (una corrección = un commit = un chat fresco). Antes de eliminar código pide aprobación humana explícita por cada item. Uso - /deadcode-odoo-fix <ruta_al_modulo>
---

# Aplicador de correcciones de código muerto en Odoo

Este skill es el complemento de `deadcode-odoo`. Lee el informe de análisis estático, genera un **plan de corrección priorizado en oleadas**, y ejecuta los fixes uno a la vez respetando la misma disciplina de `audit-odoo-fix` / `enhance-odoo-fix` (un fix = un commit = un chat fresco).

**Diferencia clave vs `audit-odoo-fix`**: acá se están **eliminando o re-cableando elementos**, no agregando features ni arreglando bugs convencionales. Por eso hay un **gate humano obligatorio** para cada eliminación: el análisis estático no puede confirmar al 100% que algo es dead code.

## Flujo general

```
/deadcode-odoo <modulo>         →  .deadcode/DEADCODE_REPORT.md
    ↓
/deadcode-odoo-fix <modulo>     →  .deadcode/DEADCODE_PLAN.md     (primera vez: genera plan)
    ↓
/deadcode-odoo-fix <modulo>     →  ejecuta UN fix                  (invocaciones siguientes)
    ↓ (chat nuevo)
/deadcode-odoo-fix <modulo>     →  ejecuta siguiente fix
    ...
```

## Detección de estado

Al invocarse con `<ruta_al_modulo>`:

1. **Verificar precondiciones**:
   - Existe `<modulo>/__manifest__.py` (si no → error).
   - Existe `<modulo>/.deadcode/DEADCODE_REPORT.md` (si no → sugerir correr `/deadcode-odoo <modulo>` primero).
   - `git -C <modulo> status` limpio (si no → pedir al usuario committear o stash antes de arrancar).

2. **Determinar fase**:

| Estado en disco | Fase a ejecutar |
|---|---|
| Hay `DEADCODE_REPORT.md`, no hay `DEADCODE_PLAN.md` | **Fase A — Generar plan** |
| Hay `DEADCODE_PLAN.md` con tareas pendientes `[ ]` | **Fase B — Ejecutar próxima tarea** |
| Todas las tareas `[x]` o `[~]` | **Terminado** — mostrar resumen de cierre |

Anunciá al usuario la fase detectada y esperá confirmación antes de arrancar.

## Fase A — Generar `DEADCODE_PLAN.md`

### Entrada
- `<modulo>/.deadcode/DEADCODE_REPORT.md`
- `<modulo>/.deadcode/DEADCODE_SCAN.json` (para datos estructurados cuando necesites cross-reference)

### Protocolo

1. Leer el REPORT completo. Extraer todos los findings `D01, D02, ...` con su severidad, categoría, archivo:línea, evidencia, y acciones posibles.

2. **Ignorar findings marcados como `~descartado~`** por el usuario en el REPORT. Listarlos en el plan como referencia pero sin tareas.

3. **Descomponer cada finding en una tarea atómica** siguiendo estas reglas:
   - Una tarea = un commit coherente. Un finding = una tarea (salvo casos de agrupación explícita, ver abajo).
   - Tareas paralelas dentro de la misma ola llevan flag `[∥]`.
   - Tareas con dependencia llevan `dep: TXX`.
   - **Acceptance verificable** (no "limpiar X" sino "grep Y devuelve 0 matches" o "módulo instala sin errores" o "test Z pasa").

4. **Agrupación permitida**:
   - Varios `orphan_xmlid` 🔵 del mismo archivo XML se pueden bundle en UNA tarea si el usuario está de acuerdo con eliminar todos juntos.
   - Varios `unused_field` de la MISMA entidad lógica (ej. un wizard entero no usado) se pueden agrupar.
   - Todo lo 🔴 (rojos) es siempre **una tarea por finding** — son bugs y cada uno requiere decisión individual.

5. **Distribuir las tareas en 6 oleadas** según riesgo y dependencia:

   | Oleada | Características | Tipos de findings |
   |---|---|---|
   | **Ola 0 — Preparación** | Tag + branch + tree limpio + update `.gitignore` para `.deadcode/`. | (infra) |
   | **Ola 1 — Referencias rotas 🔴** | Bugs confirmados: decidir implementar, arreglar o remover la referencia. | `broken_button_ref`, `broken_field_ref`, `decorator_field_missing`, `missing_compute_method` |
   | **Ola 2 — Binding recovery 🟡** | Métodos/computes con prefijo correcto pero sin binding: decidir **conectar** (agregar botón/compute=) o **eliminar**. Requiere criterio humano por cada uno. | `orphan_method` con prefijo `action_/_compute_/_onchange_`, `button_model_mismatch` |
   | **Ola 3 — Modelos aislados 🟡** | Modelos sin ACL/vista/FK: **wiring** (agregar ACL + vista + menú) o **deprecación** (eliminar modelo y todo lo dependiente). | `isolated_model` |
   | **Ola 4 — Métodos/campos huérfanos 🟡🔵** | Después de Olas 1-3, lo que queda huérfano pasó el filtro humano: eliminar. | `orphan_method` genérico, `unused_field`, `unused_selection_value` |
   | **Ola 5 — XML IDs y data cleanup 🔵** | XML IDs que nada referencia: eliminar records en XML. | `orphan_xmlid` |
   | **Ola 6 — Tests de regresión** | Escribir/actualizar tests que cubran los flujos reconectados en Olas 2-3. Sanity check final: instalación limpia + tests existentes siguen verdes. | (infra) |

6. **Priorización dentro de cada oleada**:
   - Ola 1: primero las que crashean obviamente (botones del form principal), después las de vistas secundarias.
   - Ola 2: primero métodos que el usuario DECIDE conservar+cablear, después los que decide eliminar.
   - Ola 4 y 5: orden libre, todas `[∥]`.

7. **Producir el archivo** `<modulo>/.deadcode/DEADCODE_PLAN.md` con esta estructura:

```markdown
# DEADCODE_PLAN — <nombre_modulo>

**Generado:** <fecha>
**Basado en:** `.deadcode/DEADCODE_REPORT.md` (análisis del <fecha_del_report>)
**Total tareas:** N en 7 oleadas
**Findings cubiertos:** D01, D02, ..., D0N
**Findings descartados por usuario:** D05 (motivo), D12 (motivo) — NO forman parte del plan.

## Decisiones tomadas durante la planificación

<Si al planificar vos detectás que varios findings están obviamente relacionados (ej. 10 métodos de un mismo wizard no usado), anotar acá la decisión y referenciar la tarea bundle>
- **Wizard `sgc.wizard.legacy`** — tiene 5 métodos orphan + 3 campos unused + 2 orphan_xmlid. Agrupamos en **T12** (eliminar wizard completo).
- ...

## Ola 0 — Preparación

- [ ] **T00** — Tag + branch de trabajo + .gitignore
  ```
  cd <ruta_modulo>
  git status                                          # debe estar limpio
  git tag pre-deadcode-$(date +%Y%m%d)
  git checkout -b deadcode/<modulo>
  grep -q "^\.deadcode/" .gitignore || echo ".deadcode/" >> .gitignore
  git add .gitignore && git commit -m "chore: ignore .deadcode/ analysis output"
  ```
  - **Acceptance:** branch `deadcode/<modulo>` creado; tag creado; `.deadcode/` en gitignore.
  - **Dep:** ninguna.

### Gate Ola 0
Branch creado y tree limpio.

## Ola 1 — Referencias rotas 🔴

**Regla de oro Ola 1**: estos son bugs que crashean en runtime. Si el usuario no puede decidir qué hacer, el default seguro es **remover la referencia** (no el elemento referenciado).

- [ ] **T01** **Arreglar botón `action_old_confirm` en `order_views.xml:45`** — ref: D01
  - **Archivo:** `views/order_views.xml:45`
  - **Decisión requerida (pre-task)**: preguntar al usuario:
    - (a) Implementar `action_old_confirm` en `models/order.py` (si tiene sentido lógico).
    - (b) Renombrar el botón a `action_confirm` (método existente) si es typo.
    - (c) Remover el `<button>` completamente.
  - **Qué hacer (según decisión)**:
    - (a) agregar método con signatura `def action_old_confirm(self): ...`
    - (b) cambiar `name="action_old_confirm"` → `name="action_confirm"`
    - (c) borrar el elemento `<button>` del XML.
  - **Acceptance:** `odoo-bin -u <modulo>` sin error de carga XML; grep del button target ahora apunta a método existente (o no apunta a nada si se removió).
  - **Dep:** ninguna.

- [ ] **T02** ...

### Gate Ola 1
Todas las referencias rojas resueltas. Módulo instala limpio (`odoo-bin -u <modulo> --stop-after-init` sin errores).

## Ola 2 — Binding recovery 🟡

**Regla de oro Ola 2**: por cada método huérfano, preguntar al usuario: **¿conectar o eliminar?** Ningún delete ciego.

- [ ] **T10** **`action_deprecated_flow` en `sgc.order` — decidir conectar/eliminar** — ref: D15
  - **Archivo:** `models/sgc_order.py:120`
  - **Decisión requerida**: mostrar al usuario el cuerpo del método (10 líneas arriba/abajo) y preguntar:
    - (a) **Conectar**: agregar `<button name="action_deprecated_flow">` en `order_views.xml` con label apropiado.
    - (b) **Eliminar**: borrar el método.
    - (c) **Preservar (marcar consumer externo)**: el método es llamado desde JS/server action que el scanner no ve — actualizar el REPORT con `~descartado (razón)~` y saltar esta tarea.
  - **Qué hacer (según decisión)**: aplicar la acción elegida.
  - **Acceptance:**
    - (a) grep de `action_deprecated_flow` en XML devuelve 1+ matches; módulo instala; probar botón manualmente.
    - (b) grep de `action_deprecated_flow` en `.py` y `.xml` del módulo devuelve 0 matches; módulo instala.
    - (c) REPORT actualizado; tarea marcada `[~]`.
  - **Dep:** ninguna.

- [ ] **T11** ...

### Gate Ola 2
Todos los métodos huérfanos amarillos resueltos. Para cada uno hay decisión registrada. Ningún delete sin aprobación humana explícita.

## Ola 3 — Modelos aislados 🟡

- [ ] **T20** **Modelo `sgc.legacy.audit` aislado — decidir wiring/deprecación** — ref: D30
  - **Archivo:** `models/sgc_legacy_audit.py:12`
  - **Evidencia**: sin entrada en `ir.model.access.csv`, sin vista, no es FK de nadie.
  - **Decisión requerida**:
    - (a) **Wire up**: agregar ACL + form/tree view + menú + (opcionalmente) smart button en modelo padre.
    - (b) **Deprecar**: eliminar el modelo completo (Python + tests + cualquier referencia residual).
  - **Acceptance:**
    - (a) abrir Odoo, navegar al menú, abrir form, crear registro → no errores.
    - (b) grep `sgc.legacy.audit` en todo el módulo devuelve 0 matches; módulo instala.
  - **Dep:** ninguna.

### Gate Ola 3
Cada modelo aislado o está wired con ACL+view+menu, o está eliminado completamente junto con sus dependencias.

## Ola 4 — Métodos/campos huérfanos restantes 🟡🔵

**Pre-requisito**: Olas 1-3 cerradas. Lo que quedó huérfano después de esas olas ya pasó el filtro humano (o el usuario decidió en Ola 2-3 que había que eliminarlo aunque la tarea específica esté en Ola 4).

- [ ] **T30** `[∥]` **Eliminar campo `foo_bar` de `sgc.order`** — ref: D50
  - **Archivos:** `models/sgc_order.py:34`, `views/sgc_order_views.xml` (si aparece), `security/ir.model.access.csv` (no aplica para fields).
  - **Acceptance:** grep `foo_bar` en todo el módulo devuelve 0 matches; módulo instala; tests existentes siguen pasando.
  - **Dep:** ninguna.

### Gate Ola 4
Todos los huérfanos aprobados para eliminación están eliminados. Módulo instala y tests pasan.

## Ola 5 — XML IDs y data cleanup 🔵

- [ ] **T40** `[∥]` **Eliminar XML IDs huérfanos en `order_views.xml`** — ref: D60..D65 (bundle)
  - **Archivo:** `views/order_views.xml`
  - **Qué hacer:** borrar los `<record id="...">` listados en los findings D60-D65.
  - **Acceptance:** grep de esos IDs en todo el addons_path devuelve 0 matches; módulo instala; no hay errores de `ref=` colgado.
  - **Dep:** ninguna.

### Gate Ola 5
XML limpio de records huérfanos.

## Ola 6 — Tests de regresión

- [ ] **T50** **Tests de smoke para flujos reconectados**
  - **Archivos:** `tests/test_deadcode_cleanup.py` (nuevo).
  - **Qué hacer:** escribir tests mínimos que validen:
    - Si hubo wiring de métodos en Ola 2 → test que el botón ejecuta el método sin crashear.
    - Si hubo wiring de modelos en Ola 3 → test que el modelo se puede crear/leer.
    - Sanity: módulo se instala desde cero limpio.
  - **Acceptance:** `odoo-bin -u <modulo> --test-enable --test-tags /<modulo> --stop-after-init` pasa todos los tests.
  - **Dep:** Olas 1-5 completas.

- [ ] **T51** **Re-correr scanner para verificar reducción de findings**
  - **Qué hacer:** `python3 scan_deadcode.py <modulo>` y comparar `findings_total` vs pre-corrección.
  - **Acceptance:** el número de 🔴 es 0 (todos los bugs resueltos); 🟡 bajó significativamente; 🔵 bajó o se mantiene con anotaciones de descarte del usuario.
  - **Dep:** T50.

### Gate Ola 6
Tests verdes + scan final con 0 🔴 y 🟡 residuales todos justificados.

## Resumen

| Ola | Tareas | Tiempo estimado | Riesgo | Gate crítico |
|-----|--------|-----------------|--------|--------------|
| 0 | 1 | 5 min | Bajo | Branch OK |
| 1 | N | 1-3h | **Alto** (bugs) | Módulo instala limpio |
| 2 | N | 2-4h | **Alto** (delete ciego) | Decisión humana por método |
| 3 | N | 1-3h | **Alto** (delete ciego) | Decisión humana por modelo |
| 4 | N | 1-2h | Medio | Tests existentes siguen OK |
| 5 | N | 30 min | Bajo | Módulo instala |
| 6 | 2 | 1-2h | Bajo | Tests verdes + scan final |

## Findings fuera del plan

<Findings marcados por el usuario como `~descartado~` en REPORT: listar acá con motivo para trazabilidad.>
```

8. **Al terminar, imprimir en chat**:

```
✅ DEADCODE_PLAN.md generado con N tareas en 7 oleadas.

**Próximo paso**: revisá el plan en <ruta>/.deadcode/DEADCODE_PLAN.md.
Revisá especialmente:
- Acceptance de cada tarea: ¿son criterios objetivos?
- Dependencias: ¿te cierra el orden?
- Ola 2 y 3: ¿las decisiones requeridas están claras? — acá se toma criterio humano por cada item.
- Si querés sacar alguna tarea del plan, marcala como `[~]` (skipped) con motivo.

Si te queda cómodo, volvé a invocar /deadcode-odoo-fix <ruta> en un chat nuevo —
voy a detectar el plan y empezar a ejecutar la primera tarea pendiente.

PLAN READY FOR REVIEW — no arranco ejecución hasta aprobar el plan.
```

**Gate humano obligatorio**: no avanzar a Fase B hasta que el usuario revise `DEADCODE_PLAN.md`. Si tiene comentarios, ajustá y regenerá.

## Fase B — Ejecutar la próxima tarea

### Entrada
- `<modulo>/.deadcode/DEADCODE_PLAN.md` con al menos una tarea `[ ]`.

### Protocolo

1. **Leer `DEADCODE_PLAN.md`**, encontrar la **primera tarea `[ ]`** cuyas dependencias estén `[x]`. **Respetar el orden de oleadas**: no saltar a Ola N+1 si Ola N tiene pendientes, salvo que el usuario lo pida explícitamente.

2. **Re-state al usuario** en una línea: "Voy a ejecutar `TXX — <título>`. Archivos: X. Acceptance: Y. ¿OK?".
   - Esperar confirmación.
   - Si el usuario quiere saltar o hacer otra, preguntar cuál.

3. **Si la tarea requiere decisión humana (Olas 1-3)**: **antes de tocar código**, mostrar al usuario:
   - El código completo del método/campo/modelo en cuestión (±15 líneas de contexto).
   - Las 2-3 opciones posibles (conectar vs eliminar vs preservar).
   - Pedir decisión explícita: *"¿Qué querés hacer con `<item>`? Opciones: (a) ..., (b) ..., (c) ..."*
   - **No decidir por el usuario**. Si no responde o es ambiguo, **preservar** y marcar la tarea como `[~] diferida a revisión humana`.

4. **Leer solo los archivos listados** en la tarea + la sección del REPORT del finding referenciado. **Scope disciplinado.**

5. **Implementar el fix**:
   - Cambios mínimos para cumplir acceptance.
   - No refactors adicionales ("drive-by").
   - Si encontrás otros issues que no están en la tarea, anotarlos en `<modulo>/.deadcode/FOLLOWUPS.md` — no los arregles.
   - **Si la tarea es un delete**: doble check antes de ejecutar — re-grep el nombre a eliminar en TODO el `addons_path` (no solo el módulo target) para confirmar que nadie más lo usa. Si aparece un match inesperado, pausar y preguntar.

6. **Verificar el acceptance**:
   - Sintáctico (grep, read) → verificar en seguida.
   - Runtime (instalación, test) → dar comando al usuario y esperar confirmación con output.
   - **Si es Ola 6 (test)**: **obligatorio correr el test y que pase** antes de marcar ✅.

7. **Commit con mensaje convencional**:
   ```
   deadcode(<modulo>): <TXX> <título corto>

   <descripción: qué se eliminó/reconectó y por qué; referenciar D0N del REPORT>

   Ref: deadcode finding <D0N>
   ```

8. **Actualizar `DEADCODE_PLAN.md`**: cambiar `[ ]` → `[x]` + hash del commit al final de la línea. Si la tarea fue diferida, `[~]` con motivo.

9. **Parar**. Imprimir:
   ```
   ✅ TXX completa. Commit: <hash>.

   Siguiente tarea: TYY — <título>
   **Importante**: abrí un chat NUEVO e invocá /deadcode-odoo-fix <ruta>.
   Voy a detectar que TXX está ✅, que TYY es la próxima, y la arranco.

   Si querés hacer varias en paralelo (las marcadas [∥] en Olas 4-5),
   podés abrir varios chats simultáneos — cada uno toma una tarea distinta.
   ```

## Reglas duras

1. **Una corrección = un commit = un chat fresco**. No batchees fixes en el mismo chat — la IA empieza a perder scope y puede eliminar cosas no aprobadas.

2. **No ejecutar Fase B sin plan aprobado por humano**. Si el usuario no confirmó el DEADCODE_PLAN.md, volvé a Fase A o avisá.

3. **Ninguna eliminación sin aprobación explícita del usuario** (Olas 1-4). Por cada item a eliminar:
   - Mostrar el código al usuario.
   - Pedir decisión.
   - Si no hay respuesta clara → preservar + diferir.

4. **Scope estricto por tarea**. Si el acceptance dice "eliminar método X" y ves que también se puede eliminar un campo relacionado, anotarlo en FOLLOWUPS.md y seguir con la tarea original.

5. **No saltar oleadas**. Si Ola N tiene pendientes, no arrancar Ola N+1 (excepto paralelismo dentro de la misma ola con flag `[∥]`).

6. **Double-check pre-delete**: antes de ejecutar un delete, re-grep el nombre en TODO el `addons_path` (no solo el módulo target). Si hay match inesperado → pausar, mostrar al usuario, pedir decisión.

7. **Si una tarea falla verificación**: STOP. No forzar. Reportar al usuario por qué falla y esperar decisión (reintentar, diferir, skip).

8. **Tests existentes deben seguir pasando**. Si un fix rompe un test existente, STOP. Hay dos posibilidades:
   - El test cubre una feature mal implementada → discutir con el usuario si el test también era parte del dead code.
   - Introdujiste una regresión → revertir el fix y re-planear.

9. **Ola 6 es no-opcional**. Aunque parezca "solo tests", es el gate que prueba que las Olas 1-5 no introdujeron regresiones. Si el usuario quiere skipearla, avisar que el scan final + tests de regresión son la única forma de verificar que la limpieza fue correcta.

## Paralelización

Tareas marcadas `[∥]` en la **misma oleada** se pueden ejecutar en chats paralelos:
- Cada chat toma una tarea distinta.
- Al terminar, cada chat marca `[x]` en el PLAN — posible race al commit. Mitigación: commit inmediato, y si hay conflict, el segundo rebase manualmente.
- **Ola 2 y 3 NO son paralelizables** en serio: cada decisión humana afecta el siguiente. El usuario puede abrir múltiples chats pero va a tener que ir decidiendo uno por uno.
- **Ola 4 y 5 son muy paralelizables**: delete de cosas independientes. Limitar a 2-3 chats para no perder el hilo.

## FOLLOWUPS.md

Si durante la ejecución encontrás issues adicionales (bugs, prácticas pobres, oportunidades), agregarlos a `<modulo>/.deadcode/FOLLOWUPS.md`:

```markdown
- **F01** — encontrado durante T10
  - **Archivo:** models/order.py:145
  - **Descripción:** al eliminar `action_deprecated_flow` vi que `action_confirm` tiene un helper `_helper_old` que también parece no usarse, pero no está en el REPORT.
  - **Sugerencia:** re-correr `/deadcode-odoo` después de completar este PLAN; el scan va a encontrar nuevos huérfanos expuestos por las eliminaciones de esta ronda.
  - **Severidad estimada:** 🟡
```

Al finalizar todas las oleadas, sugerir al usuario:

1. **Re-correr `/deadcode-odoo`** — el nuevo scan puede encontrar nuevos huérfanos expuestos por las eliminaciones de esta ronda (efecto dominó: eliminar un método puede hacer que su helper pase a ser huérfano).
2. Si el re-scan devuelve 0 🔴 y pocos 🟡 justificados → módulo limpio.
3. Correr `/audit-odoo` para verificar que las eliminaciones no introdujeron problemas nuevos (ACL laxa, ORM patterns, etc.).

## Integración con el resto del toolkit

- **Prerequisito**: `/deadcode-odoo <modulo>` debe haber corrido y persistido `.deadcode/DEADCODE_REPORT.md`.
- **Recomendado antes**: `/audit-odoo` + `/audit-odoo-fix` — trabajar sobre módulo saneado reduce falsos 🟡 por callers rotos.
- **Post-deadcode**: re-correr `/deadcode-odoo` para verificar efecto dominó, y después `/audit-odoo` para regresiones.
- **Antes de migrar**: limpiar dead code ANTES de `/migrate-odoo`. Migrar código muerto a una versión nueva es puro desperdicio.

## ¿Qué NO hace este skill?

- No detecta dead code por sí mismo — eso lo hace `/deadcode-odoo`.
- No optimiza performance ni moderniza código — eso es `/enhance-odoo-fix`.
- No arregla bugs genéricos — eso es `/audit-odoo-fix`.
- No migra entre versiones — eso es `/migrate-odoo`.
- **No elimina código sin aprobación humana por cada item**, incluso cuando el finding parece obvio.
