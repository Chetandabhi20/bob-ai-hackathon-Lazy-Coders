"""
watsonx.ai Narrative Client for Grid Guardian
===============================================

Turns structured risk-engine and crew-plan output into a natural-language
incident brief, via IBM watsonx.ai (when credentials are available) or a
clearly-labeled local stub (when they are not).

Public API:
    summarize_risk_brief(ranked_assets, crew_plan) -> str

Design rationale
-----------------
The prompt is the critical piece. It must:
  1. Present the structured data (top assets, scores, signals, crew plan) in a
     compact format the LLM can read.
  2. Instruct the model to produce a short (3–5 paragraph), actionable brief
     that a grid operations manager would actually use:
       - Which assets need attention NOW and why (blast radius, not just prob)
       - What crews are en route and estimated arrival
       - What weather is compounding the risk
  3. Avoid generic filler; every sentence should reference a real asset ID,
     score, or signal from the input data.

Stub mode
----------
When WATSONX_API_KEY is not set or is a placeholder, the module falls back to
a structured-template generator that still produces a brief referencing the
real data — it just doesn't go through an LLM. This is clearly labeled in the
output with a "[STUB MODE]" prefix and documented in known_limitations.

To swap in live watsonx: set WATSONX_API_KEY, WATSONX_PROJECT_ID, and
WATSONX_URL in your .env file with real credentials. No code changes needed.
"""

import os
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────

# watsonx model to use for text generation (IBM Granite is a safe default)
WATSONX_MODEL_ID = os.environ.get("WATSONX_MODEL_ID", "meta-llama/llama-3-3-70b-instruct")

# Maximum tokens for the generated brief
MAX_TOKENS = 600


def _credentials_available() -> bool:
    """Check if real watsonx credentials are configured."""
    api_key = os.environ.get("WATSONX_API_KEY", "")
    return (
        bool(api_key)
        and api_key != "your_api_key_here"
        and not api_key.startswith("your_")
    )


# ── Prompt Construction ───────────────────────────────────────────────────

def _build_prompt(ranked_assets: list[dict], crew_plan: dict) -> str:
    """
    Build the prompt that will be sent to watsonx.ai.

    The prompt is designed to produce a concise, actionable incident brief
    for a grid operations manager. It embeds the structured data directly
    so the LLM has concrete numbers to cite.
    """
    # Extract weather context from the first ranked asset (all share the same value)
    weather_risk = ranked_assets[0].get("weather_risk", "low") if ranked_assets else "low"
    weather_multiplier = ranked_assets[0].get("weather_multiplier", 1.0) if ranked_assets else 1.0
    weather_block = (
        f"LIVE WEATHER CONTEXT:\n"
        f"  Storm risk for grid area: {weather_risk.upper()} "
        f"(priority scores scaled by ×{weather_multiplier:.2f})\n"
        + (
            "  ⚠️ Incoming storm conditions are actively increasing failure urgency for all assets.\n"
            if weather_risk in ("moderate", "high") else
            "  Weather conditions are within normal operational tolerance.\n"
        )
    )

    # Format top assets
    top_assets = ranked_assets[:5]
    asset_lines = []
    for i, a in enumerate(top_assets, 1):
        signals = ", ".join(a.get("top_contributing_signals", [])[:4])
        backup = "NO backup path" if not a.get("has_backup_path") else "has backup path"
        critical = ", ".join(a.get("critical_loads_at_risk", [])) or "none"
        asset_lines.append(
            f"  {i}. {a['asset_id']}: "
            f"failure_prob={a['failure_probability_14d']:.1%}, "
            f"blast_radius={a['blast_radius_score']:.1f}, "
            f"combined_score={a['combined_priority_score']:.1f}, "
            f"customers_at_risk={a['customers_at_risk']:,}, "
            f"critical_loads=[{critical}], "
            f"{backup}, "
            f"signals=[{signals}]"
        )
    asset_block = "\n".join(asset_lines)

    # Format crew assignments
    assignment_lines = []
    for a in crew_plan.get("assignments", []):
        assignment_lines.append(
            f"  - {a['crew_id']} -> {a['assigned_asset_id']} "
            f"(rank #{a['priority_rank']}, ETA {a['eta_minutes']}min): "
            f"{a['reason']}"
        )
    assignment_block = "\n".join(assignment_lines) or "  (no assignments)"

    unassigned = crew_plan.get("unassigned_high_risk_assets", [])
    unassigned_block = ", ".join(unassigned) if unassigned else "none"

    prompt = f"""You are an AI assistant for a power grid operations center. Write a concise incident brief (3-5 paragraphs) for the duty manager based on the following real-time risk assessment data.

{weather_block}
TOP AT-RISK ASSETS (ranked by combined priority score, weather-adjusted):
{asset_block}

CREW PRE-POSITIONING PLAN:
{assignment_block}
  Unassigned high-risk assets: {unassigned_block}
  Generated at: {crew_plan.get('generated_at', 'N/A')}

INSTRUCTIONS:
- Address the duty manager directly.
- Lead with the most critical asset and WHY it's critical (blast radius, customer impact, lack of backup path — not just failure probability).
- If weather risk is moderate or high, mention it explicitly and explain how it compounds the sensor-based risk.
- Mention specific asset IDs, scores, and customer counts.
- Describe the crew deployment plan with ETAs.
- If there are unassigned high-risk assets, flag them as requiring additional resources.
- Keep it actionable — what should the manager do RIGHT NOW?
- Do NOT use generic phrases like "the system has identified risks." Be specific.
- Write 3-5 short paragraphs. No bullet points, no headers, no markdown."""

    return prompt


# ── Live watsonx.ai Path ──────────────────────────────────────────────────

def _call_watsonx(prompt: str) -> str:
    """
    Call watsonx.ai to generate the incident brief.

    Uses the IBM watsonx.ai Python SDK with the foundation models API.
    Requires WATSONX_API_KEY, WATSONX_PROJECT_ID, and WATSONX_URL
    environment variables to be set with real credentials.

    Raises:
        RuntimeError: If the API call fails.
    """
    try:
        from ibm_watsonx_ai import APIClient, Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
    except ImportError as e:
        raise RuntimeError(
            "ibm-watsonx-ai package not installed. "
            "Install it with: pip install ibm-watsonx-ai"
        ) from e

    api_key = os.environ.get("WATSONX_API_KEY", "")
    project_id = os.environ.get("WATSONX_PROJECT_ID", "")
    url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key or not project_id:
        raise RuntimeError(
            "WATSONX_API_KEY and WATSONX_PROJECT_ID must be set. "
            "See src/.env.example for details."
        )

    try:
        credentials = Credentials(url=url, api_key=api_key)
        client = APIClient(credentials=credentials, project_id=project_id)

        model = ModelInference(
            model_id=WATSONX_MODEL_ID,
            api_client=client,
            project_id=project_id,
        )

        response = model.chat(
            messages=[{"role": "user", "content": prompt}],
            params={
                "max_tokens": MAX_TOKENS,
                "temperature": 0.3,
                "top_p": 0.9,
            },
        )

        # chat() returns a dict; extract the assistant message content
        result = (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        if not result:
            raise RuntimeError(
                "watsonx.ai returned an empty response. "
                "Check model availability and quota."
            )

        return result

    except Exception as e:
        raise RuntimeError(
            f"watsonx.ai API call failed: {type(e).__name__}: {e}"
        ) from e


# ── Stub Path (no credentials) ───────────────────────────────────────────

def _generate_stub_brief(ranked_assets: list[dict], crew_plan: dict) -> str:
    """
    Generate a data-driven incident brief WITHOUT calling watsonx.ai.

    This is a clearly-labeled stub used when watsonx credentials are not
    available. It produces a coherent, non-generic brief that references
    actual asset IDs, scores, and reasoning from the input data.

    TODO(user): Replace with live watsonx output by setting WATSONX_API_KEY,
    WATSONX_PROJECT_ID, and WATSONX_URL in your .env file.
    """
    top = ranked_assets[:5] if ranked_assets else []
    assignments = crew_plan.get("assignments", [])
    unassigned = crew_plan.get("unassigned_high_risk_assets", [])

    if not top:
        return (
            "[STUB MODE — watsonx credentials not configured]\n\n"
            "No at-risk assets detected in the current assessment window."
        )

    # Extract weather context
    weather_risk = top[0].get("weather_risk", "low")
    weather_multiplier = top[0].get("weather_multiplier", 1.0)

    # ── Paragraph 1: Lead with the most critical asset ────────────────
    a1 = top[0]
    signals_str = " and ".join(a1.get("top_contributing_signals", [])[:3])
    backup_str = (
        "critically, it has no backup power path"
        if not a1.get("has_backup_path")
        else "although a backup path exists"
    )
    critical_loads = a1.get("critical_loads_at_risk", [])
    critical_str = ""
    if critical_loads:
        loads = " and ".join(critical_loads)
        critical_str = f", including a {loads} facility"

    para1 = (
        f"Immediate attention is required for {a1['asset_id']}, which has "
        f"reached a combined priority score of {a1['combined_priority_score']:.1f} "
        f"with a {a1['failure_probability_14d']:.0%} failure probability over "
        f"the next 14 days. Its blast-radius score of "
        f"{a1['blast_radius_score']:.1f} reflects that a failure would impact "
        f"{a1['customers_at_risk']:,} customers{critical_str}. "
        f"The primary risk signals are {signals_str}, and {backup_str}."
    )

    # ── Paragraph 2: Other high-risk assets ───────────────────────────
    if len(top) > 1:
        other_lines = []
        for a in top[1:3]:
            backup = "no backup" if not a.get("has_backup_path") else "backup available"
            other_lines.append(
                f"{a['asset_id']} (score {a['combined_priority_score']:.1f}, "
                f"{a['customers_at_risk']:,} customers, {backup})"
            )
        others = " and ".join(other_lines)
        para2 = (
            f"Secondary risks include {others}. "
            f"In total, {len(ranked_assets)} assets have been assessed, with "
            f"the top {min(len(top), 5)} requiring prioritized monitoring."
        )
    else:
        para2 = (
            f"No other assets are currently showing elevated risk scores."
        )

    # ── Paragraph 3: Crew deployment plan ─────────────────────────────
    if assignments:
        crew_details = []
        for c in assignments[:4]:
            crew_details.append(
                f"{c['crew_id']} is assigned to {c['assigned_asset_id']} "
                f"with an ETA of {c['eta_minutes']} minutes"
            )
        crew_str = "; ".join(crew_details)
        para3 = f"Crew deployment is underway: {crew_str}."
    else:
        para3 = "No crew deployments have been scheduled at this time."

    if unassigned:
        para3 += (
            f" Note: {len(unassigned)} high-risk asset(s) "
            f"({', '.join(unassigned)}) remain unassigned and require "
            f"additional crew resources."
        )

    # ── Paragraph 4: Weather context & recommended actions ────────────
    if weather_risk in ("moderate", "high"):
        weather_note = (
            f"Live weather data shows {weather_risk} storm risk for the grid area "
            f"(priority scores scaled ×{weather_multiplier:.2f}). "
            f"Adverse conditions compound sensor-based degradation signals and can "
            f"precipitate failures that would otherwise remain latent for days. "
        )
    else:
        weather_note = "Current weather conditions are within normal operational tolerance. "

    para4 = (
        weather_note
        + f"Recommended actions: Dispatch {assignments[0]['crew_id'] if assignments else 'nearest available crew'} "
        f"to {a1['asset_id']} immediately for on-site inspection. "
        f"Coordinate with system control to prepare load-shedding procedures "
        f"for affected feeders if conditions deteriorate. "
        f"Monitor sensor telemetry for any further degradation in the next "
        f"4-6 hours."
    )

    header = "[STUB MODE — watsonx credentials not configured]\n\n"
    return header + "\n\n".join([para1, para2, para3, para4])


# ── Public API ────────────────────────────────────────────────────────────

def summarize_risk_brief(
    ranked_assets: list[dict],
    crew_plan: dict,
) -> str:
    """
    Generate a natural-language incident brief from structured risk data.

    If watsonx.ai credentials are configured (WATSONX_API_KEY,
    WATSONX_PROJECT_ID), calls the watsonx.ai API with a carefully
    designed prompt. Otherwise, falls back to a structured-template
    stub that still produces a data-driven, non-generic brief.

    Args:
        ranked_assets: List of dicts matching Section 5.5 schema,
            sorted by combined_priority_score descending (output of
            risk_engine.rank_assets()).
        crew_plan: Dict matching Section 5.6 schema (output of
            risk_engine.crew_planner.generate_crew_plan()).

    Returns:
        A natural-language incident brief (3-5 paragraphs) referencing
        actual asset IDs, scores, and reasoning. If using the stub,
        the output is prefixed with "[STUB MODE ...]".

    Raises:
        RuntimeError: If watsonx credentials are configured but the
            API call fails (never silently falls back to the stub
            when real credentials are present — fail loudly per
            Global Rule #3).
    """
    if not ranked_assets:
        return "No assets provided for risk assessment."

    if _credentials_available():
        logger.info("watsonx credentials detected — calling watsonx.ai API")
        prompt = _build_prompt(ranked_assets, crew_plan)
        return _call_watsonx(prompt)
    else:
        logger.info(
            "watsonx credentials not configured — using stub mode. "
            "Set WATSONX_API_KEY and WATSONX_PROJECT_ID in .env to enable "
            "live watsonx.ai generation."
        )
        return _generate_stub_brief(ranked_assets, crew_plan)


# ── CLI entry point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

    from risk_engine import rank_assets
    from risk_engine.crew_planner import generate_crew_plan

    print("Generating risk brief...\n")

    ranked = rank_assets()
    plan = generate_crew_plan()
    brief = summarize_risk_brief(ranked, plan)

    print(brief)
    print(f"\n{'=' * 60}")
    print(f"Mode: {'LIVE watsonx.ai' if _credentials_available() else 'STUB (local template)'}")
    print(f"Assets assessed: {len(ranked)}")
    print(f"Crew assignments: {len(plan['assignments'])}")
