---
name: deadcode-odoo
description: Análisis estático de un módulo Odoo que detecta código muerto, métodos huérfanos, referencias rotas, modelos aislados y XML IDs sin uso. Cruza contra todos los addons del addons_path para evitar falsos positivos por referencias cross-module. Produce .deadcode/DEADCODE_REPORT.md con findings clasificados. Uso - /deadcode-odoo <ruta_al_modulo>
---

# Analizador de código muerto en Odoo

Este skill corre un análisis estático sobre un módulo Odoo y genera un informe narrativo de código muerto o desconectado: métodos sin caller, campos que nadie lee, botones apuntando a métodos inexistentes, modelos aislados (sin ACL ni vista ni FK), XML IDs huérfanos, valores de Selection sin uso.

**Complemento**: `/deadcode-odoo-fix` lee el informe y ejecuta las correcciones en oleadas (una corrección = un commit = un chat fresco).

**Scope del cruce**: por defecto, el scanner analiza **todos los módulos del `addons_path`** (resuelto desde `odoo.conf` del repo). Esto es clave: un método llamado desde un módulo que hereda el modelo target no debe aparecer como huérfano.

## Flujo general

```
/deadcode-odoo <modulo>      →  .deadcode/DEADCODE_SCAN.json   (scan estático)
                             →  .deadcode/DEADCODE_REPORT.md    (informe narrativo)
    ↓ (revisión humana)
/deadcode-odoo-fix <modulo>  →  .deadcode/DEADCODE_PLAN.md     (plan en oleadas)
    ↓ (chat nuevo por cada fix)
/deadcode-odoo-fix <modulo>  →  ejecuta una corrección
    ...
```

## Detección de estado

Al invocarse con `<ruta_al_modulo>`:

1. **Verificar precondiciones**:
   - Existe `<modulo>/__manifest__.py` (si no → error).
   - Existe el script scanner en la skill: `scripts/scan_deadcode.py` (dentro del propio skill dir).

2. **Determinar fase**:

| Estado en disco | Fase a ejecutar |
|---|---|
| No hay `<modulo>/.deadcode/DEADCODE_SCAN.json` o está desactualizado | **Fase A — Correr scanner** |
| Hay scan pero no hay `DEADCODE_REPORT.md` (o es más viejo que el scan) | **Fase B — Generar informe narrativo** |
| Hay report fresco | **Mostrar resumen** y sugerir `/deadcode-odoo-fix` |

"Desactualizado" = el scan es más viejo que cualquier archivo `.py`/`.xml`/`.csv` del módulo target.

Anunciá al usuario la fase detectada antes de arrancar.

## Fase A — Correr scanner

### Entrada
- `<ruta_al_modulo>` (path absoluto o relativo).

### Protocolo

1. **Estado git del módulo**: sugerir `git -C <modulo> status` limpio. El scan es read-only, pero los fixes posteriores necesitan tree limpio. Si hay WIP, avisar al usuario pero no bloquear el scan.

2. **Ejecutar el scanner**. Path del script: el mismo skill lo tiene en `scripts/scan_deadcode.py`. Invocación típica:
   ```bash
   python3 "$HOME/.claude/skills/deadcode-odoo/scripts/scan_deadcode.py" <ruta_al_modulo>
   ```
   (si la skill está instalada en otro path, usar ese).

   Flags opcionales:
   - `--addons-path <p1:p2:...>`: lista explícita. Si no se pasa, el script detecta automáticamente leyendo `<repo>/odoo.conf` y mapeando `/sources/*` → `<repo>/addons/*` (patrón del docker-compose del toolkit).
   - `--output pretty`: imprime el resumen y lista de findings en stdout además del JSON.

3. El script escribe `<modulo>/.deadcode/DEADCODE_SCAN.json` con todos los findings detectados.

4. Si el scan falla (exit != 0), reportar al usuario con el stderr y parar.

### Tiempos de referencia

- Scan sobre `sgc_mission` cruzando 1091 módulos de addons_path: ~30-60s (primera corrida), ~15s con FS cacheado.
- Si tarda >5 min: probablemente el `addons_path` incluye directorios gigantes irrelevantes (ej. `odoo-sources/odoo/addons` completo). Sugerir al usuario pasar `--addons-path` explícito con solo los addons relevantes.

## Fase B — Generar `DEADCODE_REPORT.md`

### Entrada
- `<modulo>/.deadcode/DEADCODE_SCAN.json`.

### Protocolo

1. Leer el JSON. Verificar integridad mínima: presencia de `stats`, `findings`, `modules_scanned`.

2. **Agrupar findings por categoría y severidad**. El scanner emite estas categorías:

| Categoría | Severidad típica | Significado |
|---|---|---|
| `broken_button_ref` | 🔴 | `<button name="X">` pero `X` no existe en ningún modelo |
| `broken_field_ref` | 🔴 | `<field name="X">` en vista pero `X` no existe en el modelo ni en sus mixins |
| `decorator_field_missing` | 🔴 | `@api.onchange('X')` pero `X` no existe en el modelo |
| `missing_compute_method` | 🔴 | `fields.X(compute='_compute_foo')` pero `_compute_foo` no existe |
| `orphan_method` | 🟡 | Método Python sin caller estático (ni XML, ni Python, ni decorador, ni dynamic dispatch) |
| `isolated_model` | 🟡 | Modelo sin ACL + sin vista + sin FK (2 de 3 o más) |
| `button_model_mismatch` | 🟡 | El método existe pero en otro modelo que el hint de la vista |
| `unused_field` | 🔵 | Campo no referenciado en ningún archivo del addons_path |
| `orphan_xmlid` | 🔵 | `<record id="X">` no es referenciado por `env.ref`/`ref=`/`action=`/`parent=` |
| `unused_selection_value` | 🔵 | Valor de `Selection` no seteado ni leído en ningún archivo |

**Semántica de severidades**:
- 🔴 **rojas son bugs confirmados**: rompen runtime o apuntan a algo inexistente. Decisión del autor: implementar, arreglar, o eliminar la referencia.
- 🟡 **amarillas son sospechosas**: métodos con prefijo `action_` sin binding pueden haber sido dejados sin botón por error, pero también pueden ser helpers mal nombrados o llamados desde JS frontend.
- 🔵 **azules requieren siempre criterio humano**: probable código muerto, pero puede usarse desde JS frontend, server actions (code inline), o configuración externa que el scanner no ve.

3. **Escribir `<modulo>/.deadcode/DEADCODE_REPORT.md`** con este formato:

```markdown
# DEADCODE_REPORT — <nombre_modulo>

**Generado:** <fecha>
**Scan:** `.deadcode/DEADCODE_SCAN.json` (<fecha_del_scan>)
**Addons escaneados:** N (cruce contra addons_path completo)
**Modelos:** N | **Métodos:** N | **Campos:** N | **XML refs:** N | **XML IDs:** N

## Resumen ejecutivo

| Severidad | Cantidad | Categorías principales |
|---|---|---|
| 🔴 Crítico | N | broken_field_ref (X), decorator_field_missing (Y), ... |
| 🟡 Sospechoso | N | orphan_method (X), isolated_model (Y), ... |
| 🔵 Revisión | N | orphan_xmlid (X), unused_field (Y), ... |

**Bugs confirmados (🔴):** X findings que referencian elementos inexistentes — rompen o están por romper runtime.
**Código posiblemente muerto (🟡):** Y findings con prefijo `action_`/`_compute_` sin binding detectable.
**A revisar con criterio humano (🔵):** Z findings de bajo riesgo, posibles leftovers.

## Caveats del análisis estático

- **Herencia cross-module**: escaneamos todos los addons en `addons_path`, pero NO los addons core de Odoo (`odoo/addons/*` fuera del addons_path). Campos de mixins conocidos (`mail.thread`, `mail.activity.mixin`, `portal.mixin`, `image.mixin`, `mail.alias.mixin`, `website.published.mixin`) están whitelisted.
- **Dispatch dinámico**: `getattr(self, 'method_'+state)()` no puede resolverse. Strings literales usados con `getattr(self, 'name')` se detectan, pero concatenaciones dinámicas no.
- **Frontend JS**: métodos `@api.model` expuestos vía JSON-RPC al web client no tienen caller Python — pueden aparecer como huérfanos.
- **Server actions**: métodos llamados desde `ir.actions.server` cuyo `code` es un string Python no pueden ser rastreados con AST. Revisar `data/server_actions.xml` manualmente.
- **Hooks de otros módulos no instalados**: si un módulo NO instalado extiende el target, no va a aparecer como caller — por eso el scan no incluye addons fuera del addons_path configurado.

## Findings

### 🔴 Críticos (bugs confirmados)

#### D01 — [broken_field_ref] Vista referencia campo inexistente `foo_bar`

**Archivo:** `views/sgc_order_views.xml:45`
**Evidencia:** `<field name="foo_bar"/>` en vista del modelo `sgc.order`
**Descripción:** El campo `foo_bar` no existe en `sgc.order` ni en ningún módulo que lo extiende en el addons_path escaneado. La vista va a crashear al renderizarse.
**Acciones posibles:**
- `add_field` — Declarar `foo_bar` en `models/sgc_order.py`.
- `remove_from_view` — Remover el `<field>` de la vista.
- `rename_to_existing` — Puede ser typo de un campo existente (listar candidatos con edit distance pequeña cuando sea obvio).

**Impacto:** vista inusable en runtime.

---

#### D02 — [decorator_field_missing] `@api.onchange('partner_x')` sobre campo inexistente

**Archivo:** `models/sgc_order.py:89`
**Evidencia:** `@api.onchange('partner_x') → def _onchange_partner_x(self)`
**Descripción:** El decorador referencia un campo `partner_x` que no existe en `sgc.order`. El onchange nunca se dispara.
**Acciones posibles:**
- `rename_decorator_arg` — si hay un typo (ej. `partner_id`).
- `add_field` — si el campo se olvidó declarar.
- `remove_decorator` — si el onchange ya no aplica.

---

[... resto de 🔴 ...]

### 🟡 Sospechosos (posible código muerto)

#### D15 — [orphan_method] Método huérfano `sgc.order.action_deprecated_flow`

**Archivo:** `models/sgc_order.py:120`
**Descripción:** Método público `action_deprecated_flow` sin caller en XML (buttons), Python (`self.action_...()`), decoradores de field, ni dispatch dinámico detectado. Motivo: el scanner recorrió N módulos sin encontrar referencia.
**Caveat:** puede ser llamado desde JS frontend (JSON-RPC), `ir.actions.server` con código inline, o un módulo fuera del `addons_path` escaneado.
**Acciones posibles:**
- `delete` — si el usuario confirma que no hay consumers externos.
- `wire_to_button_or_field` — si el método tiene lógica valiosa pero quedó sin gancho, agregarlo como botón en el form view.
- `confirm_external_caller` — si hay un consumer externo conocido, anotar dónde y dejarlo (marcar como `~descartado~`).

---

[... resto de 🟡 ...]

### 🔵 A revisar (bajo riesgo)

<Si hay >20 findings azules: tabla compacta. Si ≤20: uno por uno como los anteriores.>

| ID | Categoría | Archivo:línea | Target | Acción sugerida |
|---|---|---|---|---|
| D45 | orphan_xmlid | views/foo.xml:12 | `view_sgc_order_tree_custom` | delete / confirm_external |
| ... | ... | ... | ... | ... |

## Findings descartados por el usuario

<Si el usuario marca findings como falsos positivos editando el REPORT con ~descartado~, listarlos acá con motivo para trazabilidad. El `-fix` los va a ignorar.>

## Próximo paso

Correr `/deadcode-odoo-fix <ruta_al_modulo>` para generar el DEADCODE_PLAN.md en oleadas y ejecutar los fixes uno a uno (una corrección = un commit = un chat fresco).
```

4. **Criterio para detallar en el report**:
   - **Todos** los findings 🔴: uno por uno, con evidencia + acciones posibles.
   - **Todos** los findings 🟡: uno por uno si ≤20 por categoría; si más, detallar los 20 primeros y listar el resto en tabla.
   - **Findings 🔵**: si >20, tabla compacta. Si ≤20, detalle similar a 🟡.

5. **No eliminar nada todavía**. El REPORT es solo informativo.

6. **Al terminar, imprimir en chat**:

```
✅ Análisis completo.

📊 Stats:
   - Módulos escaneados: N
   - Métodos/campos target: M/F
   - Findings: T (🔴 R | 🟡 Y | 🔵 B)

📁 Archivos generados:
   - <modulo>/.deadcode/DEADCODE_SCAN.json  (raw data — podés regenerarlo cuando quieras)
   - <modulo>/.deadcode/DEADCODE_REPORT.md  (informe narrativo)

🔴 Bugs confirmados: R — estos rompen runtime o apuntan a elementos inexistentes.
🟡 Sospechosos: Y — requieren tu criterio sobre dispatch externo / JS frontend.
🔵 A revisar: B — probables leftovers, bajo riesgo.

Próximo paso:
1. Revisá DEADCODE_REPORT.md — especialmente los 🔴 y los 🟡 que te parecen importantes.
2. Marcá cualquier finding que sea obvio falso positivo (ej. "este método SÍ lo uso desde X"):
   editá el report y cambiá severidad a ~descartado (razón)~.
3. Cuando te cierre, invocá /deadcode-odoo-fix <ruta_al_modulo> en un chat nuevo —
   va a generar un plan de corrección en oleadas y ejecutar fix por fix.
```

## Reglas duras

1. **El scan es read-only**. Bajo ninguna circunstancia este skill modifica código del módulo target. Solo produce archivos en `<modulo>/.deadcode/`.

2. **No eliminar nada por tu cuenta**. Las acciones `delete` son **sugerencias** para el `-fix` — este skill nunca ejecuta deletes.

3. **Scope disciplinado**. El analizador no opina sobre estilo, performance, ni seguridad. Para eso están `/audit-odoo` y `/enhance-odoo`. Acá se detecta **muerto/roto/desconectado** y nada más.

4. **Sugerir agregar `.deadcode/` al `.gitignore`** del módulo si todavía no está. Es output de análisis, no source code. Nunca commitear el SCAN.json (cambia con cada corrida). El REPORT.md puede commitearse si el usuario quiere trazabilidad, pero por default también va al gitignore.

5. **Caveats visibles**. El informe siempre incluye la sección "Caveats del análisis estático" explícita. El usuario debe saber qué NO detecta la herramienta para evitar eliminaciones ciegas.

6. **Si el scan falla** (exit != 0, JSON inválido, timeout): parar, mostrar stderr, sugerir `--addons-path` explícito o correr `python3 scan_deadcode.py --help`.

7. **No regenerar scan automáticamente**. Si ya hay un SCAN.json y el usuario re-invoca la skill, preguntar antes de re-scanear — el scan puede tardar 30s+. Solo re-scan si el usuario confirma o si el SCAN es más viejo que el último cambio de código del módulo.

## Integración con el resto del toolkit

- **Antes**: idealmente `/audit-odoo` ya pasó (no es requisito, pero un módulo con bugs de ACL/ORM graves puede producir falsos 🟡 porque sus callers están rotos).
- **Después**: `/deadcode-odoo-fix` consume el REPORT y genera el PLAN de corrección.
- **Complementario**: `/enhance-odoo` propone features nuevas; `/deadcode-odoo` detecta features quedadas a medio implementar. No se pisan.
- **Antes de migrar**: correr `/deadcode-odoo` antes de `/migrate-odoo` evita arrastrar código muerto a la nueva versión.

## FAQ

**¿Qué pasa si el scan marca un método como huérfano pero YO sé que se usa?**
Anotalo en el REPORT reemplazando la severidad por `~descartado (razón: llamado desde módulo X externo al addons_path)~`. El `-fix` respetará ese marcador y no te va a proponer eliminarlo.

**¿El scan detecta si un campo del módulo A está siendo usado por el módulo B?**
Sí — es el caso que resuelve el cruce del addons_path. Si A declara `field_x` y B hace `self.field_x` o lo muestra en una vista extendida, A.field_x NO sale como unused.

**¿Qué pasa con controllers HTTP y portal templates?**
- Controllers con `@http.route(...)` se marcan como "bound by @http.route" → no huérfanos.
- Portal templates (QWeb) se detectan como referenciados si alguna vista los menciona por id, o si aparecen como string en `request.render('module.template_id')` en código Python.

**¿Por qué tantos `orphan_xmlid` en vistas tree/form del mismo modelo?**
Odoo resuelve vistas `tree`/`form`/`kanban`/... implícitamente por `res_model` + `view_mode` de una `ir.actions.act_window`. El scanner **whitelistea vistas cuyo modelo es target de alguna `act_window` conocida**. Si igual aparecen como huérfanas, probablemente el módulo no tiene `act_window` sobre ese modelo — vale la pena revisar si es intencional (¿el modelo se accede solo via smart button? ¿solo desde otro módulo?).

**¿Puedo limitar el scan a un subset de addons para que sea más rápido?**
Sí: `--addons-path <p1>:<p2>:...` — el script acepta coma o dos puntos como separador. Útil cuando solo te importa el cruce con módulos de tu organización y no con OCA/Enterprise completos.

**¿Por qué hay tantos falsos positivos de `broken_field_ref` si estoy usando mixins de OCA?**
Los mixins de OCA no están hardcodeados en el whitelist del scanner — solo los core de Odoo (`mail.*`, `portal.mixin`, `image.mixin`, `website.*`). Si tu módulo hereda de un mixin OCA, el campo aparecerá como "roto" si el módulo OCA no está en el `addons_path` escaneado. Solución: asegurar que OCA está en el addons_path, o marcar esos findings como `~descartado~` en el REPORT.
