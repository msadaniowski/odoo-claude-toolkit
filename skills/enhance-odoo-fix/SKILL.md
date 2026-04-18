---
name: enhance-odoo-fix
description: A partir de un ENHANCEMENT_REPORT.md producido por enhance-odoo, genera ENHANCEMENT_PLAN.md con oleadas y ejecuta las mejoras una a una (una mejora = un commit = un chat fresco). Requiere tests pasando en oleadas de features de negocio y UX. Uso - /enhance-odoo-fix <ruta_al_modulo>
---

# Aplicador de mejoras post-análisis Odoo

Este skill es el complemento de `enhance-odoo`. Lee el informe de análisis propositivo, genera un **plan de implementación priorizado en oleadas**, y ejecuta las mejoras una a la vez respetando la misma disciplina de `migrate-odoo` y `audit-odoo-fix` (una mejora = un commit = un chat fresco).

**Diferencia clave vs `audit-odoo-fix`**: acá se están **agregando features nuevas**, no arreglando bugs. Por eso las oleadas son distintas, y las Olas de features (4 y 5) tienen un gate extra obligatorio: **el test diseñado en el informe tiene que correr y pasar antes de marcar la tarea como ✅**.

## Flujo general

```
/enhance-odoo <modulo>         →  .enhance/ENHANCEMENT_REPORT.md
    ↓
/enhance-odoo-fix <modulo>     →  .enhance/ENHANCEMENT_PLAN.md   (primera vez: genera plan)
    ↓
/enhance-odoo-fix <modulo>     →  ejecuta UNA mejora             (invocaciones siguientes)
    ↓ (chat nuevo)
/enhance-odoo-fix <modulo>     →  ejecuta siguiente mejora
    ...
```

## Detección de estado

Al invocarse con `<ruta_al_modulo>`:

1. **Verificar precondiciones**:
   - Existe `<modulo>/__manifest__.py` (si no → error).
   - Existe `<modulo>/.enhance/ENHANCEMENT_REPORT.md` (si no → sugerir correr `/enhance-odoo <modulo>` primero).

2. **Determinar fase**:

| Estado en disco | Fase a ejecutar |
|---|---|
| Hay `ENHANCEMENT_REPORT.md`, no hay `ENHANCEMENT_PLAN.md` | **Fase A — Generar plan** |
| Hay `ENHANCEMENT_PLAN.md` con tareas pendientes (checkbox vacío) | **Fase B — Ejecutar próxima tarea** |
| Todas las tareas en `ENHANCEMENT_PLAN.md` ✅ | **Terminado** — mostrar resumen de cierre |

Anunciá al usuario qué fase detectaste y esperá confirmación antes de arrancar.

## Fase A — Generar `ENHANCEMENT_PLAN.md`

### Entrada
- `<modulo>/.enhance/ENHANCEMENT_REPORT.md`

### Protocolo

1. Leer el informe completo. Extraer todas las propuestas validadas (P01, P02, ...) con su categoría, archivos a tocar, test propuesto, y acceptance.

2. **Descomponer cada propuesta en tareas atómicas** siguiendo estas reglas:
   - Una tarea = un commit coherente. Si una propuesta toca >5 archivos, dividir en sub-tareas (groundwork + implementación + test).
   - Una tarea que se puede hacer en cualquier orden respecto de otras va con flag `[∥]` (paralelizable).
   - Una tarea que depende de otra va con `dep: TXX`.
   - Cada tarea lleva **acceptance verificable** (no "mejora X" sino "el test Y pasa" o "grep Z devuelve N matches").

3. **Distribuir las tareas en 7 oleadas** según riesgo y dependencia:

   | Oleada | Características | Ejemplos típicos |
   |---|---|---|
   | **Ola 0 — Preparación** | Branch + tag + verificación de que no hay cambios sin commitear. | `git tag`, `git checkout -b`, revisar `git status` limpio |
   | **Ola 1 — Groundwork** | Agregar `depends` nuevas, crear archivos base (modelos vacíos, carpetas, `__init__.py`). Sin lógica de negocio. Commits chicos y seguros. | Agregar `'portal'` a depends, crear `models/nuevo.py` con modelo vacío, crear `data/` folder, declarar archivos en manifest |
   | **Ola 2 — Mejoras técnicas** | Refactors que no agregan features: N+1, `@api.model_create_multi`, `@api.multi` → quitar, índices. Menor riesgo funcional. | Reemplazar `@api.multi`, agregar `index=True`, migrar `create()` a multi |
   | **Ola 3 — Seguridad** | Record rules, grupos nuevos, ACL. Antes de exponer features nuevas. | Agregar `ir.rule` multi-company, crear grupos más granulares, completar `ir.model.access.csv` |
   | **Ola 4 — Nuevas features de negocio** | Las propuestas de Categoría "Negocio" con sus tests. **Gate `test_pasa` obligatorio**. | Workflow de aprobación, notificaciones con `mail.template`, exposición portal |
   | **Ola 5 — UX** | Smart buttons, filtros, wizards, kanban, tooltips. Sobre base funcional. **Gate `test_pasa` obligatorio si hay tests**. | Smart button a modelo relacionado, kanban view, wizard de bulk action |
   | **Ola 6 — Cobertura y docs** | Completar tests faltantes, `.pot`, actualizar README del módulo. | Generar `.pot` nuevo, escribir tests para features existentes sin cobertura, README sección de uso |

4. **Priorización dentro de cada oleada**:
   - Primero las de Impacto Alto, después Medio, después Bajo.
   - Dentro de la misma categoría de impacto, primero las que NO dependen de otras.
   - Las propuestas marcadas como "Resolver primero" (por referencia a audit 🔴) van al inicio de su oleada correspondiente.

5. **Producir el archivo** `<modulo>/.enhance/ENHANCEMENT_PLAN.md` con esta estructura:

```markdown
# ENHANCEMENT_PLAN — <nombre_modulo>

**Generado:** <fecha>
**Basado en:** `.enhance/ENHANCEMENT_REPORT.md` (análisis del <fecha_del_report>)
**Total tareas:** N en 7 oleadas
**Propuestas cubiertas:** P01, P02, ..., P0N

## Ola 0 — Preparación

- [ ] **T00** — Tag + branch de trabajo
  ```
  cd <ruta_modulo>
  git status   # debe estar limpio
  git tag pre-enhance-$(date +%Y%m%d)
  git checkout -b enhance/<modulo>
  ```
  - **Acceptance:** estás parado en branch `enhance/<modulo>` con el tag creado.
  - **Dep:** ninguna.

### Gate Ola 0
Branch creado y working tree limpio.

## Ola 1 — Groundwork

- [ ] **T01** `[∥]` **Agregar `portal` a depends** — ref: P05
  - **Archivos:** `__manifest__.py`
  - **Qué hacer:** agregar `'portal'` al list `depends`. Verificar que el módulo sigue instalando (`-u <modulo>`).
  - **Acceptance:** `grep "'portal'" __manifest__.py` devuelve match; `odoo-bin -u <modulo>` sin errores.
  - **Dep:** ninguna.

- [ ] **T02** `[∥]` **Crear modelo vacío `modulo.approval`** — ref: P01
  - **Archivos:** `models/approval.py` (nuevo), `models/__init__.py` (+ import)
  - **Qué hacer:** crear modelo con `_name`, `_description`, campos básicos (`name`, `state`, `record_id`). Sin lógica todavía.
  - **Acceptance:** módulo instala con `-u`; el modelo aparece en `ir.model`.
  - **Dep:** ninguna.

- [ ] **T03** **Declarar archivos de datos en manifest** — ref: P01
  - **Archivos:** `__manifest__.py`, crear placeholders `data/mail_templates.xml` y `data/sequences.xml` (con root `<odoo>` vacío).
  - **Acceptance:** manifest lista los archivos en orden correcto (security → data → views → reports → menús); instala sin errores.
  - **Dep:** T02.

### Gate Ola 1
Módulo instala limpio con toda la estructura base. `ir.model.access.csv` todavía NO refleja los modelos nuevos (eso va en Ola 3).

## Ola 2 — Mejoras técnicas

- [ ] **T04** `[∥]` **Reemplazar `@api.multi`** — ref: P10
  - **Archivos:** `models/order.py:45`, `models/order.py:78`, `models/line.py:120`
  - **Qué hacer:** remover el decorador `@api.multi` (deprecado en 13+, removido en 14+). El método ya opera sobre recordset por default.
  - **Acceptance:** `grep -rn "@api.multi" models/` sin matches; módulo instala.
  - **Dep:** ninguna.

- [ ] **T05** `[∥]` **Migrar `create()` a `@api.model_create_multi`** — ref: P11
  - **Archivos:** `models/order.py:90`
  - **Qué hacer:** cambiar `@api.model def create(self, vals):` a `@api.model_create_multi def create(self, vals_list):` y ajustar body para iterar.
  - **Acceptance:** `grep "model_create_multi" models/order.py` match; test existente `test_create_order` sigue pasando.
  - **Dep:** ninguna.

### Gate Ola 2
Código técnico modernizado, sin cambio de comportamiento funcional. Todos los tests existentes siguen pasando.

## Ola 3 — Seguridad

- [ ] **T06** **Agregar ACL para `modulo.approval`** — ref: P01
  - **Archivos:** `security/ir.model.access.csv`
  - **Qué hacer:** agregar entradas para grupos `base.group_user` (read) y `modulo.group_manager` (CRUD).
  - **Acceptance:** archivo tiene 2 entradas nuevas, válidas (no faltan columnas); módulo instala.
  - **Dep:** T02 (modelo debe existir).

- [ ] **T07** `[∥]` **Record rule multi-company para `modulo.order`** — ref: P02
  - **Archivos:** `security/security.xml` (nuevo o extendido)
  - **Qué hacer:** crear `<record model="ir.rule">` con `domain_force="[('company_id','in',company_ids)]"`.
  - **Acceptance:** regla aparece en `ir.rule`; test de Ola 4 que valida aislamiento multi-company pasa cuando se llegue.
  - **Dep:** ninguna.

### Gate Ola 3
Toda la seguridad necesaria para las features de Ola 4 está en su lugar. Los tests de permisos pueden arrancar sin bloqueos de ACL.

## Ola 4 — Nuevas features de negocio

**Regla de oro**: ninguna tarea arranca hasta que Olas 0–3 estén ✅. Cada tarea requiere que su test pase antes de ✅.

- [ ] **T10** **Implementar flujo de aprobación de orden** — ref: P01
  - **Archivos:** `models/order.py`, `models/approval.py`, `views/order_views.xml`, `data/mail_templates.xml`, `data/sequences.xml`, `tests/test_order_approval.py`
  - **Qué hacer:** implementar `action_confirm`, `action_cancel`, transiciones de estado, `mail.template`, `ir.sequence`. Escribir el test tal como está diseñado en `ENHANCEMENT_REPORT.md` sección P01.
  - **Acceptance:**
    - Test `TestOrderConfirmation.test_confirm_happy_path` pasa.
    - Test `TestOrderConfirmation.test_cannot_confirm_from_done` pasa.
    - Test `TestOrderConfirmation.test_access_denied_basic_user` pasa.
    - Validación manual del usuario: crear una order, confirmar, llegar email.
  - **Dep:** T01, T02, T03, T06.
  - **Gate:** `test_pasa` ✅ (obligatorio antes de marcar completa).

- [ ] **T11** ...

### Gate Ola 4
Todas las features de negocio tienen test pasando + validación manual del usuario.

## Ola 5 — UX

- [ ] **T20** `[∥]` **Smart button "Órdenes relacionadas" en partner form** — ref: P15
  - **Archivos:** `views/partner_views.xml`
  - **Qué hacer:** agregar botón en `res.partner.view.form.inherit.modulo` con `name="action_view_orders"` y contador via compute.
  - **Acceptance:** abrir form de partner, ver el botón con contador correcto; click abre list filtrada.
  - **Dep:** T10 (depende de que `modulo.order` esté completo).
  - **Gate:** `test_pasa` si hay test asociado.

- [ ] **T21** ...

### Gate Ola 5
Todas las mejoras UX implementadas y visibles. Si hay tests HttpCase, pasan.

## Ola 6 — Cobertura y docs

- [ ] **T30** `[∥]` **Generar `.pot` actualizado** — ref: P20
  - **Archivos:** `i18n/<modulo>.pot`
  - **Qué hacer:** correr `odoo-bin --i18n-export <modulo>.pot -l en_US -d <db> --modules=<modulo>` (o equivalente).
  - **Acceptance:** archivo existe y contiene al menos los nuevos strings de `mail.template`.
  - **Dep:** T10, T11, ... (todas las features con strings nuevos).

- [ ] **T31** `[∥]` **Actualizar README.md del módulo** — ref: P21
  - **Archivos:** `README.md` o `README.rst`
  - **Qué hacer:** sección de uso con los nuevos flujos agregados.
  - **Acceptance:** README menciona los nuevos botones/flujos.
  - **Dep:** T10, T20, ...

## Resumen

| Ola | Tareas | Tiempo estimado | Riesgo | Gate crítico |
|-----|--------|-----------------|--------|--------------|
| 0 | 1 | 5 min | Bajo | Branch OK |
| 1 | 3 | 30 min | Bajo | Instala limpio |
| 2 | 2 | 20 min | Bajo | Tests existentes OK |
| 3 | 2 | 30 min | Medio | ACL completa |
| 4 | 2 | 2-4h | **Alto** | `test_pasa` |
| 5 | 2 | 1-2h | Medio | `test_pasa` si aplica |
| 6 | 2 | 30 min | Bajo | Docs + i18n |

## Propuestas fuera del plan

<Si hubo propuestas descartadas en el REPORT, no van acá. Pero si hubo propuestas validadas que el usuario decidió skipear, listarlas para trazabilidad.>
```

6. **Al terminar**, imprimir en chat:

```
✅ ENHANCEMENT_PLAN.md generado con N tareas en 7 oleadas.

**Próximo paso**: revisá el plan en `<ruta>/.enhance/ENHANCEMENT_PLAN.md`.
Revisá especialmente:
- Acceptance de cada tarea: ¿son criterios objetivos?
- Dependencias: ¿te cierra el orden?
- Olas 4 y 5: ¿estás de acuerdo con el alcance?
- Si querés sacar alguna propuesta del plan, marcala como `[~]` (skipped) con motivo.

Si te queda cómodo, volvé a invocar `/enhance-odoo-fix <ruta>` en un chat nuevo —
voy a detectar el plan y empezar a ejecutar la primera tarea pendiente.

PLAN READY FOR REVIEW — no arranco ejecución hasta aprobar el plan.
```

**Gate humano obligatorio**: no avanzar a Fase B hasta que el usuario revise `ENHANCEMENT_PLAN.md`. Si tiene comentarios, ajustá el plan y regenerá.

## Fase B — Ejecutar la próxima tarea

### Entrada
- `<modulo>/.enhance/ENHANCEMENT_PLAN.md` con al menos una tarea con checkbox vacío `[ ]`.

### Protocolo

1. **Leer `ENHANCEMENT_PLAN.md`**, encontrar la **primera tarea con `[ ]`** que tenga todas sus dependencias `dep:` ya marcadas como `[x]`. **Respetar el orden de oleadas**: no saltar a Ola N+1 si Ola N tiene pendientes, salvo que el usuario lo pida explícitamente.

2. **Re-state la tarea al usuario** en una línea: "Voy a ejecutar `TXX — <título>`. Archivos: X. Acceptance: Y. ¿OK?".
   - Esperar confirmación.
   - Si el usuario quiere saltar o hacer otra, preguntar cuál.

3. **Leer solo los archivos listados** en la tarea + el `ENHANCEMENT_REPORT.md` (sección de la propuesta referenciada). No explorar más. **Scope disciplinado.**

4. **Implementar la mejora**:
   - Cambios mínimos para cumplir acceptance.
   - No refactors adicionales ("drive-by").
   - Si encontrás otros issues que no están en la tarea, anotarlos en `<modulo>/.enhance/FOLLOWUPS.md` — no los arregles.

5. **Verificar el acceptance**:
   - Si es sintáctico (ej: "campo agregado") → grep / re-read para confirmar.
   - Si es runtime (ej: "módulo instala sin errores") → sugerir comando al usuario y esperar su confirmación manual antes de marcar ✅.
   - **Si es test (Ola 4 y 5)**: **obligatorio correr el test y que pase**.
     - Si tenés entorno Odoo disponible → correr: `odoo-bin -d <db> -i <modulo> --test-enable --test-tags /<modulo>:TestXXX --stop-after-init`.
     - Si no → dar al usuario el comando exacto y esperar que te pase el output. No marcar ✅ sin output OK.

6. **Commit con mensaje convencional**:
   ```
   enhance(<modulo>): <TXX> <título corto>

   <descripción si es compleja, referenciar P0N del ENHANCEMENT_REPORT>

   Ref: enhance proposal <P0N>
   ```

7. **Actualizar `ENHANCEMENT_PLAN.md`**: cambiar el `[ ]` de esta tarea a `[x]`. Agregar hash del commit al final de la línea. Si la tarea es de Ola 4 o 5, anotar "test: ✅" junto al hash.

8. **Parar**. Imprimir:
   ```
   ✅ TXX completa. Commit: <hash>. Test: ✅ (Ola 4/5) | N/A (otras olas).

   Siguiente tarea: TYY — <título>
   **Importante**: abrí un chat NUEVO e invocá `/enhance-odoo-fix <ruta>`.
   Voy a detectar que TXX está ✅, que TYY es la próxima, y la arranco.

   Si querés hacer varias en paralelo (las marcadas `[∥]` en la misma ola),
   podés abrir varios chats simultáneos — cada uno toma una tarea distinta.
   ```

## Reglas duras

1. **Una mejora = un commit = un chat fresco**. No batchees mejoras en el mismo chat — la IA empieza a perder scope y hace atajos.
2. **No ejecutar Fase B sin plan aprobado por humano**. Si el usuario no confirmó el ENHANCEMENT_PLAN.md, volvé a Fase A o avisá.
3. **Scope estricto por tarea**. Si el acceptance dice "agregar `action_confirm`" y ves que también falta un helper, anotá en FOLLOWUPS.md y seguí con la tarea original.
4. **No saltar oleadas**. Si Ola N no está completa, no arranques Ola N+1 (excepto paralelismo dentro de la misma ola, con flag `[∥]`).
5. **Ola 4 y 5 SIEMPRE requieren test pasando**. No hay excepción. Si no hay entorno para correrlo, se espera confirmación manual del usuario con output del test — no se marca ✅ por fe.
6. **Si una tarea falla verificación**: STOP. No forzar. Reportar al usuario por qué falla y esperar decisión (re-planear, diferir, skip). Si es un problema de diseño de la propuesta → posiblemente haya que volver a Fase 4 de `enhance-odoo` y refinar el trace.
7. **Cambios de esquema (si alguna Ola 4 los requiere)**: pedir backup de DB al usuario antes de arrancar. Documentar migration script si aplica.

## Paralelización

Tareas marcadas `[∥]` en la **misma oleada** se pueden ejecutar en chats paralelos:
- Cada chat toma una tarea distinta.
- Al terminar, cada chat marca su `[x]` en `ENHANCEMENT_PLAN.md` — posible race condition si dos terminan a la vez. Mitigación: commit inmediato después de cada `[x]`, y si hay conflict, el segundo rebase manualmente.
- Limitar a máximo 2-3 chats paralelos — más allá de eso, el cuello de botella es la revisión humana.

**Ola 4 es más estrictamente serie** que las otras: cada feature de negocio puede depender de estructura creada por una anterior. Si dos tareas de Ola 4 NO comparten archivos y NO comparten modelos en sus tests, se pueden marcar `[∥]`. En duda → serie.

## FOLLOWUPS.md

Si durante la ejecución encontrás issues adicionales (bugs, prácticas pobres, oportunidades nuevas), agregálos a `<modulo>/.enhance/FOLLOWUPS.md`:

```markdown
- **F01** — encontrado durante T10
  - **Archivo:** models/order.py:145
  - **Descripción:** el método `_get_default` usa `self.env.user` dentro de un compute almacenado, lo que puede dar resultados distintos entre runs.
  - **Sugerencia:** usar `self.env.company` o agregar al `depends` el campo de contexto.
  - **Severidad estimada:** 🟡 Medio
```

Al finalizar todas las oleadas, sugerir al usuario:

1. Correr `/audit-odoo` para validar que las mejoras no introdujeron regresiones.
2. Re-correr `/enhance-odoo` si quiere — el nuevo informe va a considerar los FOLLOWUPS y las features recién agregadas para proponer la siguiente camada.

## Integración con el resto del toolkit

- **Prerequisito**: `/enhance-odoo <modulo>` debe haberse corrido y persistido `.enhance/ENHANCEMENT_REPORT.md`.
- **Recomendado antes**: `/audit-odoo <modulo>` + `/audit-odoo-fix <modulo>` — trabajar sobre módulo saneado evita proponer/implementar features sobre bugs críticos.
- **Post-enhance**: correr `/audit-odoo` de nuevo para verificar que las mejoras no introdujeron problemas (nuevos N+1, ACL laxa, etc.).
- **Antes de migrar**: si el módulo va a migrarse a otra versión Odoo, **completar todas las oleadas del enhance-fix antes** de `/migrate-odoo`. Migrar features nuevas a una versión nueva en el mismo paso es una receta para confusión.
