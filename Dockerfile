FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
COPY vocab/ vocab/
# stdio by default; set BORME_MCP_TRANSPORT=streamable-http (+ BORME_DSN) to serve HTTP
CMD ["python", "server.py"]
