import pytest
from studychat.db import connection, migrate, ready

pytestmark = pytest.mark.integration


def test_migration_is_idempotent_and_vector_extension_works(db_settings):
    migrate(db_settings)
    assert ready(db_settings)
    with connection(db_settings) as conn:
        assert (
            conn.execute("SELECT '[1,0]'::vector <=> '[0,1]'::vector AS distance").fetchone()[
                "distance"
            ]
            == 1
        )
        assert conn.execute("SELECT count(*) AS n FROM schema_migrations").fetchone()["n"] == 1
