"""Task management logic with healthcare workflow support."""
from typing import Optional, List
from .models import Task, TaskStatus, SensitivityLevel, User
from .logger import AuditLog


from .db import delete_task as db_delete_task, get_task_by_id, init_db, insert_task, list_tasks as db_list_tasks


class TaskManager:
    def __init__(self):
        # Ensure database is initialized whenever the task manager is created.
        init_db()

    def _can_view_sensitivity(self, user: User, sensitivity: SensitivityLevel) -> bool:
        """Check if user can view tasks of given sensitivity level."""
        if sensitivity == SensitivityLevel.HIGH:
            return user.can_view_high_sensitivity
        elif sensitivity == SensitivityLevel.MEDIUM:
            return user.can_view_medium_sensitivity
        return True  # LOW sensitivity visible to all

    def list_tasks(self, user: User) -> List[Task]:
        """List tasks visible to user.

        Admin users can view all tasks. Non-admin users can only view tasks
        assigned directly to their username.
        """
        visible_tasks = []
        for task in db_list_tasks():
            # Admins see all tasks
            if "admin" in user.roles:
                visible_tasks.append(task)
                continue

            # Non-admin users only see tasks assigned to them.
            if task.assigned_to == user.username:
                visible_tasks.append(task)
                AuditLog.log_access_attempt(
                    user.username, task.id, True, task.sensitivity.value
                )
            else:
                # Log access denial for compliance
                AuditLog.log_access_attempt(
                    user.username,
                    task.id,
                    False,
                    task.sensitivity.value,
                    reason="Task is not assigned to this user",
                )

        return visible_tasks

    def create_task(self, user: User, data: dict) -> Task:
        """Create a task with comprehensive logging and persistent storage."""
        sensitivity = SensitivityLevel(data.get("sensitivity", "low"))
        task = Task(
            title=data.get("title", ""),
            description=data.get("description", ""),
            sensitivity=sensitivity,
            created_by=user.username,
            assigned_to=data.get("assigned_to"),
            department=user.department,
            status=TaskStatus.NEW,
            priority=data.get("priority", 0),
        )

        insert_task(task)

        # Log creation with full details
        AuditLog.log_action(
            user_id=user.username,
            action="create",
            resource_type="task",
            resource_id=task.id,
            sensitivity=sensitivity.value,
            details={
                "title": task.title,
                "assigned_to": task.assigned_to,
                "department": task.department,
                "priority": task.priority,
            },
        )
        return task

    def get_task(self, user: User, task_id: str) -> Optional[Task]:
        """Retrieve a single task with authorization check."""
        task = get_task_by_id(task_id)
        if not task:
            return None

        # Admin can access any task. Non-admin can access only assigned tasks.
        if "admin" in user.roles or task.assigned_to == user.username:
            AuditLog.log_access_attempt(user.username, task.id, True, task.sensitivity.value)
            return task

        AuditLog.log_access_attempt(
            user.username,
            task.id,
            False,
            task.sensitivity.value,
            reason="Task is not assigned to this user",
        )
        return None

    def update_task(self, user: User, task_id: str, data: dict) -> Optional[Task]:
        """Update task with change logging."""
        task = self.get_task(user, task_id)
        if not task:
            AuditLog.log_action(
                user_id=user.username,
                action="update",
                resource_type="task",
                resource_id=task_id,
                status="denied",
                reason="Not found or access denied",
            )
            return None

        # Only creator or admin can update
        if task.created_by != user.username and "admin" not in user.roles:
            AuditLog.log_action(
                user_id=user.username,
                action="update",
                resource_type="task",
                resource_id=task_id,
                status="denied",
                reason="Only creator or admin can update",
            )
            return None

        # Track changes for audit log
        changes = {}
        if "title" in data and data["title"] != task.title:
            changes["title"] = (task.title, data["title"])
            task.title = data["title"]
        if "description" in data and data["description"] != task.description:
            changes["description"] = (task.description, data["description"])
            task.description = data["description"]
        if "status" in data:
            new_status = TaskStatus(data["status"])
            if new_status != task.status:
                changes["status"] = (task.status.value, new_status.value)
                task.status = new_status
        if "assigned_to" in data and data["assigned_to"] != task.assigned_to:
            changes["assigned_to"] = (task.assigned_to, data["assigned_to"])
            task.assigned_to = data["assigned_to"]
        if "priority" in data and data["priority"] != task.priority:
            changes["priority"] = (task.priority, data["priority"])
            task.priority = data["priority"]

        from datetime import datetime

        task.updated_at = datetime.utcnow()

        # Persist the updated task
        insert_task(task)

        # Log all changes
        for field, (old_val, new_val) in changes.items():
            AuditLog.log_modification(user.username, task.id, field, str(old_val), str(new_val))

        return task

    def complete_task(self, user: User, task_id: str) -> Optional[Task]:
        """Mark a task as completed.

        This is intentionally more permissive than full edit: task assignees,
        creators, and admins can complete a task.
        """
        task = self.get_task(user, task_id)
        if not task:
            AuditLog.log_action(
                user_id=user.username,
                action="complete",
                resource_type="task",
                resource_id=task_id,
                status="denied",
                reason="Not found or access denied",
            )
            return None

        if (
            "admin" not in user.roles
            and task.created_by != user.username
            and task.assigned_to != user.username
        ):
            AuditLog.log_action(
                user_id=user.username,
                action="complete",
                resource_type="task",
                resource_id=task_id,
                status="denied",
                reason="Only admin, creator, or assignee can complete",
            )
            return None

        if task.status != TaskStatus.COMPLETED:
            previous_status = task.status.value
            task.status = TaskStatus.COMPLETED
            from datetime import datetime

            task.updated_at = datetime.utcnow()
            insert_task(task)
            AuditLog.log_modification(user.username, task.id, "status", previous_status, TaskStatus.COMPLETED.value)
            AuditLog.log_action(
                user_id=user.username,
                action="complete",
                resource_type="task",
                resource_id=task.id,
                sensitivity=task.sensitivity.value,
            )
        return task

    def delete_task(self, user: User, task_id: str) -> bool:
        """Delete task (admin only) with audit logging."""
        # Attempt to retrieve the task for logging
        task = get_task_by_id(task_id)
        deleted = db_delete_task(task_id)
        if deleted:
            AuditLog.log_action(
                user_id=user.username,
                action="delete",
                resource_type="task",
                resource_id=task_id,
                sensitivity=(task.sensitivity.value if task else None),
                details={"title": task.title} if task else None,
            )
            return True

        AuditLog.log_action(
            user_id=user.username,
            action="delete",
            resource_type="task",
            resource_id=task_id,
            status="error",
            reason="Task not found",
        )
        return False

    def get_stats(self, user: User) -> dict:
        """Get task statistics visible to user."""
        tasks = self.list_tasks(user)
        return {
            "total_tasks": len(tasks),
            "by_status": {
                status.value: sum(1 for t in tasks if t.status == status)
                for status in TaskStatus
            },
            "by_sensitivity": {
                sens.value: sum(1 for t in tasks if t.sensitivity == sens)
                for sens in SensitivityLevel
            },
            "assigned_to_user": sum(1 for t in tasks if t.assigned_to == user.username),
            "created_by_user": sum(1 for t in tasks if t.created_by == user.username),
        }

