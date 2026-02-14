from urllib.parse import urlparse, parse_qs

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..database import get_flows, get_flow, clear_flows, get_stats, get_flows_for_export
from ..models import FlowList, FlowDetail, FlowSummary, Stats

router = APIRouter(prefix="/api")


@router.get("/requests", response_model=FlowList)
async def list_requests(
    page: int = 1,
    page_size: int = 100,
    host: str | None = None,
    method: str | None = None,
    status_code: int | None = None,
    search: str | None = None,
):
    flows, total = await get_flows(
        page=page, page_size=page_size,
        host=host, method=method,
        status_code=status_code, search=search,
    )
    return FlowList(
        flows=[FlowSummary(**f) for f in flows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/requests/{flow_id}", response_model=FlowDetail)
async def get_request(flow_id: int):
    flow = await get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Request not found")
    return FlowDetail(**flow)


@router.delete("/requests")
async def delete_requests():
    await clear_flows()
    return {"status": "cleared"}


@router.get("/export/postman")
async def export_postman(
    host: str | None = None,
    method: str | None = None,
    search: str | None = None,
):
    flows = await get_flows_for_export(host=host, method=method, search=search)

    folders: dict[str, list] = {}
    for flow in flows:
        item = _flow_to_postman_item(flow)
        folders.setdefault(flow["host"], []).append(item)

    collection = {
        "info": {
            "name": "Proxseer Export",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [
            {"name": host, "item": items}
            for host, items in folders.items()
        ],
    }

    return JSONResponse(
        content=collection,
        headers={
            "Content-Disposition": 'attachment; filename="proxseer_collection.json"',
        },
    )


def _flow_to_postman_item(flow: dict) -> dict:
    parsed = urlparse(flow["url"])

    url_obj: dict = {
        "raw": flow["url"],
        "protocol": parsed.scheme,
        "host": parsed.hostname.split(".") if parsed.hostname else [],
        "path": [s for s in parsed.path.split("/") if s],
    }

    if parsed.query:
        url_obj["query"] = [
            {"key": k, "value": v[0] if len(v) == 1 else v[-1]}
            for k, v in parse_qs(parsed.query, keep_blank_values=True).items()
        ]

    if parsed.port:
        url_obj["port"] = str(parsed.port)

    skip = {"host", "content-length"}
    headers = [
        {"key": k, "value": str(v)}
        for k, v in (flow.get("request_headers") or {}).items()
        if k.lower() not in skip and not k.startswith(":")
    ]

    request: dict = {
        "method": flow["method"],
        "header": headers,
        "url": url_obj,
    }

    body = flow.get("request_body")
    if body and not body.startswith("[binary content:") and not body.startswith("[truncated:"):
        ct = next(
            (h["value"] for h in headers if h["key"].lower() == "content-type"),
            "",
        ).lower()
        if "json" in ct:
            mode = "raw"
            options = {"raw": {"language": "json"}}
        elif "x-www-form-urlencoded" in ct:
            mode = "urlencoded"
            options = {}
        else:
            mode = "raw"
            options = {}

        request["body"] = {"mode": mode, "raw": body, "options": options}

    return {
        "name": f"{flow['method']} {flow['path']}",
        "request": request,
        "response": [],
    }


@router.get("/stats", response_model=Stats)
async def stats():
    return Stats(**(await get_stats()))
