#!/usr/bin/env python3
"""Поиск примеров в базе данных Civilization VI (кэш последней партии).

Использование:
    python3 find_examples.py GOLD_DISPERSAL            # модификаторы по ModifierType / EffectType / ModifierId
    python3 find_examples.py --trait TRAIT_LEADER_     # трейты и их модификаторы
    python3 find_examples.py --req ADJACENT            # типы требований и их аргументы
    python3 find_examples.py --leader-traits           # служебные ИИ-трейты «характера» лидеров
    python3 find_examples.py --table Units UNIT_ROMAN_LEGION   # строка таблицы по ключу (первый столбец)
    python3 find_examples.py ... --cache <папка Cache>

Кэш содержит всё, что было включено в последней партии, в том числе чужие моды.
Для калибровки баланса опирайся на официальный контент.
"""
import argparse
import platform
import sqlite3
import sys
from pathlib import Path


def default_cache_dir():
    home = Path.home()
    if platform.system() == "Darwin":
        return home / "Library/Application Support/Sid Meier's Civilization VI/Firaxis Games/Sid Meier's Civilization VI/Cache"
    return home / "Documents/My Games/Sid Meier's Civilization VI/Cache"


def connect(cache, name="DebugGameplay.sqlite"):
    path = cache / name
    if not path.is_file():
        sys.exit(f"Не найден {path}. Запусти партию один раз или укажи --cache.")
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def req_set_text(con, set_id, depth=0):
    if not set_id or depth > 2:
        return ""
    row = con.execute("SELECT RequirementSetType FROM RequirementSets WHERE RequirementSetId=?", (set_id,)).fetchone()
    parts = []
    for rid, rtype, inv in con.execute(
            "SELECT r.RequirementId, r.RequirementType, r.Inverse FROM RequirementSetRequirements s "
            "JOIN Requirements r USING(RequirementId) WHERE s.RequirementSetId=?", (set_id,)):
        args = ", ".join(f"{n}={v}" for n, v in con.execute(
            "SELECT Name, Value FROM RequirementArguments WHERE RequirementId=?", (rid,)))
        parts.append(f"{'НЕ ' if inv else ''}{rtype}({args}) [{rid}]")
    joiner = " ИЛИ " if row and row[0] == "REQUIREMENTSET_TEST_ANY" else " И "
    return f"{set_id}: " + joiner.join(parts)


OWNERS = [
    ("TraitModifiers", "TraitType"), ("UnitAbilityModifiers", "UnitAbilityType"), ("BuildingModifiers", "BuildingType"),
    ("PolicyModifiers", "PolicyType"), ("BeliefModifiers", "BeliefType"), ("DistrictModifiers", "DistrictType"),
    ("ImprovementModifiers", "ImprovementType"), ("GreatPersonIndividualActionModifiers", "GreatPersonIndividualType"),
]


def owners_of(con, mid):
    out = []
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table, col in OWNERS:
        if table in tables:
            out += [f"{table}.{v}" for (v,) in con.execute(f'SELECT "{col}" FROM "{table}" WHERE ModifierId=?', (mid,))]
    return out


def show_modifier(con, mid, mtype, subj, owner, run_once, permanent):
    args = ", ".join(f"{n}={v}{'' if t == 'ARGTYPE_IDENTITY' else ' (' + t + ')'}" for n, v, t in con.execute(
        "SELECT Name, Value, Type FROM ModifierArguments WHERE ModifierId=?", (mid,)))
    flags = " ".join(f for f, on in (("RunOnce", run_once), ("Permanent", permanent)) if on)
    print(f"• {mid}  [{mtype}] {flags}")
    if args:
        print(f"    аргументы: {args}")
    for label, rs in (("условие на объект", subj), ("условие на владельца", owner)):
        if rs:
            print(f"    {label}: {req_set_text(con, rs)}")
    who = owners_of(con, mid)
    if who:
        print(f"    используется: {', '.join(who[:4])}")


def search_modifiers(con, kw, limit):
    like = f"%{kw}%"
    dyn = con.execute("SELECT ModifierType, CollectionType, EffectType FROM DynamicModifiers "
                      "WHERE ModifierType LIKE ? OR EffectType LIKE ? LIMIT 30", (like, like)).fetchall()
    if dyn:
        print("Типы модификаторов (ModifierType → коллекция / эффект):")
        for m, c, e in dyn:
            print(f"  {m} → {c} / {e}")
        print()
    rows = con.execute(
        "SELECT m.ModifierId, m.ModifierType, m.SubjectRequirementSetId, m.OwnerRequirementSetId, m.RunOnce, m.Permanent "
        "FROM Modifiers m LEFT JOIN DynamicModifiers d USING(ModifierType) "
        "WHERE m.ModifierType LIKE ? OR m.ModifierId LIKE ? OR d.EffectType LIKE ? "
        "ORDER BY (m.ModifierId LIKE 'TRAIT%') DESC, m.ModifierId LIMIT ?", (like, like, like, limit)).fetchall()
    print(f"Модификаторы ({len(rows)} показано, трейты первыми):")
    for r in rows:
        show_modifier(con, *r)


def search_trait(con, kw, limit):
    for (trait,) in con.execute("SELECT TraitType FROM Traits WHERE TraitType LIKE ? LIMIT ?", (f"%{kw}%", limit)):
        print(f"\n=== {trait}")
        for r in con.execute(
                "SELECT m.ModifierId, m.ModifierType, m.SubjectRequirementSetId, m.OwnerRequirementSetId, m.RunOnce, m.Permanent "
                "FROM TraitModifiers t JOIN Modifiers m USING(ModifierId) WHERE t.TraitType=?", (trait,)):
            show_modifier(con, *r)


def search_req(con, kw):
    rows = con.execute("SELECT Type FROM Types WHERE Kind='KIND_REQUIREMENT' AND Type LIKE ? ORDER BY Type",
                       (f"%{kw}%",)).fetchall()
    for (rtype,) in rows:
        names = [n for (n,) in con.execute(
            "SELECT DISTINCT a.Name FROM Requirements r JOIN RequirementArguments a USING(RequirementId) WHERE r.RequirementType=?",
            (rtype,))]
        ex = con.execute("SELECT RequirementId FROM Requirements WHERE RequirementType=? LIMIT 1", (rtype,)).fetchone()
        print(f"{rtype}  аргументы: {', '.join(names) or '—'}  пример: {ex[0] if ex else '—'}")


def leader_traits(con):
    rows = con.execute(
        "SELECT lt.TraitType, COUNT(*) FROM LeaderTraits lt JOIN Traits t USING(TraitType) "
        "WHERE t.Name IS NULL GROUP BY lt.TraitType ORDER BY 2 DESC").fetchall()
    print("Служебные трейты лидеров (без названия — влияют на поведение ИИ):")
    for t, n in rows:
        print(f"  {t}  (у {n} лидеров)")


def show_table(con, table, key):
    cols = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
    if not cols:
        sys.exit(f"Таблицы {table} нет в этой базе (попробуй --db DebugConfiguration.sqlite)")
    for row in con.execute(f'SELECT * FROM "{table}" WHERE "{cols[0]}" LIKE ? LIMIT 20', (key,)):
        print("\n".join(f"  {c} = {v}" for c, v in zip(cols, row) if v not in (None, "", 0)))
        print()


def main():
    ap = argparse.ArgumentParser(description="Поиск примеров в базе Civilization VI")
    ap.add_argument("keyword", nargs="?")
    ap.add_argument("--trait")
    ap.add_argument("--req")
    ap.add_argument("--leader-traits", action="store_true")
    ap.add_argument("--table", nargs=2, metavar=("TABLE", "KEY"))
    ap.add_argument("--db", default="DebugGameplay.sqlite")
    ap.add_argument("--cache")
    ap.add_argument("--limit", type=int, default=15)
    a = ap.parse_args()
    cache = Path(a.cache).expanduser() if a.cache else default_cache_dir()
    con = connect(cache, a.db)
    if a.trait:
        search_trait(con, a.trait, a.limit)
    elif a.req:
        search_req(con, a.req)
    elif a.leader_traits:
        leader_traits(con)
    elif a.table:
        show_table(con, *a.table)
    elif a.keyword:
        search_modifiers(con, a.keyword, a.limit)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
