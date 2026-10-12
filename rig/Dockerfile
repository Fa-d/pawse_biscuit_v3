# Pawse Studio server image (built and run by Cloudflare Containers, see cloudflare/).
# Same Python as local development, so the tested library versions install as wheels.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    STUDIO_CACHE=/tmp/studio-cache STUDIO_DB=/tmp/studio.db
WORKDIR /srv

COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

COPY mascot ./mascot
COPY studio ./studio
COPY app ./app

RUN useradd --create-home --uid 10001 studio
USER studio
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
