"""Data models for Vision Task."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from datetime import datetime
import uuid


class SensitivityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    title: str
    description: str = ""
    sensitivity: SensitivityLevel = SensitivityLevel.LOW
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_by: str = ""
    assigned_to: Optional[str] = None
    department: str = ""
    status: TaskStatus = TaskStatus.NEW
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    priority: int = 0  # 0=low, 1=medium, 2=high

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "sensitivity": self.sensitivity.value,
            "created_by": self.created_by,
            "assigned_to": self.assigned_to,
            "department": self.department,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "priority": self.priority,
        }


@dataclass
class User:
    username: str
    roles: List[str] = field(default_factory=list)
    department: str = ""
    can_view_high_sensitivity: bool = False
    can_view_medium_sensitivity: bool = True
