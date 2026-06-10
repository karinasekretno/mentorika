#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
python << 'EOF'
import os
import sys
import time

import psycopg2

host = os.environ.get("POSTGRES_HOST", "db")
port = os.environ.get("POSTGRES_PORT", "5432")
dbname = os.environ.get("POSTGRES_DB", "mentoring")
user = os.environ.get("POSTGRES_USER", "mentoring")
password = os.environ.get("POSTGRES_PASSWORD", "mentoring")

for attempt in range(30):
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
        )
        conn.close()
        print("PostgreSQL is ready.")
        sys.exit(0)
    except psycopg2.OperationalError:
        print(f"Attempt {attempt + 1}/30: PostgreSQL not ready yet...")
        time.sleep(1)

print("Could not connect to PostgreSQL.")
sys.exit(1)
EOF

python manage.py migrate --noinput

exec "$@"
