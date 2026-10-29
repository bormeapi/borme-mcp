# A stdio bridge to the hosted BORME API MCP server, not the server itself.
# MCP directories such as Glama build this image to list the tools; it holds
# no data and no server code. mcp-remote is a third-party bridge
# (https://github.com/geelen/mcp-remote), pinned to a tested version.
FROM node:22-alpine
RUN npm install -g --no-fund --no-audit mcp-remote@0.15.2 \
    && npm cache clean --force
COPY entrypoint.sh /usr/local/bin/borme-mcp
USER node
# Optional: BORME_API_KEY=<your key> to use your plan instead of the free one.
ENTRYPOINT ["/usr/local/bin/borme-mcp"]
