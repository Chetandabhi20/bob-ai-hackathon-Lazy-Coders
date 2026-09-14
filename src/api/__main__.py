"""Entry point for `python -m api.server`."""

from api.server import app

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("MCP_SERVER_PORT", "8001"))
    print(f"Starting Grid Guardian API on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
