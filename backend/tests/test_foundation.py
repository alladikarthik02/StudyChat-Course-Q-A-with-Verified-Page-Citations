import math

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from studychat.config import Settings
from studychat.main import create_app
from studychat.providers import FixtureProvider, validate_embeddings


def test_health_excludes_secrets_and_rejects_unknown_hosts():
    settings = Settings(database_url="postgresql://sentinel:secret@localhost/missing")
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")
        assert response.json() == {"status": "ok", "provider_mode": "fixture"}
        assert "secret" not in response.text
        assert client.get("/health", headers={"host": "attacker.example"}).status_code == 400
    assert "secret" not in repr(settings)


def test_invalid_config_fails_closed():
    with pytest.raises(ValidationError):
        Settings(max_pages=0)
    with pytest.raises(ValidationError):
        Settings(provider_mode="live")


def test_unavailable_database_is_not_ready():
    settings = Settings(database_url="postgresql://x:x@127.0.0.1:1/missing")
    with TestClient(create_app(settings)) as client:
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json() == {"ready": False}


async def test_fixture_vectors_are_deterministic_and_normalized():
    provider = FixtureProvider()
    vectors = await provider.embed(["page one", "page two", ""])
    assert vectors == await provider.embed(["page one", "page two", ""])
    assert vectors[0] != vectors[1]
    validate_embeddings(vectors, 3, 1536)
    assert all(math.isclose(sum(v * v for v in row), 1) for row in vectors)


@pytest.mark.parametrize(
    "vectors,count,dimensions",
    [([[1]], 2, 1), ([[1]], 1, 2), ([[float("nan")]], 1, 1), ([[0]], 1, 1)],
)
def test_invalid_embeddings_are_rejected(vectors, count, dimensions):
    with pytest.raises(ValueError):
        validate_embeddings(vectors, count, dimensions)
