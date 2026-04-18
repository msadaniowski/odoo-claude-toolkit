---
name: enhance-odoo
description: Analiza un módulo Odoo y propone mejoras y nuevas funcionalidades validadas end-to-end (negocio, técnico, UX, seguridad). Cada propuesta incluye trace de flujo, verificación de prerequisitos, chequeo de colisiones con lógica existente y test automatizado. Descarta propuestas cuyo flujo no se pueda completar en el módulo actual. Uso - /enhance-odoo <ruta_al_modulo>
---

# Analizador de mejoras para módulos Odoo

Análisis propositivo de un módulo Odoo para sugerir mejoras y nuevas funcionalidades **validadas end-to-end antes de proponerlas**. A diferencia de `audit-odoo` (que busca problemas en lo existente), esta skill busca oportunidades para agregar valor — pero con una disciplina dura: si un candidato no se puede ejecutar completo en el módulo actual, se descarta con razón explícita.

## Principio rector

> **Proponer es fácil, validar es difícil. Preferí descartar antes que proponer algo roto.**
>
> Cada propuesta que aparece en el informe tiene que poder ejecutarse end-to-end en este módulo, con la infraestructura que ya existe o con la que el candidato incluya crear como parte de su propio scope. Si falta una pieza del flujo (un grupo, una dependencia, un controller, un template, un usuario portal configurable, un `mail.template`, un `ir.sequence`), el candidato o la absorbe o se descarta — nunca se propone un circuito dependiendo de que "alguien más" configure una pieza silenciosa.
>
> Caso paradigmático a evitar: proponer un "quiz por portal para operarios" cuando el módulo no tiene portal instalado, no hay controller portal, no hay template, no hay flujo de alta de usuario portal, y no hay `mail.template` para la notificación. Eso es una propuesta aspiracional que no sirve para nada.

## Uso

El usuario invoca con `/enhance-odoo <ruta_al_modulo>`. Si no provee ruta, pedir la ruta absoluta del directorio que contiene `__manifest__.py`.

**Prerequisito recomendado (no obligatorio)**: correr `/audit-odoo <ruta>` antes. Si existe `<modulo>/.audit/AUDIT_REPORT.md`, esta skill lo lee para enriquecer el perfil del módulo y evitar proponer mejoras sobre código con bugs conocidos. Si no existe, avisar al usuario pero continuar.

## Flujo de trabajo

Trabajá en español (registro argentino). Seguí estas fases en orden. Usá TodoWrite para trackear el progreso — una tarea por fase.

### Fase 0 — Reconocimiento

1. Verificar que la ruta existe y contiene `__manifest__.py` y `__init__.py`.
2. Leer `__manifest__.py` para extraer:
   - `name`, `version`, `depends`, `data`, `demo`, `assets`, `license`, `installable`, `application`, `auto_install`.
   - **Versión de Odoo**: el primer número de `version` (ej: `"17.0.1.0.0"` → Odoo 17). Si no es claro, preguntar al usuario.
3. Mapear la estructura de carpetas con Glob (`**/*` en la ruta del módulo). Identificar presencia de: `models/`, `views/`, `security/`, `data/`, `demo/`, `static/`, `wizard/`, `report/`, `controllers/`, `tests/`, `i18n/`.
4. Contar archivos por tipo (`.py`, `.xml`, `.csv`, `.po`, `.js`).
5. Leer (si existe) `.audit/AUDIT_REPORT.md` — sirve como input para no proponer sobre código con bugs críticos pendientes.

Guardá estos hallazgos en memoria del turno — vas a referenciarlos en cada fase.

### Fase 1 — Perfil del módulo

Entender qué hace HOY el módulo antes de proponer qué podría hacer. Para cada archivo en `models/`, `wizard/`, `controllers/`, `report/`:

- **Modelos**: listar `_name`, `_inherit`, `_inherits`. Para cada modelo nuevo, listar campos clave (compute, related, selection, state), `_order`, `_rec_name`, `_description`.
- **Estado/workflow**: detectar campos `state` con `Selection`. Anotar los valores y los métodos que hacen transiciones (buttons, automated actions).
- **Hooks/puntos de extensión**: métodos con nombres convencionales `_prepare_*`, `_get_*`, `_compute_*`, `_onchange_*`, `_check_*`, `_action_*`.
- **Botones de acción**: métodos decorados o que emiten `return { 'type': 'ir.actions...' }`.
- **Crons**: buscar `ir.cron` en XML o en data.
- **Wizards**: modelos `TransientModel` — qué hacen, desde dónde se invocan.
- **Actores**: grupos definidos (`res.groups` en XML), referencias a grupos externos en `ir.model.access.csv`.
- **Views relevantes**: form, list, kanban, search — cuáles existen por modelo.
- **Menús**: jerarquía básica (raíz + hijos).

Producir en memoria un "perfil" breve: 3-5 líneas describiendo QUÉ hace el módulo, quiénes lo usan, y cuáles son los flujos principales.

### Fase 2 — Capability matrix (crítico)

Antes de proponer, mapear explícitamente qué infraestructura YA está disponible. Esta matrix es la base para filtrar candidatos en la Fase 4.

| Capacidad | Cómo detectarla |
|---|---|
| `mail.thread` | modelos heredan `mail.thread`? `mail.activity.mixin`? |
| `portal` | `portal` en `depends`? modelos heredan `portal.mixin`? hay controller que extiende `portal.CustomerPortal`? hay templates portal en XML? |
| `website` | `website` en `depends`? hay `website.page`? templates con `inherit_id="website.layout"` o `t-call="website.layout"`? |
| `multi-company` | modelos tienen `company_id`? hay `ir.rule` por compañía? |
| `mail.template` | hay `<record model="mail.template">` declarados? notificaciones existentes? |
| `reports` | hay `ir.actions.report`? QWeb templates con `t-call="web.html_container"`? |
| `tests` | hay `tests/__init__.py`? qué framework se usa (`TransactionCase`, `HttpCase`, `SavepointCase`)? |
| `i18n` | hay `.pot`? `.po`? |
| `account` | en `depends` o modelos heredan de `account.move`/`account.payment`? |
| `stock` | en `depends` o referencias a `stock.move`/`stock.picking`? |
| `hr` | en `depends` o referencias a `hr.employee`? |
| `sale` / `purchase` / `crm` / `project` | en `depends`? |
| `queue_job` / `base_automation` | disponibles para async / reglas automatizadas? |

Guardar la matrix como tabla. **No proponer nada cuyo prerequisito dependa de capacidades marcadas ❌ sin absorberlas explícitamente en el candidato** (ver Fase 4).

### Fase 3 — Generación de candidatos

Generar 3-10 candidatos brutos por categoría. Acá se puede ser exploratorio — el filtro viene en Fase 4. Apuntar a cobertura amplia y pensar como product owner, no como AI genérica.

#### Nuevas funcionalidades de negocio
- **Workflows extendidos**: estados que "suenan" faltantes (ej: modelo de órdenes sin `cancelled` explícito, sin `approved`). Considerar qué estados existen hoy y qué transiciones faltan.
- **Aprobaciones**: si hay transiciones críticas (ej: `draft → confirmed`) sin validación humana, proponer flujo de aprobación con grupo dedicado.
- **Notificaciones**: si el modelo hereda `mail.thread` pero no emite notificaciones en cambios importantes (ej: state transition), proponer `mail.template` + `message_post`.
- **Exposición portal**: si hay records que el cliente final podría beneficiarse de ver, proponer vista portal. **Solo si `portal` ya está en depends o el candidato incluye agregarlo + todo lo necesario.**
- **Reports faltantes**: si el módulo genera records relevantes y no hay PDF/report, proponer QWeb.
- **Integraciones cross-módulo**: si el módulo toca `sale` pero no genera línea de factura en `account`, proponer integración.

#### Mejoras técnicas / refactor
- **N+1**: loops con `.browse()` adentro, `filtered()` sobre recordsets enormes, accesos repetidos a related fields.
- **`@api.model_create_multi`**: si la versión es 13+ y el `create()` no está decorado así, proponer migrar.
- **Legacy**: `@api.multi` (removido en 14+), `_defaults` dict, imports de `openerp`.
- **Índices**: campos buscados frecuentemente sin `index=True`.
- **Compute store**: computes pesados con `store=False` que se usan en list views o búsquedas.
- **`sudo()` sin justificar**: reemplazar por permisos explícitos.

#### UX / usabilidad
- **Smart buttons**: en form view del modelo A, botón que abra records relacionados en modelo B. Aplicable cuando hay `One2many` o relación inversa frecuente.
- **Filtros/group-by**: en search view, agregar filtros pre-armados para estados/fechas/responsables.
- **Wizards**: operaciones repetitivas manuales que se podrían bulk-procesar.
- **Stat buttons**: contadores en form view (ej: "3 órdenes asociadas").
- **Kanban view**: si el modelo tiene estados, kanban por estado puede mejorar visualización.
- **Tooltips/helps**: campos críticos sin `help` text.

#### Seguridad y permisos
- **Record rules multi-company**: modelos con `company_id` sin `ir.rule` que filtre.
- **Grupos más granulares**: un solo grupo para lectura y escritura cuando tendría sentido separarlos (ej: user vs. manager).
- **ACL faltantes**: modelos nuevos sin entrada en `ir.model.access.csv`.
- **`sudo()` auditable**: documentar cada uso o reemplazar por grupo dedicado.

### Fase 4 — Validación de viabilidad (corazón de la skill)

Para cada candidato generado en Fase 3, correr el **Viability Trace**. Si algún check falla y no es absorbible dentro del scope del propio candidato → **descartar** (aparece en sección "descartadas" del informe con razón explícita).

#### 4.1 Prerequisitos técnicos
- [ ] ¿Las `depends` necesarias ya están? Si no, ¿agregarlas es seguro (no crea ciclos, no trae módulos pesados o licencias incompatibles)?
- [ ] ¿Los modelos referenciados existen (como `_name` local o en dependencias declaradas)?
- [ ] ¿Los campos referenciados existen o se crean en el candidato?
- [ ] ¿Los grupos referenciados existen o se crean en el candidato?
- [ ] ¿Las vistas/acciones/templates referenciados existen o se crean?

#### 4.2 Flujo end-to-end (el trace)

Documentar explícitamente cada etapa del happy path. **Este es el check más importante** — el que evita el caso del "quiz portal sin portal".

- **Trigger**: ¿quién o qué lo dispara?
  - Usuario interno con grupo X (¿el grupo existe?)
  - Cron (¿se crea el `ir.cron`? ¿con qué frecuencia? ¿idempotente?)
  - Webhook / controller público (¿con qué auth? ¿rate-limit?)
  - Portal user (¿hay flujo de alta? ¿el modelo hereda `portal.mixin`? si no → absorber o descartar)
  - Automated action (¿`base.automation` está disponible?)

- **Acceso**: ¿el trigger tiene los permisos necesarios?
  - `ir.model.access.csv` cubre el modelo para el grupo correcto.
  - `ir.rule` no bloquea (ni permite de más).
  - Si es portal: `ir.rule` específico que limita a records "propios" del user portal.

- **Datos de soporte**: ¿todo lo que consume el flujo existe?
  - `mail.template` para notificaciones → si no existe, se crea en el candidato.
  - `ir.sequence` para numeración → si no existe, se crea.
  - `ir.cron` para procesamiento diferido → se crea.
  - Parámetros de sistema (`ir.config_parameter`) → se crean o se documentan.

- **Procesamiento**: lógica de negocio concreta.
  - Métodos a agregar/modificar (nombres específicos).
  - Transiciones de estado (¿cuáles? ¿qué dispara cada una?).
  - Computes/constrains nuevos.

- **Salida / delivery**: cada output debe tener su "delivery point" verificado.
  - **Notificación**: `mail.template` + `message_post` + destinatarios resueltos (¿tienen email?).
  - **Vista**: menú + acción + form view (¿está en el menú correcto? ¿el grupo lo ve?).
  - **Reporte**: action + template + botón en la vista de origen.
  - **Página portal**: route + controller + template + link desde `/my`.
  - **Signal externo**: webhook POST + manejo de error + retry.

- **Reversibilidad**: ¿se puede deshacer/corregir si algo sale mal?
  - Transición de estado con botón "cancel" o reset.
  - Record creado con flag que permita unlink o archive.
  - Notificación enviada — ¿se registra en `mail.message` para tener trazabilidad?

**Ejemplo aplicado al caso del usuario (quiz por portal para operarios)**:

| Etapa | Check | Resultado |
|---|---|---|
| Trigger | Asignación a operario con user portal | ❌ No hay flujo de alta de portal user para operarios |
| Acceso | `ir.rule` que limite quiz a su propio operario | ❌ No existe |
| Datos | `mail.template` para aviso | ❌ No existe |
| Salida | Página `/my/quiz/<id>` + controller + template | ❌ No existe |

Gap: 4 sub-features mayores. **Veredicto: descartar**. Razón: el candidato no es una mejora, es un proyecto. Sugerencia: abrir spec de feature separado; luego re-evaluar con esta skill sobre la base ya configurada.

**Regla de corte**: si el gap total para cerrar el flujo requiere **3+ sub-features mayores** (alta de users, crear infraestructura de portal, controllers nuevos, etc.), el candidato se descarta. Si el gap es 1-2 piezas chicas (crear un `mail.template`, agregar un grupo), se absorbe en el candidato.

#### 4.3 Colisiones con lógica existente

- **Compute fields**: ¿el nuevo compute/campo pisa uno existente? ¿agrega `depends` que crean ciclos con otros computes?
- **Onchange / constrains**: ¿el nuevo `@api.constrains` rechaza registros que YA existen en DB? (si sí, requiere data migration — documentar).
- **Required fields**: ¿agregar `required=True` rompe records existentes, wizards, imports, o flujos que no los setean? Chequear si hay registros demo o de seed afectados.
- **State machines**: si se agrega un estado nuevo en una `Selection`:
  - ¿TODOS los botones existentes manejan el nuevo estado (o explícitamente lo ignoran)?
  - ¿Las vistas (filtros, kanban columns) lo muestran?
  - ¿Los métodos con `if state == ...` cubren el nuevo caso?
- **Security**: ¿la nueva feature da acceso a datos que otra lógica asume restringidos? ¿rompe una `ir.rule` existente?
- **Views**: ¿el nuevo campo agregado a una vista hereda-able rompe vistas que otros módulos heredan? (grep `inherit_id` apuntando a vistas que vas a modificar).
- **Performance**: ¿introduce N+1? ¿cron nuevo corre sobre tabla grande sin `limit` o paginación?
- **Idempotencia**: ¿la acción se puede disparar dos veces sin efectos duplicados? (crítico en crons, botones, webhooks).

#### 4.4 Compatibilidad de versión Odoo

- ¿Usa APIs que no existen en la versión declarada?
  - `@api.model_create_multi` → Odoo 13+
  - `portal.mixin` → Odoo 12+
  - Owl components → Odoo 14+, Owl 2.0 → Odoo 16+
  - `<list>` tag → Odoo 18 (aunque `<tree>` sigue funcionando)
- ¿Widgets JS son válidos para la versión? (muchos cambios entre 16 y 17).
- ¿Patrones XML son válidos? (`<setting>` de `res.config.settings` solo en 17+).

**Si un candidato falla cualquier check de 4.1–4.4 y el fix excede un ajuste menor → se descarta.**

### Fase 5 — Diseño de test automatizado

Para cada candidato que sobrevive la validación, diseñar al menos un test que pruebe el happy path completo. **Si no se puede escribir un test plausible, la propuesta no es lo suficientemente concreta — descartar o refinar.**

- **`TransactionCase`**: lógica ORM (create, write, compute, constrains, state transitions).
- **`HttpCase`**: portal/website flows, controllers, rutas.
- **`SavepointCase`** (< 15) o `TransactionCase` (15+): el default razonable.

Estructura mínima del test:

```python
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import AccessError, ValidationError


@tagged('post_install', '-at_install')
class TestPNN(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Crear users con grupos correctos
        cls.user_manager = cls.env['res.users'].create({...})
        cls.user_basic = cls.env['res.users'].create({...})
        # Crear records padre mínimos
        cls.record = cls.env['modelo'].create({...})

    def test_happy_path(self):
        # Act: disparar el flujo como el user correcto
        self.record.with_user(self.user_manager).action_xxx()
        # Assert: estado final esperado
        self.assertEqual(self.record.state, 'expected')
        # Assert: side-effects (mail.message creado, campo actualizado, etc.)
        self.assertTrue(self.record.message_ids.filtered(...))

    def test_access_denied_without_group(self):
        with self.assertRaises(AccessError):
            self.record.with_user(self.user_basic).action_xxx()

    def test_invalid_transition(self):
        # Estado incorrecto de origen
        self.record.state = 'done'
        with self.assertRaises(ValidationError):
            self.record.action_xxx()
```

Incluir en el informe el test completo o un esqueleto que el fix va a poder ejecutar sin inventar.

### Fase 6 — Ranking y priorización

Por cada candidato validado:

- **Impacto**: Alto / Medio / Bajo (valor para usuario/negocio).
- **Esfuerzo**: S / M / L (archivos tocados, líneas, complejidad técnica).
- **Riesgo**: Bajo / Medio / Alto (colisión con lógica, cambios de esquema, alcance).
- **Score**: función simple. Mapear A/M/B → +2/+1/0 para impacto. Penalizar esfuerzo (S=0, M=-1, L=-2) y riesgo (Bajo=0, Medio=-1, Alto=-2). Score final = impacto + esfuerzo + riesgo.

Ordenar por score descendente. Los 🔴 de seguridad siempre ocupan los primeros puestos aunque el score sea menor (son no-opcionales).

### Fase 7 — Informe `ENHANCEMENT_REPORT.md`

**Persistencia en disco (obligatorio)**: además de mostrar el informe en chat, guardá una copia en:

- `<modulo>/.enhance/ENHANCEMENT_REPORT.md` — siempre la última corrida (se sobreescribe).
- `<modulo>/.enhance/history/ENHANCEMENT_REPORT_<YYYY-MM-DD>.md` — histórico inmutable.

Esto es **crítico** para que el skill `enhance-odoo-fix` pueda leer el informe en un chat posterior y generar el plan.

Si la carpeta `.enhance/` no existe, creala. Sugerir al usuario agregar `.enhance/` al `.gitignore` del módulo si no quiere comitear los informes. Dejar la decisión al usuario.

Estructura del informe:

```markdown
# Análisis de mejoras: <nombre_modulo> v<version>

**Odoo:** <version_odoo>
**Ruta:** <ruta>
**Archivos:** X Python, Y XML, Z CSV
**Fecha:** <hoy>
**Base de audit:** <si existía AUDIT_REPORT.md: "sí, auditoría del <fecha>"; si no: "no corrido — recomendado antes de aplicar mejoras">

## Perfil del módulo

<3-5 líneas describiendo qué hace el módulo, modelos clave, flujos principales, actores.>

## Capability matrix

| Capacidad | Estado | Notas |
|---|---|---|
| mail.thread | ✅ | Heredado en modelo.X |
| portal | ❌ | No instalado, módulo no extiende portal.mixin |
| multi-company | ✅ | company_id + ir.rule presentes |
| tests | 🟡 | Existe `tests/`, solo 2 tests básicos |
| i18n | ❌ | No hay `.pot` |
| ... | | |

## Resumen

| Categoría | Candidatos brutos | Validados | Descartados |
|---|---|---|---|
| Negocio | 6 | 2 | 4 |
| Técnico | 4 | 3 | 1 |
| UX | 5 | 4 | 1 |
| Seguridad | 2 | 2 | 0 |
| **Total** | **17** | **11** | **6** |

## Propuestas validadas

### P01 — <título corto> [Negocio | Impacto: Alto | Esfuerzo: M | Riesgo: Bajo | Score: +1]

**Problema que resuelve:** <1 línea>

**Flujo end-to-end:**
- **Trigger:** usuario del grupo X hace click en botón "Confirmar" en form de modelo.Y
- **Acceso:** grupo X ya existe (modulo.group_y_manager). Se agrega `ir.model.access.csv` para el nuevo modelo.Z.
- **Datos de soporte:** se crea `mail.template` `modulo.email_template_confirmation`. Se crea `ir.sequence` `modulo.seq_confirmation`.
- **Procesamiento:** método `action_confirm()` valida estado origen, genera número, cambia state, dispara notificación.
- **Salida:** `message_post` con template al partner_id del record + creación de actividad tipo "follow-up" al responsable.
- **Reversibilidad:** botón `action_cancel()` permite volver a `draft` si state aún es `confirmed`.

**Prerequisitos y creación:**
- `depends`: no cambia (todo lo necesario ya está: `mail`).
- Grupos: reusa `modulo.group_y_manager`.
- Templates: se crea `email_template_confirmation` (nuevo en `data/mail_templates.xml`).
- Secuencia: se crea `seq_confirmation` (nuevo en `data/sequences.xml`).

**Archivos a crear/modificar:**
- `models/order.py` (+ método `action_confirm`, + método `action_cancel`)
- `views/order_views.xml` (+ botones en header form)
- `data/mail_templates.xml` (nuevo)
- `data/sequences.xml` (nuevo)
- `__manifest__.py` (+ los 2 data files en clave `data`, en posición correcta)
- `tests/test_order_confirmation.py` (nuevo)

**Colisiones verificadas:**
- ✅ No pisa compute `amount_total` existente.
- ✅ No afecta constrain `_check_amount` (se dispara antes de la transición).
- ✅ State `confirmed` no existe actualmente — se agrega a la Selection sin romper transiciones existentes (solo `draft` y `done` hoy; nuevo flujo: `draft → confirmed → done`, con `done` preservado).
- ✅ Botones existentes no entran en conflicto (solo hay "Marcar como hecho" que ahora va en `confirmed → done`).
- ✅ Vistas heredadas por otros módulos: ninguna conocida inherita este form.

**Test propuesto:**
```python
@tagged('post_install', '-at_install')
class TestOrderConfirmation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = cls.env['res.users'].create({
            'name': 'Test Manager',
            'login': 'test_mgr',
            'groups_id': [(6, 0, [cls.env.ref('modulo.group_y_manager').id])],
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente', 'email': 'c@x.com'})
        cls.order = cls.env['modulo.order'].create({
            'partner_id': cls.partner.id,
            'amount': 100.0,
        })

    def test_confirm_happy_path(self):
        self.order.with_user(self.manager).action_confirm()
        self.assertEqual(self.order.state, 'confirmed')
        self.assertTrue(self.order.sequence_number)
        # Notificación emitida
        mails = self.order.message_ids.filtered(lambda m: 'Confirmed' in (m.subject or ''))
        self.assertTrue(mails)

    def test_cannot_confirm_from_done(self):
        self.order.state = 'done'
        with self.assertRaises(ValidationError):
            self.order.action_confirm()

    def test_access_denied_basic_user(self):
        basic = self.env['res.users'].create({'name': 'Basic', 'login': 'basic'})
        with self.assertRaises(AccessError):
            self.order.with_user(basic).action_confirm()
```

**Acceptance:** los 3 tests pasan. Revisión manual: crear una order, confirmar, verificar que llega el email al partner.

### P02 — ...

## Propuestas descartadas (con razón)

### D01 — Quiz portal para operarios

**Motivo:** el módulo no tiene portal instalado (`portal` no está en `depends`, ningún modelo hereda `portal.mixin`, no hay controller portal, no hay template portal, no hay flujo de alta de usuario portal para operarios). Cubrir el gap requiere 4 sub-features mayores: (1) alta de user portal para operario, (2) herencia `portal.mixin` en el modelo de operario, (3) controller + ruta `/my/quiz`, (4) template portal.

**Veredicto:** no es una mejora — es un proyecto.

**Sugerencia:** si realmente se quiere avanzar, abrir un spec separado para "habilitar portal para operarios", implementarlo como feature aparte, y luego re-correr esta skill para que proponga el quiz sobre base ya configurada.

### D02 — ...

## Ranking

| ID | Categoría | Título | Impacto | Esfuerzo | Riesgo | Score |
|----|-----------|--------|---------|----------|--------|-------|
| P01 | Negocio | Confirmación con notificación | Alto | M | Bajo | +1 |
| P02 | Seguridad | Record rule multi-company | Alto | S | Bajo | +2 |
| P03 | UX | Smart button órdenes relacionadas | Medio | S | Bajo | +1 |
| ... |

## Próximos pasos

Invocá `/enhance-odoo-fix <ruta>` (chat nuevo) para generar el plan de implementación en oleadas. El fix va a pedirte aprobación del plan antes de ejecutar, y va a ir tarea por tarea con un chat fresco por cada una.

**Recomendado**: si `.audit/AUDIT_REPORT.md` tiene issues 🔴 o 🟠 sin resolver, corré `/audit-odoo-fix` primero — implementar mejoras sobre código con bugs críticos es riesgoso.
```

## Criterios de decisión finales

- **Si < 3 candidatos sobreviven validación** → el módulo está en buen estado estructural o el scope es limitado. Avisar al usuario y sugerir expandir contexto (ej: "¿hay módulos relacionados que debería considerar para proponer integraciones?").
- **Si > 15 candidatos sobreviven** → limitar el reporte principal a los top 10 por score. El resto va en apéndice "Oportunidades adicionales" al final del informe, para no abrumar.
- **Si el módulo es muy grande (>30 archivos Python)** → paralelizar Fase 1 y Fase 3 con sub-agentes Explore (uno por bloque lógico: `models/`, `views/`, `controllers/`, etc.).
- **Si `AUDIT_REPORT.md` tiene 🔴 críticos sin resolver** → agregar al inicio del informe un bloque 🚨 **"Resolver primero"** con referencia a esos findings. No proponer enhancements que toquen código con bugs críticos activos.

## Notas finales

- **Descartar con razón es mejor que proponer aspiracional**. Cada descarte es información útil — el usuario entiende qué le falta al módulo para habilitar ciertos flujos.
- **Si dudás entre descartar o absorber** — preferir descartar y anotar sugerencia de spec separado. Mejor una skill que propone 5 cosas que funcionan que una que propone 15 cosas de las cuales 10 no cierran.
- **No re-descubras lo que audit ya encontró**. Si un finding 🔴 de `AUDIT_REPORT.md` dice "falta `ir.model.access.csv`", no generes un candidato de seguridad duplicado — referenciá el audit.
- **Tests son parte de la propuesta, no opcionales**. Una propuesta sin test diseñado → sospechar que no es concreta.
- **El flujo end-to-end se documenta SIEMPRE explícitamente**. La tentación de escribir "el usuario recibe notificación" sin detallar `mail.template` + destinatario + template existente vs. nuevo es exactamente el modo de fallo que esta skill previene.
