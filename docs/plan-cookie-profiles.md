# Plan: Migrate User Profiles from SQLite to Browser Cookies

**Status:** Benched — investigate actual OOM cause first

## Motivation

- User preferences belong on the client (per-browser, not per-server)
- Eliminates `user_data.sqlite` — one fewer file to manage on Streamlit Cloud
- Survives Cloud environment restarts (which can wipe server files)
- No server-side state for user profiles = simpler deployment

## Research Summary

Streamlit has no native cookie-writing support. `st.context.cookies` is read-only
and returns an empty dict on Streamlit Community Cloud (proxy strips cookies).

### Recommended Package: `extra-streamlit-components`

- **PyPI:** `extra-streamlit-components` (v0.1.81, Aug 2025)
- **GitHub:** 558 stars, most battle-tested for Streamlit Cloud
- **Why:** Reads cookies in frontend JS, bypassing Streamlit Cloud's proxy filtering
- **Gotcha:** Triggers an extra app rerun on init (causes slight flickering)

### Alternatives Considered

| Package | Verdict |
|---------|---------|
| `streamlit-cookies-controller` | Simpler but uncertain Cloud compatibility |
| `streamlit-cookies-manager-v2` | Encrypted cookies, modernized fork, smaller community |
| `st.query_params` (native) | Zero deps but data visible in URL, clears on page nav |
| `streamlit-local-storage` | Reported build errors, iframe isolation issues |

## Current User Data Model

**Table: `profiles`** in `user_data.sqlite`

| Field | Type | Example |
|-------|------|---------|
| name | string (PK) | "Jonas" |
| active | boolean | true |
| progression_step | integer | 12 |
| rod_level | string | "Good Rod" |
| difficulty | string | "Any" |

~100 bytes per profile. Fits easily in a single JSON cookie (4KB limit).

## Implementation Plan

### Step 1: Add dependency

```
pip install extra-streamlit-components
```

Add to `requirements.txt` and `pyproject.toml`.

### Step 2: Create `unbounddb/app/cookie_profiles.py`

Replace `user_database.py` with a cookie-backed equivalent.

- Store all profiles as one JSON cookie: `unbounddb_profiles`
- JSON structure:
  ```json
  {
    "active": "Jonas",
    "profiles": {
      "Jonas": {"progression_step": 12, "rod_level": "Good Rod", "difficulty": "Any"},
      "Tim": {"progression_step": 0, "rod_level": "None", "difficulty": null}
    }
  }
  ```
- Keep the same public API:
  - `create_profile(name) -> bool`
  - `get_profile(name) -> dict | None`
  - `list_profiles() -> list[str]`
  - `update_profile(name, **fields) -> bool`
  - `delete_profile(name) -> bool`
  - `get_active_profile() -> str | None`
  - `set_active_profile(name | None) -> None`
  - `profile_exists(name) -> bool`
  - `get_profile_count() -> int`

### Step 3: Update `game_progress_persistence.py`

- Replace `from unbounddb.app.user_database import ...` with cookie_profiles imports
- Remove `get_user_connection()` calls — cookie manager passed instead

### Step 4: Update `main.py`

- Instantiate `CookieManager` once at top level (singleton per page)
- Pass cookie manager to profile functions
- Handle the extra rerun triggered by CookieManager init

### Step 5: Remove server-side user DB

- Delete `unbounddb/app/user_database.py`
- Remove `user_db_path` from `settings.py`
- Update tests to mock cookie reads/writes instead of SQLite

### Step 6: Update tests

- `test_user_database.py` → `test_cookie_profiles.py`
- `test_game_profiles.py` — update to use cookie-backed profiles
- Mock `CookieManager` in tests (needs user permission for mocking)

### Step 7: Cleanup

- Remove `duckdb`/`sqlite3` imports from user-facing code
- Update CLAUDE.md and README.md
- Remove `user_data.sqlite` from `.gitignore` if present

## Gotchas & Risks

- **Cookie size:** 4KB limit per cookie. Our data is ~500 bytes for several profiles. Fine.
- **Shared domain:** On `share.streamlit.io`, other apps can read cookies. Use a unique
  cookie name (`unbounddb_profiles`) to avoid clashes.
- **Rerun on init:** CookieManager triggers an extra Streamlit rerun. Handle with a
  guard: `if not cookie_manager.ready(): st.stop()`
- **No encryption:** Profile data (names, game progress) is not sensitive. Plain JSON ok.
- **Test mocking:** Will need permission to mock CookieManager in unit tests.
