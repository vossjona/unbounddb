# Advanced Move Search - Design Document

## Overview

Replace the existing "search by type and move" tab with a powerful structured filter UI that answers questions like "Which Pokemon learns a special ghost type move with 80+ power?" with optional game progress restrictions.

## UI Layout

### Filter Panel

#### Move Filters (expandable section)

| Filter | Control | Notes |
|--------|---------|-------|
| Move Type | Multiselect dropdown | Ghost, Fire, etc. Select one or more |
| Category | Checkboxes | Physical / Special / Status |
| Power | Min/Max number inputs | e.g., min=80 means "80+" |
| Accuracy | Min/Max number inputs | |
| Priority | Min/Max number inputs | min=1 finds priority moves |
| PP | Min/Max number inputs | |
| Makes Contact | Checkbox | For ability interactions (Iron Fist, etc.) |
| Sound Move | Checkbox | |
| Punch Move | Checkbox | |
| Bite Move | Checkbox | |
| Pulse Move | Checkbox | |
| Has Secondary Effect | Checkbox | |

#### Pokemon Filters (expandable section)

| Filter | Control | Notes |
|--------|---------|-------|
| Learn Method | Multiselect | Level Up, Egg, TM, Tutor |
| Max Learn Level | Number input | Only applies to level-up moves |
| HP minimum | Number input | Base stat minimum |
| ATK minimum | Number input | Base stat minimum |
| DEF minimum | Number input | Base stat minimum |
| SPA minimum | Number input | Base stat minimum |
| SPD minimum | Number input | Base stat minimum |
| SPE minimum | Number input | Base stat minimum |
| BST minimum | Number input | Base stat total minimum |
| STAB Only | Toggle | Only show moves matching the Pokemon's type(s) |

#### Game Progress (optional)

- **Apply Game Progress**: Checkbox toggle
- When enabled, reuses the active profile's location and level cap
- Filters which Pokemon are available based on game state

### Results Display

**Summary line**: "Found 23 Pokemon learning 47 matching moves"

**Grouped by Pokemon**, each in a Streamlit expander:

Pokemon header row:
| Name | Type1 | Type2 | HP | ATK | DEF | SPA | SPD | SPE | BST | Abilities |

Matching moves table underneath:
| Move | Type | Cat | Power | Acc | PP | Pri | Learn Method | Level | STAB |

**Sorting**:
- Pokemon sorted by BST descending (strongest first), with option to sort by specific stat
- Moves within each Pokemon sorted by power descending

## Technical Implementation

### Backend

**New function** `search_moves_advanced()` in `unbounddb/app/queries.py`:
- Dynamically builds SQL joining `pokemon`, `pokemon_moves`, and `moves`
- Only applies WHERE clauses for filters the user actually set
- Returns flat rows (one per Pokemon-move combination)
- STAB logic: `WHERE (m.type = p.type1 OR m.type = p.type2)`

**Game progress**: Calls existing `get_available_pokemon_set()` to get available `pokemon_key`s, adds `WHERE pokemon_key IN (...)` clause.

### Frontend

**New module** `unbounddb/app/tabs/move_search.py`:
- Filter panel and results rendering
- Uses `@st.cache_data` for query caching
- Grouping/sorting in Python after query returns

### Files to Touch

1. `unbounddb/app/queries.py` - add `search_moves_advanced()`
2. `unbounddb/app/tabs/move_search.py` - new file for the tab UI
3. `unbounddb/app/main.py` - wire in new tab, remove old search
4. Unit tests for the query function

### No Schema Changes

All required data already exists in the database tables: `pokemon`, `pokemon_moves`, `moves`.
