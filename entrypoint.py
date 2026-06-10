#!/usr/bin/env python3
import os
import subprocess
import sys
import time

import psycopg2


def wait_for_db():
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    dbname = os.environ.get("POSTGRES_DB", "mentoring")
    user = os.environ.get("POSTGRES_USER", "mentoring")
    password = os.environ.get("POSTGRES_PASSWORD", "mentoring")

    print("Waiting for PostgreSQL...")
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
            return
        except psycopg2.OperationalError:
            print(f"Attempt {attempt + 1}/30: PostgreSQL not ready yet...")
            time.sleep(1)

    print("Could not connect to PostgreSQL.")
    sys.exit(1)


def main():
    wait_for_db()
    subprocess.run(["python", "manage.py", "migrate", "--noinput"], check=True)
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: entrypoint.py <command> [args...]")
        sys.exit(1)
    main()
