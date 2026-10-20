# Структура мода и .modinfo

## Содержание
1. Где лежат моды, логи и кэш
2. Папка мода
3. .modinfo — разбор по частям
4. FrontEnd и InGame: что куда
5. Базовая игра и дополнения (Criteria)
6. Форматы файлов: SQL и XML
7. LoadOrder — когда меняешь чужой контент
8. Графика: что реально без инструментов Firaxis

---

## 1. Пути

| | macOS | Windows |
|---|---|---|
| Моды | `~/Library/Application Support/Sid Meier's Civilization VI/Sid Meier's Civilization VI/Mods/` | `Documents\My Games\Sid Meier's Civilization VI\Mods\` |
| Логи | `~/Library/Application Support/Sid Meier's Civilization VI/Firaxis Games/Sid Meier's Civilization VI/Logs/` | `Documents\My Games\Sid Meier's Civilization VI\Logs\` |
| Кэш БД | `.../Firaxis Games/Sid Meier's Civilization VI/Cache/` (`DebugGameplay.sqlite`, `DebugConfiguration.sqlite`, `DebugLocalization.sqlite`) | `Documents\My Games\Sid Meier's Civilization VI\Cache\` |
| Файлы игры (образцы) | `~/Library/Application Support/Steam/steamapps/common/Sid Meier's Civilization VI/Civ6.app/Contents/Assets/` | `...\steamapps\common\Sid Meier's Civilization VI\` |

Лучшие образцы в файлах игры: `DLC/JuliusCaesar/` (новый лидер для существующей цивы), `Base/Assets/Gameplay/Data/Leaders.xml`, `Modifiers.xml`, `Civilizations.xml`. Их полезно **читать**, но не копировать целиком в свой мод.

Кэш БД — это собранная база последней запущенной партии. Её удобно читать через `sqlite3` или `scripts/find_examples.py`: видно реальные таблицы, столбцы и значения.

## 2. Папка мода

```
MyLeader/
├── MyLeader.modinfo          # манифест: что, когда и куда загружать
├── Data/
│   ├── Leader.sql            # лидер, трейт, модификаторы, повестка, ИИ   (InGame)
│   ├── Config.sql            # строки экрана выбора лидера                (FrontEnd)
│   ├── Colors.xml            # цвета игрока                               (оба)
│   └── Expansion2.sql        # (необязательно) только для Gathering Storm  (InGame + Criteria)
└── Text/
    └── Text.xml              # все LOC_* на en_US и ru_RU                 (оба)
```

Имя папки может быть любым; игра находит мод по файлу `.modinfo`.

## 3. .modinfo

```xml
<?xml version="1.0" encoding="utf-8"?>
<Mod id="СВОЙ-GUID" version="1">
  <Properties>
    <Name>LOC_MOD_XYZ_NAME</Name>              <!-- или просто текст -->
    <Description>LOC_MOD_XYZ_DESCRIPTION</Description>
    <Teaser>Короткое описание</Teaser>
    <Authors>Ник</Authors>
    <AffectsSavedGames>1</AffectsSavedGames>  <!-- геймплейный мод: 1 -->
    <CompatibleVersions>1.2,2.0</CompatibleVersions>
  </Properties>

  <ActionCriteria>
    <Criteria id="XYZ_Expansion2">
      <RuleSetInUse>RULESET_EXPANSION_2</RuleSetInUse>
    </Criteria>
  </ActionCriteria>

  <FrontEndActions>
    <UpdateDatabase id="XYZ_Config"><File>Data/Config.sql</File></UpdateDatabase>
    <UpdateColors   id="XYZ_Colors_FE"><File>Data/Colors.xml</File></UpdateColors>
    <UpdateText     id="XYZ_Text_FE"><File>Text/Text.xml</File></UpdateText>
  </FrontEndActions>

  <InGameActions>
    <UpdateDatabase id="XYZ_Gameplay"><File>Data/Leader.sql</File></UpdateDatabase>
    <UpdateDatabase id="XYZ_Gameplay_XP2" criteria="XYZ_Expansion2"><File>Data/Expansion2.sql</File></UpdateDatabase>
    <UpdateColors   id="XYZ_Colors"><File>Data/Colors.xml</File></UpdateColors>
    <UpdateText     id="XYZ_Text"><File>Text/Text.xml</File></UpdateText>
  </InGameActions>

  <Files>
    <File>Data/Config.sql</File>
    <File>Data/Leader.sql</File>
    <File>Data/Expansion2.sql</File>
    <File>Data/Colors.xml</File>
    <File>Text/Text.xml</File>
  </Files>
</Mod>
```

Правила:
- `id` — **уникальный GUID** (`python3 -c "import uuid; print(uuid.uuid4())"`). Не копируй чужой.
- `id` у каждого действия уникален внутри мода.
- Каждый файл из действий — также в `<Files>`. Лишний или отсутствующий файл = мод молча не грузит часть контента.
- `AffectsSavedGames=1` — мод сохраняется в сейве и обязателен для его загрузки (так и нужно для геймплея).
- Если мод **требует** дополнение — добавь `<Dependencies><Mod id="4873eb62-8ccc-4574-b784-dda455e74e68" title="Expansion2"/></Dependencies>` (Rise & Fall: `1B28771A-C749-434B-9053-D1380C553DE9`). Лучше — не требовать, а грузить доп. файлы через Criteria.

Типы действий: `UpdateDatabase` (SQL/XML в БД), `UpdateText` (локализация), `UpdateIcons` (атласы иконок), `UpdateColors` (цвета), `UpdateArt` (`.dep`-файл с артом), `ImportFiles` (сырые файлы), `AddGameplayScripts` (Lua, InGame).

## 4. FrontEnd и InGame

| Что | Где | Таблицы |
|---|---|---|
| Экран выбора лидера | **FrontEnd** `UpdateDatabase` (база Configuration) | `Players`, `PlayerItems` |
| Геймплей | **InGame** `UpdateDatabase` (база Gameplay) | `Leaders`, `Traits`, `Modifiers`, ... |
| Тексты | **оба** `UpdateText` | `LocalizedText` |
| Цвета, иконки | **оба** | `Colors`/`PlayerColors`, `IconTextureAtlases`/`IconDefinitions` |

Самая частая ошибка: строки `Players` положили в InGame — лидера нет в списке выбора.

## 5. Базовая игра и дополнения

- В `Players`/`PlayerItems` нужна строка **на каждый ruleset**, где лидер должен быть доступен, — столбец `Domain`: `Players:StandardPlayers` (базовая игра), `Players:Expansion1_Players` (Rise & Fall), `Players:Expansion2_Players` (Gathering Storm).
- Геймплей, который работает везде, — в общий файл. Всё, что использует механики дополнений (губернаторы, лояльность, эпохи, гнев, дипломатическая победа), — в отдельный файл с `criteria`, как у DLC Юлия Цезаря: `RuleSetInUse` = `RULESET_EXPANSION_1` / `RULESET_EXPANSION_2`.
- Ссылка в базовой игре на тип, которого нет (например, `GOVERNOR_...`), даст ошибку внешнего ключа в `Database.log` и мод не загрузится.

## 6. Форматы

**SQL** (удобнее для больших вставок):
```sql
INSERT INTO Types (Type, Kind) VALUES ('LEADER_XYZ', 'KIND_LEADER');
UPDATE Units SET Combat = 40 WHERE UnitType = 'UNIT_XYZ_LEGION';
DELETE FROM LeaderTraits WHERE LeaderType = 'LEADER_XYZ' AND TraitType = 'TRAIT_LEADER_AGGRESSIVE_MILITARY';
```

**XML** (так пишет Firaxis):
```xml
<GameInfo>          <!-- для текста — <GameData> или <GameInfo>, оба работают -->
  <Types>
    <Row Type="LEADER_XYZ" Kind="KIND_LEADER"/>
  </Types>
  <ModifierArguments>
    <Row>
      <ModifierId>XYZ_GOLD</ModifierId>
      <Name>Amount</Name>
      <Value>100</Value>
      <Type>ScaleByGameSpeed</Type>
    </Row>
  </ModifierArguments>
  <Units>
    <Update><Where UnitType="UNIT_XYZ"/><Set Combat="40"/></Update>
  </Units>
  <LeaderTraits>
    <Delete LeaderType="LEADER_XYZ"/>
  </LeaderTraits>
</GameInfo>
```
`<Replace>` вместо `<Row>` — вставить или заменить.

**Текст:**
```xml
<GameData>
  <LocalizedText>
    <Row Tag="LOC_LEADER_XYZ_NAME" Language="en_US"><Text>Name</Text></Row>
    <Row Tag="LOC_LEADER_XYZ_NAME" Language="ru_RU"><Text>Имя</Text></Row>
  </LocalizedText>
</GameData>
```
Без строки `en_US` в английском клиенте увидят голый `LOC_...`. Иконки в тексте: `[ICON_Strength]`, `[ICON_Science]`, `[ICON_Production]`, `[ICON_Gold]`, `[ICON_Culture]`, `[ICON_Faith]`, `[ICON_Food]`, `[NEWLINE]`.

## 7. LoadOrder

Если мод **меняет** существующий контент (не только добавляет), он должен грузиться после него:
```xml
<UpdateDatabase id="XYZ_Changes">
  <Properties><LoadOrder>100</LoadOrder></Properties>
  <File>Data/Changes.sql</File>
</UpdateDatabase>
```
Для изменений поверх дополнений нужен больший `LoadOrder` и criteria на ruleset.

## 8. Графика

- **3D-лидер с анимацией** — недостижимо без Asset Editor/ModBuddy (только Windows) и исходных моделей. Не обещай.
- **Иконки** (`IconTextureAtlases` + `IconDefinitions`, размеры 32/45/48/50/64/80/256, формат `.dds`): официальный путь — «приготовить» текстуры в ModBuddy. Загрузка «сырых» `.dds` через `ImportFiles` встречается в модах сообщества, но **не гарантирована** — проверяй в игре. Надёжный путь без инструментов: переиспользовать существующую иконку (`ICON_LEADER_TRAJAN`, иконку цивилизации и т.п.).
- **Экран загрузки и дипломатии**: таблицы `LoadingInfo` (`ForegroundImage`, `BackgroundImage`) и `DiplomacyInfo` (`BackgroundImage`) — для 2D-изображений. Без своих картинок диплом-экран лидера будет пустым фоном — это не ошибка, игра работает.
- Аудио-реплики лидера — без инструментов Wwise недостижимо; `LeaderQuotes.QuoteAudio` можно не заполнять.
