# How to Deploy to Railway

> One-time setup. After this, every `git push` auto-deploys.

## Step 1 — Create a Railway account

Go to https://railway.app and sign up (free tier is enough).

## Step 2 — Create a new project from GitHub

1. In Railway dashboard → **New Project** → **Deploy from GitHub repo**
2. Authorize Railway to access your GitHub account
3. Select your repo: `bob-ai-hackathon-Lazy-Coders`
4. Railway will detect `railway.json` and `nixpacks.toml` automatically

## Step 3 — Set environment variables

In Railway dashboard → your service → **Variables** tab, add:

| Variable | Value |
|---|---|
| `WEATHER_API_BASE` | `https://api.open-meteo.com/v1` |
| `WATSONX_API_KEY` | *(your key, or leave blank for STUB mode)* |
| `WATSONX_PROJECT_ID` | *(your project ID, or leave blank)* |
| `WATSONX_URL` | `https://us-south.ml.cloud.ibm.com` |

Railway injects `PORT` automatically — the server reads it.

## Step 4 — Deploy

Click **Deploy**. Railway will:
1. Install Python deps: `pip install -r src/requirements.txt`
2. Build React: `cd src/frontend && npm ci && npm run build`
3. Start: `cd src && python -m api.server`

Build takes ~3-4 minutes on first deploy.

## Step 5 — Get your URL

In Railway → your service → **Settings** → **Networking** → **Generate Domain**.

Your URL will be something like `grid-guardian-production.up.railway.app`.

Update these files with your actual URL:
- `demo/live-demo-url.txt`
- `docs/bob-demo.md` (the "Quick Connect" section)
- `docs/setup-guide.md` (the live deployment table)

## Step 6 — Verify

Visit `https://<your-url>/docs` — you should see the FastAPI Swagger UI.
Visit `https://<your-url>/` — you should see the React dashboard.

Test the MCP endpoint:
```bash
curl -X POST https://<your-url>/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

Should return a JSON list of 5 tools.

## Step 7 — Connect Bob

Add to your `.bob/mcp.json`:
```json
{
  "mcpServers": {
    "grid-guardian": {
      "type": "streamable-http",
      "url": "https://<your-url>/mcp",
      "alwaysAllow": [
        "get_asset_health", "get_weather_risk",
        "rank_at_risk_assets", "generate_crew_plan", "generate_incident_brief"
      ]
    }
  }
}
```
