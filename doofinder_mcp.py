"""Doofinder Search Analytics MCP server.

Exposes Doofinder Stats API (v2) endpoints as MCP tools. All tools take a date
range (YYYYMMDD strings) and query the EU1 stats API for the configured search
engine (hashid).

Required environment variables:
    DOOFINDER_API_KEY  - API token (sent as "Authorization: Token <key>")
    DOOFINDER_HASHID   - hashid of the search engine to query
"""

import os
from datetime import datetime, timezone
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://eu1-api.doofinder.com/api/v2/stats"
TIMEZONE = "Europe/Warsaw"

API_KEY = os.environ.get("DOOFINDER_API_KEY", "")
HASHID = os.environ.get("DOOFINDER_HASHID", "")

mcp = FastMCP("doofinder")


def _request(path: str, params: dict[str, Any] | None = None) -> Any:
    """Perform an authenticated GET against the Doofinder stats API.

    Always injects hashid, timezone and authorization. Raises on HTTP errors.
    """
    if not API_KEY:
        raise RuntimeError("DOOFINDER_API_KEY environment variable is not set")
    if not HASHID:
        raise RuntimeError("DOOFINDER_HASHID environment variable is not set")

    # Doofinder expects the search engine id as an array param: hashids[]=VALUE
    query: dict[str, Any] = {"hashids[]": HASHID, "tz": TIMEZONE}
    if params:
        query.update({k: v for k, v in params.items() if v is not None})

    headers = {"Authorization": f"Token {API_KEY}"}
    url = f"{BASE_URL}{path}"

    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, params=query, headers=headers)
        response.raise_for_status()
        return response.json()


def _ms_to_date(value: Any) -> Any:
    """Convert a Unix timestamp in milliseconds to a YYYY-MM-DD string.

    Returns the original value untouched if it is not a numeric timestamp.
    """
    if value is None:
        return value
    try:
        ms = float(value)
    except (TypeError, ValueError):
        return value
    dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def _date_range(from_date: str, to_date: str) -> dict[str, str]:
    """Build the from/to query params used by every endpoint."""
    return {"from": from_date, "to": to_date}


def _as_list(data: Any) -> list[dict[str, Any]]:
    """Normalize an API response into a list of dict rows.

    Doofinder endpoints sometimes wrap rows under common keys; fall back to the
    raw payload when it is already a list.
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("results", "data", "items", "values", "series"):
            inner = data.get(key)
            if isinstance(inner, list):
                return inner
        return [data]
    return []


def _timeseries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map daily rows into {timestamp: YYYY-MM-DD, count: int}."""
    out: list[dict[str, Any]] = []
    for row in rows:
        ts = row.get("timestamp", row.get("date", row.get("key")))
        count = row.get("count", row.get("value", row.get("total", 0)))
        out.append({"timestamp": _ms_to_date(ts), "count": count})
    return out


@mcp.tool()
def get_top_searches(from_date: str, to_date: str) -> list[dict[str, Any]]:
    """Most frequent search queries in the date range.

    Args:
        from_date: Start date, YYYYMMDD.
        to_date: End date, YYYYMMDD.

    Returns a list of {query, count}.
    """
    data = _request("/searches/top", _date_range(from_date, to_date))
    out: list[dict[str, Any]] = []
    for row in _as_list(data):
        out.append(
            {
                "query": row.get("query", row.get("term", row.get("search"))),
                "count": row.get("count", row.get("total", 0)),
            }
        )
    return out


@mcp.tool()
def get_searches_over_time(from_date: str, to_date: str) -> list[dict[str, Any]]:
    """Daily search volume over the date range.

    Args:
        from_date: Start date, YYYYMMDD.
        to_date: End date, YYYYMMDD.

    Returns a list of daily {timestamp, count}.
    """
    data = _request("/searches", _date_range(from_date, to_date))
    return _timeseries(_as_list(data))


@mcp.tool()
def get_sessions_over_time(from_date: str, to_date: str) -> list[dict[str, Any]]:
    """Daily session (init) counts over the date range.

    Args:
        from_date: Start date, YYYYMMDD.
        to_date: End date, YYYYMMDD.

    Returns a list of daily {timestamp, count}.
    """
    data = _request("/inits", _date_range(from_date, to_date))
    return _timeseries(_as_list(data))


@mcp.tool()
def get_clicks_over_time(from_date: str, to_date: str) -> list[dict[str, Any]]:
    """Daily click counts over the date range.

    Args:
        from_date: Start date, YYYYMMDD.
        to_date: End date, YYYYMMDD.

    Returns a list of daily {timestamp, count}.
    """
    data = _request("/clicks", _date_range(from_date, to_date))
    return _timeseries(_as_list(data))


@mcp.tool()
def get_checkouts_over_time(from_date: str, to_date: str) -> list[dict[str, Any]]:
    """Daily checkout counts over the date range.

    Args:
        from_date: Start date, YYYYMMDD.
        to_date: End date, YYYYMMDD.

    Returns a list of daily {timestamp, count}.
    """
    data = _request("/checkouts", _date_range(from_date, to_date))
    return _timeseries(_as_list(data))


@mcp.tool()
def get_top_clicked_items(
    from_date: str, to_date: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Most clicked result items in the date range.

    Args:
        from_date: Start date, YYYYMMDD.
        to_date: End date, YYYYMMDD.
        limit: Maximum number of items to return (default 20).

    Returns a list of {title, count, link}.
    """
    params = _date_range(from_date, to_date)
    params["limit"] = limit
    data = _request("/clicked_items", params)
    out: list[dict[str, Any]] = []
    for row in _as_list(data):
        out.append(
            {
                "title": row.get("title", row.get("name")),
                "count": row.get("count", row.get("total", 0)),
                "link": row.get("link", row.get("url", row.get("href"))),
            }
        )
    return out


@mcp.tool()
def get_search_engine_usage(from_date: str, to_date: str) -> dict[str, Any]:
    """Aggregate search engine usage summary for the date range.

    Args:
        from_date: Start date, YYYYMMDD.
        to_date: End date, YYYYMMDD.

    Returns {visits, inits, searches}.
    """
    data = _request("/search_engine_users", _date_range(from_date, to_date))
    source = data[0] if isinstance(data, list) and data else data
    if not isinstance(source, dict):
        source = {}
    return {
        "visits": source.get("visits", source.get("users", 0)),
        "inits": source.get("inits", 0),
        "searches": source.get("searches", 0),
    }


@mcp.tool()
def get_top_sales(from_date: str, to_date: str) -> list[dict[str, Any]]:
    """Top selling items in the date range.

    Args:
        from_date: Start date, YYYYMMDD.
        to_date: End date, YYYYMMDD.

    Returns a list of {title, sum_amount, avg_price}.
    """
    data = _request("/top-sales", _date_range(from_date, to_date))
    out: list[dict[str, Any]] = []
    for row in _as_list(data):
        out.append(
            {
                "title": row.get("title", row.get("name")),
                "sum_amount": row.get("sum_amount", row.get("amount", row.get("total"))),
                "avg_price": row.get("avg_price", row.get("average_price")),
            }
        )
    return out


@mcp.tool()
def get_no_result_searches(from_date: str, to_date: str) -> list[dict[str, Any]]:
    """Search queries that returned zero results in the date range.

    Args:
        from_date: Start date, YYYYMMDD.
        to_date: End date, YYYYMMDD.

    Returns a list of {query, count}.
    """
    params = _date_range(from_date, to_date)
    params["no_results"] = "true"
    data = _request("/searches/top", params)
    out: list[dict[str, Any]] = []
    for row in _as_list(data):
        out.append(
            {
                "query": row.get("query", row.get("term", row.get("search"))),
                "count": row.get("count", row.get("total", 0)),
            }
        )
    return out


@mcp.tool()
def get_popular_searches(from_date: str, to_date: str) -> list[dict[str, Any]]:
    """Searches with the most clicked items in the date range.

    Args:
        from_date: Start date, YYYYMMDD.
        to_date: End date, YYYYMMDD.

    Returns a list of {query, count}.
    """
    data = _request("/searches/popular", _date_range(from_date, to_date))
    out: list[dict[str, Any]] = []
    for row in _as_list(data):
        out.append(
            {
                "query": row.get("query", row.get("term", row.get("search"))),
                "count": row.get("count", row.get("clicks", row.get("total", 0))),
            }
        )
    return out


if __name__ == "__main__":
    mcp.run()
