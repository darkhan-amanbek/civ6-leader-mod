#!/usr/bin/env python3
"""Проверка мода Civilization VI до запуска игры.

Использование:
    python3 validate_mod.py <папка мода> [--cache <папка Cache>] [--no-dry-run]

Шаги:
  1. .modinfo: XML, GUID, файлы действий существуют и перечислены в <Files>.
  2. Все XML-файлы мода корректны.
  3. LOC_*-теги: определены в текстах мода или игры, есть en_US.
  4. Пробный прогон SQL/XML мода на копии кэша базы игры (внешние ключи,
     имена таблиц/столбцов, ModifierType/RequirementType).
  5. Подсказки по балансу.

Только стандартная библиотека Python 3.8+.
"""
import argparse
import os
import platform
import re
import shutil
import sqlite3
import sys
import tempfile
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
LOC_RE = re.compile(r"\bLOC_[A-Z0-9_]+\b")
DB_ACTIONS = {"UpdateDatabase", "UpdateText", "UpdateColors", "UpdateIcons"}

errors, warnings, notes = [], [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def note(msg):
    notes.append(msg)


def default_cache_dir():
    home = Path.home()
    if platform.system() == "Darwin":
        return home / "Library/Application Support/Sid Meier's Civilization VI/Firaxis Games/Sid Meier's Civilization VI/Cache"
    return home / "Documents/My Games/Sid Meier's Civilization VI/Cache"


# ---------------------------------------------------------------- modinfo

def parse_modinfo(mod_dir):
    infos = list(mod_dir.glob("*.modinfo"))
    if len(infos) != 1:
        err(f"В папке должен быть ровно один .modinfo, найдено: {len(infos)}")
        return None, []
    path = infos[0]
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        err(f"{path.name}: некорректный XML — {e}")
        return path, []

    mod_id = root.get("id", "")
    if not GUID_RE.match(mod_id):
        err(f"{path.name}: id «{mod_id}» не похож на GUID. Сгенерируй: python3 -c \"import uuid; print(uuid.uuid4())\"")

    criteria_ids = {c.get("id") for c in root.iter("Criteria")}
    actions, action_ids = [], set()
    for section in ("FrontEndActions", "InGameActions"):
        for sec in root.findall(section):
            for act in sec:
                aid = act.get("id")
                if aid in action_ids:
                    err(f"{path.name}: id действия «{aid}» повторяется")
                action_ids.add(aid)
                crit = act.get("criteria")
                if crit and crit not in criteria_ids:
                    err(f"{path.name}: действие «{aid}» ссылается на неизвестный criteria «{crit}»")
                files = [f.text.strip() for f in act.findall("File") if f.text]
                actions.append({"section": section, "type": act.tag, "id": aid, "criteria": crit, "files": files})

    listed = {f.text.strip() for f in root.findall("./Files/File") if f.text}
    used = {f for a in actions for f in a["files"]}
    for f in sorted(used):
        if not (mod_dir / f).is_file():
            err(f"Файл из действий не найден на диске: {f}")
        if f not in listed:
            err(f"Файл используется в действиях, но не указан в <Files>: {f}")
    for f in sorted(listed):
        if not (mod_dir / f).is_file():
            err(f"Файл из <Files> не найден на диске: {f}")
    if not any(a["section"] == "FrontEndActions" and a["type"] == "UpdateDatabase" for a in actions):
        warn("Нет FrontEnd UpdateDatabase — лидер не появится на экране выбора (таблица Players)")
    return path, actions


# ---------------------------------------------------------------- text

def check_xml_files(mod_dir):
    for p in mod_dir.rglob("*"):
        if p.suffix.lower() in (".xml", ".artdef", ".dep") and p.is_file():
            try:
                ET.parse(p)
            except ET.ParseError as e:
                err(f"{p.relative_to(mod_dir)}: некорректный XML — {e}")


def collect_text(mod_dir, actions):
    """Возвращает {tag: set(languages)} из файлов UpdateText."""
    defined = {}
    for a in actions:
        if a["type"] != "UpdateText":
            continue
        for f in a["files"]:
            p = mod_dir / f
            if not p.is_file() or p.suffix.lower() != ".xml":
                continue
            try:
                root = ET.parse(p).getroot()
            except ET.ParseError:
                continue
            for table in root:
                default_lang = "en_US" if table.tag == "EnglishText" else None
                for row in table:
                    tag = row.get("Tag") or (row.findtext("Tag") or "").strip()
                    lang = row.get("Language") or (row.findtext("Language") or "").strip() or default_lang or "en_US"
                    if tag:
                        defined.setdefault(tag, set()).add(lang)
    return defined


def check_loc(mod_dir, actions, defined, loc_db):
    referenced = set()
    text_files = {f for a in actions if a["type"] == "UpdateText" for f in a["files"]}
    for a in actions:
        for f in a["files"]:
            if f in text_files:
                continue
            p = mod_dir / f
            if p.is_file() and p.suffix.lower() in (".sql", ".xml"):
                referenced |= set(LOC_RE.findall(p.read_text(encoding="utf-8", errors="ignore")))
    info = next(mod_dir.glob("*.modinfo"), None)
    if info:
        referenced |= set(LOC_RE.findall(info.read_text(encoding="utf-8", errors="ignore")))

    game_tags = set()
    if loc_db and loc_db.is_file():
        con = sqlite3.connect(f"file:{loc_db}?mode=ro", uri=True)
        game_tags = {r[0] for r in con.execute("SELECT DISTINCT Tag FROM LocalizedText")}
        con.close()

    missing = sorted(t for t in referenced if t not in defined and t not in game_tags)
    for t in missing:
        if game_tags:
            warn(f"Тег {t} не найден ни в тексте мода, ни в текстах игры. Если это твой тег — добавь его в Text; "
                 f"если тег из дополнения, а последняя партия была без него — можно игнорировать")
        else:
            warn(f"Тег {t} не определён в тексте мода (базу текстов игры проверить не удалось)")
    for tag, langs in sorted(defined.items()):
        if "en_US" not in langs:
            warn(f"У тега {tag} нет строки en_US — в английском клиенте будет виден голый тег")


# ---------------------------------------------------------------- XML -> SQL

def _val(v):
    if v is None:
        return None
    s = v.strip()
    if s.lower() == "true":
        return 1
    if s.lower() == "false":
        return 0
    return s


def _cols(elem):
    data = {k: _val(v) for k, v in elem.attrib.items()}
    for child in elem:
        data[child.tag] = _val(child.text or "")
    return data


def xml_to_statements(path):
    """Переводит GameInfo/GameData XML в список (sql, params)."""
    root = ET.parse(path).getroot()
    out = []
    for table in root:
        name = table.tag
        default_lang = None
        if name == "EnglishText":
            name, default_lang = "LocalizedText", "en_US"
        for op in table:
            if op.tag in ("Row", "Replace"):
                data = _cols(op)
                if name == "LocalizedText" and "Language" not in data:
                    data["Language"] = default_lang or "en_US"
                cols = list(data)
                verb = "INSERT OR REPLACE" if op.tag == "Replace" else "INSERT"
                sql = f'{verb} INTO "{name}" ({", ".join(chr(34) + c + chr(34) for c in cols)}) VALUES ({", ".join("?" * len(cols))})'
                out.append((sql, [data[c] for c in cols]))
            elif op.tag == "Update":
                where = _cols(op.find("Where")) if op.find("Where") is not None else {}
                sets = _cols(op.find("Set")) if op.find("Set") is not None else {}
                if not sets:
                    continue
                sql = f'UPDATE "{name}" SET ' + ", ".join(f'"{c}"=?' for c in sets)
                params = list(sets.values())
                if where:
                    sql += " WHERE " + " AND ".join(f'"{c}"=?' for c in where)
                    params += list(where.values())
                out.append((sql, params))
            elif op.tag == "Delete":
                where = _cols(op)
                sql = f'DELETE FROM "{name}"'
                if where:
                    sql += " WHERE " + " AND ".join(f'"{c}"=?' for c in where)
                out.append((sql, list(where.values())))
    return out


def sql_statements(path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    out, buf = [], ""
    for line in text.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            stmt = buf.strip()
            if stmt and not all(l.strip().startswith("--") or not l.strip() for l in stmt.splitlines()):
                out.append((stmt, []))
            buf = ""
    if buf.strip() and not all(l.strip().startswith("--") or not l.strip() for l in buf.splitlines()):
        out.append((buf.strip(), []))
    return out


# ---------------------------------------------------------------- dry run

def open_copy(src, tmpdir):
    dst = Path(tmpdir) / src.name
    shutil.copyfile(src, dst)
    con = sqlite3.connect(dst)
    con.create_function("Make_Hash", 1, lambda s: zlib.crc32((s or "").encode()) - (1 << 31))
    return con


def fk_violations(con):
    return {tuple(r) for r in con.execute("PRAGMA foreign_key_check")}


def apply_file(con, mod_dir, rel, label):
    p = mod_dir / rel
    try:
        stmts = xml_to_statements(p) if p.suffix.lower() == ".xml" else sql_statements(p)
    except ET.ParseError:
        return False
    ok = True
    for sql, params in stmts:
        try:
            con.execute(sql, params)
        except sqlite3.IntegrityError as e:
            msg = str(e)
            if "UNIQUE" in msg:
                warn(f"{rel}: дубль ({msg}). Если этот мод уже запускался — кэш содержит его прошлую версию, это нормально. "
                     f"Иначе идентификатор совпадает с существующим. Оператор: {sql[:90]}…")
            else:
                err(f"{rel}: {msg}. Оператор: {sql[:120]}…")
                ok = False
        except sqlite3.Error as e:
            err(f"{rel}: {e}. В игре это остановит загрузку остатка файла. Оператор: {sql[:120]}…")
            ok = False
    return ok


def dry_run(mod_dir, actions, cache):
    gp, cfg, loc = cache / "DebugGameplay.sqlite", cache / "DebugConfiguration.sqlite", cache / "DebugLocalization.sqlite"
    if not gp.is_file():
        warn(f"Кэш базы игры не найден ({cache}). Запусти партию один раз или укажи --cache. Пробный прогон пропущен.")
        return
    tmp = tempfile.mkdtemp(prefix="civ6mod_")
    try:
        dbs = {"gameplay": open_copy(gp, tmp)}
        if cfg.is_file():
            dbs["config"] = open_copy(cfg, tmp)
        if loc.is_file():
            dbs["text"] = open_copy(loc, tmp)
        base_fk = {k: fk_violations(c) for k, c in dbs.items()}
        g = dbs["gameplay"]
        before_mods = {r[0] for r in g.execute("SELECT ModifierId FROM Modifiers")}
        before_reqs = {r[0] for r in g.execute("SELECT RequirementId FROM Requirements")}
        before_lists = {r[0] for r in g.execute("SELECT ListType FROM AiLists")}
        before_replaces = set(g.execute("SELECT CivUniqueUnitType, ReplacesUnitType FROM UnitReplaces")) | \
            set(g.execute("SELECT CivUniqueDistrictType, ReplacesDistrictType FROM DistrictReplaces"))

        def target(a):
            if a["type"] == "UpdateText":
                return "text"
            if a["type"] in ("UpdateIcons", "UpdateColors"):
                return None  # у иконок и цветов своя база, её нет в кэше
            return "config" if a["section"] == "FrontEndActions" else "gameplay"

        seen = set()
        for gated in (False, True):
            for a in actions:
                if bool(a["criteria"]) != gated:
                    continue
                key = target(a)
                if key is None or key not in dbs:
                    continue
                con = dbs[key]
                for f in a["files"]:
                    if (key, f) in seen or not (mod_dir / f).is_file():
                        continue
                    seen.add((key, f))
                    if gated:
                        con.execute("SAVEPOINT gated")
                        n_err = len(errors)
                        apply_file(con, mod_dir, f, a["id"])
                        if len(errors) > n_err:
                            moved = errors[n_err:]
                            del errors[n_err:]
                            for m in moved:
                                warn(f"[criteria={a['criteria']}] {m} — если последняя партия была в другом ruleset, это ожидаемо")
                        con.execute("RELEASE gated")
                    else:
                        apply_file(con, mod_dir, f, a["id"])

        for k, con in dbs.items():
            for v in sorted(fk_violations(con) - base_fk[k]):
                table, rowid, parent = v[0], v[1], v[2]
                row = con.execute(f'SELECT * FROM "{table}" WHERE rowid=?', (rowid,)).fetchone()
                err(f"Битая ссылка: {table} {row} → нет строки в {parent}. Обычно — опечатка или тип не объявлен")

        new_mods = {r[0] for r in g.execute("SELECT ModifierId FROM Modifiers")} - before_mods
        new_reqs = {r[0] for r in g.execute("SELECT RequirementId FROM Requirements")} - before_reqs
        new_lists = {r[0] for r in g.execute("SELECT ListType FROM AiLists")} - before_lists
        check_types(g, new_mods, new_reqs, new_lists)
        balance_hints(g, new_mods, before_replaces)
        note("Пробный прогон выполнен на копии кэша; файлы игры не изменялись.")
        note("Кэш — это база последней партии вместе с её модами. Ссылка на контент чужого мода пройдёт проверку, "
             "но сломается у друзей без этого мода. Для финальной проверки запусти партию только с этим модом.")
        for c in dbs.values():
            c.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_types(g, new_mods, new_reqs, new_lists):
    dyn = {r[0] for r in g.execute("SELECT ModifierType FROM DynamicModifiers")}
    for mid, mtype in g.execute("SELECT ModifierId, ModifierType FROM Modifiers"):
        if mid in new_mods and mtype not in dyn:
            err(f"Модификатор {mid}: ModifierType {mtype} не существует (нет в DynamicModifiers)")
    req_types = {r[0] for r in g.execute("SELECT Type FROM Types WHERE Kind='KIND_REQUIREMENT'")}
    for rid, rtype in g.execute("SELECT RequirementId, RequirementType FROM Requirements"):
        if rid in new_reqs and rtype not in req_types:
            err(f"Требование {rid}: RequirementType {rtype} не существует")
    for (lst, lt) in g.execute("SELECT ListType, LeaderType FROM AiLists WHERE LeaderType LIKE 'LEADER_%'"):
        if lst in new_lists:
            err(f"AiLists.LeaderType = {lt}: здесь нужен TraitType лидера (TRAIT_LEADER_...), а не LeaderType")


# ---------------------------------------------------------------- balance

RISKY_TYPES = [
    ("GRANT_UNIT", "бесплатные юниты"),
    ("GRANT_FREE_TECH", "бесплатные технологии"),
    ("GRANT_TECHNOLOGY", "бесплатные технологии"),
    ("GRANT_CIVIC", "бесплатные цивики"),
    ("GRANT_ALL_TECHNOLOGY_BOOST", "все эврики эпохи разом"),
]


def balance_hints(g, new_mods, before_replaces):
    args = {}
    for mid, name, typ, val in g.execute("SELECT ModifierId, Name, Type, Value FROM ModifierArguments"):
        if mid in new_mods:
            args.setdefault(mid, {})[name] = (val, typ)
    for mid, mtype, run_once, subj, owner in g.execute(
            "SELECT ModifierId, ModifierType, RunOnce, SubjectRequirementSetId, OwnerRequirementSetId FROM Modifiers"):
        if mid not in new_mods:
            continue
        a = args.get(mid, {})
        amount = None
        try:
            amount = float(a.get("Amount", (None,))[0])
        except (TypeError, ValueError):
            pass
        cond = bool(subj or owner)
        if "COMBAT_STRENGTH" in mtype and amount is not None:
            if amount > 7:
                warn(f"⛔ Баланс: {mid} даёт +{amount:g} силы — у официальных лидеров обычно +3…+5 (максимум +7 узко). См. balance.md §3")
            elif amount > 5 or not cond:
                warn(f"⚠ Баланс: {mid} +{amount:g} силы{'' if cond else ' без условия'} — проверь по balance.md §3")
        if "YIELD_MODIFIER" in mtype and amount is not None and amount >= 15 and not cond:
            warn(f"⚠ Баланс: {mid} +{amount:g}% к доходу во всех городах без условия — сильный бонус на всю игру")
        if mtype in ("MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE", "MODIFIER_PLAYER_ADJUST_PLOT_YIELD") \
                and amount is not None and amount >= 2 and not cond:
            warn(f"⚠ Баланс: {mid} +{amount:g} дохода на каждый город/клетку без условия — ранний снежный ком")
        if mtype == "MODIFIER_PLAYER_GRANT_YIELD" and a.get("Amount", (None, None))[1] != "ScaleByGameSpeed":
            warn(f"⚠ {mid}: разовая выплата без Type='ScaleByGameSpeed' — на медленных скоростях будет относительно сильнее")
        for key, label in RISKY_TYPES:
            if key in mtype and not run_once:
                warn(f"⛔ Баланс: {mid} ({mtype}) — {label} без RunOnce. Красный флаг, см. balance.md §4")
        if subj is None and owner is None and mtype.endswith("_DISTRICTS_ADJUST_YIELD_CHANGE"):
            warn(f"⚠ {mid}: доход со ВСЕХ районов (нет условия на тип района) — так задумано?")

    for uu, base in g.execute("SELECT CivUniqueUnitType, ReplacesUnitType FROM UnitReplaces").fetchall():
        if (uu, base) in before_replaces:
            continue
        cols = "Combat, RangedCombat, BaseMoves, Cost, IFNULL(StrategicResource,''), Maintenance"
        u = g.execute(f"SELECT {cols} FROM Units WHERE UnitType=?", (uu,)).fetchone()
        b = g.execute(f"SELECT {cols} FROM Units WHERE UnitType=?", (base,)).fetchone()
        if not u or not b:
            continue
        d_cs, d_rs, d_mv, d_cost = u[0] - b[0], u[1] - b[1], u[2] - b[2], u[3] - b[3]
        pluses = sum([max(d_cs, d_rs) > 0, d_mv > 0, d_cost < 0, bool(b[4]) and not u[4], u[5] < b[5]])
        summary = f"{uu} против {base}: сила {u[0]}/{b[0]}, дальн. {u[1]}/{b[1]}, ходы {u[2]}/{b[2]}, цена {u[3]}/{b[3]}"
        if max(d_cs, d_rs) > 8 or pluses >= 3:
            warn(f"⛔ Баланс: {summary}. Официально обычно +3…+5 силы ИЛИ +1 ход, часто дороже. См. balance.md §3")
        elif max(d_cs, d_rs) > 5 or pluses == 2:
            warn(f"⚠ Баланс: {summary}. Проверь по таблице уникальных юнитов")
        else:
            note(f"Юнит: {summary} — в пределах официальных значений")

    for ud, base in g.execute("SELECT CivUniqueDistrictType, ReplacesDistrictType FROM DistrictReplaces").fetchall():
        if (ud, base) in before_replaces:
            continue
        u = g.execute("SELECT Cost FROM Districts WHERE DistrictType=?", (ud,)).fetchone()
        b = g.execute("SELECT Cost FROM Districts WHERE DistrictType=?", (base,)).fetchone()
        if u and b and u[0] < b[0] * 0.5:
            warn(f"⚠ Баланс: {ud} стоит {u[0]} против {b[0]} — дешевле официальной половины цены")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Проверка мода Civilization VI")
    ap.add_argument("mod_dir")
    ap.add_argument("--cache", help="папка Cache игры (по умолчанию — стандартная для ОС)")
    ap.add_argument("--no-dry-run", action="store_true", help="не прогонять мод на копии базы игры")
    args = ap.parse_args()

    mod_dir = Path(args.mod_dir).expanduser().resolve()
    if not mod_dir.is_dir():
        print(f"Папка не найдена: {mod_dir}")
        return 2
    cache = Path(args.cache).expanduser() if args.cache else default_cache_dir()

    _, actions = parse_modinfo(mod_dir)
    check_xml_files(mod_dir)
    defined = collect_text(mod_dir, actions)
    check_loc(mod_dir, actions, defined, cache / "DebugLocalization.sqlite")
    if not args.no_dry_run and actions:
        dry_run(mod_dir, actions, cache)

    print(f"Проверка мода: {mod_dir.name}\n")
    for title, items, mark in (("Ошибки", errors, "✖"), ("Предупреждения", warnings, "⚠"), ("Заметки", notes, "·")):
        if items:
            print(f"{title} ({len(items)}):")
            for m in items:
                print(f"  {m}" if m[:1] in "⚠⛔" else f"  {mark} {m}")
            print()
    if not errors and not warnings:
        print("✔ Проблем не найдено.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
