---
name: audit-odoo-fix
description: Genera plan de remediación a partir de un AUDIT_REPORT.md producido por audit-odoo, y ejecuta los fixes uno a uno con regla de chat fresco por tarea. Uso - /audit-odoo-fix <ruta_al_modulo>
---

# Aplicador de fixes post-auditoría Odoo

Este skill es el complemento de `audit-odoo`. Lee el informe de auditoría producido por el audit, genera un **plan de remediación priorizado en oleadas**, y ejecuta los fixes uno a la vez respetando la misma disciplina de `migrate-odoo` (un fix = un commit = un chat fresco).

## Flujo general

```
/audit-odoo <modulo>        →  .audit/AUDIT_REPORT.md
    ↓
/audit-odoo-fix <modulo>    →  .audit/FIX_PLAN.md  (primera vez: genera plan)
    ↓
/audit-odoo-fix <modulo>    →  ejecuta UN fix     (invocaciones siguientes)
    ↓ (chat nuevo)
/audit-odoo-fix <modulo>    →  ejecuta siguiente fix
    ...
```

## Detección de estado

Al invocarse con `<ruta_al_modulo>`:

1. **Verificar precondiciones**:
   - Existe `<modulo>/__manifest__.py` (si no → error).
   - Existe `<modulo>/.audit/AUDIT_REPORT.md` (si no → sugerir correr `/audit-odoo <modulo>` primero).

2. **Determinar fase**:

| Estado en disco | Fase a ejecutar |
|---|---|
| Hay `AUDIT_REPORT.md`, no hay `FIX_PLAN.md` | **Fase A — Generar plan** |
| Hay `FIX_PLAN.md` con tareas pendientes (checkbox vacío) | **Fase B — Ejecutar próxima tarea** |
| Todas las tareas en `FIX_PLAN.md` ✅ | **Terminado** — mostrar resumen de cierre |

Anunciá al usuario qué fase detectaste y esperá confirmación antes de arrancar.

## Fase A — Generar `FIX_PLAN.md`

### Entrada
- `<modulo>/.audit/AUDIT_REPORT.md`

### Protocolo

1. Leer el informe completo. Extraer todos los hallazgos clasificados por severidad.

2. **Agrupar los hallazgos en tareas atómicas** siguiendo estas reglas:
   - Una tarea = un commit coherente. Si un hallazgo es grande, dividir.
   - Una tarea que se puede hacer **en cualquier orden respecto de otras** va con flag `[∥]` (paralelizable).
   - Una tarea que **depende del output de otra** va con `dep: TXX`.
   - Cada tarea lleva acceptance criteria **verificables**.

3. **Distribuir las tareas en 4 oleadas** según riesgo/dependencia:

   | Oleada | Características | Ejemplos típicos |
   |---|---|---|
   | **Ola 1 — Quick wins** | Config, CSV, manifest, estructura de carpetas, README. Sin riesgo de bug funcional. | Corregir `__manifest__.py`, quitar permisos indebidos en ACL CSV, mover archivos a carpetas estándar |
   | **Ola 2 — Refactors de código** | Cambios en Python que no alteran esquema de DB. Requieren test después. | N+1, decorators, validación de inputs, paginación |
   | **Ola 3 — Cambios de esquema** | Tocan la DB. Requieren script de migración. **Serie obligatoria** entre sí. | Agregar `company_id`, hashear tokens existentes, nuevas constraints |
   | **Ola 4 — Cobertura y compliance** | Tests, i18n, documentación, UX de consent. No bloquean funcionalidad pero sí deploy a prod. | Tests unitarios, `.pot`, README ampliado, checkbox de consentimiento |

4. **Priorización dentro de cada oleada**:
   - Primero los 🔴 Críticos, después 🟠 Altos, después 🟡/🔵.
   - Dentro de la misma severidad, primero los que NO dependen de otros.

5. **Producir el archivo** `<modulo>/.audit/FIX_PLAN.md` con esta estructura:

```markdown
# FIX_PLAN — <nombre_modulo>

**Generado**: <fecha>
**Basado en**: `.audit/AUDIT_REPORT.md` (auditoría del <fecha_del_report>)
**Total tareas**: N en M oleadas

## Pre-oleada — Preparación

- [ ] T00 — Tag + branch de trabajo
  ```
  git tag pre-audit-fixes-$(date +%Y%m%d)
  git checkout -b audit-fixes/<modulo>
  ```

## Ola 1 — Quick wins

- [ ] **T01** `[∥]` **<título>** — Sev: 🔴 C1
  - **Archivos**: `path/to/file.py:line`
  - **Qué hacer**: <descripción concreta>
  - **Acceptance**: <criterio verificable>
  - **Dep**: (ninguna | Txx)

- [ ] **T02** `[∥]` ...

### Gate Ola 1
<criterio objetivo para declarar ola cerrada>

## Ola 2 — Refactors de código
...

## Ola 3 — Cambios de esquema (requieren migración)
...

## Ola 4 — Cobertura y compliance
...

## Resumen

| Ola | Tareas | Tiempo estimado | Riesgo |
|---|---|---|---|
| 1 | ... | ... | Bajo |
| ...
```

6. **Al terminar**, imprimir en chat:

```
✅ FIX_PLAN.md generado con N tareas en M oleadas.

**Próximo paso**: revisá el plan en `<ruta>/.audit/FIX_PLAN.md`.
Si te queda cómodo, volvé a invocar `/audit-odoo-fix <ruta>` en un chat nuevo —
voy a detectar el plan y empezar a ejecutar la primera tarea pendiente.

PLAN READY FOR REVIEW — no arrancar ejecución hasta aprobar el plan.
```

**Gate humano obligatorio**: no avanzar a Fase B hasta que el usuario revise `FIX_PLAN.md`. Si tiene comentarios, ajustá el plan y regenerá.

## Fase B — Ejecutar la próxima tarea

### Entrada
- `<modulo>/.audit/FIX_PLAN.md` con al menos una tarea con checkbox vacío `[ ]`.

### Protocolo

1. **Leer `FIX_PLAN.md`**, encontrar la **primera tarea con `[ ]`** que tenga todas sus dependencias `dep:` ya marcadas como `[x]`.

2. **Re-state la tarea al usuario** en una línea: "Voy a ejecutar `TXX — <título>`. Archivos: X. Acceptance: Y. ¿OK?".
   - Esperar confirmación.
   - Si el usuario quiere saltar o hacer otra, preguntar cuál.

3. **Leer solo los archivos listados** en la tarea. No explorar más. Scope disciplinado.

4. **Implementar el fix**:
   - Cambios mínimos para cumplir acceptance.
   - No refactors adicionales ("drive-by").
   - Si encontrás otros issues que no están en la tarea, anotarlos en `<modulo>/.audit/FOLLOWUPS.md` — no los arregles.

5. **Verificar el acceptance**:
   - Si es sintáctico (ej: "campo agregado") → grep / re-read para confirmar.
   - Si es runtime (ej: "cron corre en <5s con 500 leases") → sugerir comando al usuario y esperar su confirmación manual antes de marcar ✅.
   - Si es test → correrlo si podés (respetar que no siempre hay entorno Odoo disponible).

6. **Commit con mensaje convencional**:
   ```
   audit-fix(<modulo>): <TXX> <título corto>

   <descripción si es compleja>

   Closes: audit finding <ref>
   ```

7. **Actualizar `FIX_PLAN.md`**: cambiar el `[ ]` de esta tarea a `[x]`. Agregar hash del commit al final de la línea de la tarea.

8. **Parar**. Imprimir:
   ```
   ✅ TXX completa. Commit: <hash>.

   Siguiente tarea: TYY — <título>
   **Importante**: abrí un chat NUEVO e invocá `/audit-odoo-fix <ruta>`.
   Voy a detectar que TXX está ✅, que TYY es la próxima, y la arranco.

   Si querés hacer varias en paralelo (las marcadas `[∥]` en la misma ola),
   podés abrir varios chats simultáneos — cada uno toma una tarea distinta.
   ```

## Reglas duras

1. **Un fix = un commit = un chat fresco**. No batchees fixes en el mismo chat — la IA empieza a perder scope y hace atajos.
2. **No ejecutar Fase B sin plan aprobado por humano**. Si el usuario no confirmó el FIX_PLAN.md, volvé a Fase A o avisá.
3. **Scope estricto por tarea**. Si el acceptance dice "agregar `_order`" y ves que también falta `_description`, anotá en FOLLOWUPS.md. No lo arregles.
4. **No saltar oleadas**. Si Ola 1 no está completa, no arranques Ola 2 (excepto que el usuario explícitamente lo pida — en cuyo caso preguntar por qué).
5. **Ola 3 SIEMPRE en serie**. Son cambios de esquema — no paralelizar aunque no haya dep explícita. Cada una requiere backup + verificación antes de la siguiente.
6. **Antes de cada tarea de Ola 3**: pedir al usuario que confirme que hizo backup de DB reciente.
7. **Si una tarea falla verificación**: STOP. No forzar. Reportar al usuario por qué falla y esperar decisión (re-planear, diferir, skip).

## Paralelización

Tareas marcadas `[∥]` en la **misma oleada** se pueden ejecutar en chats paralelos:
- Cada chat toma una tarea distinta.
- Al terminar, cada chat marca su `[x]` en `FIX_PLAN.md` — hay una posible race condition si dos terminan a la vez y editan el archivo. Mitigación: commitear inmediato después de cada `[x]`, y si hay conflict, el segundo rebase manualmente.
- Limitar a máximo 2-3 chats paralelos — más allá de eso, el cuello de botella es la revisión humana.

No paralelizar entre oleadas. Ola 2 depende de gate de Ola 1.

## FOLLOWUPS.md

Si encontrás issues adicionales que no están en el plan original, agregálos a `<modulo>/.audit/FOLLOWUPS.md` con este formato:

```markdown
- **Issue F01** — encontrado durante T05
  - **Archivo**: path/to/file.py:line
  - **Descripción**: qué pasa
  - **Sugerencia**: cómo arreglar
  - **Severidad estimada**: 🟡 Medio
```

Al finalizar todas las oleadas, sugerir al usuario correr `/audit-odoo` de nuevo → el nuevo informe va a incluir estos followups + cambios hechos, y el próximo `FIX_PLAN.md` los absorbe.

## Integración con el resto del toolkit

- **Prerequisito**: `/audit-odoo <modulo>` debe haberse corrido y persistido `.audit/AUDIT_REPORT.md`.
- **Post-fixes**: después de aplicar todo el FIX_PLAN, correr `/audit-odoo` de nuevo para validar que los issues marcados estén resueltos y detectar regresiones o nuevos.
- **Antes de migrar**: si el módulo va a migrarse a otra versión Odoo, idealmente aplicar Ola 1 y Ola 2 del FIX_PLAN **antes** de invocar `/migrate-odoo` — la migración sobre código limpio es 5x más fácil.
