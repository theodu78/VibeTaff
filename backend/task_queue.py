"""
Async task queue for background agent work.

Tasks survive UI disconnections — the backend continues working
even if the user closes the window.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class Task:
    id: str
    project_id: str
    conversation_id: str
    messages: list[dict]
    source: str = "user"  # "user" | "heartbeat"
    status: TaskStatus = TaskStatus.QUEUED
    result: str | None = None
    progress: dict = field(default_factory=dict)
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "conversation_id": self.conversation_id,
            "source": self.source,
            "status": self.status.value,
            "result": self.result,
            "progress": self.progress,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class TaskQueue:
    def __init__(self, executor=None):
        """
        executor: async callable(task: Task) -> str
        Will be set by main.py at startup with the agent execution function.
        """
        self._queue: asyncio.Queue[Task] = asyncio.Queue()
        self._tasks: dict[str, Task] = {}
        self._worker_task: asyncio.Task | None = None
        self._executor = executor

    def set_executor(self, executor):
        self._executor = executor

    async def start(self):
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("Task queue worker started")

    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            logger.info("Task queue worker stopped")

    async def submit(self, task: Task) -> str:
        self._tasks[task.id] = task
        await self._queue.put(task)
        logger.info(f"Task {task.id} queued ({task.source})")
        return task.id

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def list_tasks(self, project_id: str | None = None, limit: int = 50) -> list[dict]:
        tasks = list(self._tasks.values())
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in tasks[:limit]]

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        if task.status in (TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.PAUSED):
            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()
            return True
        return False

    async def _worker(self):
        while True:
            task = await self._queue.get()

            if task.status == TaskStatus.CANCELLED:
                self._queue.task_done()
                continue

            task.status = TaskStatus.RUNNING
            task.started_at = time.time()

            try:
                if self._executor:
                    result = await self._executor(task)
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                else:
                    task.status = TaskStatus.FAILED
                    task.error = "No executor configured"
            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED
                raise
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                logger.error(f"Task {task.id} failed: {e}")
            finally:
                task.completed_at = time.time()
                self._queue.task_done()

            from notify import notify
            if task.status == TaskStatus.COMPLETED:
                notify("VibeTaff", f"Tâche terminée : {task.id[:8]}…")
            elif task.status == TaskStatus.FAILED:
                notify("VibeTaff", f"Tâche échouée : {task.error or 'erreur inconnue'}")


task_queue = TaskQueue()
