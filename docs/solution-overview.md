# Solution Overview

## What We Built

Grid Guardian is an intelligent grid risk-assessment system that moves utility maintenance from a reactive/calendar-based approach to a proactive, risk-aware model. By combining sensor telemetry, grid topology (how lines are connected), and geospatial crew tracking, it identifies which assets are most likely to fail *and* which of those failures would cause the most catastrophic damage. It then dispatches crews optimally and uses generative AI to provide human-readable incident briefs.

## How It Works

Grid Guardian processes data through a four-stage pipeline:

1. **Telemetry Analysis (Predictive Model):** We ingest 90 days of sensor readings (temperature, vibration, partial discharge, oil quality) from 25 assets and extract key features (e.g., 14-day trends, standard deviations, and recent delta ratios). An sklearn Gradient Boosted Tree computes a 14-day probability of failure for each asset.
2. **Blast-Radius Scoring (The Differentiator):** A failure probability alone isn't enough. We map the grid topology as a directed graph. For every asset, we run a graph traversal to find all downstream assets that would lose power if it failed. The "Blast Radius" score (0-100) heavily penalizes assets that support critical infrastructure (hospitals, water treatment) and assets without redundant backup paths.
3. **Crew Optimization:** We combine the failure probability (40% weight) and the blast radius score (60% weight) into a final Priority Score. A geospatial optimizer then matches the 4 highest-priority assets to the 4 available maintenance crews, minimizing driving distance using the Haversine formula while ensuring the highest risks are covered first.
4. **Bob Integration & watsonx:** We expose these algorithms as standard MCP tools. The frontend chat interface queries these tools and pipes the results to an IBM Granite model to generate an actionable, natural-language incident brief.

## Architecture Diagram

> See [`architecture.md`](architecture.md) for the detailed diagram.

```
[Sensors/Weather] → [Risk Engine] → [FastMCP Server] ↔ [React Dashboard]
                                         ↓
                            [watsonx.ai (Granite Model)]
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Blast Radius > Probability** | A 40% chance of taking down a hospital is fundamentally more urgent than a 60% chance of taking down a residential cul-de-sac. |
| **FastMCP over HTTP APIs** | Exposing the tools via the Model Context Protocol (MCP) ensures that IBM Bob and future AI agents can natively invoke our analytical models without custom API mapping. |
| **Gradient Boosted Trees** | For tabular sensor data, gradient boosting is extremely effective, fast to train, and avoids the overhead of deep learning for a synthetic dataset. |
| **React Frontend with proxy** | By using a FastAPI backend to call the same Python functions the MCP server uses, we decouple the UI from the Bob CLI while still ensuring they rely on the exact same risk engine logic. |

## IBM Technologies Used

- **IBM Bob (via FastMCP):** We built four tools (`get_asset_health`, `get_weather_risk`, `rank_at_risk_assets`, `generate_crew_plan`) that comply with the Model Context Protocol, enabling intelligent agentic orchestration of grid repairs.
- **watsonx.ai:** Used the `ibm-watsonx-ai` Python SDK to invoke a Granite model. The model receives a structured context window of ranked assets and crew deployments and synthesizes an executive summary for operations managers.
