/**
 * Grid Guardian — API Client
 *
 * Fetch helpers for all backend endpoints.
 * All functions return parsed JSON or throw on error.
 */

const BASE = '/api';

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

async function postJSON(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

/** Grid topology with risk scores merged into nodes */
export function getTopology() {
  return fetchJSON(`${BASE}/topology`);
}

/** Ranked asset list */
export function getRankedAssets(topN = 25) {
  return fetchJSON(`${BASE}/ranked-assets?top_n=${topN}`);
}

/** Single-asset health details */
export function getAssetHealth(assetId) {
  return fetchJSON(`${BASE}/asset/${encodeURIComponent(assetId)}/health`);
}

/** Weather forecast */
export function getWeather(lat = 22.31, lon = 73.18, days = 7) {
  return fetchJSON(`${BASE}/weather?lat=${lat}&lon=${lon}&days=${days}`);
}

/** Crew pre-positioning plan */
export function getCrewPlan() {
  return fetchJSON(`${BASE}/crew-plan`);
}

/** Chat / incident brief */
export function sendChat(topN = 5) {
  return postJSON(`${BASE}/chat`, { top_n: topN });
}
