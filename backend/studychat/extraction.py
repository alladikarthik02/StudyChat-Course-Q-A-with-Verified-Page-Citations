import asyncio
import json
import sys
from pathlib import Path

import psutil

from studychat.config import Settings


class IngestionError(Exception):
    pass


async def memory_watch(process, limit_bytes: int):
    """RSS watchdog for macOS; Linux additionally enforces RLIMIT_AS in the worker."""
    child = psutil.Process(process.pid)
    while process.returncode is None:
        try:
            if child.memory_info().rss > limit_bytes:
                raise IngestionError("parser_resource_limit")
        except psutil.NoSuchProcess:
            return
        await asyncio.sleep(0.01)


async def extract_pdf(path: Path, settings: Settings) -> dict:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-I",
        str(Path(__file__).with_name("pdf_worker.py")),
        str(path),
        str(settings.max_pages),
        str(settings.max_text_chars),
        str(settings.parse_memory_mb),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    reader = asyncio.create_task(process.communicate())
    watcher = asyncio.create_task(memory_watch(process, settings.parse_memory_mb * 1024 * 1024))
    try:
        (stdout, _), _ = await asyncio.wait_for(
            asyncio.gather(reader, watcher), settings.parse_timeout_seconds
        )
    except TimeoutError:
        raise IngestionError("parser_timeout") from None
    finally:
        if process.returncode is None:
            process.kill()
        await process.wait()
        for task in (reader, watcher):
            if not task.done():
                task.cancel()
        await asyncio.gather(reader, watcher, return_exceptions=True)
    if process.returncode != 0:
        raise IngestionError("parser_resource_limit")
    try:
        result = json.loads(stdout)
    except (ValueError, UnicodeError):
        raise IngestionError("invalid_pdf") from None
    if "error" in result:
        raise IngestionError(result["error"])
    return result
