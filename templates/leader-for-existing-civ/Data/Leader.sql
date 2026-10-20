-- ===========================================================================
-- Лидер: Марк Агриппа (Рим) — шаблон
-- Способность «Curator Aquarum»:
--   1) Сухопутные юниты ближнего/дальнего боя и противоконные: +4 силы на своей территории.
--   2) Каждый район «Бани» (уникальный акведук Рима) даёт +2 производства.
-- Баланс-карточка — в README шаблона.
-- ===========================================================================

-- 1. Типы
INSERT INTO Types (Type, Kind) VALUES
    ('LEADER_EXAMPLE_AGRIPPA',          'KIND_LEADER'),
    ('TRAIT_LEADER_EXAMPLE_AGRIPPA',    'KIND_TRAIT'),
    ('ABILITY_EXAMPLE_AGRIPPA_DEFENSE', 'KIND_ABILITY');

-- 2. Лидер
INSERT INTO Leaders (LeaderType, Name, InheritFrom, SceneLayers, Sex) VALUES
    ('LEADER_EXAMPLE_AGRIPPA', 'LOC_LEADER_EXAMPLE_AGRIPPA_NAME', 'LEADER_DEFAULT', 4, 'Male');

INSERT INTO LeaderQuotes (LeaderType, Quote) VALUES
    ('LEADER_EXAMPLE_AGRIPPA', 'LOC_LEADER_EXAMPLE_AGRIPPA_QUOTE');

-- CapitalName обязателен; для существующей цивы берём её столицу
INSERT INTO CivilizationLeaders (CivilizationType, LeaderType, CapitalName) VALUES
    ('CIVILIZATION_ROME', 'LEADER_EXAMPLE_AGRIPPA', 'LOC_CITY_NAME_ROME');

-- 3. Способность лидера
INSERT INTO Traits (TraitType, Name, Description) VALUES
    ('TRAIT_LEADER_EXAMPLE_AGRIPPA', 'LOC_TRAIT_LEADER_EXAMPLE_AGRIPPA_NAME', 'LOC_TRAIT_LEADER_EXAMPLE_AGRIPPA_DESCRIPTION');

INSERT INTO LeaderTraits (LeaderType, TraitType) VALUES
    ('LEADER_EXAMPLE_AGRIPPA', 'TRAIT_LEADER_EXAMPLE_AGRIPPA'),
    -- служебные трейты «характера» для ИИ (существуют в игре)
    ('LEADER_EXAMPLE_AGRIPPA', 'TRAIT_LEADER_EXPANSIONIST'),
    ('LEADER_EXAMPLE_AGRIPPA', 'TRAIT_LEADER_LOW_RELIGIOUS_PREFERENCE');

INSERT INTO TraitModifiers (TraitType, ModifierId) VALUES
    ('TRAIT_LEADER_EXAMPLE_AGRIPPA', 'EXAMPLE_AGRIPPA_GRANT_DEFENSE'),
    ('TRAIT_LEADER_EXAMPLE_AGRIPPA', 'EXAMPLE_AGRIPPA_BATH_PRODUCTION');

-- 3.1 Эффект 1: способность юнитов +4 силы на своей территории
INSERT INTO TypeTags (Type, Tag) VALUES
    ('ABILITY_EXAMPLE_AGRIPPA_DEFENSE', 'CLASS_MELEE'),
    ('ABILITY_EXAMPLE_AGRIPPA_DEFENSE', 'CLASS_RANGED'),
    ('ABILITY_EXAMPLE_AGRIPPA_DEFENSE', 'CLASS_ANTI_CAVALRY');

INSERT INTO UnitAbilities (UnitAbilityType, Name, Description, Inactive) VALUES
    ('ABILITY_EXAMPLE_AGRIPPA_DEFENSE', 'LOC_ABILITY_EXAMPLE_AGRIPPA_DEFENSE_NAME', 'LOC_ABILITY_EXAMPLE_AGRIPPA_DEFENSE_DESCRIPTION', 1);

INSERT INTO UnitAbilityModifiers (UnitAbilityType, ModifierId) VALUES
    ('ABILITY_EXAMPLE_AGRIPPA_DEFENSE', 'EXAMPLE_AGRIPPA_DEFENSE_STRENGTH');

INSERT INTO RequirementSets (RequirementSetId, RequirementSetType) VALUES
    ('EXAMPLE_AGRIPPA_UNIT_IN_OWN_TERRITORY', 'REQUIREMENTSET_TEST_ALL');

INSERT INTO RequirementSetRequirements (RequirementSetId, RequirementId) VALUES
    ('EXAMPLE_AGRIPPA_UNIT_IN_OWN_TERRITORY', 'UNIT_IN_OWNER_TERRITORY_REQUIREMENT');

INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId) VALUES
    ('EXAMPLE_AGRIPPA_GRANT_DEFENSE',    'MODIFIER_PLAYER_UNITS_GRANT_ABILITY',  NULL),
    ('EXAMPLE_AGRIPPA_DEFENSE_STRENGTH', 'MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH', 'EXAMPLE_AGRIPPA_UNIT_IN_OWN_TERRITORY');

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
    ('EXAMPLE_AGRIPPA_GRANT_DEFENSE',    'AbilityType', 'ABILITY_EXAMPLE_AGRIPPA_DEFENSE'),
    ('EXAMPLE_AGRIPPA_DEFENSE_STRENGTH', 'Amount',      '4');

INSERT INTO ModifierStrings (ModifierId, Context, Text) VALUES
    ('EXAMPLE_AGRIPPA_DEFENSE_STRENGTH', 'Preview', 'LOC_ABILITY_EXAMPLE_AGRIPPA_DEFENSE_PREVIEW');

-- 3.2 Эффект 2: +2 производства с каждого района «Бани»
INSERT INTO RequirementSets (RequirementSetId, RequirementSetType) VALUES
    ('EXAMPLE_AGRIPPA_DISTRICT_IS_BATH', 'REQUIREMENTSET_TEST_ALL');

INSERT INTO Requirements (RequirementId, RequirementType) VALUES
    ('EXAMPLE_AGRIPPA_REQ_DISTRICT_IS_BATH', 'REQUIREMENT_DISTRICT_TYPE_MATCHES');

INSERT INTO RequirementArguments (RequirementId, Name, Value) VALUES
    ('EXAMPLE_AGRIPPA_REQ_DISTRICT_IS_BATH', 'DistrictType', 'DISTRICT_BATH');

INSERT INTO RequirementSetRequirements (RequirementSetId, RequirementId) VALUES
    ('EXAMPLE_AGRIPPA_DISTRICT_IS_BATH', 'EXAMPLE_AGRIPPA_REQ_DISTRICT_IS_BATH');

INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId) VALUES
    ('EXAMPLE_AGRIPPA_BATH_PRODUCTION', 'MODIFIER_PLAYER_DISTRICTS_ADJUST_YIELD_CHANGE', 'EXAMPLE_AGRIPPA_DISTRICT_IS_BATH');

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
    ('EXAMPLE_AGRIPPA_BATH_PRODUCTION', 'YieldType', 'YIELD_PRODUCTION'),
    ('EXAMPLE_AGRIPPA_BATH_PRODUCTION', 'Amount',    '2');

-- 4. Повестка: переиспользуем существующую (проще и надёжнее, чем писать свою)
INSERT INTO HistoricalAgendas (LeaderType, AgendaType) VALUES
    ('LEADER_EXAMPLE_AGRIPPA', 'AGENDA_BACKSTAB_AVERSE');

-- 5. Предпочтения ИИ. ВНИМАНИЕ: AiLists.LeaderType — это TraitType лидера
INSERT INTO AiListTypes (ListType) VALUES
    ('ExampleAgrippaTechs'),
    ('ExampleAgrippaCivics'),
    ('ExampleAgrippaWonders');

INSERT INTO AiLists (ListType, LeaderType, System) VALUES
    ('ExampleAgrippaTechs',   'TRAIT_LEADER_EXAMPLE_AGRIPPA', 'Technologies'),
    ('ExampleAgrippaCivics',  'TRAIT_LEADER_EXAMPLE_AGRIPPA', 'Civics'),
    ('ExampleAgrippaWonders', 'TRAIT_LEADER_EXAMPLE_AGRIPPA', 'Buildings');

INSERT INTO AiFavoredItems (ListType, Item, Favored) VALUES
    ('ExampleAgrippaTechs',   'TECH_MASONRY',       1),
    ('ExampleAgrippaTechs',   'TECH_ENGINEERING',   1),
    ('ExampleAgrippaCivics',  'CIVIC_EARLY_EMPIRE', 1),
    ('ExampleAgrippaWonders', 'BUILDING_COLOSSEUM', 1);
