# Glossary (only the concepts you listed)

## Battle Core Mechanics

- Turn order
  - Default: higher Speed acts first
  - Modified by: priority, Trick Room, paralysis/speed drops, etc.
  - Example: 120 Speed Jolteon moves before 80 Speed Blastoise unless Blastoise uses a higher-priority move

- Priority
  - Move “tier” that overrides Speed when comparing actions
  - Example: Quick Attack (priority) can move before a faster Pokémon using Flamethrower (normal priority)

- Damage calculation
  - Core pieces: Level, Base Power, Attack/SpA vs Defense/SpD, then multipliers (STAB, type, crit, weather, items/abilities, random, etc.)
  - Example multipliers stacking: STAB * type effectiveness * crit * item boost

- Random damage roll
  - Final damage multiplied by a random factor ~0.85–1.00 (inclusive) :contentReference[oaicite:0]{index=0}
  - Example: same hit can deal e.g. 100–118 damage across rolls

- Critical hits
  - Damage multiplier (modern: 1.5×) :contentReference[oaicite:1]{index=1}
  - Ignores: attacker’s negative offensive stages and target’s positive defensive stages (for that damage calc) :contentReference[oaicite:2]{index=2}
  - Example: if your Attack is -2, a crit uses your “un-dropped” Attack for that hit

- STAB (Same-Type Attack Bonus)
  - Using a move whose type matches one of the user’s types → damage boost (commonly 1.5×) :contentReference[oaicite:3]{index=3}
  - Example: Charizard using Flamethrower hits harder than using Thunder Punch (no STAB)

- Type effectiveness
  - Damage multiplier from the type chart (0, 0.25, 0.5, 1, 2, 4)
  - Example: Ice vs Dragon = 2×; Ice vs Water = 0.5×; Ice vs Dragon/Water = 1× (2× * 0.5×)

- Immunities
  - Multiplier 0× (no damage), from type or effects
  - Example: Normal-type move into a Ghost-type = 0×

- Resistances
  - Multiplier <1× (commonly 0.5×)
  - Example: Fire into Water = 0.5×

- Weather
  - Global battle modifier for several turns; can change move power, accuracy, and enable/disable effects :contentReference[oaicite:4]{index=4}
  - Example: Rain boosts Water moves and weakens Fire moves :contentReference[oaicite:5]{index=5}

- Terrain
  - Ground-based field lasting a set duration (commonly 5 turns) :contentReference[oaicite:6]{index=6}
  - Only affects “grounded” Pokémon for many effects
  - Example: Psychic Terrain blocks priority moves targeting grounded Pokémon :contentReference[oaicite:7]{index=7}

- Field effects
  - Any special battlefield state beyond weather/terrain that changes move interactions (damage boosts, move alterations, immunities, etc.)
  - Example: a “field” may boost a type’s moves or change status application rules (game-specific implementation)

- Side conditions
  - Effects attached to one team’s side (persist when Pokémon switch)
  - Example: Reflect/Light Screen, Tailwind, Safeguard

- Entry hazards
  - Side conditions that trigger when a Pokémon switches in
  - Example: Stealth Rock damages on entry; Spikes layers add more entry damage

- Screens
  - Side conditions reducing incoming damage
  - Example: Reflect reduces physical damage; Light Screen reduces special damage

- Stat stages
  - Temporary boost/drop levels: -6 to +6; applied per stat (Atk/Def/SpA/SpD/Spe/Acc/Evasion)
  - Example: +2 Attack = “two stages up” from Swords Dance

- Stat boosts
  - Increasing stat stages (setup / snowballing)
  - Example: Dragon Dance = +1 Attack, +1 Speed

- Stat drops
  - Decreasing stat stages (debuffing / self-drop)
  - Example: Close Combat drops Defense and SpD after dealing damage

- Accuracy checks
  - Hit chance = move accuracy * user accuracy stage multiplier / target evasion stage multiplier
  - Example: a 90% accurate move can become near-certain after accuracy boosts, or miss more after evasion boosts

- Evasion checks
  - Evasion stages change how likely the target is hit (part of the same accuracy formula)
  - Example: Double Team raises evasion → incoming moves miss more often

- Move targeting (single, spread, self, ally)
  - Single-target: chooses one opponent (e.g., Thunderbolt)
  - Spread: hits multiple targets in doubles (e.g., Rock Slide)
  - Self: affects user (e.g., Swords Dance)
  - Ally: targets partner (e.g., Helping Hand)

- Multi-hit moves
  - One move use hits multiple times; may break substitutes/sturdy-like effects depending on rules
  - Example: Icicle Spear can hit 2–5 times; “hit count” matters for abilities/items

- Recoil
  - User takes damage based on damage dealt (or fixed) after landing the move
  - Example: Brave Bird recoil after dealing damage

- Crash damage
  - Penalty damage when a move fails/misses (common on high-power moves)
  - Example: High Jump Kick misses → user takes crash damage

- Contact vs non-contact
  - “Contact” moves trigger contact-based abilities/items
  - Example: a contact move can trigger Rough Skin / Rocky Helmet; a non-contact move typically won’t

## Types & Type System

- Pokémon types
  - Element labels (e.g., Water, Steel) driving offense/defense matchups via the type chart

- Dual typing
  - Pokémon has two types simultaneously; effectiveness multiplies
  - Example: Fire vs Bug/Steel = 4× (2× vs Bug * 2× vs Steel)

- Type chart
  - Reference grid mapping attacking type → defending type multiplier

- Offensive typing
  - How well a Pokémon’s attacking types/moves hit common targets
  - Example: Ground is strong offensively because it hits Steel/Electric/Rock, etc.

- Defensive typing
  - How well a Pokémon takes hits based on resistances/immunities/weaknesses
  - Example: Steel often has many resistances, good defensive typing

- Type coverage
  - Set of types you can hit super-effectively with your moveset
  - Example: Ice + Ground coverage hits many common types effectively

- Type stacking
  - Dual typing combining to amplify weakness or resistance
  - Example weakness stacking: Rock/Flying takes 4× from Ice
  - Example resistance stacking: Steel/Water may resist several types at 0.5× or 0.25×

## Moves

- Physical moves
  - Damage uses Attack vs Defense :contentReference[oaicite:8]{index=8}
  - Example: Earthquake, Close Combat

- Special moves
  - Damage uses Special Attack vs Special Defense :contentReference[oaicite:9]{index=9}
  - Example: Surf, Flamethrower

- Status moves
  - No direct damage; causes effects or stat changes
  - Example: Toxic (status), Reflect (screen), Swords Dance (setup)

- Base power
  - Strength value plugged into the damage formula
  - Example: 40-power Quick Attack vs 120-power Close Combat (before modifiers)

- Accuracy
  - Base hit chance before modifiers (accuracy/evasion stages)
  - Example: 100% moves can still miss if accuracy is lowered or evasion is raised

- Priority brackets
  - Discrete priority tiers; higher tier resolves first
  - Example: “priority move” vs “normal move” decides order even if slower

- Secondary effects
  - Extra effects besides damage (status, stat drops, flinch, etc.)
  - Example: Flamethrower can burn; Crunch can drop Defense

- Chance-based effects
  - Secondary effects with a probability
  - Example: Rock Slide can flinch; Ice Beam can freeze/frostbite depending on game rules

- Self-targeting moves
  - Apply only to the user
  - Example: Calm Mind, Recover, Substitute

- Setup moves
  - Moves primarily used to gain advantage (stat boosts, screens, hazards, speed control)
  - Example: Swords Dance; Stealth Rock; Tailwind; Reflect

## Status Conditions

- Major status conditions
  - One-per-Pokémon persistent status (typical: burn/poison/paralysis/sleep/freeze or replacements) :contentReference[oaicite:10]{index=10}
  - Example: a Pokémon can’t be both burned and poisoned at the same time

- Minor status conditions
  - “Volatile” conditions that can stack with major status; often removed by switching or after turns
  - Example: confusion + burn can coexist

- Burn
  - Residual HP loss each turn; physical damage reduction :contentReference[oaicite:11]{index=11}
  - Example: burned physical attacker hits much weaker with contact moves

- Poison
  - Residual HP loss each turn
  - Example: regular poison chips consistently until cured

- Badly poisoned
  - “Toxic” poison; damage increases over time (turn counter escalates)
  - Example: long stalls become impossible without curing

- Paralysis
  - Speed reduced; chance to be unable to move on a turn
  - Example: slower turn order + occasional “fully paralyzed” turns

- Sleep
  - Unable to act for a random duration (varies by generation/mechanics)
  - Example: Sleep Powder → target loses turns unless it wakes early

- Freezeburn
  - In Unbound context, commonly treated as **Frostbite**: residual damage + special damage reduction (special-version burn) :contentReference[oaicite:12]{index=12}
  - Example: special attacker frostbitten hits weaker with special moves and takes chip damage each turn

- Confusion
  - Temporary volatile condition: each turn may act normally or hit itself
  - Example: Swagger can confuse; confusion can end after several turns

- Flinch
  - Prevents action for that turn only (volatile; depends on move timing)
  - Example: Rock Slide flinch chance can deny the opponent’s move if it hits first

## Abilities

- Passive abilities
  - Constant effect without needing a trigger event
  - Example: Levitate-like immunity; damage reduction abilities

- Triggered abilities
  - Activate on a defined event (switch-in, being hit, end of turn, etc.)
  - Example: “on hit” ability that punishes contact

- Weather-setting abilities
  - Automatically start weather (typically on switch-in) :contentReference[oaicite:13]{index=13}
  - Example: Drizzle-like ability sets rain for weather-boosted Water attacks

- Terrain-setting abilities
  - Automatically start terrain (typically on switch-in) :contentReference[oaicite:14]{index=14}
  - Example: Electric Surge-like ability creates Electric Terrain

- Intimidate-like effects
  - On-entry stat reduction to opponents (commonly Attack -1)
  - Example: switch-in causes opposing physical attackers to deal less damage

## Items

- Held items
  - Equipped item providing a battle effect until removed/suppressed
  - Example: Leftovers-style healing; Choice items; type-boost items

- Consumable items
  - Single-use held items that activate when conditions are met
  - Example: berries (HP threshold), Focus Sash-like effects

- Berries
  - Consumables triggered by HP thresholds, status, or type hits
  - Example: Sitrus restores HP at low HP; Lum cures status

- Choice items
  - Boost a stat but lock user into the first move chosen until switch out
  - Example: Choice Scarf boosts Speed but forces repeating the chosen move

- Life Orb–like effects
  - Boost damage output with recoil chip each attack
  - Example: stronger hits but self-damage adds up quickly

- Focus items
  - Prevent being KO’d from full HP once (typically consumed)
  - Example: Focus Sash lets you survive a lethal hit at 1 HP

- Type-boosting items
  - Boost power of moves of a specific type
  - Example: Mystic Water boosts Water moves; Magnet boosts Electric moves

- Status-curing items
  - Remove major status
  - Example: Lum Berry cures burn/paralysis/sleep/etc.

- Megaevolution items
  - Specific held item enabling Mega Evolution for that species
  - Example: Charizardite X enables Mega Charizard X

- Item activation timing
  - When an item triggers in the turn sequence (on hit, before move, end of turn, on switch-in, etc.)
  - Example: Focus Sash triggers on taking lethal damage; Leftovers triggers end-of-turn

- Item suppression
  - Effects that prevent an item from functioning while active
  - Example: “embargo/magic room”-like effects stop item benefits temporarily

- Knock Off interactions
  - Knock Off removes the target’s item (if removable); often has boosted damage when the target holds an item (game-dependent but commonly true)
  - Example: using Knock Off to remove Eviolite/Leftovers swings the matchup

## Stats & Growth

- Base stats
  - Species-defined HP/Atk/Def/SpA/SpD/Spe values (foundation for final stats)

- HP
  - Total health pool; reaches 0 → faint

- Attack
  - Increases damage of physical moves

- Defense
  - Reduces damage taken from physical moves

- Special Attack
  - Increases damage of special moves

- Special Defense
  - Reduces damage taken from special moves

- Speed
  - Determines turn order when priority is equal

- Stat totals
  - Sum of base stats; rough “overall power budget” indicator
  - Example: pseudo-legendaries tend to have higher totals than early-route mons

- Stat spreads
  - How stats are distributed (min-max vs balanced) for a role
  - Example: glass cannon (high Atk/SpA + Spe, low bulk) vs wall (high HP/Def/SpD)

- Level scaling
  - Stats increase with level via the standard stat formula; level also appears in damage formula

- Nature modifiers
  - One stat +10%, one stat -10% (or neutral) at final stat calculation

- Nature neutral stats
  - Stats unaffected by nature (either because nature is neutral, or for the 4 stats not boosted/dropped)

## Encounter & World Mechanics

- Wild encounters
  - Random battles from area encounter tables
  - Example: tall grass/surf/cave step encounters (depending on area rules)

- Static encounters
  - Fixed, non-random encounter on the map
  - Example: a legendary-like overworld interaction

- Gift Pokémon
  - Received directly from an NPC (not battled/caught)
  - Example: starter gift, quest reward gift

- Trade Pokémon
  - Obtained via NPC trade (your Pokémon exchanged for theirs)
  - Example: trade for a version-unique or special-nature Pokémon

- Encounter tables
  - Per-area list of possible species (and often levels/slots/methods)
  - Example: Route table: 30% Pikachu, 20% Pidgey, etc.

- Encounter rates
  - How often encounters occur and/or per-slot probabilities
  - Example: caves often have higher encounter frequency than routes

- Time-based encounters
  - Encounter table changes based on time (day/night/dawn/dusk)
  - Example: certain Ghost types appear only at night

- Location-based encounters
  - Species only appear in specific areas or sub-areas
  - Example: a water-only species appears only via fishing in one town

- Weather-based encounters
  - Encounter table changes based on overworld weather
  - Example: rain-only encounters or boosted rates for certain types

## Moves Acquisition

- Level-up moves
  - Learned at specific levels; includes evolution-level learn events
  - Example: learns “X move” at Level 24; relearnable via move relearner

- TM moves
  - Learned via TM item; compatibility per species
  - Example: TM “Earthquake” teachable to many Ground-capable Pokémon

- HM / VM moves
  - Overworld progression moves; learned/used under special rules (game-specific naming and gating)
  - Example: “Cut/Surf”-type moves used to access new areas

- Move tutors
  - NPC teaches a move, usually for a cost/condition; limited list per tutor
  - Example: tutor teaches elemental punches or rare utility

- Egg moves
  - Moves inherited through breeding parents/egg groups; often rare/strong utility
  - Example: newborn gets a move it normally can’t learn by level/TM
