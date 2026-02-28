"""Task management logic."""
from .models import Task, SensitivityLevel
from .auth import require_role


class TaskManager:
    def __init__(self):
        self._tasks = []

    def list_tasks(self, user):
        # In a real system we'd filter according to sensitivity/roles
        return self._tasks

    def create_task(self, user, data):
        sensitivity = SensitivityLevel(data.get("sensitivity", "low"))
        task = Task(
            title=data.get("title", ""),
            description=data.get("description", ""),
            sensitivity=sensitivity,
            created_by=user.username,
        )
        self._tasks.append(task)
        return task

    @require_role("admin")
    def delete_task(self, user, task_id):
        for t in self._tasks:
            if t.id == task_id:
                if t.sensitivity == SensitivityLevel.HIGH:
                    # require re-authentication, omitted for demo
                    pass
                self._tasks.remove(t)
                return True
        return False
