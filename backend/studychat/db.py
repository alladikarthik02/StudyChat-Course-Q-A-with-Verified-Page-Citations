from contextlib import contextmanager
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from studychat.config import Settings

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


@contextmanager
def connection(settings: Settings, *, vectors: bool = False):
    with psycopg.connect(
        settings.database_url.get_secret_value(), connect_timeout=3, row_factory=dict_row
    ) as conn:
        if vectors:
            register_vector(conn)
        yield conn


def migrate(settings: Settings):
    with connection(settings) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(83012001)")
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY)")
        for path in sorted(MIGRATIONS.glob("*.sql")):
            found = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version = %s", (path.name,)
            ).fetchone()
            if not found:
                conn.execute(path.read_text())
                conn.execute("INSERT INTO schema_migrations VALUES (%s)", (path.name,))


def ready(settings: Settings) -> bool:
    try:
        with connection(settings) as conn:
            versions = conn.execute("SELECT version FROM schema_migrations").fetchall()
            extension = conn.execute(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ).fetchone()
            return bool(extension) and {v["version"] for v in versions} == {
                p.name for p in MIGRATIONS.glob("*.sql")
            }
    except psycopg.Error:
        return False


if __name__ == "__main__":
    migrate(Settings())
    print("Migrations applied.")
