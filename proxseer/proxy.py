import asyncio
import logging
import threading
from datetime import datetime, timezone

from mitmproxy import options, http
from mitmproxy.tools.dump import DumpMaster

from .config import PROXY_PORT, MAX_BODY_SIZE, BINARY_CONTENT_TYPES

logger = logging.getLogger("proxseer.proxy")


def _is_binary(content_type: str | None) -> bool:
    if not content_type:
        return False
    ct = content_type.lower()
    return any(ct.startswith(b) for b in BINARY_CONTENT_TYPES)


def _safe_decode(raw: bytes | None, content_type: str | None, max_size: int = MAX_BODY_SIZE) -> str | None:
    if raw is None:
        return None
    if _is_binary(content_type):
        return f"[binary content: {len(raw)} bytes]"
    if len(raw) > max_size:
        return f"[truncated: {len(raw)} bytes, showing first {max_size}]"
    try:
        return raw[:max_size].decode("utf-8", errors="replace")
    except Exception:
        return f"[decode error: {len(raw)} bytes]"


class TrafficCapture:
    """mitmproxy addon that captures HTTP flows and pushes them to a queue."""

    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self._queue = queue
        self._loop = loop

    def response(self, flow: http.HTTPFlow):
        try:
            req = flow.request
            resp = flow.response

            req_ct = req.headers.get("content-type", "")
            resp_ct = resp.headers.get("content-type", "") if resp else ""

            duration_ms = None
            if flow.response and flow.request.timestamp_end and flow.request.timestamp_start:
                duration_ms = round(
                    (flow.response.timestamp_end - flow.request.timestamp_start) * 1000, 2
                )

            data = {
                "method": req.method,
                "url": req.pretty_url,
                "host": req.pretty_host,
                "path": req.path,
                "status_code": resp.status_code if resp else None,
                "request_headers": dict(req.headers),
                "response_headers": dict(resp.headers) if resp else {},
                "request_body": _safe_decode(req.raw_content, req_ct),
                "response_body": _safe_decode(resp.raw_content, resp_ct) if resp else None,
                "content_type": resp_ct.split(";")[0].strip() if resp_ct else None,
                "request_size": len(req.raw_content) if req.raw_content else 0,
                "response_size": len(resp.raw_content) if resp and resp.raw_content else 0,
                "duration_ms": duration_ms,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self._loop.call_soon_threadsafe(self._queue.put_nowait, data)
        except Exception:
            logger.exception("Error capturing flow")


def run_proxy(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop, shutdown_event: threading.Event):
    """Run mitmproxy in a dedicated thread with its own event loop."""

    async def _run():
        opts = options.Options(
            listen_host="0.0.0.0",
            listen_port=PROXY_PORT,
            ssl_insecure=True,
        )
        master = DumpMaster(opts, with_dumper=False, with_termlog=False)
        master.addons.add(TrafficCapture(queue, loop))

        logger.info(f"Proxy listening on 0.0.0.0:{PROXY_PORT}")

        try:
            await master.run()
        except Exception:
            if not shutdown_event.is_set():
                logger.exception("Proxy error")
        finally:
            master.shutdown()

    proxy_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(proxy_loop)

    task = proxy_loop.create_task(_run())

    def _check_shutdown():
        if shutdown_event.is_set():
            task.cancel()
        else:
            proxy_loop.call_later(0.5, _check_shutdown)

    proxy_loop.call_later(0.5, _check_shutdown)

    try:
        proxy_loop.run_until_complete(task)
    except asyncio.CancelledError:
        pass
    finally:
        proxy_loop.close()
