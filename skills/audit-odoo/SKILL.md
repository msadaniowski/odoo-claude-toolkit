---
name: audit-odoo
description: Auditar un módulo Odoo antes de instalarlo. Analiza estructura, manifest, código Python (ORM/API), seguridad, vistas XML y datos. Se adapta a la versión de Odoo declarada en __manifest__.py. Uso - /audit-odoo <ruta_al_modulo>
---

# Auditor de módulos Odoo

Auditoría exhaustiva de un módulo Odoo para detectar problemas de estructura, calidad, seguridad y cumplimiento de convenciones antes de instalarlo.

## Uso

El usuario invoca con `/audit-odoo <ruta_al_modulo>`. Si no provee ruta, pedir la ruta absoluta del directorio que contiene `__manifest__.py`.

## Flujo de trabajo

Trabajá en español (registro argentino). Seguí estas fases en orden. Usá TodoWrite para trackear el progreso — una tarea por fase.

### Fase 0 — Reconocimiento

1. Verificar que la ruta existe y contiene `__manifest__.py` y `__init__.py`.
2. Leer `__manifest__.py` para extraer:
   - `name`, `version`, `depends`, `data`, `demo`, `assets`, `license`, `installable`, `application`, `auto_install`.
   - **Versión de Odoo**: el primer número de `version` (ej: `"17.0.1.0.0"` → Odoo 17). Si no es claro, preguntar al usuario.
3. Mapear la estructura de carpetas con Glob (`**/*` en la ruta del módulo). Identificar presencia de: `models/`, `views/`, `security/`, `data/`, `demo/`, `static/`, `wizard/`, `report/`, `controllers/`, `tests/`, `i18n/`.
4. Contar archivos por tipo (`.py`, `.xml`, `.csv`, `.po`, `.js`, `.xml` de QWeb, `.scss`/`.css`).

Guardá estos hallazgos en memoria del turno — vas a referenciarlos en cada fase.

### Fase 1 — Estructura y manifest

Verificá:

- **Manifest obligatorio/recomendado**: `name`, `version` (con formato `X.0.Y.Z.W`), `depends` (al menos `['base']` implícito), `license` (LGPL-3, AGPL-3, OEEL-1, etc. — advertir si falta), `author`, `category`, `summary`, `installable: True`.
- **`version`**: debe empezar con la versión mayor de Odoo (17.0.x, 18.0.x). Advertir si está desfasada.
- **`depends`**: chequear que cada módulo listado exista como import razonable (no puede depender de un módulo que no existe en Odoo core conocido; si es custom, dejarlo como "verificar manualmente").
- **`data` vs `demo`**: archivos en `data` cargan siempre; `demo` solo con `--load-demo`. Los seeds de prueba no deben ir en `data`.
- **Orden de carga en `data`**: security → data → views → reports → menús. Errores de orden generan `ExternalId not found`.
- **Estructura de carpetas estándar**:
  - `models/__init__.py` importa cada modelo.
  - `security/ir.model.access.csv` existe si hay modelos nuevos.
  - `views/` separado por modelo (ej: `views/partner_views.xml`).
  - `tests/` con `__init__.py` y tests.
  - NO debe haber archivos sueltos `.py` con lógica en la raíz (excepto `__init__.py` y `__manifest__.py`).
- **`__init__.py`**: debe importar `models`, `controllers`, `wizard` según corresponda. Falta común: definir un modelo pero no importarlo.
- **Iconos**: `static/description/icon.png` recomendado.
- **README**: `README.rst` o `README.md` recomendado (OCA exige RST).

### Fase 2 — Código Python (ORM y calidad)

Leé cada archivo en `models/`, `wizard/`, `controllers/`, `report/`. Para cada uno verificá:

#### Convenciones y herencia
- Nombres de clase en `CamelCase`, nombres de modelo en `dot.notation` (ej: `sale.order.line`).
- `_name` para nuevos, `_inherit` (string) para extender en el mismo modelo, `_inherit + _name` para prototype inheritance (delegación).
- `_inherits` (plural) usa composición con campo `_inherits = {'res.partner': 'partner_id'}` — verificar que el campo exista como `Many2one required=True ondelete='cascade'`.
- `_description` obligatorio en modelos nuevos (sin él, Odoo emite warning al cargar).
- `_order` recomendado si hay vistas list.

#### API y decoradores
- `@api.depends(...)` obligatorio en campos `compute`. Campos computados que no dependen de nada deben usar `@api.depends_context` o declarar `store=False` explícito.
- `@api.onchange(...)` solo para UX en formularios — **nunca** para lógica de negocio.
- `@api.model` para métodos que no operan sobre un recordset.
- `@api.constrains(...)` para validaciones. No usar `raise` sin `UserError`/`ValidationError` (importar de `odoo.exceptions`).
- `@api.model_create_multi` recomendado en Odoo 13+ (aceptar lista de dicts). En Odoo 17/18 es casi obligatorio para performance.

#### Problemas de performance (N+1 y smells)
- `for record in self: record.browse(...)` dentro de loops → N+1.
- `self.env['modelo'].search([])` sin límite ni filtro en métodos que corren frecuentemente.
- Uso de `filtered(lambda r: r.field == x)` sobre recordsets enormes — preferir `search` con dominio.
- `sum(record.line_ids.mapped('amount'))` bien; `sum([l.amount for l in record.line_ids])` también, pero evitar iterar con `.browse(id)` adentro.
- Escribir dentro de un `compute` → casi siempre error. Los compute deben asignar a `self.field`, no hacer `write`.

#### Seguridad en el código
- `sudo()` **solo** cuando realmente hace falta cruzar permisos — documentar por qué. Auditar cada uso.
- `self._cr.execute(...)` / SQL crudo → verificar que use parámetros (`%s`), nunca f-strings/format con input de usuario. Esto es SQL injection.
- Controllers `@http.route(..., auth='public')` → advertir: cualquier endpoint público necesita validación de inputs y rate-limiting en el diseño.
- `auth='user'` es el default seguro.
- `csrf=False` en POST → solo permitido en webhooks con firma; justificar.

#### Campos
- `Selection` con strings hardcoded → ok, pero preferir método si puede extenderse.
- `Monetary` requiere `currency_field`.
- `One2many` requiere `inverse_name`.
- `Many2one` en modelos importantes → considerar `ondelete='restrict'` o `'cascade'` explícito (el default `set null` suele sorprender).
- `compute` sin `store=True` y usado en dominios de búsqueda → debe tener `search=` method.
- `default=` con funciones lambda: `default=lambda self: self.env.user.company_id` — asegurar que devuelve el tipo correcto.

#### Imports
- `from odoo import models, fields, api, _` (con `_` para traducciones).
- `from odoo.exceptions import UserError, ValidationError`.
- NO importar de `openerp` (API legacy pre-10.0).
- NO usar `print()` — usar `_logger = logging.getLogger(__name__)`.

#### Tests
- Carpeta `tests/` con `__init__.py` que importe los tests.
- Heredan de `odoo.tests.common.TransactionCase` o `HttpCase`.
- Decorador `@tagged('post_install', '-at_install')` recomendado.
- Advertir si el módulo no tiene tests.

### Fase 3 — Seguridad

#### `security/ir.model.access.csv`
- Debe existir si hay modelos nuevos. Formato:
  `id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink`
- Para cada modelo nuevo (con `_name`), verificar que tenga al menos una entrada.
- Si el modelo es solo para uso interno (TransientModel/wizard), puede tener acceso a `base.group_user`.
- Advertir si **algún grupo tiene los 4 permisos en True para un modelo sensible** (ej: `account.move`).

#### `security/*.xml` (record rules)
- Reglas multi-company: si el modelo tiene `company_id`, debe existir una `ir.rule` para filtrar por compañía.
- `groups` en las reglas: verificar que los XIDs existen.
- `domain_force`: validar sintaxis básica de dominio.

#### Grupos
- Si el módulo define grupos (`res.groups`), deben tener `category_id` apuntando a un módulo/categoría existente.

### Fase 4 — Vistas XML y datos

Para cada archivo XML en `views/`, `data/`, `demo/`, `report/`:

#### Estructura
- Declaración `<?xml version="1.0" encoding="utf-8"?>` al inicio.
- Root `<odoo>` (moderno) o `<odoo><data>` (legacy, advertir).
- `noupdate="1"` en datos que el usuario modificará (ej: plantillas de email por defecto). Sin `noupdate`, se sobreescriben en updates.

#### Vistas
- `<record id="..." model="ir.ui.view">` con:
  - `name` descriptivo (`modelo.tipo.form` convención).
  - `model` correcto.
  - `inherit_id` con XID válido si es herencia.
  - `arch` con XPath correcto (`<xpath expr="..." position="after|before|inside|replace|attributes">`).
- `position="replace"` → advertir: rompe compatibilidad con otros módulos. Preferir `attributes` o `after+invisible`.
- **En Odoo 17+**: las vistas list (`<tree>` renombrado a `<list>` en 18, `<tree>` sigue funcionando). Verificar coherencia con la versión.
- **En Odoo 17+**: nuevo sistema de `<setting>` en res.config.settings.
- Acciones (`ir.actions.act_window`): `res_model`, `view_mode` obligatorios. `view_mode="tree,form"` antes de 18, `"list,form"` en 18.

#### Menús
- `<menuitem>` con `parent`, `action`, `sequence`. Si no hay parent, se crea menú raíz — advertir si no es intencional.

#### IDs externos
- Formato `modulo.xid` si es referencia a otro módulo. Dentro del mismo módulo, solo `xid`.
- No usar `ref="base.main_company"` en data si el módulo es multi-company sin cuidado.

#### Traducciones
- Carpeta `i18n/` con archivos `.po` o `.pot`.
- Si el módulo tiene strings de usuario y no tiene `.pot` → advertir.
- Strings en Python deben usar `_()`, en XML usan automáticamente traducción si el atributo es traducible.

#### Assets (JS/CSS)
- En Odoo 15+: definidos en `__manifest__.py` bajo clave `assets`, no en XML `<template>` con `inherit_id="web.assets_backend"`.
- Advertir si usa el método viejo (template) en módulos declarados para 15+.

#### QWeb / Reports
- `<template id="...">` con `name`. Reports con `<t t-call="web.html_container">`.
- Revisar `t-esc` (escapa) vs `t-raw` (no escapa — **peligroso con input de usuario**, XSS).

### Fase 5 — Informe

**Persistencia en disco (obligatorio)**: además de mostrar el informe en chat, guardá una copia en:

- `<modulo>/.audit/AUDIT_REPORT.md` — siempre la última auditoría (se sobreescribe).
- `<modulo>/.audit/history/AUDIT_REPORT_<YYYY-MM-DD>.md` — histórico inmutable.

Esto es **crítico** para que el skill `audit-odoo-fix` pueda leer el informe en un chat posterior y generar el plan de remediación.

Si la carpeta `.audit/` no existe, creala. Si el módulo tiene `.gitignore` y el usuario no quiere comitear las auditorías, sugerirle agregar `.audit/` al `.gitignore`. Dejar la decisión al usuario.

Produce el informe en Markdown con esta estructura:

```markdown
# Auditoría: <nombre_modulo> v<version>

**Odoo:** <version_odoo>
**Ruta:** <ruta>
**Archivos:** X Python, Y XML, Z CSV
**Fecha:** <hoy>

## Resumen ejecutivo

<1 párrafo: veredicto general + cantidad de issues por severidad>

| Severidad | Cantidad |
|-----------|----------|
| 🔴 Crítico | N |
| 🟠 Alto    | N |
| 🟡 Medio   | N |
| 🔵 Bajo    | N |
| ℹ️  Info    | N |

## Hallazgos

### 🔴 Crítico
- **[archivo:línea]** Descripción corta. **Por qué:** impacto. **Cómo arreglar:** sugerencia concreta.

### 🟠 Alto
...

### 🟡 Medio
...

### 🔵 Bajo / ℹ️ Info
...

## Checklist de cumplimiento

- [x] Manifest completo
- [ ] Tests presentes
- [x] Seguridad (ir.model.access.csv)
- [ ] Record rules multi-company
- [x] Convenciones de naming
- [ ] ...

## Recomendaciones generales

<sugerencias de mejora, no necesariamente bugs>
```

**Criterios de severidad:**
- 🔴 **Crítico**: rompe instalación, vulnerabilidad de seguridad (SQL injection, XSS, permisos abiertos), pérdida de datos potencial.
- 🟠 **Alto**: bug funcional probable, N+1 severo, incompatibilidad con versión de Odoo declarada.
- 🟡 **Medio**: mala práctica con impacto moderado (sudo sin justificar, compute sin depends en caso ambiguo).
- 🔵 **Bajo**: estilo, convenciones menores, falta de README.
- ℹ️ **Info**: observación/sugerencia.

## Diferencias por versión de Odoo

Adaptá los checks según la versión declarada:

- **< 13**: API vieja, `@api.multi` aún existe. `_defaults` dict todavía válido.
- **13–15**: `@api.multi` deprecado. `@api.model_create_multi` introducido.
- **16**: Owl 2.0 para frontend. Assets siempre vía manifest.
- **17**: Cambios en `res.config.settings` (nuevo `<setting>`). Owl templates con nueva sintaxis.
- **18**: `<tree>` → `<list>` (ambos funcionan, pero `<list>` es el nuevo estándar). `view_mode="list,form"`.

Si la versión del manifest no coincide con la API usada en código → issue 🟠 Alto.

## Notas finales

- Si encontrás algo que no te cierra, preguntá al usuario antes de marcarlo como issue — puede ser intencional.
- No marques como issue prácticas válidas en versiones viejas si el manifest declara esa versión.
- Al final, ofrecé al usuario aplicar fixes automáticos si son triviales (con su confirmación).
- Si el módulo es muy grande (>30 archivos Python), podés paralelizar la lectura con subagentes Explore para las fases 2–4.
