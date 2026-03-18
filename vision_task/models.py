"""Data models used across the Vision Task application.

This module defines the core domain entities (User, Task) and related enums
used for task status and sensitivity levels.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import uuid
from typing import List, Optional


class TaskStatus(Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SensitivityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: Optional[str] = ""
    sensitivity: SensitivityLevel = SensitivityLevel.LOW
    created_by: str = ""
    assigned_to: Optional[str] = None
    department: Optional[str] = None
    status: TaskStatus = TaskStatus.NEW
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    priority: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert enums to their string values for template rendering / JSON.
        d["sensitivity"] = self.sensitivity.value
        d["status"] = self.status.value
        # Ensure datetimes are serializable / sliceable in templates.
        d["created_at"] = self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        d["updated_at"] = self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        return d


@dataclass
class User:
    username: str
    password_hash: str
    roles: List[str] = field(default_factory=list)
    department: Optional[str] = None
    can_view_high_sensitivity: bool = False
    can_view_medium_sensitivity: bool = False

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "roles": self.roles,
            "department": self.department,
            "can_view_high_sensitivity": self.can_view_high_sensitivity,
            "can_view_medium_sensitivity": self.can_view_medium_sensitivity,
        }
