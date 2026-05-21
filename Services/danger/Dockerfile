# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 \
        ffmpeg \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . .

# Pre-download models into image (optional – set CACHE_DIR in .env)
# RUN python scripts/download_models.py

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004", "--workers", "1"]
