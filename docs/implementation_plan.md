# Implementation Plan: UnboundDB Feature Expansion

## Overview

This plan adds 5 new tools to UnboundDB for analyzing Pokemon Unbound trainer battles and game data:

1. **Defensive Type Suggester** - Find type combinations that resist opponent movesets
2. **Offensive Type Suggester** - Find move types that hit opponent teams super-effectively
3. **Physical/Special Analyzer** - Determine if opponent is physical or special focused
4. **Pokemon/Move Matcher** - Find Pokemon that can learn moves matching specific criteria
5. **Catch Location Finder** - Find where to catch a Pokemon or its pre-evolutions

---

## Data Sources

| Source | URL | Format | Status |
|--------|-----|--------|--------|
| Pokemon stats | `Base_Stats.c` (DPE/Unbound) | C structs | Already ingested |
| Level-up learnsets | `Learnsets.c` (DPE/Unbound) | C structs | Already ingested |
| Move properties | `moves_info.h` (pokeemerald-expansion) | C structs | **New** |
| Trainer battles | [Google Sheet](https://docs.google.com/spreadsheets/d/1pLTQKQkWTnSkev4_kcjHbY0AkBujbTUDybxXFNZ_aVY/edit?gid=707456878) | CSV | **New** |
| Catch locations | [Google Sheet](https://docs.google.com/spreadsheets/d/1PyGm-yrit5Ow6cns2tBA9VEMwLVMzn3YhDRipABjLUM/edit?gid=897380238) | CSV | **New** |
| Evolution data | `Evolution Table.c` (DPE/Unbound) | C structs | **New** |
| TM/Tutor moves | `TM_Tutor_Tables.c` (DPE/Unbound) | C structs | **New** |
| Egg moves | `Egg_Moves.c` (DPE/Unbound) | C structs | **New** |

### GitHub Raw URLs

```
# Already configured
https://raw.githubusercontent.com/Skeli789/Dynamic-Pokemon-Expansion/Unbound/src/Base_Stats.c
https://raw.githubusercontent.com/Skeli789/Dynamic-Pokemon-Expansion/Unbound/src/Learnsets.c

# New sources
https://raw.githubusercontent.com/Skeli789/Dynamic-Pokemon-Expansion/Unbound/src/Evolution%20Table.c
https://raw.githubusercontent.com/Skeli789/Dynamic-Pokemon-Expansion/Unbound/src/TM_Tutor_Tables.c
https://raw.githubusercontent.com/Skeli789/Dynamic-Pokemon-Expansion/Unbound/src/Egg_Moves.c
https://raw.githubusercontent.com/rh-hideout/pokeemerald-expansion/master/src/data/moves_info.h
```

### Google Sheet GIDs

```
Trainer Battles: 707456878
Locations: 897380238
```

### Pokemon Glossary
docs/pokemon_glossary.md
If you need extra information about any pokemon concept - use web search.

---

## Database Schema

### Existing Tables (no changes)

```sql
pokemon (
    pokemon_key TEXT PRIMARY KEY,  -- slugified name
    name TEXT,
    hp INTEGER,
    attack INTEGER,
    defense INTEGER,
    sp_attack INTEGER,
    sp_defense INTEGER,
    speed INTEGER,
    bst INTEGER,
    type1 TEXT,
    type2 TEXT,
    ability1 TEXT,
    ability2 TEXT,
    hidden_ability TEXT,
    catch_rate INTEGER,
    exp_yield INTEGER,
    egg_group1 TEXT,
    egg_group2 TEXT
)

learnsets (
    pokemon_key TEXT,
    move_key TEXT,
    level INTEGER,
    PRIMARY KEY (pokemon_key, move_key, level)
)
```

### Expanded Table

```sql
moves (
    move_key TEXT PRIMARY KEY,     -- slugified name
    name TEXT,
    type TEXT,                     -- e.g., "Fire", "Water"
    category TEXT,                 -- "Physical", "Special", "Status"
    power INTEGER,                 -- 0 for status moves
    accuracy INTEGER,              -- 0 for moves that never miss
    pp INTEGER,
    priority INTEGER,              -- -7 to +5
    effect TEXT,                   -- e.g., "EFFECT_BURN_HIT", "EFFECT_ABSORB"
    effect_chance INTEGER,         -- secondary effect probability (0-100)
    makes_contact BOOLEAN,
    is_sound_move BOOLEAN,
    is_punch_move BOOLEAN,
    is_bite_move BOOLEAN,
    is_pulse_move BOOLEAN
)
```

### New Tables

```sql
trainers (
    trainer_id INTEGER PRIMARY KEY,
    name TEXT,                     -- e.g., "Mirskle"
    specialty_type TEXT,           -- e.g., "Grass" (from sheet)
    difficulty TEXT,               -- e.g., "Insane", "Expert", "Difficult"
    fight_gimmicks TEXT,           -- e.g., "Double Battle, Fog"
    trainer_items TEXT,            -- e.g., "none" or item list
    is_double_battle BOOLEAN
)

trainer_pokemon (
    id INTEGER PRIMARY KEY,
    trainer_id INTEGER,            -- FK to trainers
    pokemon_key TEXT,              -- FK to pokemon
    slot INTEGER,                  -- 1-6 (1st lead, 2nd lead, etc.)
    level INTEGER,
    ability TEXT,
    held_item TEXT,
    nature TEXT,
    ev_hp INTEGER,
    ev_attack INTEGER,
    ev_defense INTEGER,
    ev_sp_attack INTEGER,
    ev_sp_defense INTEGER,
    ev_speed INTEGER
)

trainer_pokemon_moves (
    trainer_pokemon_id INTEGER,    -- FK to trainer_pokemon
    move_key TEXT,                 -- FK to moves
    slot INTEGER,                  -- 1-4
    PRIMARY KEY (trainer_pokemon_id, slot)
)

locations (
    id INTEGER PRIMARY KEY,
    location_name TEXT,            -- e.g., "Route 1", "Ice Hole"
    pokemon_key TEXT,              -- FK to pokemon
    encounter_notes TEXT,          -- e.g., "Daytime", "Special Encounter", "Swarm"
    UNIQUE (location_name, pokemon_key)
)

evolutions (
    id INTEGER PRIMARY KEY,
    from_pokemon_key TEXT,         -- FK to pokemon
    to_pokemon_key TEXT,           -- FK to pokemon
    method TEXT,                   -- e.g., "Level", "Stone", "Trade", "Friendship"
    condition TEXT                 -- e.g., "32", "Thunder Stone", "holding Razor Fang"
)

tm_moves (
    pokemon_key TEXT,
    move_key TEXT,
    PRIMARY KEY (pokemon_key, move_key)
)

egg_moves (
    pokemon_key TEXT,
    move_key TEXT,
    PRIMARY KEY (pokemon_key, move_key)
)
```

---

## Type Chart

Gen 6+ type chart with 18 types (Fairy included). Stored as a Python dict/matrix.

Types: Normal, Fire, Water, Electric, Grass, Ice, Fighting, Poison, Ground, Flying, Psychic, Bug, Rock, Ghost, Dragon, Dark, Steel, Fairy

Effectiveness values: 0 (immune), 0.25, 0.5, 1, 2, 4

---

## Phase Breakdown

### Phase 1: Move Data Ingestion

**Goal:** Expand `moves` table with full move properties.

**Tasks:**
1. Add `moves_info.h` URL to `github_sources.yml`
2. Create parser for `moves_info.h` C structs in `c_parser.py`
3. Update `transformers.py` to handle moves data
4. Update pipeline to build expanded moves table
5. Write unit tests for move parsing

**Deliverables:**
- `moves` table with 800+ moves including type, category, power, accuracy, effects
- Parser handles all move flags (contact, sound, punch, bite, pulse)

---

### Phase 2: Trainer Battles Ingestion

**Goal:** Ingest trainer battle data from Google Sheet.

**Tasks:**
1. Add Trainer Battles sheet config to `sheets.yml`
2. Create CSV fetcher for the specific sheet format (trainer blocks)
3. Create transformer to normalize the wide format into relational tables
4. Build `trainers`, `trainer_pokemon`, `trainer_pokemon_moves` tables
5. Write unit tests for trainer parsing

**Sheet Structure (for reference):**
```
Name,1. Mirskle (Grass),,,,,,
Fight Gimmicks,"Double Battle, Fog",,,,,,
Trainer Items,none,,,,,,
Mons,,,,,,,
Pokemon Names,Floette [1st lead],Gloom [2nd lead],Weedle,Comfey,,,
Level at Cap,19,21,17,18,,,
Ability,Flower Veil / Aroma Veil,Chlorophyll,Technician,Triage,,,
Held Item,Grassy Seed,Leftovers,Silver Powder,Leftovers,,,
Moves,Moonblast,Apple Acid,Bug Bite,Draining Kiss,,,
,Petal Blizzard,Moonblast,Electroweb,Helping Hand,,,
,Wish,Ingrain,Poison Sting,Flower Shield,,,
,Grassy Terrain,Sleep Powder,String Shot,Floral Healing,,,
Nature,Bold,Bold,Adamant,Bold,,,
HP EVs,252,252,6,252,,,
...
```

**Deliverables:**
- All trainers with difficulty levels
- Pokemon with slots preserved (1st lead, 2nd lead, etc.)
- Double battle flag extracted from gimmicks
- All moves linked to trainer Pokemon

---

### Phase 3: Locations & Evolution Ingestion

**Goal:** Ingest catch locations and evolution data.

**Tasks:**
1. Add Locations sheet config
2. Create transformer for wide-format locations CSV (routes as columns)
3. Add `Evolution Table.c` URL to `github_sources.yml`
4. Create parser for evolution C structs
5. Build `locations` and `evolutions` tables
6. Write unit tests

**Locations Sheet Structure (for reference):**
```
Route 1,,Route 2,,Route 3,,...
Snorunt,,Pikipek,,Wingull,,...
Vanillite,,Patrat,,Bidoof,,...
```

**Deliverables:**
- `locations` table mapping Pokemon to catch locations
- `evolutions` table with method and condition
- Encounter notes preserved (Daytime, Swarm, Special Encounter)

---

### Phase 4: TM & Egg Moves Ingestion

**Goal:** Ingest TM/Tutor and Egg move data.

**Tasks:**
1. Add `TM_Tutor_Tables.c` and `Egg_Moves.c` URLs
2. Create parsers for both C file formats
3. Build `tm_moves` and `egg_moves` tables
4. Write unit tests

**Deliverables:**
- `tm_moves` table (Pokemon -> Move mappings)
- `egg_moves` table (Pokemon -> Move mappings)

---

### Phase 5: Type Chart Utility Module

**Goal:** Create reusable type effectiveness utilities.

**Tasks:**
1. Create `unbounddb/utils/type_chart.py`
2. Implement 18x18 effectiveness matrix
3. Implement helper functions:
   - `get_effectiveness(atk_type, def_type1, def_type2) -> float`
   - `get_all_resistances(def_type1, def_type2) -> list[str]`
   - `get_all_weaknesses(def_type1, def_type2) -> list[str]`
   - `get_all_immunities(def_type1, def_type2) -> list[str]`
   - `generate_all_type_combinations() -> list[tuple]`
   - `score_defensive_typing(def_types, atk_types) -> dict`
4. Write comprehensive unit tests

**Deliverables:**
- Type chart module with full test coverage
- Scoring function for defensive type analysis

---

### Phase 6: UI Tool 1 - Defensive Type Suggester

**Goal:** Suggest defensive types against a trainer's moveset.

**UI Flow:**
1. Select Trainer (dropdown)
2. Select Difficulty (dropdown, filters trainers)
3. Click "Analyze"
4. View results

**Logic:**
1. Query all moves from selected trainer's team
2. Filter to offensive moves (category != "Status")
3. Extract unique move types
4. For each single type and dual-type combination:
   - Count how many move types are resisted (<=0.5x)
   - Count how many move types are immune (0x)
   - Count how many trainer Pokemon have NO super-effective moves against this typing
5. Rank by: most resistances, then most immunities, then most "harmless" Pokemon

**Output:**
- Table: Type Combo | # Resisted | # Immune | # Pokemon Can't Hurt You
- Expandable detail: which moves are resisted/immune

**Files to modify:**
- `unbounddb/app/queries.py` - add trainer/move queries
- `unbounddb/app/main.py` - add new tab
- Create `unbounddb/app/tools/defensive_suggester.py`

---

### Phase 7: UI Tool 2 - Offensive Type Suggester

**Goal:** Suggest offensive move types for coverage against a trainer's team.

**UI Flow:**
1. Select Trainer (dropdown)
2. Select Difficulty (dropdown)
3. Click "Analyze"
4. View results

**Logic:**
1. Query all Pokemon from trainer's team with their types
2. For each offensive type:
   - Count Pokemon hit super-effectively (2x or 4x)
   - Count Pokemon hit neutrally (1x)
   - Count Pokemon that resist (<=0.5x)
   - Count Pokemon immune (0x)
3. Rank by: most super-effective hits

**Output:**
- Table: Move Type | # Super Effective | # Neutral | # Resisted | # Immune
- Recommendation: "Best coverage types: [X, Y, Z]"

**Files to modify:**
- `unbounddb/app/queries.py` - add queries
- `unbounddb/app/main.py` - add new tab
- Create `unbounddb/app/tools/offensive_suggester.py`

---

### Phase 8: UI Tool 3 - Physical/Special Analyzer

**Goal:** Determine if opponent is physical or special focused.

**UI Flow:**
1. Select Trainer (dropdown)
2. Select Difficulty (dropdown)
3. Click "Analyze"
4. View results

**Logic:**
1. Query trainer's Pokemon with stats and moves
2. Calculate offensive profile:
   - Count physical moves vs special moves
   - Sum base power of physical moves vs special moves
   - Average Attack stat vs Sp. Attack stat of team
3. Calculate defensive profile:
   - Average Defense stat vs Sp. Defense stat of team
4. Verdict: "Physical", "Special", or "Mixed"

**Output:**
- Bar charts: Physical vs Special moves (count and total power)
- Bar charts: Avg Attack vs Sp.Atk, Avg Defense vs Sp.Def
- Text verdict with recommendation

**Files to modify:**
- `unbounddb/app/queries.py` - add queries
- `unbounddb/app/main.py` - add new tab
- Create `unbounddb/app/tools/phys_spec_analyzer.py`

---

### Phase 9: UI Tool 4 - Pokemon/Move Matcher

**Goal:** Find Pokemon that can learn moves matching specific criteria.

**UI Flow:**
1. Set filters:
   - Move type (multi-select dropdown)
   - Category (Physical / Special / Status)
   - Min power (slider)
   - Min accuracy (slider)
   - Effect type (multi-select dropdown)
   - Include TM moves (checkbox)
   - Include Egg moves (checkbox)
2. Click "Search"
3. View results

**Logic:**
1. Query moves matching all filters
2. Join with learnsets
3. Optionally union with tm_moves and egg_moves
4. Group by Pokemon, list matching moves

**Output:**
- Table: Pokemon | Matching Moves | Learn Method (Level/TM/Egg)
- Click Pokemon to expand move details

**Files to modify:**
- `unbounddb/app/queries.py` - add move filter queries
- `unbounddb/app/main.py` - add new tab
- Create `unbounddb/app/tools/move_matcher.py`

---

### Phase 10: UI Tool 5 - Catch Location Finder

**Goal:** Find where to catch a Pokemon or its pre-evolutions.

**UI Flow:**
1. Enter Pokemon name (autocomplete)
2. Click "Search"
3. View results

**Logic:**
1. Look up Pokemon in locations table
2. Recursively find pre-evolutions via evolutions table
3. For each Pokemon in evolution line, get locations

**Output:**
- Evolution chain display (e.g., Pichu -> Pikachu -> Raichu)
- For each stage: table of locations with encounter notes
- Highlight if a pre-evolution is easier to find

**Files to modify:**
- `unbounddb/app/queries.py` - add location/evolution queries
- `unbounddb/app/main.py` - add new tab
- Create `unbounddb/app/tools/location_finder.py`

---

## Implementation Order

| Phase | Description | Dependencies |
|-------|-------------|--------------|
| 1 | Move Data Ingestion | None |
| 2 | Trainer Battles Ingestion | Phase 1 (for move_key FKs) |
| 3 | Locations & Evolution Ingestion | None |
| 4 | TM & Egg Moves Ingestion | Phase 1 (for move_key FKs) |
| 5 | Type Chart Utility | None |
| 6 | Defensive Type Suggester UI | Phases 1, 2, 5 |
| 7 | Offensive Type Suggester UI | Phases 2, 5 |
| 8 | Physical/Special Analyzer UI | Phases 1, 2 |
| 9 | Pokemon/Move Matcher UI | Phases 1, 4 |
| 10 | Catch Location Finder UI | Phase 3 |

**Suggested parallel tracks:**
- Track A: Phases 1 → 2 → 6 → 7 → 8
- Track B: Phases 3 → 10
- Track C: Phases 4 → 9
- Phase 5 can be done anytime before Phase 6

---

## Testing Strategy

Each phase includes:
1. Unit tests for parsers/transformers
2. Integration test: full pipeline produces expected row counts
3. UI phases: manual testing of Streamlit interface

---

## Definition of Done (per phase)

- [ ] All new code has ABOUTME comments
- [ ] All public functions have docstrings
- [ ] `make format` passes
- [ ] `make lint` passes
- [ ] `make typing` passes
- [ ] `make unittests` passes
- [ ] Data loads correctly into DuckDB
- [ ] UI displays data correctly (for UI phases)
