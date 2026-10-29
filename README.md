# BORME MCP Server

*Español: [README.es.md](README.es.md)*

MCP server for **BORME** (Boletín Oficial del Registro Mercantil), the official
gazette of Spain's commercial registry: 9.5M+ typed company events since 2009,
updated every business day. Incorporations, director appointments, insolvencies,
capital changes - 52 event types, each an English enum.

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

In Claude Code:

```bash
claude mcp add --transport http borme https://mcp.bormeapi.com/mcp
```

Read-only; `limit` is at most 200 per call. Without a key it runs on the free plan:
the last 7 days, 50 calls a day per IP address. An API key from
[bormeapi.com/account](https://bormeapi.com/account), sent in the `X-API-Key`
header, unlocks your plan: `"headers": {"X-API-Key": "YOUR_KEY"}` in clients
configured with JSON (Cursor's `mcp.json` and similar), `--header "X-API-Key:
YOUR_KEY"` in `claude mcp add`.

- **free** (no key): the last 7 days
- **basic**: the last 365 days, plus tax-ID and brand lookups
- **pro**: everything in basic, with the full history back to 2009
- **risk**: pro plus the risk-signals tool

Plans and prices: [bormeapi.com/pricing](https://bormeapi.com/pricing).

## Tools

| Tool | What it does | From plan |
|---|---|---|
| `search_events` | Filter events by date range, province, act type, company name | free |
| `company_history` | Timeline of one company (slug or name), paged, as deep as your plan's window | free |
| `daily_digest` | One publication day's registry activity, aggregated | free |
| `registry_stats` | Corpus coverage and freshness | free |
| `list_act_types` | The event-type vocabulary: each enum with its Spanish original and English label | free |
| `company_by_nif` | Resolve a NIF/CIF tax ID to a company (more than 520,000 mappings from public sources; a miss means "not matched yet") | basic |
| `brand_owner` | Which company holds a trademark or trading name | basic |
| `company_brands` | Trademarks and trading names held by one company | basic |
| `recent_signals` | Sample of the latest derived risk signals, including insolvency declarations, phoenix companies, mass officer exits and AEAT debtor-list entries | risk |

## Agent skill

[`skills/borme-registry`](skills/borme-registry/SKILL.md) is an
[Agent Skill](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
that tells the agent which tool to call, how to chain them (tax ID → company →
history, brand → company → history) and how to report the answers: registry
data verbatim, a NIF miss as "not matched yet", trademarks kept apart from
company names. [`skills/borme-registry-es`](skills/borme-registry-es/SKILL.md)
is the same skill in Spanish. Install one of the two, not both: they cover the
same questions.

For Claude Code, copy the folder into your skills directory:

```bash
git clone https://github.com/bormeapi/borme-mcp.git
mkdir -p ~/.claude/skills && cp -r borme-mcp/skills/borme-registry ~/.claude/skills/
```

Other agents that support `SKILL.md` skills use the same folder, placed in
their own skills directory. The skill needs the MCP server above to be connected.

## Example prompts

The first works without a key. The other two need one, because the free plan
sees only the last 7 days; the full history needs pro.

- *"Which companies were declared insolvent in Valencia last week?"*
- *"Show the corporate history of Telefónica Audiovisual Digital"*
- *"How many new companies were incorporated in Madrid in June?"*

## Self-hosting

`server.py` is a single-file server (FastMCP + psycopg) with an earlier tool
set than the hosted endpoint: it has no plans or keys, no brand tools
(`brand_owner`, `company_brands`) and no `offset` paging in `company_history`.
The skill above is written for the hosted endpoint. The server reads a
PostgreSQL database with the tables it queries, through a read-only role; that
schema is not part of this repository:

```bash
BORME_DSN=postgresql://user:pass@host/borme \
BORME_MCP_TRANSPORT=streamable-http \
python server.py
```

What building the dataset yourself involves:
[BORME Open Data API: Source XML vs Structured Company Intelligence](https://bormeapi.com/blog/borme-open-data-api).

## Related

- REST API with webhooks & watchlists: [bormeapi.com](https://bormeapi.com)
- Apify actor (pay-per-event feed): [Spain Company Registry - BORME Events](https://apify.com/zon4a/spain-company-registry-borme-events)

## License

MIT (server code). Registry events - source of the data: Agencia Estatal Boletín
Oficial del Estado ([boe.es](https://www.boe.es)). Trademarks and trading names:
Oficina Española de Patentes y Marcas (OEPM). Tax-ID mappings and some
risk-signal inputs: other Spanish public-sector open data. Public sector
information reused under Ley 37/2007.

Independent project, not affiliated with, sponsored or endorsed by the Agencia
Estatal Boletín Oficial del Estado or the Registro Mercantil.
