"""Comprehensive activity logging for audit trails and compliance."""
import logging
import json
from datetime import datetime
from typing import Optional


# Configure detailed activity logger
activity_logger = logging.getLogger("vision_task.activity")
activity_logger.setLevel(logging.INFO)

# Create handlers
file_handler = logging.FileHandler("activity_log.txt")
console_handler = logging.StreamHandler()

# Create formatter - detailed format for compliance
formatter = logging.Formatter(
    "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

activity_logger.addHandler(file_handler)
activity_logger.addHandler(console_handler)


class AuditLog:
    """Structured audit logging for healthcare compliance."""

    @staticmethod
    def log_action(
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        status: str = "success",
        details: Optional[dict] = None,
        sensitivity: Optional[str] = None,
    ):
        """
        Log an action for audit trail.

        Args:
            user_id: Username of actor
            action: Action performed (create, read, update, delete, access_denied)
            resource_type: Type of resource (task, user, config)
            resource_id: ID of resource affected
            status: Operation status (success, denied, error)
            details: Additional details as dict
            sensitivity: Sensitivity level accessed
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "status": status,
            "sensitivity": sensitivity,
            "details": details or {},
        }

        # Use appropriate log level
        if status == "denied":
            level = logging.WARNING
            message = f"ACCESS DENIED: {user_id} tried {action} on {resource_type}({resource_id})"
        elif status == "error":
            level = logging.ERROR
            message = f"ERROR: {user_id} {action} {resource_type}({resource_id})"
        else:
            level = logging.INFO
            message = f"ACTION: {user_id} {action} {resource_type}({resource_id})"

        activity_logger.log(level, f"{message} | {json.dumps(log_entry)}")

    @staticmethod
    def log_access_attempt(
        user_id: str, task_id: str, allowed: bool, sensitivity: str, reason: str = ""
    ):
        """Log task access attempts for compliance."""
        status = "success" if allowed else "denied"
        AuditLog.log_action(
            user_id=user_id,
            action="read",
            resource_type="task",
            resource_id=task_id,
            status=status,
            sensitivity=sensitivity,
            details={"reason": reason} if reason else None,
        )

    @staticmethod
    def log_modification(
        user_id: str, task_id: str, field: str, old_value: str, new_value: str
    ):
        """Log task modifications."""
        AuditLog.log_action(
            user_id=user_id,
            action="update",
            resource_type="task",
            resource_id=task_id,
            details={"field": field, "old_value": old_value, "new_value": new_value},
        )

