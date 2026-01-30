# Phase 1: Move Data Ingestion - Detailed Plan

## Goal
Expand the `moves` table with full move properties from `moves_info.h` (pokeemerald-expansion repo).

## Current State
- `moves` table exists but only has `move` and `move_key` columns (extracted from learnsets)
- No move metadata: type, category, power, accuracy, effects, flags

## Target Schema
```sql
moves (
    move_key TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,                    -- e.g., "Fire", "Water"
    category TEXT,                -- "Physical", "Special", "Status"
    power INTEGER,                -- 0 for status moves
    accuracy INTEGER,             -- 0 for moves that never miss
    pp INTEGER,
    priority INTEGER,             -- -7 to +5
    effect TEXT,                  -- e.g., "EFFECT_BURN_HIT"
    has_secondary_effect BOOLEAN, -- TRUE if additionalEffects present (not 100% guaranteed)
    makes_contact BOOLEAN,
    is_sound_move BOOLEAN,
    is_punch_move BOOLEAN,
    is_bite_move BOOLEAN,
    is_pulse_move BOOLEAN
)
```

---

## Implementation Steps

### Step 1: Update github_sources.yml

**File:** `configs/github_sources.yml`

**Changes:**
- Add `moves_info` source with full URL (different repo)
- Add support for `url` field as alternative to `file` + `base_url`

```yaml
moves_info:
  url: "https://raw.githubusercontent.com/rh-hideout/pokeemerald-expansion/master/src/data/moves_info.h"
  description: "Move types, power, accuracy, effects, flags"
  parser: "moves_info"
```

### Step 2: Update fetcher.py to support full URLs

**File:** `unbounddb/ingestion/fetcher.py`

**Changes in `fetch_github_file()`:**
- Check if source has `url` field (full URL) vs `file` field (relative to base_url)
- Use full URL if present, otherwise construct from base_url + file

```python
source = config["sources"][source_name]
if "url" in source:
    url = source["url"]
    filename = Path(source["url"]).name  # Extract filename from URL
else:
    filename = source["file"]
    url = f"{config['base_url']}/{filename}"
```

### Step 3: Add MoveInfo dataclass to c_parser.py

**File:** `unbounddb/ingestion/c_parser.py`

**Add dataclass:**
```python
@dataclass
class MoveInfo:
    """Move information parsed from moves_info.h."""

    name: str
    type_name: str
    category: str
    power: int
    accuracy: int
    pp: int
    priority: int
    effect: str
    has_secondary_effect: bool
    makes_contact: bool
    is_sound_move: bool
    is_punch_move: bool
    is_bite_move: bool
    is_pulse_move: bool
```

### Step 4: Add cleaning functions for moves

**File:** `unbounddb/ingestion/c_parser.py`

```python
def _clean_move_type(type_const: str) -> str:
    """Convert TYPE_FIRE to Fire."""
    return type_const.replace("TYPE_", "").title()


def _clean_category(category: str) -> str:
    """Convert DAMAGE_CATEGORY_PHYSICAL to Physical."""
    mapping = {
        "DAMAGE_CATEGORY_PHYSICAL": "Physical",
        "DAMAGE_CATEGORY_SPECIAL": "Special",
        "DAMAGE_CATEGORY_STATUS": "Status",
    }
    return mapping.get(category, category)
```

### Step 5: Implement parse_moves_info()

**File:** `unbounddb/ingestion/c_parser.py`

**Key regex patterns:**
```python
# Match move blocks: [MOVE_NAME] = { ... },
move_pattern = re.compile(
    r"\[MOVE_(\w+)\]\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}",
    re.MULTILINE | re.DOTALL
)

# Field patterns
field_patterns = {
    "name": re.compile(r'\.name\s*=\s*COMPOUND_STRING\s*\(\s*"([^"]+)"'),
    "type": re.compile(r"\.type\s*=\s*(TYPE_\w+)"),
    "category": re.compile(r"\.category\s*=\s*(DAMAGE_CATEGORY_\w+)"),
    "power": re.compile(r"\.power\s*=\s*(\d+)"),
    "accuracy": re.compile(r"\.accuracy\s*=\s*(\d+)"),
    "pp": re.compile(r"\.pp\s*=\s*(?:B_UPDATED_MOVE_DATA\s*>=\s*GEN_\d+\s*\?\s*)?(\d+)"),
    "priority": re.compile(r"\.priority\s*=\s*(-?\d+)"),
    "effect": re.compile(r"\.effect\s*=\s*(EFFECT_\w+)"),
}

# Boolean flags (TRUE if field exists and is TRUE)
boolean_flags = {
    "makes_contact": re.compile(r"\.makesContact\s*=\s*TRUE"),
    "is_sound_move": re.compile(r"\.soundMove\s*=\s*TRUE"),
    "is_punch_move": re.compile(r"\.punchingMove\s*=\s*TRUE"),
    "is_bite_move": re.compile(r"\.bitingMove\s*=\s*TRUE"),
    "is_pulse_move": re.compile(r"\.pulseMove\s*=\s*TRUE"),
}

# Secondary effect detection
has_secondary_effect_pattern = re.compile(r"\.additionalEffects\s*=")
```

**Logic:**
1. Find all `[MOVE_NAME] = { ... }` blocks
2. Skip MOVE_NONE entry
3. Extract `.name` from COMPOUND_STRING
4. Extract type, category, power, accuracy, pp, priority, effect
5. Check for boolean flags (default FALSE if not present)
6. Check for `.additionalEffects` to set `has_secondary_effect`
7. Handle Gen 6+ conditional values (take first number for pp)

### Step 6: Add DataFrame converter

**File:** `unbounddb/ingestion/c_parser.py`

```python
def moves_info_to_dataframe(moves: list[MoveInfo]) -> pl.DataFrame:
    """Convert list of MoveInfo to a Polars DataFrame."""
    data = {
        "name": [m.name for m in moves],
        "type": [m.type_name for m in moves],
        "category": [m.category for m in moves],
        "power": [m.power for m in moves],
        "accuracy": [m.accuracy for m in moves],
        "pp": [m.pp for m in moves],
        "priority": [m.priority for m in moves],
        "effect": [m.effect for m in moves],
        "has_secondary_effect": [m.has_secondary_effect for m in moves],
        "makes_contact": [m.makes_contact for m in moves],
        "is_sound_move": [m.is_sound_move for m in moves],
        "is_punch_move": [m.is_punch_move for m in moves],
        "is_bite_move": [m.is_bite_move for m in moves],
        "is_pulse_move": [m.is_pulse_move for m in moves],
    }
    return pl.DataFrame(data)
```

### Step 7: Add file entry point

**File:** `unbounddb/ingestion/c_parser.py`

```python
def parse_moves_info_file(path: Path) -> pl.DataFrame:
    """Parse moves_info.h file to DataFrame."""
    content = path.read_text()
    moves = parse_moves_info(content)
    return moves_info_to_dataframe(moves)
```

### Step 8: Update pipeline.py

**File:** `unbounddb/build/pipeline.py`

**Add import:**
```python
from unbounddb.ingestion.c_parser import parse_base_stats_file, parse_learnsets_file, parse_moves_info_file
```

**Add to `run_github_build_pipeline()` after learnsets parsing:**
```python
# Parse moves_info.h -> moves table (replaces simple moves table)
moves_info_path = source_dir / "moves_info.h"
if moves_info_path.exists():
    log("Parsing moves_info.h...")
    df = parse_moves_info_file(moves_info_path)

    # Add move_key for joining
    df = df.with_columns(
        pl.col("name").map_elements(slugify, return_dtype=pl.String).alias("move_key")
    )

    parquet_path = curated_dir / "moves.parquet"
    df.write_parquet(parquet_path)
    parquet_files["moves"] = parquet_path
    log(f"  -> {parquet_path} ({len(df)} rows)")
else:
    # Fallback: extract moves from learnsets (current behavior)
    if "learnsets" in parquet_files:
        log("Extracting moves table from learnsets (moves_info.h not found)...")
        # ... existing fallback code ...
```

### Step 9: Write unit tests

**File:** `tests/unittests/test_c_parser_moves.py`

**Tests to write:**
1. `TestCleanMoveType` - test `_clean_move_type()` conversion
2. `TestCleanCategory` - test `_clean_category()` conversion
3. `TestParseMoveInfo` - test individual move parsing:
   - Simple physical move (Scratch)
   - Move with secondary effect (Fire Punch with 10% burn)
   - Status move (Swords Dance)
   - Move with negative priority (Trick Room)
   - Move with multiple boolean flags
4. `TestParseMoveInfoContent` - test full content parsing:
   - Returns list of MoveInfo
   - Skips MOVE_NONE
   - Correct field extraction

**Sample test data:**
```python
SAMPLE_MOVE_SCRATCH = """
[MOVE_SCRATCH] =
{
    .name = COMPOUND_STRING("Scratch"),
    .effect = EFFECT_HIT,
    .power = 40,
    .type = TYPE_NORMAL,
    .accuracy = 100,
    .pp = 35,
    .priority = 0,
    .category = DAMAGE_CATEGORY_PHYSICAL,
    .makesContact = TRUE,
},
"""

SAMPLE_MOVE_FIRE_PUNCH = """
[MOVE_FIRE_PUNCH] =
{
    .name = COMPOUND_STRING("Fire Punch"),
    .effect = EFFECT_HIT,
    .power = 75,
    .type = TYPE_FIRE,
    .accuracy = 100,
    .pp = 15,
    .priority = 0,
    .category = DAMAGE_CATEGORY_PHYSICAL,
    .makesContact = TRUE,
    .punchingMove = TRUE,
    .additionalEffects = ADDITIONAL_EFFECTS({
        .moveEffect = MOVE_EFFECT_BURN,
        .chance = 10,
    }),
},
"""
```

---

## Files Changed Summary

| File | Action | Description |
|------|--------|-------------|
| `configs/github_sources.yml` | Modify | Add moves_info source |
| `unbounddb/ingestion/fetcher.py` | Modify | Support full URL in config |
| `unbounddb/ingestion/c_parser.py` | Modify | Add MoveInfo dataclass + parser |
| `unbounddb/build/pipeline.py` | Modify | Add moves_info parsing step |
| `tests/unittests/test_c_parser_moves.py` | Create | Unit tests for move parsing |

---

## Validation Checklist

- [ ] `make format` passes
- [ ] `make lint` passes
- [ ] `make typing` passes
- [ ] `make unittests` passes
- [ ] `unbounddb fetch --github --verbose` downloads moves_info.h
- [ ] `unbounddb build --github --verbose` builds expanded moves table
- [ ] DuckDB query `SELECT COUNT(*) FROM moves` returns 800+ rows
- [ ] DuckDB query `SELECT * FROM moves WHERE name = 'Fire Punch'` shows correct data

---

## Edge Cases to Handle

1. **Conditional compilation**: `B_UPDATED_MOVE_DATA >= GEN_6 ? 20 : 30` - extract first number (Gen 6+ value)
2. **Missing fields**: Default power=0, accuracy=0, priority=0 for status moves
3. **MOVE_NONE**: Skip this entry
4. **Nested braces in additionalEffects**: Regex must handle `{ ... { ... } ... }`
5. **Multi-line COMPOUND_STRING**: Some descriptions span multiple lines (we only need name)

---

## Dependencies

- None (Phase 1 has no dependencies on other phases)

---

## Estimated Row Counts

- Expected: 800+ moves in final table
- pokeemerald-expansion has ~900 moves defined
