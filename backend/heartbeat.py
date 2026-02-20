"""
Heartbeat — periodic autonomous agent tasks.

Each project can define a HEARTBEAT.md file in _config/ that describes
what the agent should do automatically at regular intervals.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECTS_ROOT = Path.home() / "VibetaffProjects"


@dataclass
class HeartbeatSchedule:
    interval_seconds: int
    instructions: str
    last_run: float = 0


class Heartbeat:
    def __init__(self, task_queue, check_interval: int = 60):
        self.task_queue = task_queue
        self.check_interval = check_interval
        self._running = False
        self._task: asyncio.Task | None = None
        self._schedules: dict[str, list[HeartbeatSchedule]] = {}

    async def start(self):
        if self._task is None:
            self._running = True
            self._task = asyncio.create_task(self._loop())
            logger.info("Heartbeat started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Heartbeat stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def status(self) -> dict:
        return {
            "running": self._running,
            "projects": list(self._schedules.keys()),
            "check_interval": self.check_interval,
        }

    async def _loop(self):
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Heartbeat tick error: {e}")
            await asyncio.sleep(self.check_interval)

    async def _tick(self):
        """Scan all projects for HEARTBEAT.md and execute due schedules."""
        if not PROJECTS_ROOT.exists():
            return

        now = time.time()

        for project_dir in PROJECTS_ROOT.iterdir():
            if not project_dir.is_dir() or project_dir.name.startswith("."):
                continue

            project_id = project_dir.name
            heartbeat_file = project_dir / "_config" / "HEARTBEAT.md"

            if not heartbeat_file.exists():
                continue

            schedules = self._parse_heartbeat(heartbeat_file.read_text(encoding="utf-8"))
            self._schedules[project_id] = schedules

            for schedule in schedules:
                if now - schedule.last_run >= schedule.interval_seconds:
                    schedule.last_run = now
                    await self._submit_heartbeat_task(project_id, schedule.instructions)

    async def _submit_heartbeat_task(self, project_id: str, instructions: str):
        """Submit a heartbeat task to the queue."""
        from task_queue import Task

        task = Task(
            id=f"hb_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            project_id=project_id,
            conversation_id=f"heartbeat_{project_id}",
            messages=[{
                "role": "user",
                "content": f"[HEARTBEAT AUTO] {instructions}",
            }],
            source="heartbeat",
        )
        await self.task_queue.submit(task)

    def _parse_heartbeat(self, content: str) -> list[HeartbeatSchedule]:
        """Parse a HEARTBEAT.md file into schedules."""
        schedules = []
        current_interval = None

        for line in content.split("\n"):
            line = line.strip()

            heading = re.match(r"^##\s+(.+)", line)
            if heading:
                current_interval = self._parse_interval(heading.group(1))
                continue

            bullet = re.match(r"^[-*]\s+(.+)", line)
            if bullet and current_interval:
                schedules.append(HeartbeatSchedule(
                    interval_seconds=current_interval,
                    instructions=bullet.group(1),
                ))

        return schedules

    def _parse_interval(self, text: str) -> int | None:
        """Parse human-readable intervals like 'Toutes les 30 minutes'."""
        text_lower = text.lower()

        minutes_match = re.search(r"(\d+)\s*min", text_lower)
        if minutes_match:
            return int(minutes_match.group(1)) * 60

        hours_match = re.search(r"(\d+)\s*h", text_lower)
        if hours_match:
            return int(hours_match.group(1)) * 3600

        if "jour" in text_lower or "day" in text_lower:
            return 86400

        if "semaine" in text_lower or "week" in text_lower:
            return 604800

        return None
