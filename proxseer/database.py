import json
import aiosqlite
from .config import DB_PATH, DATA_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    method TEXT NOT NULL,
    url TEXT NOT NULL,
    host TEXT NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER,
    request_headers TEXT NOT NULL DEFAULT '{}',
    response_headers TEXT NOT NULL DEFAULT '{}',
    request_body TEXT,
    response_body TEXT,
    content_type TEXT,
    request_size INTEGER,
    response_size INTEGER,
    duration_ms REAL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_host ON requests(host);
CREATE INDEX IF NOT EXISTS idx_method ON requests(method);
CREATE INDEX IF NOT EXISTS idx_status_code ON requests(status_code);
CREATE INDEX IF NOT EXISTS idx_timestamp ON requests(timestamp DESC);
"""


async def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def insert_flow(flow: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO requests
               (method, url, host, path, status_code,
                request_headers, response_headers,
                request_body, response_body,
                content_type, request_size, response_size,
                duration_ms, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                flow["method"],
                flow["url"],
                flow["host"],
                flow["path"],
                flow.get("status_code"),
                json.dumps(flow.get("request_headers", {})),
                json.dumps(flow.get("response_headers", {})),
                flow.get("request_body"),
                flow.get("response_body"),
                flow.get("content_type"),
                flow.get("request_size"),
                flow.get("response_size"),
                flow.get("duration_ms"),
                flow["timestamp"],
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_flows(
    page: int = 1,
    page_size: int = 100,
    host: str | None = None,
    method: str | None = None,
    status_code: int | None = None,
    search: str | None = None,
) -> tuple[list[dict], int]:
    conditions = []
    params = []

    if host:
        conditions.append("host LIKE ?")
        params.append(f"%{host}%")
    if method:
        conditions.append("method = ?")
        params.append(method.upper())
    if status_code is not None:
        conditions.append("status_code = ?")
        params.append(status_code)
    if search:
        conditions.append("(url LIKE ? OR host LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        count_row = await db.execute_fetchall(
            f"SELECT COUNT(*) as cnt FROM requests {where}", params
        )
        total = count_row[0][0]

        offset = (page - 1) * page_size
        rows = await db.execute_fetchall(
            f"""SELECT id, method, url, host, path, status_code,
                       content_type, response_size, duration_ms, timestamp
                FROM requests {where}
                ORDER BY id DESC
                LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        )
        flows = [
            {
                "id": r[0], "method": r[1], "url": r[2], "host": r[3],
                "path": r[4], "status_code": r[5], "content_type": r[6],
                "response_size": r[7], "duration_ms": r[8], "timestamp": r[9],
            }
            for r in rows
        ]
        return flows, total


async def get_flow(flow_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            """SELECT id, method, url, host, path, status_code,
                      request_headers, response_headers,
                      request_body, response_body,
                      content_type, response_size, duration_ms, timestamp
               FROM requests WHERE id = ?""",
            (flow_id,),
        )
        if not rows:
            return None
        r = rows[0]
        return {
            "id": r[0], "method": r[1], "url": r[2], "host": r[3],
            "path": r[4], "status_code": r[5],
            "request_headers": json.loads(r[6]),
            "response_headers": json.loads(r[7]),
            "request_body": r[8], "response_body": r[9],
            "content_type": r[10], "response_size": r[11],
            "duration_ms": r[12], "timestamp": r[13],
        }


async def clear_flows():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM requests")
        await db.commit()


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        total_row = await db.execute_fetchall("SELECT COUNT(*) FROM requests")
        total = total_row[0][0]

        method_rows = await db.execute_fetchall(
            "SELECT method, COUNT(*) FROM requests GROUP BY method"
        )
        methods = {r[0]: r[1] for r in method_rows}

        status_rows = await db.execute_fetchall(
            "SELECT status_code, COUNT(*) FROM requests WHERE status_code IS NOT NULL GROUP BY status_code"
        )
        status_codes = {str(r[0]): r[1] for r in status_rows}

        host_rows = await db.execute_fetchall(
            "SELECT host, COUNT(*) as cnt FROM requests GROUP BY host ORDER BY cnt DESC LIMIT 10"
        )
        top_hosts = [{"host": r[0], "count": r[1]} for r in host_rows]

        return {
            "total_requests": total,
            "methods": methods,
            "status_codes": status_codes,
            "top_hosts": top_hosts,
        }
