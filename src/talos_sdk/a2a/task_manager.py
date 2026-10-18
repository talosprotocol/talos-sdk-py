from enum import Enum
from typing import Any

from pydantic import BaseModel

from .session_client import A2ASessionClient


class TaskState(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class A2ATask(BaseModel):
    task_id: str
    state: TaskState
    intent: str
    artifact: dict[str, Any] | None = None

class TaskManager:
    def __init__(self, client: A2ASessionClient):
        self.client = client
        self.active_tasks: dict[str, A2ATask] = {}

    async def propose_task(self, task_id: str, intent: str) -> A2ATask:
        """Propositions a new task to the remote agent over the encrypted ratchet."""
        task = A2ATask(task_id=task_id, state=TaskState.PENDING, intent=intent)
        self.active_tasks[task_id] = task
        # send_message expects bytes
        await self.client.send_message(task.model_dump_json().encode())
        return task

    async def update_task(
        self, task_id: str, state: TaskState, artifact: dict[str, Any] | None = None
    ) -> None:
        """Transitions task state and exchanges artifacts upon completion."""
        task = self.active_tasks.get(task_id)
        if task:
            task.state = state
            task.artifact = artifact
            await self.client.send_message(task.model_dump_json().encode())
        else:
            # If task not in local memory, we might need a way to fetch it,
            # but per blueprint we just update if it exists.
            pass
