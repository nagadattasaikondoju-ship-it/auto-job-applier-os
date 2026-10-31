#!/bin/sh
# Container start-up for hosted deploys: migrate, load companies, start the background worker
# (unless RUN_WORKER_IN_API=false, as in infra/gcp where it has its own container) and run the API.
# Uses absolute paths so it doesn't depend on how the host runs the command.
set -e
cd /app
PY=/app/.venv/bin/python

"$PY" -m alembic upgrade head
"$PY" -m packages.core.seed.load_companies

if [ "${RUN_WORKER_IN_API:-true}" = "true" ]; then
  "$PY" -m celery -A apps.workers.celery_app.celery_app worker --beat --pool=solo --loglevel=info \
    --queues=job_ingestion,embeddings,ai_matching,document_generation,form_schema,browser_automation,autopilot,notifications,maintenance,priority &
fi

exec "$PY" -m uvicorn apps.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
