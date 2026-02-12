# Proxseer

A network traffic inspector for macOS that captures HTTP/HTTPS traffic from your iPhone (or any device) through a local proxy and displays it in a real-time web UI.

## Features

- **MITM Proxy** -- intercepts HTTP and HTTPS traffic via mitmproxy on port 8080
- **Real-time Web UI** -- captured requests stream live over WebSocket to a browser dashboard
- **Request Inspector** -- view full request/response headers and bodies
- **Search & Filter** -- filter traffic by host, method, status code, or free-text search
- **Statistics** -- top hosts, method distribution, and status code breakdown
- **SQLite Storage** -- all captured flows are persisted locally at `~/.proxseer/proxseer.db`
- **iPhone Setup Guide** -- built-in `/setup` page walks you through configuring your iPhone

## Requirements

- macOS
- Python 3.10+

## Quick Start

```bash
git clone <repo-url> && cd Proxseer
./install.sh
```

The install script creates a virtual environment, installs dependencies, and starts Proxseer. On launch it prints your local IP and the ports to use.

### Manual Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m proxseer
```

## iPhone Configuration

1. Connect your iPhone to the same Wi-Fi network as your Mac
2. Open `http://<your-mac-ip>:9000/setup` for step-by-step instructions
3. Configure the iPhone Wi-Fi proxy to point at your Mac's IP on port **8080**
4. Install and trust the mitmproxy CA certificate (downloadable at `/cert`)

## Configuration

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `PROXSEER_PROXY_PORT` | `8080` | mitmproxy listen port |
| `PROXSEER_WEB_PORT` | `9000` | Web UI / API port |
| `PROXSEER_DATA_DIR` | `~/.proxseer` | Database and data directory |

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/requests` | GET | List captured requests (paginated, filterable) |
| `/api/requests/{id}` | GET | Get full request/response detail |
| `/api/requests` | DELETE | Clear all captured requests |
| `/api/stats` | GET | Traffic statistics |
| `/ws` | WebSocket | Real-time flow stream |
| `/cert` | GET | Download mitmproxy CA certificate |
| `/setup` | GET | iPhone setup guide |

## Project Structure

```
proxseer/
  __main__.py      # Entry point, wires up proxy + web server
  app.py           # FastAPI app, cert download, setup page
  config.py        # Ports, paths, constants
  database.py      # SQLite schema and queries
  models.py        # Pydantic response models
  proxy.py         # mitmproxy addon and proxy thread
  routes/
    api.py         # REST API endpoints
    websocket.py   # WebSocket connection manager
  static/          # Frontend (HTML, CSS, JS)
```

## License

MIT
