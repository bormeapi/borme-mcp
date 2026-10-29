# The local stdio server (server.py), built and run inside the image. It
# wraps the BORME API REST endpoints; tools/list needs no key and no network.
# MCP directories such as Glama build this image to list the tools.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py tools.json ./
USER nobody
# Optional: -e BORME_API_KEY=<your key>; most tools need one through REST.
CMD ["python", "server.py"]
