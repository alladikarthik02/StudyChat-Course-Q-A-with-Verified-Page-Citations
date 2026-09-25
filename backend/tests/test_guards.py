import asyncio

from studychat.guards import RequestGuards


async def test_chunked_body_is_limited_before_multipart_parser():
    called = False
    messages = iter(
        [
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"456", "more_body": False},
        ]
    )
    sent = []

    async def inner(scope, receive, send):
        nonlocal called
        called = True

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    guard = RequestGuards(inner, max_body_bytes=5)
    await guard(
        {"type": "http", "method": "POST", "path": "/documents", "headers": []}, receive, send
    )
    assert not called
    assert sent[0]["status"] == 413
    assert not guard.receiving


async def test_disconnect_releases_upload_slot():
    async def inner(*args):
        raise AssertionError("disconnected request must not reach parser")

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        raise AssertionError("do not send to a disconnected client")

    guard = RequestGuards(inner, max_body_bytes=5)
    await guard(
        {"type": "http", "method": "POST", "path": "/documents", "headers": []}, receive, send
    )
    assert not guard.receiving


async def test_cancelled_database_mutation_settles_before_cleanup():
    import threading

    import pytest
    from studychat.async_utils import settled_thread

    entered = threading.Event()
    release = threading.Event()
    finished = []

    def mutation():
        entered.set()
        release.wait(timeout=2)
        finished.append(True)

    task = asyncio.create_task(settled_thread(mutation))
    while not entered.is_set():
        await asyncio.sleep(0.001)
    task.cancel()
    await asyncio.sleep(0.001)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert finished == [True]
