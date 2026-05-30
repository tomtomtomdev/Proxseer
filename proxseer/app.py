import socket
import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR
from . import config as _config
from .database import init_db
from .routes.api import router as api_router
from .routes.websocket import websocket_endpoint

MITMPROXY_CERT = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem"


def get_local_ip() -> str:
    try:
        result = subprocess.run(
            ["ipconfig", "getifaddr", "en0"],
            capture_output=True, text=True, timeout=5,
        )
        ip = result.stdout.strip()
        if ip:
            return ip
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def create_app() -> FastAPI:
    app = FastAPI(title="Proxseer", docs_url=None, redoc_url=None)

    @app.on_event("startup")
    async def startup():
        await init_db()

    app.include_router(api_router)
    app.add_api_websocket_route("/ws", websocket_endpoint)

    @app.get("/cert")
    async def download_cert():
        if not MITMPROXY_CERT.exists():
            return HTMLResponse(
                "<h2>Certificate not ready</h2>"
                "<p>Start browsing through the proxy first to generate the CA certificate, then refresh this page.</p>",
                status_code=503,
            )
        return FileResponse(
            MITMPROXY_CERT,
            media_type="application/x-pem-file",
            filename="proxseer-ca-cert.pem",
        )

    @app.get("/setup")
    async def setup_guide():
        ip = get_local_ip()
        return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Proxseer - iPhone Setup</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'SF Pro', sans-serif;
         background: #0d1117; color: #e6edf3; padding: 2rem; line-height: 1.6; }}
  .container {{ max-width: 640px; margin: 0 auto; }}
  h1 {{ color: #58a6ff; margin-bottom: 0.5rem; font-size: 1.8rem; }}
  .subtitle {{ color: #8b949e; margin-bottom: 2rem; }}
  .step {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px;
           padding: 1.25rem; margin-bottom: 1rem; }}
  .step-num {{ display: inline-block; background: #58a6ff; color: #0d1117;
               width: 28px; height: 28px; border-radius: 50%; text-align: center;
               line-height: 28px; font-weight: 700; font-size: 0.85rem; margin-right: 0.75rem; }}
  .step h3 {{ display: inline; font-size: 1.05rem; }}
  .step p {{ margin-top: 0.5rem; color: #8b949e; padding-left: 2.5rem; }}
  code {{ background: #1f2937; color: #f0883e; padding: 2px 8px; border-radius: 4px;
          font-family: 'SF Mono', monospace; font-size: 0.95em; }}
  .info-box {{ background: #0d2847; border: 1px solid #1f6feb; border-radius: 8px;
               padding: 1rem; margin: 1.5rem 0; }}
  .info-box strong {{ color: #58a6ff; }}
  a {{ color: #58a6ff; }}
  .back {{ margin-top: 2rem; }}
</style>
</head>
<body>
<div class="container">
  <h1>Proxseer Setup</h1>
  <p class="subtitle">Configure your iPhone to route traffic through this Mac</p>

  <div class="info-box">
    <strong>Your Network Info</strong><br>
    Mac IP: <code>{ip}</code><br>
    Proxy Port: <code>{_config.PROXY_PORT}</code><br>
    Web UI: <code>http://{ip}:{_config.WEB_PORT}</code>
  </div>

  <div class="step">
    <span class="step-num">1</span>
    <h3>Configure WiFi Proxy</h3>
    <p>On your iPhone: <strong>Settings → Wi-Fi → tap your network → Configure Proxy → Manual</strong></p>
    <p>Server: <code>{ip}</code> &nbsp; Port: <code>{_config.PROXY_PORT}</code></p>
  </div>

  <div class="step">
    <span class="step-num">2</span>
    <h3>Install CA Certificate</h3>
    <p>On your iPhone's Safari, visit:<br>
    <code>http://{ip}:{_config.WEB_PORT}/cert</code></p>
    <p>Tap "Allow" when prompted to download the profile.</p>
  </div>

  <div class="step">
    <span class="step-num">3</span>
    <h3>Install the Profile</h3>
    <p><strong>Settings → General → VPN & Device Management</strong><br>
    Tap the Proxseer profile → Install → enter passcode → Install.</p>
  </div>

  <div class="step">
    <span class="step-num">4</span>
    <h3>Enable Full Trust</h3>
    <p><strong>Settings → General → About → Certificate Trust Settings</strong><br>
    Toggle ON for Proxseer → Continue.</p>
  </div>

  <div class="step">
    <span class="step-num">5</span>
    <h3>Verify</h3>
    <p>Browse any website on your iPhone. Requests should appear in the
    <a href="/">Proxseer Web UI</a> in real-time.</p>
  </div>

  <p class="back"><a href="/">← Back to Web UI</a></p>
</div>
</body>
</html>""")

    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app
