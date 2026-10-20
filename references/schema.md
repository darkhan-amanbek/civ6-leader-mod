# Таблицы базы данных

Столбцы сверены с базой игры. `!` — обязательный (NOT NULL без значения по умолчанию). Полную схему любой таблицы можно посмотреть так:
```
sqlite3 "<путь к Cache>/DebugGameplay.sqlite" "select name, type, \"notnull\", dflt_value from pragma_table_info('Leaders');"
```

## Содержание
1. Лидер (минимум)
2. ИИ: повестка и предпочтения
3. Экран выбора (Configuration)
4. Цвета и иконки
5. Новая цивилизация
6. Уникальный юнит
7. Уникальный район / здание / улучшение

---

## 1. Лидер

| Таблица | Столбцы | Зачем |
|---|---|---|
| `Types` | `Type!`, `Kind!` | Регистрация: `LEADER_XYZ`→`KIND_LEADER`, `TRAIT_LEADER_XYZ`→`KIND_TRAIT`, `ABILITY_*`→`KIND_ABILITY`, новый `MODIFIER_*`→`KIND_MODIFIER` |
| `Leaders` | `LeaderType!`, `Name!`, `InheritFrom`, `SceneLayers`, `Sex` (`Male`/`Female`), `OperationList` | Всегда `InheritFrom='LEADER_DEFAULT'`, `SceneLayers=4` |
| `LeaderQuotes` | `LeaderType!`, `Quote!`, `QuoteAudio` | Цитата на экране загрузки |
| `CivilizationLeaders` | `LeaderType!`, `CivilizationType!`, `CapitalName!` | Связь с цивилизацией. `CapitalName` обязателен — `LOC_CITY_NAME_...` (можно существующий, напр. `LOC_CITY_NAME_ROME`) |
| `Traits` | `TraitType!`, `Name`, `Description`, `InternalOnly` | Способность лидера |
| `LeaderTraits` | `LeaderType!`, `TraitType!` | Привязка трейта к лидеру |
| `TraitModifiers` | `TraitType!`, `ModifierId!` | Модификаторы трейта (см. cookbook) |
| `Modifiers`, `ModifierArguments`, `ModifierStrings`, `Requirement*` | | см. `modifiers-cookbook.md` |
| `LoadingInfo` | `LeaderType!`, `ForegroundImage`, `BackgroundImage`, `EraText`, `LeaderText`, `PlayDawnOfManAudio` | Необязательно: 2D-экран загрузки |
| `DiplomacyInfo` | `Type!`, `BackgroundImage` | Необязательно: фон диплом-экрана |

**ИИ-трейты-«характер».** У официальных лидеров в `LeaderTraits` кроме основной способности стоят служебные трейты, влияющие на поведение ИИ: `TRAIT_LEADER_EXPANSIONIST`, `TRAIT_LEADER_AGGRESSIVE_MILITARY`, `TRAIT_LEADER_LOW_RELIGIOUS_PREFERENCE` и т.п. Найти все: `python3 scripts/find_examples.py --leader-traits`. Один-два таких трейта сильно улучшают игру ИИ вашим лидером.

## 2. ИИ: повестка и предпочтения

| Таблица | Столбцы | Зачем |
|---|---|---|
| `Agendas` | `AgendaType!`, `Name!`, `Description!` | Историческая повестка (что лидер любит/не любит) |
| `HistoricalAgendas` | `LeaderType!`, `AgendaType!` | Привязка |
| `ExclusiveAgendas` | `AgendaOne!`, `AgendaTwo!` | Какие случайные повестки не выпадут вместе с этой |
| `AgendaTraits` | `AgendaType!`, `TraitType!` | Повестка реализуется через трейт (тоже в `Types` как `KIND_TRAIT` и в `Traits`) |
| `AiListTypes` | `ListType!` | Объявить список |
| `AiLists` | `ListType!`, `LeaderType` (**это TraitType!**), `AgendaType`, `System!` | `System`: `Technologies`, `Civics`, `Buildings` (чудеса), `Units`, `PseudoYields`, `Yields`, `Districts`... |
| `AiFavoredItems` | `ListType`, `Item!`, `Favored`, `Value` | Что предпочитать |

Повестка «любит/не любит» строится на `MODIFIER_PLAYER_DIPLOMACY_SIMPLE_MODIFIER` с аргументами `InitialValue` (±), `StatementKey`, `SimpleModifierDescription` и условием (`SubjectRequirementSetId`). Самый простой путь — **переиспользовать существующую повестку** (`AGENDA_...` из базы) через `HistoricalAgendas`, а не писать свою.

## 3. Экран выбора (Configuration, FrontEnd)

`Players`: `Domain`, `CivilizationType`, `LeaderType`, `LeaderName`, `LeaderIcon`, `CivilizationName`, `CivilizationIcon`, `LeaderAbilityName`, `LeaderAbilityDescription`, `LeaderAbilityIcon`, `CivilizationAbilityName`, `CivilizationAbilityDescription`, `CivilizationAbilityIcon`, `Portrait`, `PortraitBackground`, `PlayerColor`, `HumanPlayable`, `SortIndex`.

`PlayerItems` (уникальные юниты/районы на карточке выбора): `Domain`, `CivilizationType`, `LeaderType`, `Type`, `Icon`, `Name`, `Description`, `SortIndex`.

Для лидера существующей цивы `Civilization*`-поля и `PlayerItems` копируются со значений этой цивы (у Рима: `LOC_CIVILIZATION_ROME_NAME`, `ICON_CIVILIZATION_ROME`, `LOC_TRAIT_CIVILIZATION_ALL_ROADS_TO_ROME_*`, юнит `UNIT_ROMAN_LEGION`, район `DISTRICT_BATH`). Посмотреть строки официального лидера:
```
sqlite3 "<Cache>/DebugConfiguration.sqlite" "select * from Players where LeaderType='LEADER_TRAJAN';"
```

## 4. Цвета и иконки

- `PlayerColors`: `Type` (= `LEADER_XYZ`), `Usage` (`Unique`), `PrimaryColor`, `SecondaryColor`, `Alt1..3PrimaryColor/SecondaryColor`. Готовые цвета: `COLOR_STANDARD_{RED,ORANGE,YELLOW,GREEN,AQUA,BLUE,PURPLE,MAGENTA,WHITE}_{DK,MD,LT}` (список — `Base/Assets/UI/Colors/PlayerStandardColors.xml` в файлах игры; валидатор цвета не проверяет — у них отдельная база). Свои цвета объявляются в `Colors` (`Type`, `Color` = `"R,G,B,A"` 0–255, как в `Colors.xml` игры).
- `IconTextureAtlases`: `Name`, `IconSize`, `IconsPerRow`, `IconsPerColumn`, `Filename`. `IconDefinitions`: `Name`, `Atlas`, `Index`. См. оговорки про `.dds` в `mod-structure.md` §8.

## 5. Новая цивилизация

Добавь к разделу 1:
- `Types`: `CIVILIZATION_XYZ`→`KIND_CIVILIZATION`, `TRAIT_CIVILIZATION_XYZ`→`KIND_TRAIT`.
- `Civilizations`: `CivilizationType`, `Name`, `Description`, `Adjective`, `StartingCivilizationLevelType='CIVILIZATION_LEVEL_FULL_CIV'`, `RandomCityNameDepth`, `Ethnicity` (`ETHNICITY_EURO`/`ASIAN`/`AFRICAN`/`MEDIT`/`SOUTHAM` — от него внешний вид юнитов и городов).
- `CivilizationTraits` (`CivilizationType`, `TraitType`).
- `CityNames` (`CivilizationType`, `CityName`) — 10+ городов.
- `CivilizationCitizenNames` (`CivilizationType`, `CitizenName`, `Female`, `Modern`) — необязательно.
- `StartBiasTerrains` / `StartBiasFeatures` / `StartBiasRivers` / `StartBiasResources` (`CivilizationType`, `...Type`, `Tier` 1–5) — где стартовать. Сильный старт-биас (река + холмы) — тоже часть баланса.
- Уникальные юнит и инфраструктура привязываются к **трейту цивилизации** (`TraitType` в строке юнита/района/здания).

## 6. Уникальный юнит

**Сначала проверь слот.** У цивилизации уже может быть уникальный юнит на эту роль (у Греции Гоплит заменяет Копейщика). Посмотри: `python3 scripts/find_examples.py --table UnitReplaces UNIT_%` или `sqlite3 ... "select * from UnitReplaces"`. Варианты: выбрать другой базовый юнит (другая эпоха/класс) или сделать «личный» юнит лидера, заменяющий уникальный юнит цивы (цепочка «уникальный → уникальный» официально не встречается — проверь в игре, что лидер видит только свой юнит, а другие лидеры цивы — свой).

1. `Types`: `UNIT_XYZ`→`KIND_UNIT`; трейт-«ключ» `TRAIT_CIVILIZATION_UNIT_XYZ`→`KIND_TRAIT` + строка в `Traits` + `CivilizationTraits` (или `LeaderTraits` для «личного» юнита лидера).
2. `Units`: удобнее всего **скопировать строку заменяемого юнита** и поменять поля:
   ```sql
   INSERT INTO Units (UnitType, Name, Description, TraitType, BaseSightRange, BaseMoves, Combat, RangedCombat, Range, Bombard,
                      Domain, FormationClass, Cost, PromotionClass, PrereqTech, PurchaseYield, StrategicResource, Maintenance,
                      AdvisorType, ZoneOfControl, CostProgressionModel, CostProgressionParam1, MandatoryObsoleteTech)
   SELECT 'UNIT_XYZ', 'LOC_UNIT_XYZ_NAME', 'LOC_UNIT_XYZ_DESCRIPTION', 'TRAIT_CIVILIZATION_UNIT_XYZ', BaseSightRange, BaseMoves,
          Combat + 4, RangedCombat, Range, Bombard, Domain, FormationClass, Cost, PromotionClass, PrereqTech, PurchaseYield,
          StrategicResource, Maintenance, AdvisorType, ZoneOfControl, CostProgressionModel, CostProgressionParam1, MandatoryObsoleteTech
   FROM Units WHERE UnitType = 'UNIT_SWORDSMAN';
   ```
3. `UnitReplaces` (`CivUniqueUnitType`, `ReplacesUnitType`).
4. `UnitUpgrades` (`Unit`, `UpgradeUnit`) — во что улучшается; и строка, чтобы заменяемый юнит предыдущей эпохи улучшался в него (обычно наследуется через `UnitReplaces`).
5. `TypeTags` (`Type`, `Tag`) — **скопируй теги заменяемого** (`CLASS_MELEE` и т.д.), иначе юнит не получит способности/бонусы класса:
   ```sql
   INSERT INTO TypeTags (Type, Tag) SELECT 'UNIT_XYZ', Tag FROM TypeTags WHERE Type = 'UNIT_SWORDSMAN';
   ```
6. `UnitAiInfos` (`UnitType`, `AiType`) — так же скопируй, иначе ИИ не поймёт, как им воевать.
7. Графика юнита: без арта (`.artdef` + `.dep` через `UpdateArt`) новый `UNIT_...` может быть **невидим на карте** — это первое, что надо проверить в партии. Готового минимального рецепта арта без Asset Editor в этом скилле нет; честно предупреждай пользователя. Если невидимость неприемлема — вместо нового юнита дай бонус существующему через способность (раздел 4 cookbook): визуально это обычный юнит, но с уникальной силой. Баланс-ориентир — `balance.md`, таблица уникальных юнитов.

## 7. Уникальный район / здание / улучшение

- **Район**: `Types` (`KIND_DISTRICT`), `Districts` (скопировать строку заменяемого, `Cost` — вдвое меньше, `TraitType`), `DistrictReplaces`, `District_Adjacencies` (+ `Adjacency_YieldChanges` для новых правил смежности), `District_GreatPersonPoints`, `District_TradeRouteYields`, `District_CitizenYieldChanges`.
- **Здание**: `Types` (`KIND_BUILDING`), `Buildings` (копия заменяемого, цена та же, `TraitType`), `BuildingReplaces`, `Building_YieldChanges`, `Building_GreatPersonPoints`, `BuildingPrereqs`.
- **Улучшение**: `Types` (`KIND_IMPROVEMENT`), `Improvements` (`TraitType`, `PrereqTech`/`PrereqCivic`, `Buildable=1`), `Improvement_ValidTerrains`/`_ValidFeatures`/`_ValidResources`, `Improvement_YieldChanges`, `Improvement_Adjacencies`, `Improvement_ValidBuildUnits` (`UNIT_BUILDER`).

Для любого из них сначала посмотри, как устроен официальный аналог:
```
python3 scripts/find_examples.py --table Districts DISTRICT_BATH
```
