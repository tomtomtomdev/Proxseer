from pydantic import BaseModel


class FlowSummary(BaseModel):
    id: int
    method: str
    url: str
    host: str
    path: str
    status_code: int | None
    content_type: str | None
    response_size: int | None
    duration_ms: float | None
    timestamp: str


class FlowDetail(FlowSummary):
    request_headers: dict
    response_headers: dict
    request_body: str | None
    response_body: str | None


class FlowList(BaseModel):
    flows: list[FlowSummary]
    total: int
    page: int
    page_size: int


class Stats(BaseModel):
    total_requests: int
    methods: dict[str, int]
    status_codes: dict[str, int]
    top_hosts: list[dict]
