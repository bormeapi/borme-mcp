# BORME API MCP connector

*Español: [README.es.md](README.es.md)*

Connect Microsoft Copilot, Claude, ChatGPT, Cursor, VS Code or any MCP client
to the hosted **BORME API** MCP server: Spanish commercial-registry data
published in the BORME (Boletín Oficial del Registro Mercantil), with more
than 9.6 million events since 2009, company histories, company search by name,
NIF lookup, trademarks and trading names, and risk signals.

The server is hosted at `mcp.bormeapi.com`; there is nothing to install or
run. This repository holds what you need around it: connection settings for
each client, an agent skill, the event-type vocabulary, and a small Docker
image that bridges stdio clients to the hosted server.

The full guide, kept up to date, is at
[bormeapi.com/mcp](https://bormeapi.com/mcp). If this README and that page
ever disagree, the page is right.

## Two ways to connect

**API key: `https://mcp.bormeapi.com/mcp`**

- Transport: Streamable HTTP. Each request gets a plain JSON response; no
  session is kept between calls.
- Authentication: your API key in the `X-API-Key` header. Without a key, the
  free plan's limits apply.
- For clients that can send a header: Microsoft Copilot Studio, Claude Code,
  Cursor, VS Code, Claude Desktop (through mcp-remote) and any other
  Streamable HTTP client.

**OAuth: `https://mcp.bormeapi.com/mcp/oauth`**

- For assistants with custom connectors that sign in with OAuth, such as
  Claude.ai, ChatGPT or Copilot. There is no API key to paste anywhere: you
  sign in with your BORME API account, and the app uses the plan of the
  account that authorized it.
- This endpoint requires a BORME API account and ignores the `X-API-Key`
  header. Its calls share your API key's daily quota with REST API and `/mcp`
  calls made with that key.
- If your account has no active API key, the tools return an error directing
  you to your account page; they work again once your account has an active
  key, without reconnecting the app.
- If the app does not use the connection for 30 days, connect it again. You
  can disconnect the app at any time under Connected apps on your
  [account page](https://bormeapi.com/account).
- For client developers: an unauthenticated call gets `401` with
  `WWW-Authenticate: Bearer resource_metadata="https://mcp.bormeapi.com/.well-known/oauth-protected-resource/mcp/oauth"`.
  The authorization server is `https://bormeapi.com` (metadata at
  `/.well-known/oauth-authorization-server`), with dynamic client
  registration, PKCE (`S256`) and the scope `mcp`.

Get an API key on your [account page](https://bormeapi.com/account).

## Set up your client

### Claude.ai (OAuth)

1. Go to Customize > Connectors > Add custom connector.
2. Enter `https://mcp.bormeapi.com/mcp/oauth` as the server URL. Claude
   detects how to sign in and shows Sign in now and Register automatically;
   keep these options.
3. Click Add. Our sign-in page opens.
4. Sign in with the link we email you, then select Allow.
5. Back in Claude, if the connector page says the connector has no tools,
   reload the page.

On Team and Enterprise plans an owner adds the connector under Organization
settings.

To use your API key instead, enter `https://mcp.bormeapi.com/mcp`, choose No
sign-in and add the `x-api-key` header with your key under Request headers.
Anthropic offers request headers as a beta to a limited set of organizations;
if you do not see that section, use the Claude Desktop setup below.

### ChatGPT (OAuth)

ChatGPT's custom connectors cannot send an API-key header. Add a custom
connector with `https://mcp.bormeapi.com/mcp/oauth` as the server URL and
sign in with your BORME API account. The screens and their names may differ
from Claude.ai's. Without OAuth, ChatGPT can use `https://mcp.bormeapi.com/mcp`
only without a key, on the free plan.

### Microsoft Copilot Studio and Microsoft 365 Copilot (API key)

These steps follow Microsoft's documentation. They may vary with your tenant
and your data loss prevention (DLP) policies.

1. In Copilot Studio, open the agent you want to use and go to Tools > Add a
   tool > New tool > Model Context Protocol.
2. Enter a Server name (BORME API), a Server description and the Server URL:
   `https://mcp.bormeapi.com/mcp`
3. For authentication, choose API key, set Type to Header and enter
   `X-API-Key` as the header name. Select Create, then Create a new
   connection, enter your key and select Add to agent.
4. Test the agent in Copilot Studio first. Then publish it and set up the
   Teams and Microsoft 365 Copilot channel, subject to your organization's
   permissions and policies. If your organization has Power Platform data
   policies (DLP), an administrator may need to allow this connector.

### Claude Code (API key)

```bash
claude mcp add --transport http --scope user \
  --header "X-API-Key: YOUR_KEY" \
  borme https://mcp.bormeapi.com/mcp
```

`--scope user` makes the server available in all your projects; leave it out
to add it to the current project only.

### Cursor (API key)

Add this to `~/.cursor/mcp.json` (all projects) or `.cursor/mcp.json` (one
project) and set `BORME_API_KEY` in your environment:

```json
{
  "mcpServers": {
    "borme": {
      "url": "https://mcp.bormeapi.com/mcp",
      "headers": { "X-API-Key": "${env:BORME_API_KEY}" }
    }
  }
}
```

### VS Code (API key)

Add this to `.vscode/mcp.json` in your workspace. VS Code asks for the key
the first time the server starts:

```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "borme-api-key",
      "description": "BORME API key",
      "password": true
    }
  ],
  "servers": {
    "borme": {
      "type": "http",
      "url": "https://mcp.bormeapi.com/mcp",
      "headers": { "X-API-Key": "${input:borme-api-key}" }
    }
  }
}
```

### Claude Desktop (API key)

Add the server to `claude_desktop_config.json` through
[mcp-remote](https://github.com/geelen/mcp-remote), a third-party bridge that
needs Node.js:

```json
{
  "mcpServers": {
    "borme": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.bormeapi.com/mcp",
               "--header", "X-API-Key:${BORME_API_KEY}"],
      "env": { "BORME_API_KEY": "YOUR_KEY" }
    }
  }
}
```

### Any other Streamable HTTP client (API key)

Send each JSON-RPC message as a POST to `https://mcp.bormeapi.com/mcp` with
`Content-Type: application/json`, an `Accept` header that includes
`application/json`, and your key in `X-API-Key`. For example, to list the
tools:

```bash
curl -s https://mcp.bormeapi.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Docker (stdio bridge)

The [Dockerfile](Dockerfile) builds a stdio bridge to
`https://mcp.bormeapi.com/mcp` with mcp-remote. It holds no data and no
server code; MCP directories build it to list the tools, and you can use it
with any client that starts servers over stdio. It uses your API key, or the
free plan without one; it does not sign in with OAuth.

```bash
docker build -t borme-mcp .
docker run -i --rm -e BORME_API_KEY=YOUR_KEY borme-mcp
```

Leave out `-e BORME_API_KEY=...` to use the free plan.

## Tools

- `search_companies` - find companies by current or former name and get
  ranked company cards.
- `company_history` - the registry timeline of one company: the published
  acts available under your plan, newest first.
- `search_events` - search BORME notices by date, province, act type and
  company name.
- `daily_digest` - one publication day in figures, with its insolvency
  notices.
- `company_by_nif` - find a company by its NIF/CIF tax ID (Basic plan and
  above).
- `brand_owner` - find the company a trademark or trading name is linked to
  (Basic plan and above).
- `company_brands` - trademarks and trading names linked to one company
  (Basic plan and above).
- `recent_signals` - the latest risk signals, such as insolvency filings and
  mass exits (Risk plan).
- `list_act_types` - the act types, with their English labels and the
  original Spanish headings.
- `registry_stats` - size and coverage of the registry data.

Each tool's description and parameter schema, as returned by `tools/list`,
explain its parameters.

## Plans and limits

- **No key or free key:** 50 requests a day, events from the last 7 days,
  company search by name (first 5 results), company histories and daily
  digests within those 7 days, the act-type list and registry statistics.
- **Basic:** 5,000 requests a day, 365 days of history, NIF lookup, the NIF
  on company search results, trademarks and trading names.
- **Pro:** 50,000 requests a day and the full history since 2009.
- **Risk:** 200,000 requests a day and the risk signals tool.

The MCP server uses the same key and the same daily quota as the REST API.
Each tool call counts as one request against the daily quota of your key (or,
without a key, of your IP address). Results are capped per call (for example,
200 events); page with `offset` where a tool offers it.

Plans and prices: [bormeapi.com/#pricing](https://bormeapi.com/#pricing).

## Data

- More than 9.6 million events since 2009 from BORME-A (acts registered in
  the Registro Mercantil), updated every publication day.
- Results are based on published BORME notices and other public data.
  Associations involving trademarks or NIFs are data matches and do not
  constitute legal confirmation.
- Not included: annual accounts, BORME-C notices (legal announcements), and
  notices published before 2009.

## In this repository

- [`skills/borme-registry`](skills/borme-registry/SKILL.md) - an
  [Agent Skill](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
  that tells the agent which tool to call, how to chain them and how to report
  the answers. [`skills/borme-registry-es`](skills/borme-registry-es/SKILL.md)
  is the same skill in Spanish. Install one of the two, not both. For Claude
  Code:

  ```bash
  git clone https://github.com/bormeapi/borme-mcp.git
  mkdir -p ~/.claude/skills && cp -r borme-mcp/skills/borme-registry ~/.claude/skills/
  ```

  The skill needs the MCP server to be connected.
- [`vocab/`](vocab/) - the act-type vocabulary: each enum with its Spanish
  heading and English label.
- [`Dockerfile`](Dockerfile) and [`entrypoint.sh`](entrypoint.sh) - the stdio
  bridge described above.

## Related

- MCP guide: [bormeapi.com/mcp](https://bormeapi.com/mcp)
- REST API docs: [api.bormeapi.com/docs](https://api.bormeapi.com/docs)
- Apify actor: [Spain Company Registry - BORME Events](https://apify.com/zon4a/spain-company-registry-borme-events)
- This repository: [github.com/bormeapi/borme-mcp](https://github.com/bormeapi/borme-mcp)

## License

The contents of this repository are under the [MIT License](LICENSE).

The data served by BORME API contains public-sector information from the
Agencia Estatal Boletín Oficial del Estado (BORME), reused under Law 18/2015
and RD 1495/2011. Not affiliated with or endorsed by BOE.
