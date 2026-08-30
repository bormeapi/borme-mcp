# BORME MCP Server

MCP server for **Spain's official company registry** (BORME — Boletín Oficial del
Registro Mercantil): 9.5M+ typed company events since 2009, updated every business
day. Incorporations, director appointments, insolvencies, capital changes — 52
event kinds as English enums.

## Hosted endpoint (no setup)

```json
{
  "mcpServers": {
    "borme": {
      "url": "https://mcp.bormeapi.com/mcp"
    }
  }
}
```

Free, read-only, capped at 200 rows per query. Backed by the full 17-year corpus.

## Tools

| Tool | What it does |
|---|---|
| `search_events` | Filter events by date range, province, act type, company name |
| `company_history` | Full timeline of one company (fuzzy name match) |
| `daily_digest` | One day's registry activity, aggregated |
| `registry_stats` | Corpus coverage and volume stats |
| `list_act_types` | The 52-enum vocabulary with Spanish originals |
| `company_by_nif` | Resolve a NIF/CIF tax ID to a company (cross-referenced from open official sources, ~560k companies — 17% of the corpus) |
| `recent_signals` | Sample of derived risk signals: insolvencies, phoenix companies, mass officer exits, AEAT debtors (last 7 days) |

## Example prompts

- *"Which companies declared insolvency in Valencia last week?"*
- *"Show the corporate history of Telefónica Audiovisual Digital"*
- *"How many new companies were incorporated in Madrid in June?"*

## Self-hosting

`server.py` is the complete server (FastMCP + psycopg). It expects a Postgres
with the BORME schema and a read-only role:

```bash
BORME_DSN=postgresql://user:pass@host/borme \
BORME_MCP_TRANSPORT=streamable-http \
python server.py
```

Building the dataset yourself: see our engineering notes —
[You don't need to scrape BORME](https://bormeapi.com/blog/borme-open-data-api).

## Related

- REST API with webhooks & watchlists: [bormeapi.com](https://bormeapi.com)
- Apify actor (pay-per-event feed): [Spain Company Registry — BORME Events](https://apify.com/zon4a/spain-company-registry-borme-events)

## License

MIT (server code). The underlying data originates from [boe.es](https://www.boe.es)
open data (public sector information, Ley 37/2007).
