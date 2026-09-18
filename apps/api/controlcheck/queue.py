"""Asynchronous background job queue and worker for ingestion tasks."""
import asyncio
import logging
from typing import Any

from .ingestion import run_ingestion

logger = logging.getLogger(__name__)


class JobQueue:
    def __init__(self, repository, storage_provider, mapper, max_workers: int = 2):
        self.repo = repository
        self.storage = storage_provider
        self.mapper = mapper
        self.max_workers = max_workers
        self._queue: asyncio.Queue | None = None
        self._workers: list[asyncio.Task] = []
        self._running = False

    def _ensure_queue(self):
        if self._queue is None:
            self._queue = asyncio.Queue()
        return self._queue

    async def start(self):
        if self._running:
            return
        self._running = True
        queue = self._ensure_queue()
        for i in range(self.max_workers):
            task = asyncio.create_task(self._worker_loop(f"worker-{i+1}", queue))
            self._workers.append(task)
        logger.info("Ingestion JobQueue started with %d workers", self.max_workers)

    async def stop(self):
        if not self._running:
            return
        self._running = False
        queue = self._ensure_queue()
        for _ in self._workers:
            await queue.put(None)
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("Ingestion JobQueue stopped")

    async def enqueue_ingestion(self, project: dict, job_id: str,
                                uploads: list[tuple[str, bytes]]) -> dict:
        queue = self._ensure_queue()
        # If workers haven't been started (e.g. in test client without lifespan), start them
        if not self._running:
            await self.start()

        item = {
            'type': 'ingestion',
            'project': project,
            'job_id': job_id,
            'uploads': uploads,
        }
        await queue.put(item)
        return self.repo.job(project['id'], job_id)

    async def _worker_loop(self, worker_name: str, queue: asyncio.Queue):
        while self._running:
            try:
                item = await queue.get()
                if item is None:
                    queue.task_done()
                    break
                await self._process_item(item)
                queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("Unexpected error in worker loop %s: %s", worker_name, exc)

    async def _process_item(self, item: dict[str, Any]):
        job_id = item['job_id']
        project = item['project']
        uploads = item['uploads']

        def progress_cb(stage: str, percent: int):
            self.repo.update_job(
                job_id=job_id,
                status='running',
                stage=stage,
                progress_percent=percent
            )

        try:
            self.repo.update_job(
                job_id=job_id,
                status='running',
                stage='storing_raw',
                progress_percent=10
            )

            # run synchronous ingestion in threadpool to avoid blocking event loop
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                run_ingestion,
                project,
                uploads,
                self.repo,
                self.mapper,
                self.storage,
                progress_cb
            )

            status = 'completed'
            self.repo.update_job(
                job_id=job_id,
                status=status,
                stage='completed',
                progress_percent=100,
                result_payload=result
            )
        except Exception as exc:
            logger.exception("Ingestion job %s failed: %s", job_id, exc)
            self.repo.update_job(
                job_id=job_id,
                status='failed',
                stage='failed',
                progress_percent=100,
                error_message=str(exc)
            )
