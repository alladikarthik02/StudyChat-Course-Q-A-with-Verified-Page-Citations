import os

import pytest
from studychat.config import Settings
from studychat.db import connection, migrate, ready

pytestmark = pytest.mark.integration


@pytest.fixture
def db_settings():
    url = os.environ.get("STUDYCHAT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set STUDYCHAT_TEST_DATABASE_URL to a dedicated test database")
    settings = Settings(database_url=url)
    migrate(settings)
    return settings


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
