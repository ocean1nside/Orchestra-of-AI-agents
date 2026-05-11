from __future__ import annotations

import asyncio

from orchestrator_api.modules.indexing.pipeline import execute_index_job


def run_index_job(job_id: str) -> None:
    asyncio.run(execute_index_job(job_id))
