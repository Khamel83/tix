FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends     build-essential curl sqlite3 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .
RUN mkdir -p /data/backups /data/captures

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn ticket_sniper.web.app:app --host 0.0.0.0 --port 8000"]
