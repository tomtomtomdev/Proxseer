import asyncio
import logging
import signal
import threading

import uvicorn

from .app import create_app, get_local_ip
from .config import PROXY_PORT, WEB_PORT
from .database import insert_flow
from .proxy import run_proxy
from .routes.websocket import manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("proxseer")


async def flow_consumer(queue: asyncio.Queue, shutdown_event: threading.Event):
    """Consume flows from the proxy queue, persist and broadcast."""
    while not shutdown_event.is_set():
        try:
            flow = await asyncio.wait_for(queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue
        except Exception:
            break

        try:
            flow_id = await insert_flow(flow)
            flow["id"] = flow_id
            await manager.broadcast({"type": "new_flow", "flow": flow})
        except Exception:
            logger.exception("Error processing flow")


def main():
    ip = get_local_ip()

    print(f"""
╔══════════════════════════════════════════════╗
║              Proxseer Started                ║
╠══════════════════════════════════════════════╣
║                                              ║
║  Web UI:   http://{ip}:{WEB_PORT:<5}              ║
║  Proxy:    {ip}:{PROXY_PORT}                     ║
║  Setup:    http://{ip}:{WEB_PORT}/setup           ║
║                                              ║
║  Configure iPhone WiFi proxy to:             ║
║    Server: {ip}                              ║
║    Port:   {PROXY_PORT}                            ║
║                                              ║
╚══════════════════════════════════════════════╝
""")

    queue = asyncio.Queue()
    shutdown_event = threading.Event()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    proxy_thread = threading.Thread(
        target=run_proxy,
        args=(queue, loop, shutdown_event),
        daemon=True,
        name="mitmproxy",
    )
    proxy_thread.start()
    logger.info("Proxy thread started")

    consumer_task = loop.create_task(flow_consumer(queue, shutdown_event))

    app = create_app()

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=WEB_PORT,
        log_level="warning",
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    def _shutdown(sig, frame):
        logger.info("Shutting down...")
        shutdown_event.set()
        server.should_exit = True

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(server.serve())
    finally:
        shutdown_event.set()
        consumer_task.cancel()
        try:
            loop.run_until_complete(consumer_task)
        except asyncio.CancelledError:
            pass
        proxy_thread.join(timeout=3)
        loop.close()
        logger.info("Proxseer stopped")


if __name__ == "__main__":
    main()
