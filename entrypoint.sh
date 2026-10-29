#!/bin/sh
# stdio proxy to the hosted BORME API MCP server.
# The server runs at https://mcp.bormeapi.com/mcp; this only bridges stdio
# clients (and MCP directories that introspect a container) to it.
# BORME_API_KEY is optional: without it the free plan applies.
set -eu

url="${BORME_MCP_URL:-https://mcp.bormeapi.com/mcp}"

if [ -n "${BORME_API_KEY:-}" ]; then
  # A header file keeps the key out of the process list.
  umask 077
  header_file="$(mktemp)"
  printf 'X-API-Key: %s\n' "$BORME_API_KEY" > "$header_file"
  exec mcp-remote "$url" --transport http-only --header-file "$header_file"
fi

exec mcp-remote "$url" --transport http-only
