"""Local stdio MCP server that wraps the BORME API REST endpoints.

The tools, with their names, descriptions and input schemas, come from
tools.json, a copy of the hosted server's tools/list (regenerate it with
scripts/update_tools.py). Each tool call becomes one or more requests to the
public REST API at https://api.bormeapi.com/v1, with BORME_API_KEY, when set,
in the X-API-Key header. Nothing touches the network until a tool is called.

The hosted server at https://mcp.bormeapi.com/mcp is the recommended way to
use BORME API from an MCP client; this server is for stdio-only clients and
for MCP directories that build and inspect a container.
"""
import asyncio
import datetime as dt
import json
import os
from pathlib import Path
from urllib.parse import quote

import httpx
import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

VERSION = "2.0.0"
HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "tools.json").read_text(encoding="utf-8"))
TOOLS = {t["name"]: t for t in SPEC["tools"]}

API_BASE = os.environ.get("BORME_API_URL", "https://api.bormeapi.com").rstrip("/")
USER_AGENT = f"borme-mcp-local/{VERSION} (+https://github.com/bormeapi/borme-mcp)"
NO_KEY_HINT = (
    "This tool needs a BORME API key when used through the local server: set "
    "BORME_API_KEY (a free key is available at https://bormeapi.com/account), "
    "or connect to the hosted server at https://mcp.bormeapi.com/mcp, which "
    "serves the free plan without a key."
)

server = Server("borme-mcp", version=VERSION)


class ApiError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body = body


def seg(value):
    """One URL path segment, fully encoded."""
    return quote(str(value), safe="")


def clean(params):
    """Drop arguments the caller did not give; lists become repeated params."""
    out = []
    for key, value in params.items():
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, (list, tuple)):
            out.extend((key, str(v)) for v in value)
        elif isinstance(value, bool):
            out.append((key, "true" if value else "false"))
        else:
            out.append((key, str(value)))
    return out


class Api:
    def __init__(self):
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        key = os.environ.get("BORME_API_KEY", "").strip()
        if key:
            headers["X-API-Key"] = key
        self.has_key = bool(key)
        self.client = httpx.AsyncClient(base_url=API_BASE, headers=headers,
                                        timeout=60, follow_redirects=True)

    async def get(self, path, params=None):
        resp = await self.client.get(path, params=clean(params or {}))
        try:
            body = resp.json()
        except ValueError:
            body = {"detail": resp.text[:500]}
        if resp.status_code >= 400:
            raise ApiError(resp.status_code, body)
        return body

    async def close(self):
        await self.client.aclose()


# --- one handler per tool -------------------------------------------------

async def search_events(api, a):
    params = {
        "date_from": a.get("date_from"),
        "date_to": a.get("date_to"),
        # REST takes several provinces separated by commas and repeats
        # act_type for several act types.
        "province": ",".join(a.get("provinces") or []) or None,
        "act_type": a.get("act_types") or None,
        "company_name_contains": a.get("company_name_contains"),
        "limit": a.get("limit", 50),
    }
    return await api.get("/v1/events", params)


async def company_history(api, a):
    company = str(a["company"]).strip()
    page = {"limit": a.get("limit", 100), "offset": a.get("offset", 0),
            "order": a.get("order", "desc")}
    try:
        return await api.get(f"/v1/companies/{seg(company)}/events", page)
    except ApiError as err:
        if err.status != 404:
            raise
    # Not a known slug: treat it as a name.
    found = await api.get("/v1/companies", {"name": company, "limit": 10})
    cards = found.get("companies") or []
    if len(cards) == 1:
        slug = cards[0]["company_slug"]
        return await api.get(f"/v1/companies/{seg(slug)}/events", page)
    return {
        "company": company,
        "detail": ("no company with this slug; candidates by name follow, "
                   "call again with one company_slug" if cards else
                   "no company found with this slug or name"),
        "candidates": [
            {k: c.get(k) for k in ("company_slug", "name", "province", "status", "match")}
            for c in cards
        ],
    }


async def company_by_nif(api, a):
    return await api.get(f"/v1/companies/by-nif/{seg(a['nif'])}")


async def brand_owner(api, a):
    return await api.get("/v1/brands", {"q": a["brand"], "limit": a.get("limit", 20)})


async def company_brands(api, a):
    return await api.get(f"/v1/companies/{seg(a['company'])}/brands",
                         {"limit": a.get("limit", 50)})


async def recent_signals(api, a):
    since = (dt.date.today() - dt.timedelta(days=10)).isoformat()
    return await api.get("/v1/signals", {"signal_type": a.get("signal_type"),
                                         "date_from": since, "limit": 10})


async def daily_digest(api, a):
    day = a.get("date")
    if not day:
        day = (await api.get("/v1/health")).get("latest_publication")
    stats = await api.get("/v1/stats/daily", {"date_from": day, "date_to": day})
    found = await api.get("/v1/events", {
        "date_from": day, "date_to": day, "limit": 200,
        "act_type": ["INSOLVENCY_DECLARATION", "INSOLVENCY_STATUS"],
    })
    # The REST API has no per-day breakdown by event type or province, so
    # this digest carries the day's totals and its insolvency notices only.
    days = stats.get("days") or []
    return {
        "date": day,
        "events": days[0].get("events") if days else 0,
        "parse_completeness": days[0].get("completeness") if days else None,
        "insolvencies": [
            {"company_name": e.get("company_name"), "company_slug": e.get("company_slug"),
             "province": e.get("province"),
             "act_types": sorted({x.get("act_type") for x in e.get("acts") or []
                                  if x.get("act_type")})}
            for e in found.get("events") or []
        ],
        "tier": stats.get("tier"),
    }


async def search_companies(api, a):
    return await api.get("/v1/companies", {
        "name": a["name"], "province": a.get("province"), "status": a.get("status"),
        "limit": a.get("limit", 10), "offset": a.get("offset", 0),
    })


async def list_act_types(api, a):
    return await api.get("/v1/act-types")


async def registry_stats(api, a):
    health = await api.get("/v1/health")
    report = {
        "coverage": {"to": health.get("latest_publication")},
        "source": "BORME (Agencia Estatal Boletin Oficial del Estado)",
    }
    # Parse completeness comes from /v1/stats/daily, which needs a key; the
    # REST API publishes no event or company estimates, so they are left out.
    if api.has_key:
        try:
            stats = await api.get("/v1/stats/daily")
            days = sorted(stats.get("days") or [], key=lambda d: d["date"])[-30:]
            total = sum(d.get("events") or 0 for d in days)
            if total:
                report["parse_completeness_last_30d"] = round(
                    sum((d.get("events") or 0) * (d.get("completeness") or 0)
                        for d in days) / total, 4)
        except ApiError:
            pass
    return report


HANDLERS = {
    "search_events": search_events,
    "company_history": company_history,
    "company_by_nif": company_by_nif,
    "brand_owner": brand_owner,
    "company_brands": company_brands,
    "recent_signals": recent_signals,
    "daily_digest": daily_digest,
    "search_companies": search_companies,
    "list_act_types": list_act_types,
    "registry_stats": registry_stats,
}


# --- MCP wiring -----------------------------------------------------------

@server.list_tools()
async def list_tools():
    return [types.Tool(name=t["name"], description=t["description"],
                       inputSchema=t["inputSchema"]) for t in SPEC["tools"]]


@server.call_tool()
async def call_tool(name, arguments):
    handler = HANDLERS.get(name)
    if handler is None or name not in TOOLS:
        raise ValueError(f"unknown tool: {name}")
    api = Api()
    try:
        result = await handler(api, arguments or {})
    except ApiError as err:
        detail = err.body.get("detail") if isinstance(err.body, dict) else err.body
        message = {"error": f"BORME API answered HTTP {err.status}", "detail": detail}
        if err.status == 401 and not api.has_key:
            message["hint"] = NO_KEY_HINT
        raise ValueError(json.dumps(message, ensure_ascii=False)) from None
    finally:
        await api.close()
    return [types.TextContent(type="text",
                              text=json.dumps(result, ensure_ascii=False, indent=1))]


async def main():
    async with mcp.server.stdio.stdio_server() as (read, write):
        await server.run(read, write, InitializationOptions(
            server_name="borme-mcp",
            server_version=VERSION,
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={}),
            instructions=("Spanish company registry (BORME) data through the "
                          "BORME API REST endpoints. Set BORME_API_KEY for your "
                          "plan; the hosted server at https://mcp.bormeapi.com/mcp "
                          "is the recommended way to connect."),
        ))


if __name__ == "__main__":
    if set(HANDLERS) != set(TOOLS):
        raise SystemExit(f"tools.json and server.py disagree: "
                         f"{sorted(set(HANDLERS) ^ set(TOOLS))}")
    asyncio.run(main())
