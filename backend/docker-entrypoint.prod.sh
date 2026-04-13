#!/bin/sh
set -eu

wait_for_database() {
  python - <<'PY'
import os
import sys
import time

import pymysql

host = os.environ.get("DB_HOST")
port = int(os.environ.get("DB_PORT", "3306"))
user = os.environ.get("DB_USER")
password = os.environ.get("DB_PASSWORD", "")
database = os.environ.get("DB_NAME")
timeout = int(os.environ.get("DB_WAIT_TIMEOUT", "60"))

if not all([host, user, database]):
    print("DB_HOST, DB_USER, and DB_NAME must be set when USE_SQLITE is false.", file=sys.stderr)
    sys.exit(1)

deadline = time.time() + timeout
last_error = None

while time.time() < deadline:
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=5,
            read_timeout=5,
            write_timeout=5,
        )
        connection.close()
        print(f"Database {host}:{port}/{database} is reachable.")
        sys.exit(0)
    except Exception as exc:
        last_error = exc
        print(f"Waiting for database {host}:{port}/{database}: {exc}", flush=True)
        time.sleep(2)

print(f"Database was not reachable within {timeout}s: {last_error}", file=sys.stderr)
sys.exit(1)
PY
}

if [ "${USE_SQLITE:-false}" = "true" ]; then
  echo "USE_SQLITE=true, skipping database reachability check."
else
  wait_for_database
fi

if [ "${RUN_DB_INIT:-1}" = "1" ]; then
  SKIP_SCHEDULER_INIT=1 python init_db.py
fi

exec gunicorn \
  --bind "0.0.0.0:${PORT:-5000}" \
  --workers "${GUNICORN_WORKERS:-1}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  app:app
