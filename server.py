"""MCP server over the BORME events database.

Tools for AI agents: search normalized registry events, pull a company's
history, get a daily digest. Requires BORME_DSN (postgresql://...).

Run: borme-mcp  (stdio by default; set BORME_MCP_TRANSPORT=streamable-http
plus BORME_MCP_HOST/PORT for the hosted endpoint at /mcp). Public deployments
set BORME_MCP_MAX_LIMIT (row cap per response, e.g. 50).
"""

from __future__ import annotations

import datetime as dt
import json
import os
from functools import lru_cache
from pathlib import Path

import psycopg
import yaml
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "borme",
    host=os.environ.get("BORME_MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("BORME_MCP_PORT", "8000")),
    stateless_http=True,
)

MAX_LIMIT = int(os.environ.get("BORME_MCP_MAX_LIMIT", "200"))


def _conn() -> psycopg.Connection:
    dsn = os.environ.get("BORME_DSN")
    if not dsn:
        raise RuntimeError("BORME_DSN env var is required (postgresql://user:pass@host:port/db)")
    return psycopg.connect(dsn, connect_timeout=10)


def _event_row(r: tuple) -> dict:
    event_id, date, borme_id, province, company_name, company_slug, acts, registral = r
    return {
        "event_id": event_id,
        "date": date.isoformat(),
        "borme_id": borme_id,
        "province": province,
        "company_name": company_name,
        "company_slug": company_slug,
        "acts": [
            {
                "act_type": a["act_type"],
                "act_type_raw": a["act_type_raw"],
                **({"roles": a["roles"]} if a.get("roles") else {}),
                **({"payload": a["payload_raw"]} if a.get("payload_raw") else {}),
            }
            for a in acts
        ],
        "registral": registral,
    }


@mcp.tool()
def search_events(
    date_from: str | None = None,
    date_to: str | None = None,
    provinces: list[str] | None = None,
    act_types: list[str] | None = None,
    company_name_contains: str | None = None,
    limit: int = 50,
) -> str:
    """Search Spanish commercial-registry (BORME) events.

    All filters optional. Dates are YYYY-MM-DD (coverage starts 2009).
    provinces: BORME province names, accent-insensitive (MADRID, CADIZ...).
    act_types: normalized enums, e.g. INCORPORATION, APPOINTMENTS, TERMINATIONS,
    CAPITAL_INCREASE, DISSOLUTION, INSOLVENCY_STATUS (see list_act_types).
    Returns newest first, at most `limit` (<=200) events as JSON.
    """
    limit = max(1, min(int(limit), MAX_LIMIT))
    where, params = [], []
    if date_from:
        where.append("date >= %s"); params.append(date_from)
    if date_to:
        where.append("date <= %s"); params.append(date_to)
    if provinces:
        where.append("translate(upper(province),'ÁÉÍÓÚÜÑ','AEIOUUN') = ANY(%s)")
        params.append([p.strip().upper().translate(str.maketrans("ÁÉÍÓÚÜÑ", "AEIOUUN")) for p in provinces])
    if act_types:
        where.append("act_types && %s"); params.append([t.strip().upper() for t in act_types])
    if company_name_contains:
        where.append("company_name ILIKE %s"); params.append(f"%{company_name_contains}%")
    sql = (
        "SELECT event_id, date, borme_id, province, company_name, company_slug, acts, registral "
        "FROM events" + (" WHERE " + " AND ".join(where) if where else "") +
        " ORDER BY date DESC, event_id LIMIT %s"
    )
    params.append(limit)
    with _conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return json.dumps({"count": len(rows), "events": [_event_row(r) for r in rows]},
                      ensure_ascii=False, default=str)


@mcp.tool()
def company_history(company: str, limit: int = 100) -> str:
    """Full registry timeline for one company, oldest first.

    `company` is a company slug (e.g. vaz-metales-sl) or an exact-ish name;
    if no slug matches, falls back to case-insensitive name search and, when
    several companies match, returns the list of candidate slugs instead.
    """
    limit = max(1, min(int(limit), MAX_LIMIT))
    with _conn() as conn:
        # companies table + trigram index: events-table ILIKE would seq-scan
        # millions of rows and blow the public role's statement_timeout
        slugs = [r[0] for r in conn.execute(
            "SELECT slug FROM companies WHERE slug = %s "
            "UNION SELECT slug FROM companies WHERE name ILIKE %s LIMIT 20",
            (company.lower(), f"%{company}%")).fetchall()]
        if not slugs:
            return json.dumps({"error": f"no company found matching {company!r}"})
        if len(slugs) > 1:
            return json.dumps({"ambiguous": True, "candidates": slugs}, ensure_ascii=False)
        rows = conn.execute(
            "SELECT event_id, date, borme_id, province, company_name, company_slug, acts, registral "
            "FROM events WHERE company_slug = %s ORDER BY date, event_id LIMIT %s",
            (slugs[0], limit)).fetchall()
    events = [_event_row(r) for r in rows]
    return json.dumps({
        "company_slug": slugs[0],
        "first_seen": events[0]["date"] if events else None,
        "last_seen": events[-1]["date"] if events else None,
        "count": len(events),
        "events": events,
    }, ensure_ascii=False, default=str)


@mcp.tool()
def company_by_nif(nif: str) -> str:
    """Look up a Spanish company by its NIF/CIF tax ID.

    BORME itself prints no tax IDs — this mapping is cross-referenced from
    open official sources (GLEIF, BDNS subsidies register, AEAT) and covers
    a growing subset (~232k companies). A miss means "not matched yet",
    not "does not exist". On a hit, follow up with company_history using
    the returned slug.
    """
    q = nif.strip().upper().replace("-", "").replace(" ", "")
    with _conn() as conn:
        r = conn.execute(
            "SELECT n.company_slug, s.company_name, s.status, s.province, "
            "       n.source, n.confidence "
            "FROM company_nif n JOIN company_state s USING (company_slug) "
            "WHERE n.nif = %s", (q,)).fetchone()
    if not r:
        return json.dumps({"found": False, "nif": q,
                           "note": "NIF coverage is a subset of 3.3M companies; "
                                   "try company_history with the name instead"})
    return json.dumps({
        "found": True, "nif": q, "company_slug": r[0], "company_name": r[1],
        "status": r[2], "province": r[3],
        "nif_source": r[4], "nif_confidence": r[5],
    }, ensure_ascii=False)


@mcp.tool()
def recent_signals(signal_type: str | None = None) -> str:
    """Sample of the latest derived risk signals (last 7 publication days,
    max 10 rows). Types: INSOLVENCY_FILED, ACCORDION, MASS_EXIT,
    OWNERSHIP_CHANGE, DISTRESS_COMBO, PHOENIX, ADDRESS_CLUSTER, AEAT_DEBTOR.

    This is a teaser feed — the full historical signals firehose lives in the
    hosted API's risk tier (https://bormeapi.com/#pricing).
    """
    where, params = ["date >= current_date - 7"], []
    if signal_type:
        where.append("signal_type = %s")
        params.append(signal_type.strip().upper())
    with _conn() as conn:
        rows = conn.execute(
            "SELECT signal_type, date, company_slug, company_name, province, details "
            f"FROM signals WHERE {' AND '.join(where)} "
            "ORDER BY date DESC LIMIT 10", params).fetchall()
    return json.dumps({
        "count": len(rows), "window": "last 7 days", "sample_cap": 10,
        "signals": [{"signal_type": r[0], "date": r[1].isoformat(),
                     "company_slug": r[2], "company_name": r[3],
                     "province": r[4], "details": r[5]} for r in rows],
        "full_feed": "risk tier — https://bormeapi.com/#pricing",
    }, ensure_ascii=False, default=str)


@mcp.tool()
def daily_digest(date: str | None = None) -> str:
    """Digest of one BORME publication day (default: latest in the database):
    totals by event type, top provinces, and all insolvency declarations."""
    with _conn() as conn:
        if not date:
            date = conn.execute("SELECT max(date) FROM events").fetchone()[0].isoformat()
        by_type = conn.execute(
            "SELECT unnest(act_types) t, count(*) FROM events WHERE date = %s "
            "GROUP BY 1 ORDER BY 2 DESC", (date,)).fetchall()
        by_prov = conn.execute(
            "SELECT province, count(*) FROM events WHERE date = %s "
            "GROUP BY 1 ORDER BY 2 DESC LIMIT 10", (date,)).fetchall()
        total = conn.execute("SELECT count(*) FROM events WHERE date = %s", (date,)).fetchone()[0]
        insolv = conn.execute(
            "SELECT company_name, province FROM events WHERE date = %s "
            "AND act_types && ARRAY['INSOLVENCY_DECLARATION','INSOLVENCY_STATUS'] "
            "ORDER BY province", (date,)).fetchall()
    return json.dumps({
        "date": date,
        "total_events": total,
        "by_type": {t: n for t, n in by_type},
        "top_provinces": {p: n for p, n in by_prov},
        "insolvencies": [{"company": c, "province": p} for c, p in insolv],
    }, ensure_ascii=False)


@lru_cache(maxsize=1)
def _act_types() -> list[dict]:
    path = Path(__file__).parent / "vocab" / "act_types.yaml"
    return yaml.safe_load(path.read_text())


@mcp.tool()
def list_act_types() -> str:
    """All normalized event types (English enum + original Spanish label)."""
    seen: dict[str, str] = {}
    for e in _act_types():
        seen.setdefault(e["en"], e["es"])
    return json.dumps([{"act_type": en, "spanish": es} for en, es in sorted(seen.items())],
                      ensure_ascii=False)


@mcp.tool()
def registry_stats() -> str:
    """Coverage and freshness report for the BORME dataset behind this server.

    Returns a JSON object with: total_events (approximate count, planner
    estimate), total_companies, date_range (first and latest publication day
    covered, YYYY-MM-DD), and recent parse completeness (share of gazette text
    successfully structured over the last publication days, e.g. 0.9987).

    Use this to answer "how much data is there?", "how fresh is it?" and
    "can I trust date filters for period X?" before running searches. Takes
    no arguments; counts are estimates (fast reads), not exact tallies.
    """
    with _conn() as conn:
        # planner estimates: exact counts over millions of rows blow the
        # public read-only role's 5s statement_timeout during heavy ingest
        total, companies = conn.execute(
            "SELECT (SELECT reltuples::bigint FROM pg_class WHERE relname='events'), "
            "(SELECT reltuples::bigint FROM pg_class WHERE relname='companies')"
        ).fetchone()
        dmin, dmax = conn.execute("SELECT min(date), max(date) FROM events").fetchone()
        compl = conn.execute(
            "SELECT round((sum(events*completeness)/nullif(sum(events),0))::numeric, 4) "
            "FROM daily_runs WHERE date > (SELECT max(date) FROM daily_runs) - 30"
        ).fetchone()[0]
    return json.dumps({
        "events_approx": int(total),
        "companies_approx": int(companies),
        "coverage": {"from": dmin.isoformat() if dmin else None,
                     "to": dmax.isoformat() if dmax else None},
        "parse_completeness_last_30d": float(compl) if compl is not None else None,
        "source": "BORME via official BOE open-data API",
    })


def main() -> None:
    transport = os.environ.get("BORME_MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
