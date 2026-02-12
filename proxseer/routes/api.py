from fastapi import APIRouter, HTTPException

from ..database import get_flows, get_flow, clear_flows, get_stats
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


@router.get("/stats", response_model=Stats)
async def stats():
    return Stats(**(await get_stats()))
