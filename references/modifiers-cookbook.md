# Рецепты модификаторов

Все `ModifierType`, `RequirementType` и имена аргументов ниже проверены по базе данных игры (базовый ruleset). Префикс `XYZ` замени на свой.

## Содержание
1. Как устроена цепочка
2. Доходы (города, районы, клетки)
3. Производство (районы, чудеса, юниты, здания)
4. Сила юнитов с условием (через способность юнита)
5. Единовременные выплаты
6. Наука/культура: эврики, политики
7. Требования (условия) — справочник
8. Как найти рецепт, которого здесь нет

---

## 1. Цепочка

```
LeaderTraits ──► Traits ──► TraitModifiers ──► Modifiers ──► ModifierArguments
                                                  │
                                                  ├─ ModifierType ──► DynamicModifiers (CollectionType + EffectType)
                                                  └─ SubjectRequirementSetId ──► RequirementSets ──► RequirementSetRequirements ──► Requirements ──► RequirementArguments
```

- `CollectionType` — **к кому** применяется (все города игрока, все юниты, все районы, сам игрок).
- `EffectType` — **что** делается. Зашит в движок, новые создать нельзя.
- `SubjectRequirementSetId` — **условие** для каждого объекта коллекции (каждого города/юнита/клетки).
- `OwnerRequirementSetId` — условие на владельца (игрока) целиком.
- Флаги `Modifiers`: `RunOnce` (сработать один раз), `Permanent` (не снимать, если условие перестало выполняться), `OwnerStackLimit`/`SubjectStackLimit` (ограничить суммирование).

Трейт лидера применяется **на уровне игрока**: используй `MODIFIER_PLAYER_*`. Если нужен эффект «на город» или «на юнит», бери `MODIFIER_PLAYER_CITIES_*` / `MODIFIER_PLAYER_UNITS_*` или обёртку `..._ATTACH_MODIFIER` / `..._GRANT_ABILITY`.

Каркас любого рецепта:

```sql
INSERT INTO TraitModifiers (TraitType, ModifierId) VALUES
  ('TRAIT_LEADER_XYZ', 'XYZ_MY_EFFECT');

INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId) VALUES
  ('XYZ_MY_EFFECT', 'MODIFIER_...', NULL);

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
  ('XYZ_MY_EFFECT', 'Amount', '2');
```

## 2. Доходы

### 2.1 Плоский доход в каждом городе
`MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE` — аргументы `YieldType`, `Amount`.
```sql
INSERT INTO Modifiers (ModifierId, ModifierType) VALUES ('XYZ_CITY_FAITH', 'MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE');
INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
  ('XYZ_CITY_FAITH', 'YieldType', 'YIELD_FAITH'),
  ('XYZ_CITY_FAITH', 'Amount',    '1');
```
⚠ Масштабируется с числом городов и работает с 1-го хода — держи `Amount` 1–2 и добавляй условие.

### 2.2 Процент к доходу в городах
`MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_MODIFIER` — `YieldType`, `Amount` (в процентах). Официально: +10% всех доходов на домашнем континенте и −15% на чужом (с условием на континент).

### 2.3 Доход с района определённого типа
`MODIFIER_PLAYER_DISTRICTS_ADJUST_YIELD_CHANGE` — `YieldType`, `Amount`; тип района задаётся условием `REQUIREMENT_DISTRICT_TYPE_MATCHES` (аргумент `DistrictType`). Официально: +2…+3 веры с района.
```sql
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId) VALUES
  ('XYZ_CAMPUS_SCIENCE', 'MODIFIER_PLAYER_DISTRICTS_ADJUST_YIELD_CHANGE', 'XYZ_DISTRICT_IS_CAMPUS');
INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
  ('XYZ_CAMPUS_SCIENCE', 'YieldType', 'YIELD_SCIENCE'),
  ('XYZ_CAMPUS_SCIENCE', 'Amount',    '2');

INSERT INTO RequirementSets (RequirementSetId, RequirementSetType) VALUES ('XYZ_DISTRICT_IS_CAMPUS', 'REQUIREMENTSET_TEST_ALL');
INSERT INTO Requirements (RequirementId, RequirementType) VALUES ('XYZ_REQ_DISTRICT_IS_CAMPUS', 'REQUIREMENT_DISTRICT_TYPE_MATCHES');
INSERT INTO RequirementArguments (RequirementId, Name, Value) VALUES ('XYZ_REQ_DISTRICT_IS_CAMPUS', 'DistrictType', 'DISTRICT_CAMPUS');
INSERT INTO RequirementSetRequirements (RequirementSetId, RequirementId) VALUES ('XYZ_DISTRICT_IS_CAMPUS', 'XYZ_REQ_DISTRICT_IS_CAMPUS');
```

### 2.4 Доход с клеток (местность, особенность, улучшение, ресурс)
`MODIFIER_PLAYER_ADJUST_PLOT_YIELD` — `YieldType`, `Amount`; какие клетки — условием:
- `REQUIREMENT_PLOT_TERRAIN_TYPE_MATCHES` (`TerrainType`, напр. `TERRAIN_TUNDRA`, `TERRAIN_GRASS_HILLS`)
- `REQUIREMENT_PLOT_FEATURE_TYPE_MATCHES` (`FeatureType`, напр. `FEATURE_FOREST`)
- `REQUIREMENT_PLOT_IMPROVEMENT_TYPE_MATCHES` (`ImprovementType`, напр. `IMPROVEMENT_MINE`)
- `REQUIREMENT_PLOT_RESOURCE_TYPE_MATCHES` (`ResourceType`)
- `REQUIREMENT_PLOT_IS_HILLS`, `REQUIREMENT_PLOT_ADJACENT_TO_RIVER`, `REQUIREMENT_PLOT_IS_COASTAL_LAND` (без аргументов)

Официально: Россия +1 веры и +1 производства с тундры. Доход виден в интерфейсе, только если клетка принадлежит игроку.

## 3. Производство

| Цель | ModifierType | Аргументы | Официальный пример |
|---|---|---|---|
| Районы определённого типа | `MODIFIER_PLAYER_CITIES_ADJUST_DISTRICT_PRODUCTION` | `DistrictType`, `Amount` (%) | Ходзё: +100% к Лагерю/Святому месту/Театру |
| Чудеса | `MODIFIER_PLAYER_CITIES_ADJUST_WONDER_PRODUCTION` | `Amount` (%) | Франция: +20% (с условием на эпоху) |
| Класс юнитов в эпоху | `MODIFIER_PLAYER_CITIES_ADJUST_UNIT_TAG_ERA_PRODUCTION` | `UnitPromotionClass`, `EraType`, `Amount` (%) | Харальд: +50% морским ближнего боя |
| Конкретное здание/здания района | `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_PRODUCTION` | `BuildingType` или `DistrictType`, `Amount` (%) | Ацтеки: +20% к Уэй-Теокалли |

```sql
INSERT INTO Modifiers (ModifierId, ModifierType) VALUES ('XYZ_CAMPUS_PRODUCTION', 'MODIFIER_PLAYER_CITIES_ADJUST_DISTRICT_PRODUCTION');
INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
  ('XYZ_CAMPUS_PRODUCTION', 'DistrictType', 'DISTRICT_CAMPUS'),
  ('XYZ_CAMPUS_PRODUCTION', 'Amount',       '50');
```

## 4. Сила юнитов с условием

Боевые бонусы делаются **способностью юнита** (её видно в окне предпросмотра боя). Схема: трейт → `MODIFIER_PLAYER_UNITS_GRANT_ABILITY` → способность → `MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH` с условием. Так сделан Тедди (+5 на домашнем континенте).

```sql
-- 1) Способность и какие классы юнитов её получают
INSERT INTO Types (Type, Kind) VALUES ('ABILITY_XYZ_HOME_DEFENSE', 'KIND_ABILITY');
INSERT INTO TypeTags (Type, Tag) VALUES
  ('ABILITY_XYZ_HOME_DEFENSE', 'CLASS_MELEE'),
  ('ABILITY_XYZ_HOME_DEFENSE', 'CLASS_RANGED'),
  ('ABILITY_XYZ_HOME_DEFENSE', 'CLASS_ANTI_CAVALRY');
INSERT INTO UnitAbilities (UnitAbilityType, Name, Description, Inactive) VALUES
  ('ABILITY_XYZ_HOME_DEFENSE', 'LOC_ABILITY_XYZ_HOME_DEFENSE_NAME', 'LOC_ABILITY_XYZ_HOME_DEFENSE_DESCRIPTION', 1);

-- 2) Сам бонус силы с условием «на своей территории»
INSERT INTO UnitAbilityModifiers (UnitAbilityType, ModifierId) VALUES ('ABILITY_XYZ_HOME_DEFENSE', 'XYZ_HOME_DEFENSE_STRENGTH');
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId) VALUES
  ('XYZ_HOME_DEFENSE_STRENGTH', 'MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH', 'XYZ_UNIT_IN_OWN_TERRITORY');
INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES ('XYZ_HOME_DEFENSE_STRENGTH', 'Amount', '4');
INSERT INTO ModifierStrings (ModifierId, Context, Text) VALUES
  ('XYZ_HOME_DEFENSE_STRENGTH', 'Preview', 'LOC_ABILITY_XYZ_HOME_DEFENSE_PREVIEW');  -- строка в предпросмотре боя

INSERT INTO RequirementSets (RequirementSetId, RequirementSetType) VALUES ('XYZ_UNIT_IN_OWN_TERRITORY', 'REQUIREMENTSET_TEST_ALL');
INSERT INTO RequirementSetRequirements (RequirementSetId, RequirementId) VALUES
  ('XYZ_UNIT_IN_OWN_TERRITORY', 'UNIT_IN_OWNER_TERRITORY_REQUIREMENT');  -- существующее требование игры

-- 3) Трейт выдаёт способность всем юнитам игрока
INSERT INTO Modifiers (ModifierId, ModifierType) VALUES ('XYZ_GRANT_HOME_DEFENSE', 'MODIFIER_PLAYER_UNITS_GRANT_ABILITY');
INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES ('XYZ_GRANT_HOME_DEFENSE', 'AbilityType', 'ABILITY_XYZ_HOME_DEFENSE');
INSERT INTO TraitModifiers (TraitType, ModifierId) VALUES ('TRAIT_LEADER_XYZ', 'XYZ_GRANT_HOME_DEFENSE');
```
Текст `..._PREVIEW` пишут так же, как у Тедди: `+4 [ICON_Strength] Сила на своей территории.` (число прямо в тексте — меняешь `Amount`, меняй и текст).

Полезные условия для боя: `REQUIREMENT_PLAYER_IS_ATTACKING` (только при атаке), `REQUIREMENT_UNIT_IN_OWNER_TERRITORY`, `REQUIREMENT_UNIT_IN_ENEMY_TERRITORY`, `REQUIREMENT_UNIT_ON_HOME_CONTINENT`, `REQUIREMENT_OPPONENT_IS_DISTRICT` (против городов), `REQUIREMENT_PLOT_ADJACENT_FRIENDLY_UNIT_TAG_MATCHES` (рядом с союзным юнитом класса).

Другие эффекты юнитов: `MODIFIER_PLAYER_UNITS_ADJUST_MOVEMENT` (+ходы), `MODIFIER_PLAYER_UNITS_ADJUST_BUILDER_CHARGES` (`Amount` — Цинь: +1 заряд).

## 5. Единовременные выплаты

`MODIFIER_PLAYER_GRANT_YIELD` — `YieldType`, `Amount`; ставь `RunOnce=1`, `Permanent=1` и **`Type='ScaleByGameSpeed'`** у `Amount`:
```sql
INSERT INTO Modifiers (ModifierId, ModifierType, RunOnce, Permanent) VALUES ('XYZ_GOLD_GRANT', 'MODIFIER_PLAYER_GRANT_YIELD', 1, 1);
INSERT INTO ModifierArguments (ModifierId, Name, Type, Value) VALUES
  ('XYZ_GOLD_GRANT', 'YieldType', 'ARGTYPE_IDENTITY', 'YIELD_GOLD'),
  ('XYZ_GOLD_GRANT', 'Amount',    'ScaleByGameSpeed', '100');
```
Чтобы выплата срабатывала на событие (захват города), её оборачивают: Цезарь использует `MODIFIER_PLAYER_CAPTURED_CITY_ATTACH_MODIFIER` с аргументом `ModifierId` = выплата.

## 6. Наука, культура, политики

| Эффект | ModifierType | Аргументы | Пример |
|---|---|---|---|
| Эврики сильнее | `MODIFIER_PLAYER_ADJUST_TECHNOLOGY_BOOST` | `Amount` (+% к 50%) | Китай: `10` → 60% |
| Озарения сильнее | `MODIFIER_PLAYER_ADJUST_CIVIC_BOOST` | `Amount` | Китай |
| Случайная эврика за эпоху | `MODIFIER_PLAYER_GRANT_RANDOM_TECHNOLOGY_BOOST_ON_NEW_ERA` | `Amount` | ГГ Сеул: 1 (в игре — бонус сюзерену; как трейт лидера проверь в партии, что срабатывает при входе в эпоху, а не на старте) |
| Случайные эврики разово | `MODIFIER_PLAYER_GRANT_RANDOM_TECHNOLOGY_BOOST_BY_ERA` | `Amount`, `StartEraType`, `EndEraType` | Великие учёные |
| Доп. слот политики | `MODIFIER_PLAYER_CULTURE_ADJUST_GOVERNMENT_SLOTS_MODIFIER` | `GovernmentSlotType` (`SLOT_MILITARY`/`SLOT_ECONOMIC`/`SLOT_DIPLOMATIC`/`SLOT_WILDCARD`) | Барбаросса: военный; Греция: джокер |
| Очки великих людей | `MODIFIER_PLAYER_ADJUST_GREAT_PERSON_POINTS` | `GreatPersonClassType`, `Amount` | |
| Международные торговые пути | `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_FOR_INTERNATIONAL` | `YieldType`, `Amount`, `Intercontinental` | Португалия-подобные бонусы |

## 7. Требования — справочник

| RequirementType | Аргументы | Для чего |
|---|---|---|
| `REQUIREMENT_PLAYER_HAS_TECHNOLOGY` | `TechnologyType` | Открыть бонус с технологии (сдвиг во времени) |
| `REQUIREMENT_PLAYER_HAS_CIVIC` | `CivicType` | То же с цивиком |
| `REQUIREMENT_CITY_HAS_DISTRICT` | `DistrictType`, `MustBeFunctioning` | Город с районом |
| `REQUIREMENT_CITY_HAS_BUILDING` | `BuildingType` | Город со зданием |
| `REQUIREMENT_DISTRICT_TYPE_MATCHES` | `DistrictType` | Для коллекции районов |
| `REQUIREMENT_UNIT_TAG_MATCHES` | `Tag` | Юнит определённого класса |
| `REQUIREMENT_PLOT_*` | см. раздел 2.4 | Клетки |
| `REQUIREMENT_REQUIREMENTSET_IS_MET` | `RequirementSetId` | Вложенное условие |

У `Requirements` есть флаг `Inverse=1` — «НЕ». `RequirementSetType`: `REQUIREMENTSET_TEST_ALL` (И) или `REQUIREMENTSET_TEST_ANY` (ИЛИ).

Существующие требования игры можно переиспользовать по `RequirementId` (как `UNIT_IN_OWNER_TERRITORY_REQUIREMENT` выше) — меньше кода и меньше ошибок.

## 8. Рецепта нет?

```
python3 scripts/find_examples.py GOLD_DISPERSAL        # по ModifierType / EffectType / ModifierId
python3 scripts/find_examples.py --trait TRAIT_LEADER_  # все модификаторы трейтов лидеров
python3 scripts/find_examples.py --req ADJACENT        # типы требований
```
Скрипт читает кэш базы игры (появляется после первого запуска партии). Кэш содержит то, что было включено в последней партии, в том числе чужие моды — для калибровки баланса опирайся на официальный контент (идентификаторы без префиксов модов).
