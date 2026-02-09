# Game Progression Extraction Plan

## Goal

Extract structured game progression data from the Pokemon Unbound walkthrough to map:
**Trainer X defeated → Locations Y, Z unlocked**

## Current State

### What We Have
- **274 trainers** in DB (Leaders, Rivals, Bosses, Shadow Admins, Elite Four, etc.)
- **81 unique locations** with encounter data
- **Profile system** tracks: HM access, rod level, accessible_locations, level_cap
- **Walkthrough document**: ~40k words, consistent formatting

### What's Missing
- No link between defeating a trainer and unlocking locations
- No ordered progression through the game
- No automatic level cap updates based on badges

## Data Source

**Walkthrough URL**: https://www.pokemoncoders.com/wp-content/uploads/2022/04/Pokemon-Unbound-v2.0.3.2-18-January-2022-update-Walkthrough.txt

**Walkthrough Structure**:
- Organized by region (West/East Borrius) with area codes like `[rt01]`
- Consistent trainer format: `[Class] [Name] - Lv[X] Pokemon`
- Progression markers: "After defeating...", "we can now use Cut", etc.
- Covers early-to-mid game (~30-40% of full game)

## Implementation Plan

### Phase 1: Extract & Order Important Trainers

**Objective**: Find gym leaders, rivals, and bosses in the walkthrough and establish their order of appearance.

**Approach**:
1. Fetch the walkthrough text
2. Use regex to find trainer mentions matching our known important trainers:
   - `Leader *` (gym leaders)
   - `Rival *` (rival battles)
   - `Boss *` (story bosses)
   - `Shadow Admin *` (team encounters)
3. Record their position in the document (line number or character offset)
4. Cross-reference with our 274 trainers in DB
5. Output: Ordered list of important trainers

**Validation**: Compare extracted order against game knowledge / existing trainer data

### Phase 2: Segment Walkthrough by Major Battles

**Objective**: Split the walkthrough into chunks, where each chunk represents what happens between two important trainer fights.

**Approach**:
1. Use trainer positions from Phase 1 as segment boundaries
2. Extract text between consecutive important trainers
3. Each segment = "content accessible after defeating trainer N, before trainer N+1"
4. Output: List of (trainer, segment_text) tuples

**Example Segments**:
```
Segment 0: Game start → Leader Alice (Gym 1)
Segment 1: Leader Alice → Rival 3 (First rival battle)
Segment 2: Rival 3 → Leader Benjamin (Gym 2)
...
```

### Phase 3: Extract Progression Data per Segment

**Objective**: For each segment, extract what becomes available to the player.

**Approach**:
1. **Location extraction**:
   - Find area codes: `[rt01]`, `[dres]`, `[icy]`, etc.
   - Extract full location names from headers
   - Match against our 81 known locations in DB

2. **HM unlock detection**:
   - Pattern: "we can now use [HM]"
   - Pattern: "Surf/Cut/Rock Smash is now available"

3. **Level cap extraction**:
   - Pattern: "Pokémon will now obey us up to Lv[X]"
   - Pattern: "Badge #[N]" correlates with level caps

4. **Rod upgrade detection**:
   - Pattern: "received [Old/Good/Super] Rod"

**Output per segment**:
```python
{
    "after_trainer": "Leader Alice",
    "trainer_key": "leader_alice",
    "unlocks": {
        "locations": ["Route 2", "Dehara City", "Dehara Tunnel"],
        "hm": ["Cut"],
        "level_cap": 25,
        "rod": None
    }
}
```

### Phase 4: Build Progression Data Structure

**Objective**: Create a structured data file that maps the full game progression.

**Output Format** (YAML or JSON):
```yaml
progression:
  - trainer: null  # Game start
    trainer_key: null
    locations: ["Route 1", "Frozen Heights", "Dresco Town"]
    hm: []
    level_cap: 15
    rod: null

  - trainer: "Leader Alice"
    trainer_key: "leader_alice"
    locations: ["Route 2", "Dehara City"]
    hm: ["Cut"]
    level_cap: 25
    rod: null

  - trainer: "Rival 3"
    trainer_key: "rival_3"
    locations: ["Route 3", "Route 3 Beach"]
    hm: []
    level_cap: 25
    rod: "Old Rod"
```

### Phase 5: Integrate with Profile System

**Objective**: Update the profile system to use progression data.

**Changes**:
1. Add `defeated_trainers: list[str]` to profile schema
2. Create `get_accessible_locations(defeated_trainers)` function
3. Auto-compute `accessible_locations`, `level_cap`, HMs from progression data
4. Update UI to show progression state and next trainer

**New User Flow**:
1. User marks trainer as defeated
2. System looks up progression data
3. Auto-updates: locations, level_cap, HMs, rod
4. Pokemon filter reflects new accessibility

## File Structure

```
configs/
  game_progression.yml      # Extracted progression data

unbounddb/
  progression/
    __init__.py
    extractor.py           # Phase 1-3: Extract from walkthrough
    progression_data.py    # Phase 4: Load and query progression

unbounddb/app/
  location_filters.py      # Phase 5: Update to use progression
  user_database.py         # Phase 5: Add defeated_trainers field
```

## Validation Strategy

1. **Phase 1**: Manually verify trainer order matches game
2. **Phase 2**: Spot-check segment boundaries make sense
3. **Phase 3**: Verify extracted locations exist in our DB
4. **Phase 4**: Playtest with real game progress
5. **Phase 5**: Unit tests for progression lookups

## Next Steps

- [ ] Phase 1: Extract ordered trainer list from walkthrough
- [ ] Review and validate trainer order
- [ ] Phase 2: Segment walkthrough
- [ ] Phase 3: Extract locations per segment
- [ ] Phase 4: Create progression data file
- [ ] Phase 5: Integrate with profile system
