FROM node:20-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 NEXT_TELEMETRY_DISABLED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/package.json web/package-lock.json web/
RUN npm --prefix web ci

COPY . .
RUN python -m generator --seed 7 \
    && python -m engine.run \
    && npm --prefix web run build

CMD ["bash", "deploy/start.sh"]
