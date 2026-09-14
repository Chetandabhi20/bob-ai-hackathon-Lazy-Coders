# Grid Guardian — Source Code

All project code lives in this directory. Here's how it's organized:

```
src/
├── .env.example                 ← Environment variable template (copy to .env)
├── data/                        ← Data generation & weather integration
│   ├── generate_grid_topology.py    — Builds the synthetic grid graph (Phase 1.1)
│   ├── generate_sensor_data.py      — Synthetic sensor readings with degradation signatures (Phase 1.2)
│   ├── generate_incident_history.py — Synthetic historical incidents (Phase 1.3)
│   ├── weather_client.py            — Live weather forecasts via Open-Meteo (Phase 1.4)
│   └── generated/                   — Output of generators, committed as sample data
│       ├── grid_topology.json
│       ├── sensor_readings.csv
│       └── incident_history.csv
│
├── risk_engine/                 ← Core analytics (Phase 2)
│   ├── features.py                  — Feature engineering from raw sensor time series
│   ├── model.py                     — Failure-probability model (gradient-boosted tree)
│   ├── blast_radius.py              — Graph-based impact scoring (our key differentiator)
│   ├── crew_planner.py              — Crew pre-positioning optimization
│   └── trained_model.pkl            — Serialized trained model
│
├── mcp_server/                  ← MCP tool server (Phase 3–4)
│   ├── server.py                    — FastMCP server entry point
│   ├── tools/                       — One file per MCP tool
│   │   ├── get_asset_health.py
│   │   ├── get_weather_risk.py
│   │   ├── rank_at_risk_assets.py
│   │   └── generate_crew_plan.py
│   └── watsonx_client.py           — watsonx.ai narrative/explanation layer
│
├── frontend/                    ← React dashboard (Phase 5)
│   └── (Vite + React app — grid map, ranked list, crew plan, chat panel)
│
└── tests/                       ← Test suite (Phase 7)
    ├── test_blast_radius.py
    ├── test_risk_model.py
    └── test_mcp_tools.py
```

## Quick Start

```bash
# 1. Python setup
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. Generate sample data
python -m data.generate_grid_topology
python -m data.generate_sensor_data
python -m data.generate_incident_history

# 3. Frontend setup
cd frontend
npm install
npm run dev

# 4. MCP server
python -m mcp_server.server
```

See `docs/setup-guide.md` for full instructions.
