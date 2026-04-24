#!/usr/bin/env python3
"""
scan_deadcode.py — Análisis estático de un módulo Odoo para detectar:
  - Referencias rotas (button/field/action apuntando a algo inexistente)
  - Métodos huérfanos (sin caller estático)
  - Computes/onchange/constrains sin binding válido
  - Campos declarados pero no usados
  - Modelos aislados (sin ACL / sin vista / sin menú)
  - XML IDs huérfanos
  - Selection values sin uso

Cruza contra todos los addons en addons_path (Python + XML + CSV) para
capturar referencias cross-module.

Uso:
    python scan_deadcode.py <ruta_modulo> [--addons-path p1:p2:p3] [--output json|pretty]

Salida: DEADCODE_SCAN.json en <modulo>/.deadcode/
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

# ---------- Modelo de datos ----------


@dataclass
class MethodDecl:
    model: str
    name: str
    file: str
    line: int
    is_private: bool
    decorators: list[str] = field(default_factory=list)
    bound_by_decorator: list[str] = field(default_factory=list)  # fields mentioned in @api.onchange/depends/constrains


@dataclass
class FieldDecl:
    model: str
    name: str
    ftype: str
    file: str
    line: int
    compute: str | None = None
    inverse: str | None = None
    search: str | None = None
    related: str | None = None
    default_method: str | None = None
    selection_values: list[str] | None = None


@dataclass
class ModelDecl:
    name: str
    inherit: list[str]
    inherits_dict: list[str]
    file: str
    line: int
    module: str


@dataclass
class XmlRef:
    kind: str  # 'button' | 'field' | 'menuitem_action' | 'action_res_model' | 'view_model' | 'rule_model' | 'attr_expr'
    target: str  # method name / field name / model name
    model_hint: str | None  # model on which this ref is expected
    file: str
    line: int
    extra: str = ""


@dataclass
class XmlId:
    xmlid: str  # module.id or just id within-file
    model: str | None
    file: str
    line: int


@dataclass
class AccessEntry:
    model_xmlid: str
    group_xmlid: str
    file: str
    line: int


@dataclass
class Finding:
    id: str
    severity: str  # 'red' | 'yellow' | 'blue'
    category: str
    module: str
    file: str
    line: int
    title: str
    description: str
    evidence: str = ""
    suggested_action: str = "human_review"  # 'delete' | 'wire' | 'fix_reference' | 'human_review'
    fix_options: list[str] = field(default_factory=list)
    caveat: str = ""


# ---------- Utilidades ----------


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        try:
            return path.read_text(encoding="latin-1")
        except Exception:
            return ""


def find_line(haystack: str, needle: str) -> int:
    idx = haystack.find(needle)
    if idx == -1:
        return 0
    return haystack.count("\n", 0, idx) + 1


def is_odoo_module_dir(p: Path) -> bool:
    return p.is_dir() and (p / "__manifest__.py").exists() and (p / "__init__.py").exists()


def list_modules(addons_paths: list[Path]) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for root in addons_paths:
        if not root.exists():
            continue
        for child in root.iterdir():
            if is_odoo_module_dir(child) and child.name not in out:
                out[child.name] = child
    return out


def resolve_addons_paths_from_conf(odoo_conf: Path, repo_root: Path) -> list[Path]:
    """Lee odoo_conf y traduce paths de contenedor (/sources/...) a host (<repo>/addons/...)."""
    if not odoo_conf.exists():
        return []
    txt = read_text(odoo_conf)
    m = re.search(r"^\s*addons_path\s*=\s*(.+)$", txt, re.MULTILINE)
    if not m:
        return []
    raw = m.group(1).strip().rstrip(",")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    resolved: list[Path] = []
    host_addons = repo_root / "addons"
    for p in parts:
        candidate = Path(p)
        if p.startswith("/sources"):
            candidate = host_addons / p[len("/sources/"):]
        elif not candidate.is_absolute():
            candidate = (repo_root / p).resolve()
        resolved.append(candidate)
    return resolved


# ---------- Python AST walker ----------

ODOO_MODEL_BASES = {"Model", "TransientModel", "AbstractModel"}

# Campos heredados de mixins/base de Odoo core que no estamos escaneando (están en odoo-sources, no en addons_path).
# Cuando el modelo declara `_inherit = 'mail.thread'` (o similar) estos campos se vuelven válidos en vistas.
CORE_MIXIN_FIELDS: dict[str, set[str]] = {
    "mail.thread": {
        "message_ids", "message_follower_ids", "message_partner_ids", "message_is_follower",
        "message_unread", "message_unread_counter", "message_needaction", "message_needaction_counter",
        "message_has_error", "message_has_error_counter", "message_attachment_count",
        "message_main_attachment_id", "website_message_ids", "has_message",
    },
    "mail.activity.mixin": {
        "activity_ids", "activity_state", "activity_user_id", "activity_type_id",
        "activity_type_icon", "activity_date_deadline", "my_activity_date_deadline",
        "activity_summary", "activity_exception_decoration", "activity_exception_icon",
        "activity_calendar_event_id",
    },
    "portal.mixin": {
        "access_url", "access_token", "access_warning",
    },
    "image.mixin": {
        "image_1920", "image_1024", "image_512", "image_256", "image_128",
    },
    "mail.alias.mixin": {
        "alias_id", "alias_name", "alias_defaults", "alias_force_thread_id",
        "alias_domain", "alias_parent_model_id", "alias_parent_thread_id", "alias_contact",
    },
    "base": {
        # Campos ORM magic presentes en TODO modelo
        "id", "display_name", "create_date", "create_uid", "write_date", "write_uid",
        "__last_update", "company_id",
    },
    "website.published.mixin": {
        "website_published", "website_url", "can_publish",
    },
}

# Flatten: si no sabemos exactamente qué mixin usa un modelo, aceptamos cualquiera de estos nombres.
CORE_MIXIN_FIELDS_FLAT: set[str] = set().union(*CORE_MIXIN_FIELDS.values())

ODOO_FIELD_CLASSES = {
    "Char", "Text", "Html", "Boolean", "Integer", "Float", "Monetary",
    "Date", "Datetime", "Binary", "Image", "Selection",
    "Many2one", "One2many", "Many2many", "Reference",
    "Json", "Properties",
}


def _literal_value(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_selection_values(call: ast.Call) -> list[str] | None:
    # fields.Selection([('a', 'A'), ('b', 'B')], ...)
    if not call.args:
        return None
    first = call.args[0]
    if isinstance(first, (ast.List, ast.Tuple)):
        out: list[str] = []
        for item in first.elts:
            if isinstance(item, (ast.Tuple, ast.List)) and item.elts:
                v = _literal_value(item.elts[0])
                if v is not None:
                    out.append(v)
        return out
    return None


def _field_class_from_call(call: ast.Call) -> str | None:
    func = call.func
    # fields.Char(...)
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "fields":
        if func.attr in ODOO_FIELD_CLASSES:
            return func.attr
    # Char(...) bare (raro)
    if isinstance(func, ast.Name) and func.id in ODOO_FIELD_CLASSES:
        return func.id
    return None


def _method_calls_in_body(body: list[ast.stmt]) -> set[str]:
    """Retorna nombres de métodos llamados via self.x() o self._x() dentro del body."""
    called: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            func = node.func
            # self.foo(...)
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "self":
                called.add(func.attr)
            # self.env['x'].foo(...) → foo cuenta como llamada (aunque a otro modelo, la contamos para reducir falsos positivos)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)
            # getattr(self, 'foo')(...)
            elif isinstance(func, ast.Name) and func.id == "getattr":
                pass
            self.generic_visit(node)

        def visit_Attribute(self, node: ast.Attribute):
            # self.foo (como referencia, no call) — la ignoramos para no contar lecturas de atributos como llamadas
            self.generic_visit(node)

    for stmt in body:
        Visitor().visit(stmt)
    return called


def _getattr_strings_in_body(body: list[ast.stmt]) -> set[str]:
    """Detecta getattr(self, 'method_name') para marcar dispatch dinámico."""
    out: set[str] = set()

    class V(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "getattr" and len(node.args) >= 2:
                s = _literal_value(node.args[1])
                if s:
                    out.add(s)
            self.generic_visit(node)

    for s in body:
        V().visit(s)
    return out


def _decorator_info(dec: ast.expr) -> tuple[str, list[str]]:
    """Retorna ('api.onchange', ['field_a', 'field_b']) para @api.onchange('field_a', 'field_b')."""
    name = ""
    args: list[str] = []
    call = dec
    target = None
    if isinstance(dec, ast.Call):
        target = dec.func
        for a in dec.args:
            v = _literal_value(a)
            if v is not None:
                args.append(v)
    else:
        target = dec
    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
        name = f"{target.value.id}.{target.attr}"
    elif isinstance(target, ast.Name):
        name = target.id
    return name, args


def scan_python_file(path: Path, module_name: str) -> tuple[list[ModelDecl], list[MethodDecl], list[FieldDecl], dict[str, set[str]], dict[str, set[str]]]:
    """Devuelve models, methods, fields, intra_calls_by_model, dynamic_dispatch_by_model."""
    src = read_text(path)
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return [], [], [], {}, {}

    models: list[ModelDecl] = []
    methods: list[MethodDecl] = []
    fields_out: list[FieldDecl] = []
    intra_calls: dict[str, set[str]] = {}
    dynamic_dispatch: dict[str, set[str]] = {}

    for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        # ¿Es un modelo Odoo?
        is_model = False
        for base in cls.bases:
            if isinstance(base, ast.Attribute) and base.attr in ODOO_MODEL_BASES:
                is_model = True
                break
            if isinstance(base, ast.Name) and base.id in ODOO_MODEL_BASES:
                is_model = True
                break
        if not is_model:
            continue

        _name: str | None = None
        _inherit: list[str] = []
        _inherits: list[str] = []
        for stmt in cls.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                tgt = stmt.targets[0].id
                if tgt == "_name":
                    v = _literal_value(stmt.value)
                    if v:
                        _name = v
                elif tgt == "_inherit":
                    v = _literal_value(stmt.value)
                    if v:
                        _inherit = [v]
                    elif isinstance(stmt.value, (ast.List, ast.Tuple)):
                        _inherit = [c for c in (_literal_value(e) for e in stmt.value.elts) if c]
                elif tgt == "_inherits":
                    if isinstance(stmt.value, ast.Dict):
                        _inherits = [k for k in (_literal_value(e) for e in stmt.value.keys) if k]

        model_name = _name or (_inherit[0] if _inherit else None)
        if not model_name:
            continue

        models.append(ModelDecl(
            name=model_name,
            inherit=_inherit,
            inherits_dict=_inherits,
            file=str(path),
            line=cls.lineno,
            module=module_name,
        ))

        method_body_map: dict[str, list[ast.stmt]] = {}
        for stmt in cls.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decorators: list[str] = []
                bound_fields: list[str] = []
                for dec in stmt.decorator_list:
                    dname, dargs = _decorator_info(dec)
                    decorators.append(dname)
                    if dname in {"api.onchange", "api.depends", "api.constrains"}:
                        bound_fields.extend(dargs)
                methods.append(MethodDecl(
                    model=model_name,
                    name=stmt.name,
                    file=str(path),
                    line=stmt.lineno,
                    is_private=stmt.name.startswith("_"),
                    decorators=decorators,
                    bound_by_decorator=bound_fields,
                ))
                method_body_map[stmt.name] = stmt.body
            elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                tgt_name = stmt.targets[0].id
                if not isinstance(stmt.value, ast.Call):
                    continue
                fclass = _field_class_from_call(stmt.value)
                if not fclass:
                    continue
                compute = inverse = search = related = default_method = None
                for kw in stmt.value.keywords:
                    if kw.arg == "compute":
                        compute = _literal_value(kw.value)
                    elif kw.arg == "inverse":
                        inverse = _literal_value(kw.value)
                    elif kw.arg == "search":
                        search = _literal_value(kw.value)
                    elif kw.arg == "related":
                        related = _literal_value(kw.value)
                    elif kw.arg == "default":
                        if isinstance(kw.value, ast.Name):
                            default_method = kw.value.id
                        elif isinstance(kw.value, ast.Attribute) and isinstance(kw.value.value, ast.Name) and kw.value.value.id == "self":
                            default_method = kw.value.attr
                sel_vals = _extract_selection_values(stmt.value) if fclass == "Selection" else None
                fields_out.append(FieldDecl(
                    model=model_name,
                    name=tgt_name,
                    ftype=fclass,
                    file=str(path),
                    line=stmt.lineno,
                    compute=compute,
                    inverse=inverse,
                    search=search,
                    related=related,
                    default_method=default_method,
                    selection_values=sel_vals,
                ))

        intra: set[str] = set()
        dyn: set[str] = set()
        for mname, mbody in method_body_map.items():
            intra |= _method_calls_in_body(mbody)
            dyn |= _getattr_strings_in_body(mbody)
        intra_calls.setdefault(model_name, set()).update(intra)
        dynamic_dispatch.setdefault(model_name, set()).update(dyn)

    return models, methods, fields_out, intra_calls, dynamic_dispatch


# ---------- XML walker ----------

# En expresiones XML como invisible="state in ('draft',)" identificamos tokens de campos.
_TOKEN_RE = re.compile(r"\b([a-z_][a-z0-9_]*)\b", re.IGNORECASE)


def _iter_xml(path: Path):
    try:
        tree = ET.parse(str(path))
    except ET.ParseError:
        return None, None
    except Exception:
        return None, None
    return tree, tree.getroot()


def _line_of_element(src_text: str, elem_repr: str) -> int:
    return find_line(src_text, elem_repr) or 0


def scan_xml_file(path: Path, module_name: str) -> tuple[list[XmlRef], list[XmlId], list[tuple[str, str, str]]]:
    """
    Retorna:
      - refs: XmlRef (buttons, field references, menuitem actions, etc.)
      - xmlids: XmlId declarados en el archivo (records con id=)
      - model_view_bindings: lista (view_xmlid, model_name, view_file) para poder saber qué modelo toca cada vista
    """
    refs: list[XmlRef] = []
    xmlids: list[XmlId] = []
    view_bindings: list[tuple[str, str, str]] = []

    tree, root = _iter_xml(path)
    if root is None:
        return refs, xmlids, view_bindings
    src = read_text(path)

    # Para cada <record id=...> averiguar su modelo y, si es ir.ui.view, qué modelo "view" renderiza.
    for rec in root.iter("record"):
        rid = rec.get("id")
        rmodel = rec.get("model")
        lineno = 0
        if rid:
            lineno = find_line(src, f'id="{rid}"') or find_line(src, f"id='{rid}'") or 0
            xmlids.append(XmlId(xmlid=rid, model=rmodel, file=str(path), line=lineno))
        # ir.ui.view → field name="model"
        if rmodel == "ir.ui.view":
            model_field = None
            arch_el = None
            for fld in rec.findall("field"):
                fname = fld.get("name")
                if fname == "model":
                    model_field = (fld.text or "").strip()
                elif fname == "arch":
                    arch_el = fld
            if rid and model_field:
                view_bindings.append((rid, model_field, str(path)))
            # recorrer arch en busca de buttons / fields / attrs
            if arch_el is not None:
                _scan_arch(arch_el, model_field or "", path, src, refs)
        # ir.actions.act_window / client → res_model
        if rmodel in {"ir.actions.act_window", "ir.actions.client", "ir.actions.server"}:
            for fld in rec.findall("field"):
                if fld.get("name") == "res_model":
                    m = (fld.text or "").strip()
                    if m:
                        refs.append(XmlRef(
                            kind="action_res_model", target=m, model_hint=None,
                            file=str(path), line=lineno, extra=f"action {rid}",
                        ))
                if fld.get("name") == "binding_model_id":
                    ref_attr = fld.get("ref")
                    if ref_attr:
                        refs.append(XmlRef(
                            kind="binding_model_ref", target=ref_attr, model_hint=None,
                            file=str(path), line=lineno, extra=f"action {rid}",
                        ))
        # ir.rule → model_id ref
        if rmodel == "ir.rule":
            for fld in rec.findall("field"):
                if fld.get("name") == "model_id" and fld.get("ref"):
                    refs.append(XmlRef(
                        kind="rule_model", target=fld.get("ref"), model_hint=None,
                        file=str(path), line=lineno, extra=f"rule {rid}",
                    ))

    # <menuitem action="..."> y atributos xpath
    for menu in root.iter("menuitem"):
        act = menu.get("action")
        mid = menu.get("id")
        lineno = find_line(src, f'id="{mid}"') if mid else 0
        if act:
            refs.append(XmlRef(
                kind="menuitem_action", target=act, model_hint=None,
                file=str(path), line=lineno, extra=f"menu {mid or '?'}",
            ))

    # <template id=...> → xmlid declared
    for tmpl in root.iter("template"):
        tid = tmpl.get("id")
        if tid:
            line = find_line(src, f'id="{tid}"')
            xmlids.append(XmlId(xmlid=tid, model="ir.ui.view", file=str(path), line=line))

    return refs, xmlids, view_bindings


def _scan_arch(arch: ET.Element, model: str, path: Path, src: str, refs: list[XmlRef]) -> None:
    """Recorre el <field name='arch'> y registra refs a métodos/campos/atributos.
    Importante: saltar el elemento raíz (el propio <field name='arch'>) para no contarlo como field ref del modelo."""
    for el in arch.iter():
        if el is arch:
            continue
        tag = el.tag
        if tag == "button":
            btn_name = el.get("name")
            btn_type = el.get("type", "object")
            if btn_name and btn_type == "object":
                line = find_line(src, f'name="{btn_name}"')
                refs.append(XmlRef(
                    kind="button", target=btn_name, model_hint=model,
                    file=str(path), line=line, extra=f'type={btn_type}',
                ))
            elif btn_name and btn_type == "action":
                # action es xmlid, no método
                line = find_line(src, f'name="{btn_name}"')
                refs.append(XmlRef(
                    kind="button_action", target=btn_name, model_hint=None,
                    file=str(path), line=line, extra=f'type={btn_type}',
                ))
        elif tag == "field":
            fname = el.get("name")
            if fname:
                line = find_line(src, f'name="{fname}"')
                refs.append(XmlRef(
                    kind="field", target=fname, model_hint=model,
                    file=str(path), line=line,
                ))
        # Atributos con expresiones (invisible, readonly, required, domain, context, decoration-*)
        for attr_name in ("invisible", "readonly", "required", "domain", "context"):
            val = el.get(attr_name)
            if val:
                for token in _TOKEN_RE.findall(val):
                    # Filtrar keywords y literales obvios
                    if token in {"True", "False", "None", "and", "or", "not", "in", "is", "if", "else",
                                 "uid", "context_today", "current_date", "parent"}:
                        continue
                    refs.append(XmlRef(
                        kind="attr_expr_token", target=token, model_hint=model,
                        file=str(path), line=0, extra=f"{tag}@{attr_name}",
                    ))


# ---------- CSV walker ----------


def scan_ir_model_access(path: Path) -> list[AccessEntry]:
    entries: list[AccessEntry] = []
    if not path.exists():
        return entries
    try:
        with path.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for i, row in enumerate(reader, start=2):
                model_id = (row.get("model_id:id") or row.get("model_id/id") or "").strip()
                group_id = (row.get("group_id:id") or row.get("group_id/id") or "").strip()
                if model_id:
                    entries.append(AccessEntry(
                        model_xmlid=model_id, group_xmlid=group_id,
                        file=str(path), line=i,
                    ))
    except Exception:
        pass
    return entries


# ---------- Manifest ----------


def read_manifest(module_path: Path) -> dict:
    mp = module_path / "__manifest__.py"
    if not mp.exists():
        return {}
    try:
        return ast.literal_eval(read_text(mp))
    except Exception:
        return {}


# ---------- Scanner orchestration ----------


@dataclass
class ModuleIndex:
    module: str
    path: Path
    manifest: dict
    models: list[ModelDecl] = field(default_factory=list)
    methods: list[MethodDecl] = field(default_factory=list)
    fields: list[FieldDecl] = field(default_factory=list)
    intra_calls: dict[str, set[str]] = field(default_factory=dict)
    dynamic_dispatch: dict[str, set[str]] = field(default_factory=dict)
    xml_refs: list[XmlRef] = field(default_factory=list)
    xmlids: list[XmlId] = field(default_factory=list)
    view_bindings: list[tuple[str, str, str]] = field(default_factory=list)
    access_entries: list[AccessEntry] = field(default_factory=list)


def scan_module(module_path: Path, module_name: str) -> ModuleIndex:
    idx = ModuleIndex(module=module_name, path=module_path, manifest=read_manifest(module_path))
    for py in module_path.rglob("*.py"):
        if "/.git/" in str(py) or py.name == "__init__.py":
            continue
        if "/tests/" in str(py) or "/test/" in str(py):
            # Los tests cuentan como callers — los incluimos
            pass
        models, methods, fields_, intra, dyn = scan_python_file(py, module_name)
        idx.models.extend(models)
        idx.methods.extend(methods)
        idx.fields.extend(fields_)
        for k, v in intra.items():
            idx.intra_calls.setdefault(k, set()).update(v)
        for k, v in dyn.items():
            idx.dynamic_dispatch.setdefault(k, set()).update(v)
    for xml in module_path.rglob("*.xml"):
        if "/.git/" in str(xml):
            continue
        refs, xids, vbinds = scan_xml_file(xml, module_name)
        idx.xml_refs.extend(refs)
        idx.xmlids.extend(xids)
        idx.view_bindings.extend(vbinds)
    ira = module_path / "security" / "ir.model.access.csv"
    idx.access_entries.extend(scan_ir_model_access(ira))
    return idx


# ---------- Finding generation ----------


class FindingAggregator:
    def __init__(self) -> None:
        self.items: list[Finding] = []
        self._counter = 0

    def add(self, **kwargs) -> Finding:
        self._counter += 1
        fid = f"D{self._counter:02d}"
        f = Finding(id=fid, **kwargs)
        self.items.append(f)
        return f


def compute_findings(
    target: ModuleIndex,
    all_indexes: dict[str, ModuleIndex],
) -> list[Finding]:
    """
    Cruza información del módulo target contra todos los módulos indexados para
    producir findings de código muerto/referencias rotas.
    """
    agg = FindingAggregator()
    module = target.module

    # Índices agregados
    all_methods_by_model: dict[str, set[str]] = {}
    all_fields_by_model: dict[str, set[str]] = {}
    all_models: set[str] = set()
    all_xmlids: set[str] = set()
    all_methods_anywhere: set[str] = set()  # nombre de método en cualquier modelo (para heurística de dispatch dinámico)
    all_button_targets: set[str] = set()
    all_field_refs: set[tuple[str, str]] = set()  # (model_hint, field_name)
    all_intra_calls: set[str] = set()  # método llamado desde cualquier Python
    all_dynamic_dispatch_strings: set[str] = set()

    for idx in all_indexes.values():
        for m in idx.models:
            all_models.add(m.name)
            for inh in m.inherit:
                all_models.add(inh)
            for inh in m.inherits_dict:
                all_models.add(inh)
        for me in idx.methods:
            all_methods_by_model.setdefault(me.model, set()).add(me.name)
            all_methods_anywhere.add(me.name)
        for fd in idx.fields:
            all_fields_by_model.setdefault(fd.model, set()).add(fd.name)
        for x in idx.xmlids:
            all_xmlids.add(f"{idx.module}.{x.xmlid}")
            all_xmlids.add(x.xmlid)
        for r in idx.xml_refs:
            if r.kind == "button":
                all_button_targets.add(r.target)
            elif r.kind == "field":
                all_field_refs.add((r.model_hint or "", r.target))
        for calls in idx.intra_calls.values():
            all_intra_calls |= calls
        for dyn in idx.dynamic_dispatch.values():
            all_dynamic_dispatch_strings |= dyn

    # Mapa xmlid → model_name para resolución de access/binding refs
    xmlid_to_model: dict[str, str] = {}
    for idx in all_indexes.values():
        for m in idx.models:
            # heurística: xmlid = module.model_<name_with_underscores>
            xmlid_guess = f"{idx.module}.model_{m.name.replace('.', '_')}"
            xmlid_to_model[xmlid_guess] = m.name
            xmlid_to_model[f"model_{m.name.replace('.', '_')}"] = m.name

    # Modelos definidos en el módulo target
    target_models: set[str] = {m.name for m in target.models}
    target_models_primary: set[str] = {m.name for m in target.models if m.inherit == [] or (m.inherit and m.inherit[0] == m.name)}

    def is_method_used(method: MethodDecl) -> tuple[bool, str]:
        """Determina si un método tiene al menos un binding válido. Retorna (usado, motivo)."""
        name = method.name
        model = method.model

        # 1) Decoradores api.onchange/depends/constrains = "bound" per se
        bound = {"api.onchange", "api.depends", "api.constrains", "api.model_create_multi"}
        if any(d in bound for d in method.decorators):
            return True, "bound by @api decorator"

        # 2) http.route (controladores)
        if any("route" in d for d in method.decorators):
            return True, "bound by @http.route"

        # 3) Métodos mágicos / ORM overrides (create, write, unlink, read, search, default_get, name_get, name_search, copy, fields_view_get, _compute_display_name, etc.)
        orm_magic = {
            "create", "write", "unlink", "read", "search", "search_read",
            "default_get", "name_get", "name_search", "name_create", "copy",
            "fields_view_get", "fields_get", "_rec_name_fallback",
            "get_view", "_read_group_raw", "_search", "init", "_register_hook",
            "_auto_init", "_compute_display_name", "_name_search", "_name_compute",
            "_auto_install", "toggle_active", "open_wizard",
        }
        if name in orm_magic:
            return True, "orm magic method"

        # 4) Dunder
        if name.startswith("__") and name.endswith("__"):
            return True, "dunder"

        # 5) Referenciado como compute/inverse/search/default en cualquier FieldDecl (de cualquier módulo, mismo model o heredado)
        for idx in all_indexes.values():
            for fd in idx.fields:
                if fd.compute == name or fd.inverse == name or fd.search == name or fd.default_method == name:
                    return True, f"bound as compute/inverse/search/default of {fd.model}.{fd.name}"

        # 6) Referenciado desde <button name="..."> en XML de cualquier módulo
        if name in all_button_targets:
            return True, "referenced by XML button"

        # 7) Llamado desde Python (self.method() o .method()) en cualquier módulo
        if name in all_intra_calls:
            return True, "called from Python"

        # 8) Dynamic dispatch via getattr
        if name in all_dynamic_dispatch_strings:
            return True, "referenced via getattr dynamic dispatch"

        # 9) Sobreescrito en algún inherit de otro módulo: si OTRO módulo tiene un método con el mismo nombre sobre este modelo o sus herederos, asumir que puede haber super() chain
        # (Ya lo captura all_intra_calls si el otro módulo hace super().name())

        # 10) Prefijos especiales de Odoo
        if name.startswith("_onchange_") or name.startswith("_compute_") or name.startswith("_inverse_") or name.startswith("_search_") or name.startswith("_default_"):
            # Estos SI requieren binding explícito desde fields → si no cayó en (5), es huérfano
            return False, f"method prefix suggests {name.split('_')[1]} but no field binds to it"

        return False, "no static caller found"

    # --- A) Referencias rotas (buttons/fields a métodos/campos inexistentes) ---
    target_button_calls = [r for r in target.xml_refs if r.kind == "button"]
    for r in target_button_calls:
        model = r.model_hint or ""
        # ¿Existe algún método con ese nombre en el modelo o sus ancestros (cualquier módulo)?
        exists = False
        for idx in all_indexes.values():
            for me in idx.methods:
                if me.name == r.target and (me.model == model or not model):
                    exists = True
                    break
            if exists:
                break
        # Fallback: existe el método en algún lugar (permisivo)
        if not exists and r.target in all_methods_anywhere:
            # Está en otro modelo; lo marcamos como sospechoso pero no rojo
            agg.add(
                severity="yellow", category="button_model_mismatch", module=module,
                file=r.file, line=r.line,
                title=f"Botón `{r.target}` — método existe en otro modelo",
                description=f"El botón referencia `{r.target}` asumiendo modelo `{model}`, pero el método existe en otros modelos. Verificar que la vista no esté aplicada a un modelo erróneo.",
                evidence=f'<button name="{r.target}" .../>',
                suggested_action="human_review",
                fix_options=["verify_view_model", "rename_button", "move_method_to_model"],
            )
        elif not exists:
            agg.add(
                severity="red", category="broken_button_ref", module=module,
                file=r.file, line=r.line,
                title=f"Botón referencia método inexistente `{r.target}`",
                description=f"`<button name=\"{r.target}\">` en vista de modelo `{model}` no tiene método Python correspondiente en ninguno de los addons escaneados.",
                evidence=f'<button name="{r.target}" type="object"/>',
                suggested_action="fix_reference",
                fix_options=["implement_method", "remove_button", "rename_to_existing"],
            )

    # Set de inherits de cualquier modelo target (para aceptar mixin fields de mixins heredados).
    target_model_inherits: dict[str, set[str]] = {}
    for idx in all_indexes.values():
        for m in idx.models:
            bucket = target_model_inherits.setdefault(m.name, set())
            bucket.update(m.inherit)
            bucket.update(m.inherits_dict)

    def _mixin_fields_for(model: str) -> set[str]:
        """Retorna los campos de mixins core que un modelo hereda (recursivo via inherit chain declarada)."""
        out: set[str] = set(CORE_MIXIN_FIELDS["base"])
        seen: set[str] = set()
        stack = [model]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            if cur in CORE_MIXIN_FIELDS:
                out |= CORE_MIXIN_FIELDS[cur]
            # Seguir inherits del modelo si los conocemos
            for inh in target_model_inherits.get(cur, set()):
                if inh in CORE_MIXIN_FIELDS:
                    out |= CORE_MIXIN_FIELDS[inh]
                stack.append(inh)
        return out

    # B) Field refs rotos en vistas del target
    for r in target.xml_refs:
        if r.kind != "field":
            continue
        model = r.model_hint or ""
        if not model:
            continue
        known_fields = all_fields_by_model.get(model, set()) | _mixin_fields_for(model)
        # Si el modelo hereda de algo cuyos fields también conocemos, sumarlos
        for inh in target_model_inherits.get(model, set()):
            known_fields |= all_fields_by_model.get(inh, set())
            known_fields |= _mixin_fields_for(inh)
        exists = r.target in known_fields
        if not exists:
            # Último fallback: si el target está en el set flatten de mixins conocidos, permisivo.
            if r.target in CORE_MIXIN_FIELDS_FLAT:
                continue
            agg.add(
                severity="red", category="broken_field_ref", module=module,
                file=r.file, line=r.line,
                title=f"Vista referencia campo inexistente `{r.target}`",
                description=f"`<field name=\"{r.target}\"/>` en vista de `{model}` no tiene campo declarado en ningún módulo escaneado ni es un campo de mixin core conocido.",
                evidence=f'<field name="{r.target}"/>',
                suggested_action="fix_reference",
                fix_options=["add_field", "remove_from_view", "rename_to_existing"],
            )

    # C) Onchange/depends/constrains apuntando a campos inexistentes
    for me in target.methods:
        for fname in me.bound_by_decorator:
            # Puede ser dotted (partner_id.name) — tomar la primera parte
            head = fname.split(".")[0]
            if head not in all_fields_by_model.get(me.model, set()):
                agg.add(
                    severity="red", category="decorator_field_missing", module=module,
                    file=me.file, line=me.line,
                    title=f"`@api.*('{fname}')` sobre campo inexistente en `{me.model}`",
                    description=f"El método `{me.name}` está decorado con un campo `{fname}` que no existe en el modelo `{me.model}`.",
                    evidence=f"@{'/'.join(me.decorators)} → {me.name}",
                    suggested_action="fix_reference",
                    fix_options=["rename_decorator_arg", "add_field", "remove_decorator"],
                )

    # D) Métodos huérfanos
    for me in target.methods:
        # Excluir __init__, setUp, setUpClass, test_*
        if me.name.startswith("test_") or me.name in {"setUp", "setUpClass", "tearDown", "tearDownClass", "__init__"}:
            continue
        used, reason = is_method_used(me)
        if used:
            continue
        sev = "yellow"
        title = f"Método huérfano `{me.model}.{me.name}`"
        desc = (f"El método `{me.name}` en `{me.model}` ({me.file}:{me.line}) no tiene callers estáticos en "
                f"ninguno de los addons escaneados: ni botones XML, ni llamadas Python, ni binding como compute/inverse/search/default, "
                f"ni decorador onchange/depends/constrains, ni dispatch dinámico detectado. Motivo: {reason}.")
        caveat = "Puede ser llamado por módulos fuera del addons_path escaneado, por JS frontend (JSON-RPC), o por un server action."
        fix_opts = ["delete", "wire_to_button_or_field", "confirm_external_caller"]
        if me.name.startswith("action_"):
            sev = "yellow"
            title = f"Acción huérfana `{me.model}.{me.name}`"
            desc = f"`{me.name}` tiene prefijo `action_` (convención Odoo para handlers de botón/server-action) pero ningún XML lo referencia. {desc}"
            fix_opts = ["delete", "add_xml_button", "add_server_action", "confirm_external_caller"]
        elif me.name.startswith("_compute_"):
            sev = "yellow"
            title = f"Compute huérfano `{me.model}.{me.name}`"
            desc = f"`{me.name}` tiene convención de compute pero ningún field lo referencia con `compute=`. {desc}"
            fix_opts = ["delete", "bind_to_field", "rename"]
        elif me.name.startswith("_onchange_"):
            sev = "yellow"
            title = f"Onchange sin `@api.onchange` en `{me.model}.{me.name}`"
            desc = f"`{me.name}` tiene convención onchange pero no tiene decorador `@api.onchange(...)`. {desc}"
            fix_opts = ["add_decorator", "delete", "rename"]
        agg.add(
            severity=sev, category="orphan_method", module=module,
            file=me.file, line=me.line,
            title=title, description=desc, caveat=caveat,
            evidence=f"def {me.name}(self, ...) on {me.model}",
            suggested_action="human_review",
            fix_options=fix_opts,
        )

    # E) Campos declarados sin uso — construimos un índice global de tokens Python+XML en una sola pasada.
    field_refs_flat: set[str] = {t for _, t in all_field_refs}
    target_field_names: set[str] = {f.name for f in target.fields}

    # Pre-build: all_identifier_tokens (attribute access, name) + all_string_literals across all .py and .xml.
    # Un token o literal se considera "mención" del campo. Es permisivo — la idea es evitar falsos positivos en campos usados.
    TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    STRING_LITERAL_PATTERN = re.compile(r"['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]")
    all_identifiers: set[str] = set()
    all_string_literals: set[str] = set()
    for idx in all_indexes.values():
        for py in idx.path.rglob("*.py"):
            txt = read_text(py)
            if not txt:
                continue
            all_identifiers.update(TOKEN_PATTERN.findall(txt))
            all_string_literals.update(STRING_LITERAL_PATTERN.findall(txt))
        for xml in idx.path.rglob("*.xml"):
            txt = read_text(xml)
            if not txt:
                continue
            # En XML los field/button names aparecen como atributos name="..." y valores de <field>.
            all_string_literals.update(STRING_LITERAL_PATTERN.findall(txt))
            all_identifiers.update(TOKEN_PATTERN.findall(txt))

    python_field_mentions: set[str] = target_field_names & (all_identifiers | all_string_literals)
    for fd in target.fields:
        if fd.name in field_refs_flat:
            continue
        if fd.name in python_field_mentions:
            continue
        # Campos "core" muy comunes los skipeamos
        if fd.name in {"active", "sequence", "company_id", "currency_id", "name", "state", "color"}:
            continue
        agg.add(
            severity="blue", category="unused_field", module=module,
            file=fd.file, line=fd.line,
            title=f"Campo posiblemente no usado `{fd.model}.{fd.name}`",
            description=(f"El campo `{fd.name}` ({fd.ftype}) en `{fd.model}` no aparece en vistas XML ni "
                         f"es mencionado en código Python (ni como string literal ni como atributo). Puede ser código muerto."),
            caveat="Puede ser accedido vía ORM dinámico, exportado en reportes, o usado por un módulo fuera del addons_path.",
            evidence=f"{fd.name} = fields.{fd.ftype}(...)",
            suggested_action="human_review",
            fix_options=["delete", "add_to_view", "confirm_external_use"],
        )

    # F) Computes huérfanos (campo con compute='_compute_x' pero _compute_x no existe)
    target_methods_by_model: dict[str, set[str]] = {}
    for me in target.methods:
        target_methods_by_model.setdefault(me.model, set()).add(me.name)
    for fd in target.fields:
        for kind, val in (("compute", fd.compute), ("inverse", fd.inverse), ("search", fd.search), ("default", fd.default_method)):
            if not val:
                continue
            # Buscar método en el modelo target o herederos (cualquier módulo)
            found = False
            for idx in all_indexes.values():
                for me in idx.methods:
                    if me.name == val and (me.model == fd.model or fd.model in [i for m in idx.models if m.name == me.model for i in m.inherit]):
                        found = True
                        break
                if found:
                    break
            # fallback permisivo: ¿existe como método con ese nombre en algún lugar del mismo modelo target?
            if not found and val not in target_methods_by_model.get(fd.model, set()):
                agg.add(
                    severity="red", category="missing_compute_method", module=module,
                    file=fd.file, line=fd.line,
                    title=f"Campo `{fd.model}.{fd.name}` apunta a `{kind}='{val}'` inexistente",
                    description=f"El campo `{fd.name}` declara `{kind}='{val}'` pero no existe un método con ese nombre en `{fd.model}` ni en addons que lo extiendan.",
                    evidence=f"{fd.name} = fields.{fd.ftype}({kind}='{val}', ...)",
                    suggested_action="fix_reference",
                    fix_options=["implement_method", "rename_to_existing", "remove_kwarg"],
                )

    # G) Modelos aislados (sin ACL, sin vista, sin menú, sin FK)
    access_models: set[str] = set()
    for idx in all_indexes.values():
        for ae in idx.access_entries:
            xm = ae.model_xmlid
            if xm in xmlid_to_model:
                access_models.add(xmlid_to_model[xm])
            elif xm.startswith("model_"):
                # Heurística: model_foo_bar → foo.bar
                guess = xm[len("model_"):].replace("_", ".")
                access_models.add(guess)
    view_models: set[str] = {vm for idx in all_indexes.values() for _, vm, _ in idx.view_bindings}

    # FK targets: re-escanear Many2one/One2many/Many2many comodel_name
    m2x_targets: set[str] = set()
    for idx in all_indexes.values():
        for py in idx.path.rglob("*.py"):
            src = read_text(py)
            if not src:
                continue
            # fields.Many2one('res.partner', ...)  | comodel_name='res.partner'
            for m in re.finditer(r"fields\.(?:Many2one|One2many|Many2many)\(\s*['\"]([a-zA-Z0-9_.]+)['\"]", src):
                m2x_targets.add(m.group(1))
            for m in re.finditer(r"comodel_name\s*=\s*['\"]([a-zA-Z0-9_.]+)['\"]", src):
                m2x_targets.add(m.group(1))

    for model in target_models_primary:
        # Si el modelo es abstract/transient, no exigimos ACL/menu
        # Detectar via tag de la clase
        mdecl = next((m for m in target.models if m.name == model), None)
        if not mdecl:
            continue
        reasons: list[str] = []
        if model not in access_models:
            reasons.append("sin entrada en ir.model.access.csv (ningún módulo le otorga ACL)")
        if model not in view_models:
            reasons.append("sin vista declarada (ningún ir.ui.view apunta a este modelo)")
        if model not in m2x_targets:
            reasons.append("no es destino de ningún Many2one/One2many/Many2many")
        if len(reasons) >= 2:
            agg.add(
                severity="yellow", category="isolated_model", module=module,
                file=mdecl.file, line=mdecl.line,
                title=f"Modelo aislado `{model}`",
                description=f"El modelo `{model}` parece no conectado al resto: {'; '.join(reasons)}.",
                caveat="Puede ser usado solo vía ORM de otro módulo o vía domains dinámicos.",
                evidence=f"class ... Model  _name='{model}'",
                suggested_action="human_review",
                fix_options=["wire_acl_view_menu", "delete_model", "confirm_external_use"],
            )

    # H) XML IDs huérfanos (declarados pero no referenciados desde nada)
    all_refs_textual: set[str] = set()
    # menuitem action, ref="xxx", records referenciados
    for idx in all_indexes.values():
        for xml in idx.path.rglob("*.xml"):
            txt = read_text(xml)
            if not txt:
                continue
            for m in re.finditer(r'\b(?:ref|action|parent|model)="([a-zA-Z0-9_.]+)"', txt):
                all_refs_textual.add(m.group(1))
        # y en Python buscar env.ref('...')
        for py in idx.path.rglob("*.py"):
            txt = read_text(py)
            if not txt:
                continue
            for m in re.finditer(r"env\.ref\(\s*['\"]([a-zA-Z0-9_.]+)['\"]", txt):
                all_refs_textual.add(m.group(1))

    # Modelos con al menos un ir.actions.act_window declarado (vía res_model).
    # Odoo resuelve vistas tree/form/kanban/... implícitamente por modelo + view_mode, así que
    # si hay una act_window sobre el modelo X, no flaggeamos las vistas de ese modelo como huérfanas.
    action_res_models: set[str] = set()
    for idx in all_indexes.values():
        for r in idx.xml_refs:
            if r.kind == "action_res_model":
                action_res_models.add(r.target)

    # Mapa xmlid → modelo de la vista (solo para los view records de los módulos target+scan)
    view_id_to_model: dict[str, str] = {}
    for idx in all_indexes.values():
        for vid, vmodel, _ in idx.view_bindings:
            view_id_to_model[vid] = vmodel
            view_id_to_model[f"{idx.module}.{vid}"] = vmodel

    for x in target.xmlids:
        full = f"{target.module}.{x.xmlid}"
        short = x.xmlid
        # views con inherit_id se referencian por id del padre, no del hijo → los skipeamos
        if short.endswith("_inherit") or "_inherit_" in short:
            continue
        if full in all_refs_textual or short in all_refs_textual:
            continue
        # Menú raíz: a veces no es referenciado por parent (son menuitems que no tienen padre ni hijos directos ref)
        if x.model == "ir.ui.menu":
            continue
        # Vistas de un modelo que tiene act_window se consideran referenciadas implícitamente via view_mode
        if x.model == "ir.ui.view":
            vmodel = view_id_to_model.get(short) or view_id_to_model.get(full)
            if vmodel and vmodel in action_res_models:
                continue
        # Portal templates (QWeb) se consumen via controllers Python con request.render() — ya cubierto
        # por búsqueda textual en .py, pero si el template id está en un string de render y no lo detectamos,
        # asumimos que portal templates no son huérfanos a nivel estático.
        if x.model == "ir.ui.view" and ("portal" in short.lower() or "template" in x.file.lower()):
            # mantener como 'blue' pero menos confiable
            pass
        # act_window son válidas si se llaman desde menuitem action=… ya capturado en all_refs_textual
        agg.add(
            severity="blue", category="orphan_xmlid", module=module,
            file=x.file, line=x.line,
            title=f"XML ID huérfano `{short}`",
            description=f"`<record id=\"{short}\" model=\"{x.model}\">` no es referenciado desde ningún otro record/action/menu/env.ref en los addons escaneados.",
            caveat="Puede ser consumido vía configuración externa o data loading manual.",
            evidence=f'id="{short}" model="{x.model}"',
            suggested_action="human_review",
            fix_options=["delete", "confirm_external_consumer"],
        )

    # I) Selection values sin uso. Usamos el índice `all_string_literals` ya construido.
    # Contamos cuántas veces aparece cada valor como string literal — la declaración del propio Selection
    # aporta 2 matches (valor + label) en la misma tupla. Si el total > 2, asumimos uso externo.
    # Nota: all_string_literals es un set → perdimos cuenta. Reconstruyo un Counter rápido solo para los valores candidatos.
    from collections import Counter as _Counter
    candidate_selection_values: set[str] = set()
    for fd in target.fields:
        if fd.ftype == "Selection" and fd.selection_values:
            candidate_selection_values.update(fd.selection_values)

    sel_occurrences: _Counter = _Counter()
    if candidate_selection_values:
        # Construir pattern compuesto una sola vez y contar en una pasada por archivo.
        alts = "|".join(re.escape(v) for v in candidate_selection_values)
        sel_pat = re.compile(rf"['\"]({alts})['\"]")
        for idx in all_indexes.values():
            for f in list(idx.path.rglob("*.py")) + list(idx.path.rglob("*.xml")):
                txt = read_text(f)
                if not txt:
                    continue
                for m in sel_pat.finditer(txt):
                    sel_occurrences[m.group(1)] += 1

    for fd in target.fields:
        if fd.ftype != "Selection" or not fd.selection_values:
            continue
        for val in fd.selection_values:
            # Declaración aporta 2 (valor + label en la tupla). Si hay ≤2 → probablemente solo la declaración.
            if sel_occurrences.get(val, 0) > 2:
                continue
            agg.add(
                severity="blue", category="unused_selection_value", module=module,
                file=fd.file, line=fd.line,
                title=f"Valor `{val}` de `{fd.model}.{fd.name}` sin uso",
                description=f"El valor `{val}` del Selection `{fd.name}` no es seteado ni leído en ningún .py/.xml de los addons escaneados.",
                caveat="Puede ser seteado desde data/demo XML o desde data loading externo.",
                evidence=f"('{val}', '...') en Selection {fd.name}",
                suggested_action="human_review",
                fix_options=["delete_value", "wire_transition", "confirm_external_set"],
            )

    return agg.items


# ---------- CLI ----------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Static deadcode scan for an Odoo module.")
    p.add_argument("module_path", help="Path to the Odoo module to analyze")
    p.add_argument("--addons-path", default=None,
                   help="Colon- or comma-separated list of addons_path directories. If not given, tries to auto-detect from <repo>/odoo.conf.")
    p.add_argument("--output", default="json", choices=["json", "pretty"],
                   help="Output format for stdout (the JSON file is always written to <module>/.deadcode/)")
    p.add_argument("--limit", default=None, help="(Opcional) limitar cuántos addons escanear (debug)")
    return p.parse_args()


def find_repo_root(start: Path) -> Path:
    """Sube hasta encontrar odoo.conf (señal más fuerte que .git por submodulos/subrepos).
    Si no hay odoo.conf en ningún ancestro, cae al primer .git encontrado."""
    p = start.resolve()
    first_git: Path | None = None
    while p != p.parent:
        if (p / "odoo.conf").exists():
            return p
        if first_git is None and (p / ".git").exists():
            first_git = p
        p = p.parent
    return first_git or start.resolve()


def main() -> int:
    args = parse_args()
    module_path = Path(args.module_path).resolve()
    if not is_odoo_module_dir(module_path):
        print(f"ERROR: {module_path} no es un módulo Odoo válido (falta __manifest__.py o __init__.py).", file=sys.stderr)
        return 2

    repo_root = find_repo_root(module_path)

    # Resolver addons_path
    if args.addons_path:
        raw = args.addons_path.replace(":", ",")
        addons_paths = [Path(p).resolve() for p in raw.split(",") if p.strip()]
    else:
        odoo_conf = repo_root / "odoo.conf"
        addons_paths = resolve_addons_paths_from_conf(odoo_conf, repo_root)
        if not addons_paths:
            # fallback: carpeta padre del módulo
            addons_paths = [module_path.parent.resolve()]

    # Asegurar que el parent del módulo target esté incluido
    if module_path.parent not in addons_paths:
        addons_paths.insert(0, module_path.parent)

    # Enumerar módulos
    modules = list_modules([p for p in addons_paths if p.exists()])
    if args.limit:
        try:
            lim = int(args.limit)
            modules = dict(list(modules.items())[:lim])
        except ValueError:
            pass

    target_module_name = module_path.name
    if target_module_name not in modules:
        modules[target_module_name] = module_path

    print(f"[scan_deadcode] Módulo target: {target_module_name}", file=sys.stderr)
    print(f"[scan_deadcode] Addons paths: {len(addons_paths)} path(s), {len(modules)} módulos", file=sys.stderr)

    # Scan
    all_indexes: dict[str, ModuleIndex] = {}
    for i, (mname, mpath) in enumerate(modules.items(), start=1):
        if i % 25 == 0 or i == len(modules):
            print(f"[scan_deadcode] scanning {i}/{len(modules)}: {mname}", file=sys.stderr)
        try:
            all_indexes[mname] = scan_module(mpath, mname)
        except Exception as e:
            print(f"[scan_deadcode] warn: fallo al escanear {mname}: {e}", file=sys.stderr)

    target = all_indexes[target_module_name]
    findings = compute_findings(target, all_indexes)

    # Stats
    stats = {
        "modules_scanned": len(all_indexes),
        "target_models": len(target.models),
        "target_methods": len(target.methods),
        "target_fields": len(target.fields),
        "target_xml_refs": len(target.xml_refs),
        "target_xmlids": len(target.xmlids),
        "target_access_entries": len(target.access_entries),
        "findings_total": len(findings),
        "findings_red": sum(1 for f in findings if f.severity == "red"),
        "findings_yellow": sum(1 for f in findings if f.severity == "yellow"),
        "findings_blue": sum(1 for f in findings if f.severity == "blue"),
    }

    out_dir = module_path / ".deadcode"
    out_dir.mkdir(exist_ok=True)
    out_json = out_dir / "DEADCODE_SCAN.json"

    payload = {
        "module": target_module_name,
        "module_path": str(module_path),
        "addons_paths": [str(p) for p in addons_paths],
        "modules_scanned": sorted(all_indexes.keys()),
        "stats": stats,
        "findings": [asdict(f) for f in findings],
    }
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"[scan_deadcode] Escrito: {out_json}", file=sys.stderr)

    if args.output == "pretty":
        print(f"\n=== DEADCODE SCAN — {target_module_name} ===")
        print(f"Addons escaneados: {stats['modules_scanned']}")
        print(f"Modelos target:    {stats['target_models']}")
        print(f"Métodos target:    {stats['target_methods']}")
        print(f"Findings:          {stats['findings_total']} "
              f"(🔴 {stats['findings_red']} | 🟡 {stats['findings_yellow']} | 🔵 {stats['findings_blue']})")
        for f in findings:
            emoji = {"red": "🔴", "yellow": "🟡", "blue": "🔵"}.get(f.severity, "⚪")
            print(f"  {emoji} {f.id} [{f.category}] {f.title}")
            print(f"     {f.file}:{f.line}")
    else:
        # imprime solo el path del JSON para pipelines
        print(str(out_json))

    return 0


if __name__ == "__main__":
    sys.exit(main())
