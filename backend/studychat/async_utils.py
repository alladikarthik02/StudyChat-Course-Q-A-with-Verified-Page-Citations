import asyncio
from functools import partial


async def settled_thread(function, *args, **kwargs):
    """Do not let cancellation outlive a database mutation running in a worker thread."""
    task = asyncio.create_task(asyncio.to_thread(partial(function, *args, **kwargs)))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            await task
        finally:
            raise
