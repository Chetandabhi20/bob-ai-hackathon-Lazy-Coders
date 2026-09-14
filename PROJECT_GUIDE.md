# PROJECT GUIDE — Grid Guardian: Power Outage Prediction & Equipment Failure Advisor

**Read this entire document before writing any code.** This is the single source of
truth for the project. It exists because the human running this project is working
solo with AI coding agents (Antigravity) and has no teammates to catch mistakes,
resolve ambiguity, or remember decisions made three sessions ago. If something in
this document conflicts with what you (the agent) think is a better approach, do
**not** silently deviate — flag the conflict to the user and wait for a decision.

This document is intentionally long and explicit. Do not skim it. Every phase below
is scoped to be small enough to complete, verify, and commit in a single agent
session without losing context or burning through a large fraction of your token
budget. **Never attempt to do two phases in one session.** Never attempt to "get
ahead" by writing code for a later phase while working on an earlier one, even if it
seems efficient — it creates undocumented dependencies that break the phase-by-phase
verification model this project relies on.

---

## 0. How To Use This Document (Agent Instructions)

1. At the start of any session, re-read Section 1 (Project Charter), Section 2
   (Model Tier Strategy), and the specific Phase you are working on. You do not
   need to re-read other phases unless your current phase explicitly references
   them.
2. Check `PROGRESS.md` (create it in Phase 0 if it doesn't exist yet) to see which
   phases/sub-tasks are marked done. Never redo a completed sub-task without being
   asked. Never mark a sub-task done unless every item in its "Definition of Done"
   checklist is genuinely satisfied.
3. Work on **exactly one sub-task at a time.** Produce your Antigravity Task List
   and Implementation Plan artifacts scoped to that single sub-task only — not the
   whole phase, and never the whole project.
4. Before writing code for a sub-task, restate (in your own task list) what you
   understand the sub-task's inputs, outputs, and Definition of Done to be. If
   anything is ambiguous, stop and ask the user rather than guessing.
5. After finishing a sub-task, run the verification steps listed for it, update
   `PROGRESS.md`, and produce a short Walkthrough artifact summarizing what changed
   and how it was verified. Then stop. Do not automatically continue to the next
   sub-task in the same session unless the user explicitly says to continue.
6. Follow the **Model Tier Strategy** in Section 2 for every sub-task. Using an
   overpowered model for a trivial task wastes budget that will be needed later
   for the harder phases (risk modeling, graph scoring, MCP/watsonx integration).
7. Never modify files under `.github/workflows/`, delete `CONTRIBUTING.md`, rename
   `submission.yaml`, or change the top-level repository structure described in
   Section 4. These are hard constraints from the hackathon submission template
   and violating them fails automated validation regardless of how good the code is.
8. If a sub-task is genuinely too large to fit your context/output budget in one
   pass, do not silently truncate it. Split it into smaller pieces yourself, note
   the split in `PROGRESS.md`, and complete one piece at a time.

---

## 1. Project Charter

### 1.1 The problem (from the official brief — do not paraphrase away the specifics)

Power transformer and substation failures cause blackouts costing utilities
$1M+/hour and affecting millions of people. Most utilities still use
calendar-based maintenance, while sensors already measuring temperature,
vibration, partial discharge, and oil quality show failure signatures weeks in
advance. Weather events compound the risk, but sensor data and weather
forecasts are never combined in time to act.

### 1.2 The challenge

Build a Bob-integrated solution that:
- Combines asset health sensor data, weather forecasts, and historical incident
  records
- Predicts outage-prone areas and at-risk equipment
- Ranks assets by **grid impact severity** (not just failure probability)
- Generates a prioritized maintenance and crew pre-positioning plan

### 1.3 Our differentiator (do not lose this while building)

Most competing teams will build "ingest data → ML failure probability → list."
Our differentiator is scoring risk by **blast radius**, not probability alone:
model the grid as a graph and compute how many customers / critical loads
(hospitals, water treatment plants, etc.) are affected if a given asset fails,
weighted by whether redundant backup paths exist. An asset with a lower failure
probability but a large, non-redundant blast radius should outrank a
high-probability asset that only affects a small, redundant area. This
mechanism must be visible and explained in the demo and docs — it is the single
most important thing judges should remember about this project.

### 1.4 Judging rubric — build to this, not around it

| # | Criterion | Points | What it rewards |
|---|---|---|---|
| 1 | Technical Implementation Quality | 25 | Real, working source code — not a mocked README |
| 2 | Innovation & Differentiation | 25 | The blast-radius mechanism, visible in code |
| 3 | Problem Depth & Vision | 15 | Docs show real understanding, not spec-restating |
| 4 | Working Demo & Functionality | 15 | It runs, end to end, reproducibly |
| 5 | IBM Bob Integration | 10 | Bob/watsonx is load-bearing in the running app |
| 6 | Documentation & Reproducibility | 10 | Someone else can run it from setup-guide.md alone |

Implication for how we build: **breadth of half-finished features scores worse
than depth on a smaller, fully-working, well-explained pipeline.** If time runs
short, cut scope (see "MVP cut line" in each phase) rather than leaving things
half-wired.

### 1.5 Data honesty policy

Real utility sensor/incident data is not publicly available. We will:
- **Simulate** sensor and historical incident data, built to reflect realistic
  degradation signatures (documented, not hidden).
- Use **real** live weather forecasts (Open-Meteo, no API key required) — this
  part must be genuinely real, since it's easy and it's the credibility anchor
  of the whole pipeline.
- State this honestly and explicitly in `docs/problem-statement.md`,
  `README.md`, and the `known_limitations` field. Overclaiming realism where
  the code doesn't back it up costs more points than admitting simulation.

---

## 2. Model Tier Strategy (read before every sub-task)

Antigravity supports multiple model tiers (e.g. a fast/cheap tier such as
Gemini 3 Flash, and higher-reasoning tiers such as Gemini 3 Pro or Claude
Sonnet/Opus). Treat high-tier model budget as a scarce resource that must last
through the hardest phases (risk modeling, graph algorithms, MCP tool
contracts, watsonx integration, debugging). Burning it on boilerplate means
running out of high-tier budget exactly when it matters most.

**Rule of thumb: match model tier to task complexity, not to habit.**

| Task type | Examples in this project | Recommended tier |
|---|---|---|
| Boilerplate / scaffolding | Creating folder structure, `.env.example`, config files, basic FastAPI app skeleton, repo README skeleton, simple CRUD endpoints | **Low tier** (fast/cheap model) |
| Mechanical data generation | Writing a synthetic CSV/JSON generator once the schema is fully specified (schemas are given in Section 5 — no design decisions left to make) | **Low tier** |
| Standard glue code | Wiring an already-defined MCP tool to an already-defined function, writing simple React components from a specified layout, basic API-to-frontend fetch calls | **Mid tier** |
| Design decisions with real trade-offs | Feature engineering for the risk model, choosing/tuning the ML approach, the blast-radius graph algorithm, MCP tool contract design, watsonx prompt design for the narrative layer | **High tier** |
| Debugging non-obvious failures | A bug that survives one fix attempt, integration failures between subsystems (e.g. MCP server ↔ watsonx ↔ frontend), anything touching more than 2 files at once | **High tier** |
| Documentation writing | `docs/*.md`, README polish | **Mid tier** (use high tier only for `solution-overview.md` since it must clearly explain the blast-radius mechanism — this is scored) |

Each sub-task below has a **Suggested Model Tier** tag. Treat it as a default,
not a hard rule — if a "low tier" task keeps failing, escalate rather than
retrying the same tier repeatedly (repeated low-tier failures waste more budget
than one high-tier pass).

---

## 3. Global Engineering Rules

These apply to every phase, no exceptions:

1. **One concern per commit.** Do not mix a bug fix with a new feature, or
   scaffolding with business logic, in the same commit.
2. **No silent schema drift.** If a sub-task needs a field that isn't in the
   schemas in Section 5, update Section 5 in this document first (as an edit
   proposal for the user to approve), then implement. Never invent a field
   ad hoc inside one file only.
3. **Every function that can fail, must fail loudly.** No bare `except: pass`.
   No swallowing errors to "make the demo look clean" — a working demo with a
   visible, handled error state scores better than one that silently returns
   wrong numbers.
4. **No fabricated credentials or fake "real" data sources.** If a watsonx/Bob
   API key or endpoint isn't available yet, build against a clearly-labeled
   mock/stub and leave a `TODO(user):` comment — never hardcode a plausible-
   looking fake key.
5. **Every sub-task must leave the repo in a runnable state.** Never commit
   code that breaks `docs/setup-guide.md`'s instructions, even mid-project.
6. **Keep the top-level repo structure exactly as defined by the hackathon
   submission template** (see Section 4). All project-specific code lives
   inside `src/`.
7. **Test as you go.** Each sub-task's Definition of Done includes a concrete
   verification step (a command to run, an output to check). Do not defer all
   testing to Phase 7 — Phase 7 is for end-to-end integration testing, not for
   discovering that Phase 2's model never actually ran.

---

## 4. Repository Structure (fixed — from the official submission template)

```
bob-ai-hackathon-[team-name]/
├── submission.yaml              ← DO NOT RENAME. Fill in Phase 8.
├── README.md                    ← Human-readable front page. Fill in Phase 8.
├── CONTRIBUTING.md              ← DO NOT DELETE.
├── .gitignore                   ← Already configured. Do not remove .env rule.
├── .github/workflows/validate.yml   ← DO NOT MODIFY.
│
├── src/                          ← ALL project code goes here (structure inside is ours to define, see 4.1)
│   ├── .env.example
│   └── README.md
│
├── docs/
│   ├── problem-statement.md
│   ├── solution-overview.md
│   ├── architecture.md
│   └── setup-guide.md
│
├── demo/
│   ├── demo-video-link.txt
│   ├── live-demo-url.txt
│   └── screenshots/
│
└── presentation/
    └── slides.pdf
```

### 4.1 Structure inside `src/` (ours to define — this is the real project)

```
src/
├── README.md                    ← what's in here, how it's organized
├── .env.example
├── data/
│   ├── generate_grid_topology.py
│   ├── generate_sensor_data.py
│   ├── generate_incident_history.py
│   ├── weather_client.py
│   └── generated/               ← output of generators, committed as sample data
│       ├── grid_topology.json
│       ├── sensor_readings.csv
│       └── incident_history.csv
│
├── risk_engine/
│   ├── features.py
│   ├── model.py                 ← trained failure-probability model
│   ├── blast_radius.py          ← the graph-based impact scoring (our differentiator)
│   ├── crew_planner.py          ← crew pre-positioning optimization
│   └── trained_model.pkl
│
├── mcp_server/
│   ├── server.py
│   ├── tools/
│   │   ├── get_asset_health.py
│   │   ├── get_weather_risk.py
│   │   ├── rank_at_risk_assets.py
│   │   └── generate_crew_plan.py
│   └── watsonx_client.py        ← narrative/explanation layer
│
├── frontend/
│   ├── (React app — dashboard, grid map, ranked list, crew plan view, chat panel)
│
└── tests/
    ├── test_blast_radius.py
    ├── test_risk_model.py
    └── test_mcp_tools.py
```

---

## 5. Data Contracts (fixed schemas — do not improvise fields)

Agents must implement exactly these schemas. If a later phase seems to need a
field not listed here, stop and propose an addition to this document rather
than adding it silently in one file.

### 5.1 Grid Topology (`grid_topology.json`)

```json
{
  "nodes": [
    {
      "id": "SUB-001",
      "type": "substation",              // "substation" | "transformer" | "feeder"
      "name": "Riverside Substation",
      "lat": 22.34,
      "lon": 73.19,
      "customers_served": 4200,
      "criticality_flags": ["hospital", "water_treatment"],  // [] if none
      "has_backup_path": false,
      "install_year": 2005
    }
  ],
  "edges": [
    { "from": "SUB-001", "to": "TX-014", "type": "feeder", "capacity_kw": 5000 }
  ]
}
```

### 5.2 Sensor Reading (`sensor_readings.csv` columns)

```
asset_id, timestamp, temperature_c, vibration_mm_s, partial_discharge_pc, oil_quality_index, label_failure_within_14d
```
- `label_failure_within_14d` is 0/1, used to train the model. Only present in
  historical/synthetic training data, never in "live" simulated data fed to the
  running app.

### 5.3 Historical Incident (`incident_history.csv` columns)

```
incident_id, asset_id, date, cause, duration_minutes, customers_affected, weather_condition_at_time
```

### 5.4 Weather Forecast (function return shape from `weather_client.py`)

```json
{
  "location": { "lat": 22.34, "lon": 73.19 },
  "forecast": [
    { "date": "2026-09-15", "temp_max_c": 38, "wind_speed_kph": 42, "precip_mm": 5, "storm_risk": "moderate" }
  ]
}
```

### 5.5 Risk Score Output (from `risk_engine` — the contract the MCP tools rely on)

```json
{
  "asset_id": "TX-014",
  "failure_probability_14d": 0.62,
  "blast_radius_score": 87.5,
  "customers_at_risk": 4200,
  "critical_loads_at_risk": ["hospital"],
  "has_backup_path": false,
  "combined_priority_score": 91.3,
  "top_contributing_signals": ["rising_partial_discharge", "no_backup_path", "storm_forecast_next_72h"]
}
```

### 5.6 Crew Plan Output

```json
{
  "generated_at": "2026-09-14T10:00:00Z",
  "assignments": [
    {
      "crew_id": "CREW-A",
      "assigned_asset_id": "TX-014",
      "priority_rank": 1,
      "eta_minutes": 22,
      "reason": "Highest combined_priority_score with no backup path and active storm forecast"
    }
  ],
  "unassigned_high_risk_assets": []
}
```

---

## 6. Phase Breakdown

Each phase is split into sub-tasks. **Complete and verify sub-tasks in order.**
Do not start Phase N+1 until every sub-task in Phase N has passed its
Definition of Done.

---

### PHASE 0 — Environment & Repo Scaffolding

**Goal:** A cloned, validated repo skeleton that passes the hackathon's
automated validation action, with nothing functional yet.

**0.1 — Create repo from template and initial structure**
- Suggested Model Tier: Low
- Inputs: none
- Outputs: repo cloned locally, `src/` subfolders from Section 4.1 created (empty
  `__init__.py`/`.gitkeep` placeholders as needed), `PROGRESS.md` created with a
  checklist mirroring this document's phases/sub-tasks
- Definition of Done:
  - `git status` shows the expected folder structure
  - `PROGRESS.md` exists and lists all phases/sub-tasks as unchecked
  - Nothing in the official top-level template files has been altered

**0.2 — Python + Node environment setup**
- Suggested Model Tier: Low
- Outputs: `src/.env.example` listing every env var this project will eventually
  need (`WEATHER_API_BASE`, `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`,
  `MCP_SERVER_PORT`, `FRONTEND_API_BASE_URL` — add more as later phases need
  them, but stub them now so setup-guide.md is accurate from the start),
  `src/README.md` explaining the folder layout from Section 4.1, a Python
  virtualenv config (`requirements.txt` placeholder) and a Node/React app
  scaffold (empty, no logic yet) in `src/frontend/`
- Definition of Done:
  - `pip install -r requirements.txt` runs with no errors (even if the file
    only has a couple of base packages so far)
  - `npm install` runs with no errors in `src/frontend/`
  - Nothing yet imports files that don't exist

**MVP cut line for Phase 0:** none — this phase is required in full, it's cheap.

---

### PHASE 1 — Synthetic Data & Real Weather Integration

**Goal:** All data the rest of the system depends on exists, is realistic, and
is documented as simulated where it is simulated.

**1.1 — Grid topology generator**
- Suggested Model Tier: Mid (some design judgment in making it "realistic")
- Inputs: schema in Section 5.1
- Outputs: `src/data/generate_grid_topology.py`, run once, output committed to
  `src/data/generated/grid_topology.json`. Target: 20–30 nodes, a mix of
  substations/transformers/feeders, at least 3 nodes flagged with
  `criticality_flags`, at least 2 nodes with `has_backup_path: true` and
  several without — the mix must be deliberately uneven, since the whole
  blast-radius story depends on some assets mattering more than others.
- Definition of Done:
  - Script runs standalone and produces valid JSON matching Section 5.1 exactly
  - Manually skim the JSON: does it look like a plausible small grid, not just
    randomly connected nodes? (e.g., feeders shouldn't form disconnected islands
    unless that's intentional)

**1.2 — Synthetic sensor data generator with degradation signatures**
- Suggested Model Tier: Mid (the "degradation signature" logic needs real thought)
- Inputs: asset list from 1.1, schema in Section 5.2
- Outputs: `src/data/generate_sensor_data.py` → `sensor_readings.csv`. For a
  subset of assets, inject a realistic pre-failure pattern (e.g., partial
  discharge and vibration trending upward over the 2–4 weeks before a labeled
  failure event; oil quality index degrading). For the rest, generate
  stable/noisy-but-healthy readings. Document the injected patterns in a
  comment block at the top of the script — this becomes evidence for
  `docs/solution-overview.md` in Phase 8.
- Definition of Done:
  - CSV matches schema exactly, no missing asset_ids
  - At least ~15% of assets have `label_failure_within_14d = 1` at some point,
    with a visibly different sensor trend leading up to it (spot check with a
    quick plot or by eyeballing the numbers — don't just trust the generator)

**1.3 — Historical incident generator**
- Suggested Model Tier: Low–Mid
- Outputs: `src/data/generate_incident_history.py` → `incident_history.csv`,
  cross-referenced with the failure events from 1.2 so the story is internally
  consistent (an asset that "failed" in sensor data should have a corresponding
  incident record)
- Definition of Done: every `asset_id` in incident_history.csv exists in
  grid_topology.json; every synthetic failure event in 1.2 has a matching
  incident row

**1.4 — Real weather client**
- Suggested Model Tier: Low (this is a straightforward API wrapper)
- Outputs: `src/data/weather_client.py`, a function
  `get_forecast(lat, lon, days=7) -> dict` matching Section 5.4, backed by a
  real call to Open-Meteo (no API key required) with basic error handling
  (network failure returns a clearly-labeled error object, not a silent
  default)
- Definition of Done:
  - Calling the function with the coordinates from 1.1's nodes returns real,
    current forecast data (verify by printing it, checking dates are actually
    upcoming)
  - A deliberately broken network call (e.g., unreachable host) fails loudly
    with a clear error, not a crash with an unhelpful traceback or a silent
    fallback that looks like real data

**MVP cut line for Phase 1:** If time is very short, 1.1–1.3 can use a smaller
asset count (e.g. 12–15 nodes) — do not cut 1.4 (real weather); that's the
cheapest credibility win in the whole project.

---

### PHASE 2 — Risk Scoring Engine (the technical + innovation core)

**Goal:** Given the Phase 1 data, produce the Risk Score Output (Section 5.5)
for every asset, combining a trained failure-probability model with the
blast-radius graph calculation.

**2.1 — Feature engineering**
- Suggested Model Tier: High (real judgment calls here)
- Inputs: `sensor_readings.csv`
- Outputs: `src/risk_engine/features.py` — functions that turn raw sensor time
  series into model-ready features per asset (e.g., rolling trend slopes for
  each sensor type, most recent reading, rate-of-change over last N days, days
  since install from topology)
- Definition of Done: running the feature function on the generated data
  produces one feature row per asset with no NaNs, and the failing assets from
  1.2 visibly show distinct feature values from healthy ones (sanity-check by
  comparing means between failed vs. healthy groups)

**2.2 — Failure-probability model**
- Suggested Model Tier: High
- Inputs: features from 2.1, labels from `sensor_readings.csv`
- Outputs: `src/risk_engine/model.py` (train + predict functions),
  `trained_model.pkl` committed. Use a gradient-boosted tree model
  (XGBoost/LightGBM/sklearn GradientBoosting — pick one, document the choice).
  Include a feature-importance / SHAP explanation function — this feeds
  `top_contributing_signals` in the output schema and matters for the
  "Technical Implementation" score.
- Definition of Done:
  - Model trains without error on the synthetic data
  - Predicted probabilities are meaningfully higher for known-failed assets
    than healthy ones (this is a sanity check, not a rigorous ML eval — we
    have synthetic data, don't over-engineer cross-validation here)
  - `top_contributing_signals` returns plausible, non-random feature names

**2.3 — Blast-radius graph scoring (THE differentiator — give this real care)**
- Suggested Model Tier: High
- Inputs: `grid_topology.json`
- Outputs: `src/risk_engine/blast_radius.py`. For each asset, compute: number
  of downstream customers affected if it fails (traverse the graph from that
  node outward), whether any critical-load flags are downstream, and whether a
  backup path exists that would reduce the effective impact. Produce a
  `blast_radius_score` that combines these (document the exact formula in a
  docstring — you will need to explain it in plain English in Phase 8).
- Definition of Done:
  - A hand-picked "obviously high impact" node (large customer count, no
    backup, serves the hospital-flagged node) scores clearly higher than a
    small leaf feeder with backup
  - The function handles disconnected/edge-case nodes without crashing

**2.4 — Combined priority score**
- Suggested Model Tier: Mid
- Outputs: function combining 2.2's probability and 2.3's blast radius into
  `combined_priority_score` per Section 5.5, plus a full `rank_assets()`
  function returning all assets sorted by this score
- Definition of Done: output list matches Section 5.5 schema exactly for every
  asset; ranking order is explainable in one sentence per asset (this becomes
  the `reason` text used later in the crew plan and narrative)

**2.5 — Crew pre-positioning planner**
- Suggested Model Tier: High (this is a real optimization problem, not glue code)
- Inputs: ranked assets from 2.4, a small hardcoded/generated list of crew
  starting locations, rough travel-time estimates (straight-line distance is
  fine — do not over-engineer real routing for a hackathon)
- Outputs: `src/risk_engine/crew_planner.py` implementing a simple greedy or
  assignment-based matching of crews to the highest-priority unassigned assets
  within reasonable travel time, matching Section 5.6's schema
- Definition of Done: given the ranked list and crew locations, produces a
  sensible, non-overlapping assignment with a human-readable `reason` per
  assignment; assets that can't be covered appear in
  `unassigned_high_risk_assets` rather than being silently dropped

**MVP cut line for Phase 2:** 2.1–2.4 are not cuttable — they are the technical
core the whole rubric leans on. If time is short, 2.5's optimization can be
reduced to a simple "nearest available crew to highest-ranked uncovered asset"
loop instead of anything more sophisticated — still counts as real, working
logic, just simpler.

---

### PHASE 3 — MCP Server

**Goal:** Expose Phase 2's functionality as callable MCP tools, so Bob (or any
MCP-aware chat interface) can call them.

**3.1 — MCP tool contract design**
- Suggested Model Tier: High (getting tool signatures right avoids painful
  rework later)
- Outputs: a short design note (add to `docs/architecture.md` draft) defining
  each tool's name, input parameters, and output schema, using the schemas
  from Section 5. Tools:
  - `get_asset_health(asset_id)` → recent sensor readings + probability
  - `get_weather_risk(lat, lon)` → forecast + qualitative risk flag
  - `rank_at_risk_assets(top_n)` → sorted list from 2.4
  - `generate_crew_plan(crew_locations)` → output from 2.5
- Definition of Done: a written contract exists and is internally consistent
  with Section 5 before any server code is written

**3.2 — Implement MCP server + tools**
- Suggested Model Tier: Mid (mechanical once 3.1 is settled)
- Outputs: `src/mcp_server/server.py` and one file per tool in
  `src/mcp_server/tools/`, each a thin wrapper calling Phase 2 functions
- Definition of Done: server starts without error; each tool can be called
  directly (via a test script, not yet through Bob) and returns schema-correct
  output for at least 2 different inputs

**3.3 — MCP server test suite**
- Suggested Model Tier: Mid
- Outputs: `src/tests/test_mcp_tools.py` covering each tool's happy path and
  one failure case (e.g., unknown `asset_id`)
- Definition of Done: tests pass; a genuinely invalid input produces a clear
  error response, not a crash

**MVP cut line:** none — this phase is required for the Bob Integration score.

---

### PHASE 4 — watsonx.ai Narrative Layer (Bob Integration must-have)

**Goal:** Turn structured risk/crew-plan output into a natural-language brief,
via watsonx.ai, so the "IBM Bob Integration" score reflects a real, working
connection rather than a name-drop.

**4.1 — watsonx client**
- Suggested Model Tier: High (prompt design has real trade-offs)
- Outputs: `src/mcp_server/watsonx_client.py` — a function
  `summarize_risk_brief(ranked_assets, crew_plan) -> str` that calls watsonx.ai
  with a prompt built from the structured data, returning a short natural-
  language incident brief. If credentials aren't available yet, build this
  against a clearly-labeled stub function with the exact same signature, so it
  can be swapped in without touching any calling code (see Global Rule #4 on
  never faking credentials).
- Definition of Done: given sample ranked_assets/crew_plan data, produces a
  coherent, non-generic brief that references the actual top-ranked asset by
  ID and the actual reasoning (blast radius / no backup / storm forecast) —
  not a templated paragraph that ignores the input

**4.2 — Wire narrative layer into an MCP tool**
- Suggested Model Tier: Mid
- Outputs: a `generate_incident_brief()` MCP tool combining 3.2's ranking tool
  output with 4.1's summarizer
- Definition of Done: calling this one tool end-to-end (rank → summarize)
  produces a real, readable brief from live-generated data, no manual
  stitching required

**MVP cut line:** if watsonx credentials are unavailable during the hackathon
window, keep the stub clearly labeled and demo it as "narrative layer, ready to
swap in live watsonx" rather than hiding the limitation — say this explicitly
in `known_limitations`. Do not fake real API output.

---

### PHASE 5 — Frontend Dashboard

**Goal:** A React app visualizing the grid, ranked risk, and the crew plan —
this is what judges see first and remember.

**5.1 — Grid map / graph view**
- Suggested Model Tier: Mid
- Outputs: a React component rendering `grid_topology.json` as a simple
  node-link diagram or map, color-coded by `combined_priority_score`
- Definition of Done: loads real generated data (not hardcoded mock JSON),
  colors visibly differ between high- and low-risk nodes

**5.2 — Ranked asset list + detail view**
- Suggested Model Tier: Mid
- Outputs: a sortable list of assets by `combined_priority_score`; clicking an
  asset shows its sensor trend chart and `top_contributing_signals`
- Definition of Done: clicking through 2–3 different assets shows genuinely
  different data, not a static mock

**5.3 — Crew plan view**
- Suggested Model Tier: Mid
- Outputs: a view showing crew assignments from 2.5/Section 5.6, with the
  `reason` text visible per assignment
- Definition of Done: matches the live output of `generate_crew_plan`

**5.4 — Chat panel (Bob-style interface)**
- Suggested Model Tier: High (this is the piece that has to visibly call MCP
  tools live, on camera, for the demo — get the wiring right)
- Outputs: a minimal chat UI in the React app that sends a user's natural-
  language question to a small backend route, which either (a) invokes the
  actual Bob CLI against the MCP server, or (b) directly calls the same MCP
  tools and passes the result through the watsonx summarizer — pick whichever
  is more reliably demoable given available time/credentials, and document
  which one was chosen and why in `docs/architecture.md`
- Definition of Done: typing a question like "which assets need attention this
  week and where should crews go?" produces a real answer sourced from live
  tool calls, visible in the UI, reproducible on a second try

**MVP cut line:** 5.1–5.3 are required. If 5.4's full Bob-CLI wiring proves
unreliable close to the deadline, fall back to option (b) above (direct MCP
tool calls from the chat panel) rather than cutting the chat feature entirely
— the Bob Integration score depends on this being visibly functional.

---

### PHASE 6 — End-to-End Integration Pass

**Goal:** Everything built in isolation across Phases 1–5 now runs together,
start to finish, with no manual intervention between steps.

**6.1 — Full pipeline smoke test**
- Suggested Model Tier: High (integration bugs are exactly the "touches >2
  files" case that needs real reasoning, not pattern-matched fixes)
- Steps: run data generators → start MCP server → start frontend → ask a
  question through the chat panel → confirm the full chain (data → risk engine
  → MCP tool → watsonx → UI) produces a correct, live answer
- Definition of Done: a fresh clone of the repo, following only
  `docs/setup-guide.md` (written in Phase 8, draft it now if not yet written),
  can reproduce this end-to-end without any undocumented manual steps

**6.2 — Fix integration gaps**
- Suggested Model Tier: High
- Outputs: whatever code changes are needed to close gaps found in 6.1
- Definition of Done: 6.1 passes cleanly twice in a row (once is luck, twice is
  reproducible)

---

### PHASE 7 — Automated Tests & Validation Compliance

**7.1 — Unit test pass**
- Suggested Model Tier: Mid
- Outputs: `src/tests/` covers `blast_radius.py`, `model.py`, MCP tools (some
  already exist from 2.x/3.3 — fill gaps)
- Definition of Done: `pytest` runs green

**7.2 — Confirm hackathon validation action passes**
- Suggested Model Tier: Low
- Steps: push to the repo, check the Actions tab for the `Validate Submission`
  workflow
- Definition of Done: green check — `submission.yaml` fields filled,
  `docs/setup-guide.md` exists, `demo/demo-video-link.txt` exists (placeholder
  is fine until Phase 9, but must exist)

---

### PHASE 8 — Documentation (10 pts + supports Problem Depth's 15 pts)

**8.1 — `submission.yaml`**
- Suggested Model Tier: Low–Mid
- Fill every required field. `key_features` must explicitly name the
  blast-radius scoring and crew optimization — not generic phrases like
  "AI-powered dashboard."

**8.2 — `README.md`**
- Suggested Model Tier: Mid
- Fill every section from the template guide (Team, Problem, Solution, Key
  Features, Tech Stack, How to Run, Demo, Known Limitations, What We're Most
  Proud Of). Search the file for `[` before finishing — no leftover
  placeholders.

**8.3 — `docs/problem-statement.md`**
- Suggested Model Tier: Mid
- Go beyond the brief: name the specific audience (grid ops centers, on-call
  crews), why calendar-based maintenance fails, quantify pain using the
  $1M+/hour figure, explain why weather+sensor fusion isn't done today.

**8.4 — `docs/solution-overview.md`**
- Suggested Model Tier: High (this is the one doc that must sell the
  differentiator clearly — worth spending better model budget here)
- Explicitly explain the blast-radius mechanism in plain English, why it beats
  probability-only ranking, and the crew optimization logic.

**8.5 — `docs/architecture.md`**
- Suggested Model Tier: Mid
- Diagram (Mermaid, matching the pattern: User → Bob/Chat → MCP Server → risk
  engine/data/watsonx → response), component table, data flow description,
  note on which Bob-integration option (3.2 direct vs full CLI) was used and
  why.

**8.6 — `docs/setup-guide.md`**
- Suggested Model Tier: Mid, but **verify on a genuinely clean environment or
  fresh terminal** before finishing — this is explicitly called out as the
  most-checked doc by judges
- Every prerequisite, every env var (copied from `.env.example`), exact
  install/run commands, how to verify it's working, a troubleshooting table.

**8.7 — Known limitations, honestly stated**
- Suggested Model Tier: Low
- State plainly: sensor/incident data is simulated (with the degradation
  signature methodology briefly described), weather is real-time, watsonx
  integration status (live vs. stubbed) as of submission.

---

### PHASE 9 — Demo Video, Screenshots, Presentation, Final Submission

**9.1 — Screenshots**
- Suggested Model Tier: Low (manual/UI task, minimal agent reasoning needed)
- At least 3, named sequentially per the template
  (`01-home-dashboard.png`, `02-...`, `03-...`)

**9.2 — Demo video (3–5 min)**
- Not primarily an agent task, but agents can prep the script:
  1. ~20s: state the problem and cost
  2. ~60s: ask the chat interface a real question live, show it calling tools
  3. ~90s: show ranked risk list, click into an asset, explain blast radius
  4. ~60s: show the generated crew plan
  5. ~20s: close on impact
- Upload to an accepted platform (YouTube unlisted / Loom / Box / Drive
  view-only) with "anyone with link" permissions, and put the real URL in
  `demo/demo-video-link.txt` (search for placeholder text before final push).

**9.3 — `demo/live-demo-url.txt`**
- Real deployed URL, or literally the string `NOT DEPLOYED` if not deployed.

**9.4 — `presentation/slides.pdf`**
- Suggested Model Tier: Mid for content drafting
- Order: Problem → Solution → Demo/architecture → IBM Bob integration →
  Impact, per the template guide.

**9.5 — Final checklist pass**
- Suggested Model Tier: Low
- Walk the full Submission Checklist from the template guide line by line
  before submitting: no `[placeholder]` text, no `.env` committed, no
  `node_modules`/`.venv` committed, Actions tab green, repo set to Public,
  entry form submitted with the correct repo URL before the deadline.

---

## 7. Anti-Patterns To Avoid (agents: read this twice)

- **Do not** start Phase 5 (frontend) before Phase 2's risk engine produces
  real output. A dashboard wired to mock JSON that never gets swapped for real
  data is the single most common hackathon failure mode and it is directly
  penalized by the rubric ("reads source code, not just the README").
- **Do not** let one sub-task's session sprawl into "while I'm here, let me
  also fix/improve X." Note X in `PROGRESS.md` under a "Noticed, not yet
  scheduled" section and stop.
- **Do not** regenerate synthetic data files after Phase 2's model has been
  trained against them, unless you also retrain the model in the same session
  — a mismatched data/model pair silently produces nonsense scores that are
  very hard to debug later.
- **Do not** treat `docs/setup-guide.md` as something to write from memory of
  what you built — actually re-run it.
- **Do not** use a high-tier model to write a `.env.example` file or similarly
  trivial scaffolding; save that budget.
- **Do not** silently expand scope on the crew-planning optimization (Section
  2.5) into something elaborate — a clean, explainable greedy assignment beats
  a sophisticated solver that the user (you, later, explaining it to judges)
  can't clearly describe in one sentence.

---

## 8. `PROGRESS.md` Convention (create this in Phase 0.1)

```markdown
# Progress

## Phase 0 — Scaffolding
- [ ] 0.1 Repo structure
- [ ] 0.2 Environment setup

## Phase 1 — Data
- [ ] 1.1 Grid topology
- [ ] 1.2 Sensor data
- [ ] 1.3 Incident history
- [ ] 1.4 Weather client

...(mirror all phases/sub-tasks from Section 6)...

## Noticed, not yet scheduled
- (things agents spot mid-task that are out of scope for the current sub-task)
```

Update this file at the end of every sub-task. This is the mechanism that lets
you (or a fresh agent session with no memory of prior sessions) pick up exactly
where things left off without re-deriving context from scratch.

---

## 9. Quick Reference — What To Do If You Get Stuck

1. Re-read this document's relevant Phase section fully before assuming
   something is missing from it.
2. Check `PROGRESS.md` for whether a dependency you need was actually marked
   done and verified, not just attempted.
3. If a schema in Section 5 seems to be missing something you need, propose an
   explicit addition to this document and flag it to the user — do not
   improvise a field silently.
4. If stuck on the same error after two attempts at the suggested model tier,
   escalate to the next tier up rather than retrying identically.
5. If genuinely blocked (e.g., missing watsonx credentials), implement against
   a clearly labeled stub per Global Rule #4, note the blocker in
   `PROGRESS.md`, and continue with everything else that doesn't depend on it.
