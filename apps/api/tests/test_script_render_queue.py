import asyncio

import pytest

from app.workers.script_render_queue import ScriptRenderQueueManager


@pytest.mark.asyncio
async def test_script_queue_is_independent_and_runs_one_executor_at_a_time():
    started: list[str] = []
    finished = asyncio.Event()

    async def execute(render_id: str) -> None:
        started.append(render_id)
        await asyncio.sleep(0)
        finished.set()

    queue = ScriptRenderQueueManager(executor=execute)
    await queue.start()
    await queue.enqueue("render-1")
    await asyncio.wait_for(finished.wait(), timeout=1)
    await queue.stop()

    assert started == ["render-1"]
    assert queue.health_snapshot()["queue_depth"] == 0

