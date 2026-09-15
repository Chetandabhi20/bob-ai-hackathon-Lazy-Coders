# IBM Bob Integration — Live Demo

> **This document proves IBM Bob is load-bearing in Grid Guardian.**
> Every output block below is **real output** captured from a live Bob session
> calling the Grid Guardian MCP server. Nothing is mocked or hand-written.

---

## Quick Connect (Judges — 30 seconds)

The MCP server is **deployed live on Railway**. No cloning, no Python, no
`pip install` required. Paste this JSON into your Bob IDE's MCP config and
all 5 Grid Guardian tools appear instantly:

```json
{
  "mcpServers": {
    "grid-guardian": {
      "type": "streamable-http",
      "url": "https://grid-guardian-production.up.railway.app/mcp",
      "alwaysAllow": [
        "get_asset_health",
        "get_weather_risk",
        "rank_at_risk_assets",
        "generate_crew_plan",
        "generate_incident_brief"
      ]
    }
  }
}
```

**Live dashboard:** https://grid-guardian-production.up.railway.app

Then ask Bob:
```
"What assets are at risk right now?"
"Give me the full health report for TX-001"
"What is the current weather risk for the grid?"
"Deploy crews to the highest-risk assets"
"Give me a full incident brief for the duty manager"
```

---

## What "Load-Bearing" Means Here

Remove the MCP server and Bob cannot answer a single question about the grid.
The five tools registered in `src/mcp_server/server.py` are the **only** way
to get risk scores, asset health, weather risk, crew assignments, or an
incident brief. Bob does not access any other data source — every answer it
gives flows through these tools.

```
[Bob CLI / Bob IDE]
    │
    │  Option A: Streamable HTTP  ──► https://grid-guardian-production.up.railway.app/mcp
    │  Option B: stdio (local)    ──► python -m mcp_server
    ▼
[Grid Guardian MCP Server]   ← src/mcp_server/server.py
    │
    ├── get_asset_health()       → risk_engine + sensor CSV
    ├── get_weather_risk()       → Open-Meteo live API  (real, not cached)
    ├── rank_at_risk_assets()    → risk_engine (ML + blast-radius + weather fusion)
    ├── generate_crew_plan()     → crew_planner (Haversine geospatial optimizer)
    └── generate_incident_brief()→ all of the above + watsonx.ai Granite
```

---

## Setup Option A — Remote (Recommended for Judges)

No local setup. The server is already running.

1. **Open your Bob IDE** settings and find the MCP configuration section
2. **Add the config block** from the "Quick Connect" section above
3. **Done** — all 5 tools are available. Ask Bob anything about the grid.

---

## Setup Option B — Local (Clone and Run)

1. **Install IBM Bob** — follow https://www.ibm.com/docs/en/bob

2. **Clone and install:**
   ```bash
   git clone https://github.com/Chetandabhi20/-bob-ai-hackathon-Lazy-Coders.git
   cd bob-ai-hackathon-Lazy-Coders/src
   python -m venv .venv
   .\.venv\Scripts\activate     # Windows
   # source .venv/bin/activate  # Mac/Linux
   pip install -r requirements.txt
   ```

3. **Create the Bob config** (`.bob` is git-ignored, create it manually):
   ```bash
   mkdir .bob
   cp mcp.example.json .bob/mcp.json
   ```
   Open `.bob/mcp.json`, copy the `_option_B_local` block into a clean
   `mcp.json`, and replace `<ABSOLUTE_PATH_TO_YOUR_CLONED_REPO>` with the
   actual path on your machine.

4. **Open Bob** in the repo root. The `grid-guardian` MCP server starts
   automatically via stdio.

5. **Optional — watsonx credentials:** Copy `src/.env.example` to `src/.env`
   and add real `WATSONX_API_KEY` / `WATSONX_PROJECT_ID`. Without them the
   system runs in STUB mode (still fully functional).

---

## Live Session Transcript

All outputs below were captured live. Timestamps and scores are real.

---

### Query 1 — "What is at risk right now? Show me the top 5 assets."

**Bob called:** `rank_at_risk_assets(top_n=5)`

**Real output:**
```json
{
  "ranked_assets": [
    {
      "asset_id": "TX-001",
      "failure_probability_14d": 1.0,
      "blast_radius_score": 17.9,
      "customers_at_risk": 8400,
      "critical_loads_at_risk": ["hospital"],
      "has_backup_path": false,
      "combined_priority_score": 50.7,
      "top_contributing_signals": [
        "declining_oil_quality",
        "rising_vibration_trend",
        "chronic_high_partial_discharge",
        "no_backup_path",
        "serves_hospital"
      ]
    },
    {
      "asset_id": "FDR-013",
      "failure_probability_14d": 1.0,
      "blast_radius_score": 4.7,
      "customers_at_risk": 1800,
      "critical_loads_at_risk": ["school"],
      "has_backup_path": false,
      "combined_priority_score": 42.8,
      "top_contributing_signals": [
        "declining_oil_quality",
        "rising_vibration_trend",
        "chronic_high_partial_discharge",
        "no_backup_path",
        "serves_school"
      ]
    },
    {
      "asset_id": "SUB-001",
      "failure_probability_14d": 0.0,
      "blast_radius_score": 48.2,
      "customers_at_risk": 37500,
      "critical_loads_at_risk": ["hospital", "water_treatment"],
      "has_backup_path": false,
      "combined_priority_score": 28.9,
      "top_contributing_signals": [
        "rising_vibration_trend",
        "declining_oil_quality",
        "chronic_high_partial_discharge",
        "no_backup_path",
        "serves_hospital",
        "serves_water_treatment"
      ]
    },
    {
      "asset_id": "SUB-003",
      "failure_probability_14d": 0.0,
      "blast_radius_score": 17.2,
      "customers_at_risk": 15100,
      "critical_loads_at_risk": ["school"],
      "has_backup_path": false,
      "combined_priority_score": 10.3,
      "top_contributing_signals": [
        "declining_oil_quality",
        "chronic_high_partial_discharge",
        "rising_vibration_trend",
        "no_backup_path",
        "serves_school"
      ]
    },
    {
      "asset_id": "TX-002",
      "failure_probability_14d": 0.0,
      "blast_radius_score": 17.0,
      "customers_at_risk": 9600,
      "critical_loads_at_risk": ["water_treatment"],
      "has_backup_path": false,
      "combined_priority_score": 10.2,
      "top_contributing_signals": [
        "declining_oil_quality",
        "rising_vibration_trend",
        "chronic_high_partial_discharge",
        "no_backup_path",
        "serves_water_treatment"
      ]
    }
  ],
  "total_assets": 25,
  "as_of_date": "2026-08-20"
}
```

**Why this proves Bob is load-bearing:** Bob called the ML risk engine, which
ran the Gradient Boosted Tree classifier + blast-radius graph traversal across
all 25 assets and returned a topology-aware ranked list. No static data — the
scores are computed live on every call.

---

### Query 2 — "Give me the full health report for TX-001."

**Bob called:** `get_asset_health(asset_id="TX-001")`

**Real output:**
```json
{
  "asset_id": "TX-001",
  "asset_name": "Riverside North Transformer",
  "asset_type": "transformer",
  "latest_readings": {
    "timestamp": "2026-08-19T08:00:00",
    "temperature_c": 69.9,
    "vibration_mm_s": 5.85,
    "partial_discharge_pc": 45.1,
    "oil_quality_index": 59.8
  },
  "failure_probability_14d": 1.0,
  "blast_radius_score": 17.9,
  "customers_at_risk": 8400,
  "critical_loads_at_risk": ["hospital"],
  "has_backup_path": false,
  "combined_priority_score": 50.7,
  "top_contributing_signals": [
    "declining_oil_quality",
    "rising_vibration_trend",
    "chronic_high_partial_discharge",
    "no_backup_path",
    "serves_hospital"
  ]
}
```

**Note on SUB-001 (blast-radius vs probability contrast):**
```json
{
  "asset_id": "SUB-001",
  "asset_name": "Riverside Substation",
  "failure_probability_14d": 0.0,
  "blast_radius_score": 48.2,
  "customers_at_risk": 37500,
  "critical_loads_at_risk": ["hospital", "water_treatment"],
  "combined_priority_score": 28.9
}
```

This is the **differentiator in action**: SUB-001 has a 0% failure probability
but still ranks #3 because its blast radius of 48.2 means a failure would cut
power to 37,500 customers including a hospital and water treatment plant with
no backup path. A naive probability-only system would ignore it entirely.

---

### Query 3 — "What is the current weather risk for the grid?"

**Bob called:** `get_weather_risk(lat=22.31, lon=73.18, days=7)`

**Real output (live from Open-Meteo API, not cached):**
```json
{
  "location": { "lat": 22.31, "lon": 73.18 },
  "forecast": [
    { "date": "2026-09-15", "temp_max_c": 30.6, "wind_speed_kph": 19.0, "precip_mm": 5.6,  "storm_risk": "low" },
    { "date": "2026-09-16", "temp_max_c": 30.8, "wind_speed_kph": 13.3, "precip_mm": 1.1,  "storm_risk": "low" },
    { "date": "2026-09-17", "temp_max_c": 31.0, "wind_speed_kph": 11.9, "precip_mm": 7.6,  "storm_risk": "low" },
    { "date": "2026-09-18", "temp_max_c": 30.1, "wind_speed_kph": 13.5, "precip_mm": 11.3, "storm_risk": "moderate" },
    { "date": "2026-09-19", "temp_max_c": 29.7, "wind_speed_kph": 7.2,  "precip_mm": 14.6, "storm_risk": "moderate" },
    { "date": "2026-09-20", "temp_max_c": 32.2, "wind_speed_kph": 8.6,  "precip_mm": 0.6,  "storm_risk": "low" },
    { "date": "2026-09-21", "temp_max_c": 31.5, "wind_speed_kph": 7.6,  "precip_mm": 0.9,  "storm_risk": "low" }
  ],
  "overall_risk": "moderate"
}
```

**Weather-risk fusion:** This `moderate` overall risk triggers a ×1.10
multiplier applied to every asset's combined priority score in `rank_assets()`.
Bob can see this compounding effect — assets already at high risk become even
more urgent when a storm is incoming.

---

### Query 4 — "Deploy crews to the highest-risk assets."

**Bob called:** `generate_crew_plan()`

**Real output:**
```json
{
  "generated_at": "2026-09-15T12:23:21Z",
  "assignments": [
    {
      "crew_id": "CREW-A",
      "assigned_asset_id": "TX-001",
      "priority_rank": 1,
      "eta_minutes": 6,
      "reason": "Highest combined_priority_score; active failure signature detected; no backup path; serves hospital; 8,400 customers at risk"
    },
    {
      "crew_id": "CREW-C",
      "assigned_asset_id": "FDR-013",
      "priority_rank": 2,
      "eta_minutes": 4,
      "reason": "Priority rank #2; active failure signature detected; no backup path; serves school"
    },
    {
      "crew_id": "CREW-D",
      "assigned_asset_id": "SUB-001",
      "priority_rank": 3,
      "eta_minutes": 12,
      "reason": "Priority rank #3; no backup path; serves hospital and water_treatment; 37,500 customers at risk"
    },
    {
      "crew_id": "CREW-B",
      "assigned_asset_id": "SUB-003",
      "priority_rank": 4,
      "eta_minutes": 22,
      "reason": "Priority rank #4; no backup path; serves school; 15,100 customers at risk"
    }
  ],
  "unassigned_high_risk_assets": ["TX-002", "FDR-001", "TX-005", "FDR-003"]
}
```

**What Bob did:** Called the Haversine geospatial optimizer, matched 4 crews
to the 4 highest-priority assets minimizing travel distance, computed ETAs
using road factor × urban speed, and flagged 4 unassigned high-risk assets
that need additional crews.

---

### Query 5 — "Give me a full incident brief for the duty manager."

**Bob called:** `generate_incident_brief(top_n=5)`

This tool chains all four previous tools internally:
`rank_assets()` → `generate_crew_plan()` → `summarize_risk_brief()` (watsonx.ai / stub)

**Real output brief:**
```
Duty Manager, I need to bring to your attention the critical situation with
TX-001, which has a combined priority score of 50.7 and poses a significant
risk to 8,400 customers, including a hospital. The asset has a blast radius of
17.9 and no backup path, making it our top priority. With a failure probability
of 100%, declining oil quality, rising vibration trend, and chronic high partial
discharge, we have a high-confidence failure signature that demands immediate
action.

Our crew pre-positioning plan has CREW-A en route to TX-001 with an estimated
time of arrival of 6 minutes. This deployment is crucial given the asset's
criticality and the potential consequences of a failure. Additionally, CREW-C
is heading to FDR-013, which has a combined priority score of 42.8 and serves
a school with 1,800 customers at risk. CREW-D and CREW-B are also deployed to
SUB-001 and SUB-003, respectively, although with longer ETAs due to their
slightly lower priority scores.

However, we have unassigned high-risk assets that require additional resources.
TX-002, FDR-001, TX-005, and FDR-003 are all without assigned crews, and while
their combined priority scores are lower, they still pose significant risks.
TX-002, for example, has a blast radius of 17.0 and serves a water treatment
facility with 9,600 customers at risk. I strongly recommend that you allocate
additional crews to these assets as soon as possible to mitigate potential
failures.

Right now, you should focus on allocating resources to TX-002, FDR-001,
TX-005, and FDR-003, and continue to monitor the status of TX-001, FDR-013,
SUB-001, and SUB-003 as our crews work to mitigate the risks associated with
these assets. With prompt action, we can reduce the likelihood of failures and
protect our customers.
```

**What produced this:** The IBM Granite model (via watsonx.ai) received a
structured prompt containing the 5 ranked assets, crew assignments, and weather
context, and synthesised the above executive brief. Without the MCP server
providing the structured data, this prompt cannot be built and the brief cannot
be generated.

---

## The Bob Dependency Chain (Proof of Load-Bearing)

```
Bob asks: "What needs attention right now?"
    │
    └─► MCP tool: generate_incident_brief(top_n=5)
            │
            ├─► rank_assets()          [ML model + blast-radius graph]
            │       ├─► GradientBoostingClassifier.predict_proba()
            │       ├─► BFS graph traversal (blast radius)
            │       └─► Open-Meteo live weather multiplier
            │
            ├─► generate_crew_plan()   [Haversine geospatial optimizer]
            │       └─► greedy nearest-crew assignment
            │
            └─► summarize_risk_brief() [watsonx.ai / Granite]
                    └─► structured prompt → natural language brief

Result: A complete, actionable incident brief citing real asset IDs,
        real sensor values, real crew ETAs, and live weather risk.
        None of this is possible without the MCP server.
```

---

## MCP Tools Reference

| Tool | Input | What it runs | Output |
|------|-------|-------------|--------|
| `get_asset_health` | `asset_id: str` | ML risk engine + sensor CSV lookup | Single-asset health, readings, signals |
| `get_weather_risk` | `lat, lon, days` | Live Open-Meteo API call | 7-day forecast + overall risk flag |
| `rank_at_risk_assets` | `top_n: int` | Full ML + blast-radius pipeline | Priority-ranked list of all 25 assets |
| `generate_crew_plan` | `crew_locations?` | Haversine optimizer across ranked assets | 4 crew assignments with ETAs + reasons |
| `generate_incident_brief` | `top_n: int` | All of the above + watsonx.ai Granite | Natural-language executive brief |
