# 🚀 Grid Guardian

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | Lazy Coders |
| **Track** | AI |
| **Team Lead** | Chetan — chetan@example.com |
| **Members** | (Solo) |

---

## 🎯 Problem Statement

Electrical grid operators struggle to predict equipment failures and proactively deploy maintenance crews, leading to widespread outages, costly emergency repairs, and increased risks to critical infrastructure. Currently, maintenance is calendar-based, and dispatching crews post-failure increases the $1M+/hour downtime costs.

---

## 💡 Solution

Grid Guardian is an AI-powered electrical-grid risk-assessment tool that predicts equipment failures and scores the downstream "blast radius" impact. It provides actionable crew pre-positioning plans and a watsonx-powered narrative interface via an MCP server integration.

---

## ✨ Key Features

- **Predictive failure modeling:** Analyzes sensor telemetry to predict component failure within a 14-day window.
- **Blast-radius scoring:** A differentiator that maps grid topology to calculate downstream impact, prioritizing critical loads (like hospitals) and un-backed-up customers over redundant lines.
- **Geospatial crew pre-positioning:** Optimizes crew deployment based on risk rank and distance.
- **watsonx.ai integration:** Summarizes incidents into natural language, actionable briefs via IBM Granite.
- **IBM Bob as the primary interface (MCP):** Bob is the conversational control plane — every risk query, crew deployment, and incident brief flows through 5 registered MCP tools. See [`docs/bob-demo.md`](docs/bob-demo.md) for a full live session transcript.

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python, JavaScript |
| **Frameworks** | FastAPI, React, Vite |
| **IBM Technologies** | watsonx.ai, IBM Bob, Granite Models |
| **Databases** | None (File-based JSON/CSV data storage) |
| **Other** | FastMCP, scikit-learn, Open-Meteo |

---

## 📁 Repository Structure

```
├── src/                  # All source code
├── docs/                 # Written documentation
│   ├── problem-statement.md
│   ├── solution-overview.md
│   ├── architecture.md
│   └── setup-guide.md
├── demo/                 # Demo artifacts
│   ├── screenshots/      # App screenshots
│   └── demo-video-link.txt  # Link to demo video
├── presentation/         # Slide deck
└── submission.yaml       # Structured submission metadata
```

---

## ⚡ How to Run

> **For the full instructions, see [`docs/setup-guide.md`](docs/setup-guide.md)**

```bash
# 1. Clone the repo
git clone https://github.com/Chetandabhi20/-bob-ai-hackathon-Lazy-Coders.git
cd -bob-ai-hackathon-Lazy-Coders

# 2. Set up Python backend
cd src
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 3. Start Backend Server
python -m api.server

# 4. Start React Frontend (in a second terminal)
cd ../src/frontend
npm install
npm run dev
```

---

## 🤖 IBM Bob Integration

Bob is the **primary interface** for Grid Guardian. The MCP server exposes 5 tools that Bob calls natively — no web UI required to use the full analytical pipeline.

```
Ask Bob: "Give me a full incident brief for the duty manager"
    → generate_incident_brief() chains: rank_assets() + generate_crew_plan() + watsonx.ai
    → Returns a natural-language brief citing real asset IDs, sensor values, and crew ETAs
```

| Bob Query | MCP Tool Called | What it does |
|---|---|---|
| "What assets are at risk?" | `rank_at_risk_assets` | ML + blast-radius scoring across 25 assets |
| "Health of TX-001" | `get_asset_health` | Sensor readings + failure probability + risk signals |
| "What's the weather risk?" | `get_weather_risk` | Live Open-Meteo forecast + storm risk flag |
| "Deploy crews now" | `generate_crew_plan` | Haversine geospatial optimizer → crew assignments + ETAs |
| "Give me a full incident brief" | `generate_incident_brief` | All of the above + watsonx.ai Granite narrative |

> **Full live session with real output:** [`docs/bob-demo.md`](docs/bob-demo.md)

---

## 🖥️ Demo

| Artifact | Link |
|---|---|
| 📹 Demo Video | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo | [See demo/live-demo-url.txt](demo/live-demo-url.txt) |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/) |
| 📊 Presentation | [See presentation/slides.pdf](presentation/) |
| 🤖 Bob Live Session | [`docs/bob-demo.md`](docs/bob-demo.md) |

---

## ⚠️ Known Limitations

- Real watsonx integration requires valid credentials; currently falls back to a template-driven `[STUB MODE]` to guarantee a working demo.
- Predictive model uses a synthetic dataset of 2,250 rows due to hackathon time constraints.
- Graph/map view relies on pre-generated static coordinates rather than real GIS data.

---

## 🏅 What We're Most Proud Of

We are most proud of the **Blast-Radius Scoring System**. Instead of just returning probability like most generic ML models, we mapped the grid topology and created a domain-aware scoring mechanism that factors in un-backed-up customers and critical infrastructure (hospitals, schools) downstream. It fundamentally changes the output from "Transformer X will fail" to "Transformer X failing will drop a hospital, send a crew now."

---
