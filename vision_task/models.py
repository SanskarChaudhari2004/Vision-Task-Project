"""Data models for Vision Task."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List
import uuid


class SensitivityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Task:
    title: str
    description: str = ""
    sensitivity: SensitivityLevel = SensitivityLevel.LOW
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_by: str = ""

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "sensitivity": self.sensitivity.value,
            "created_by": self.created_by,
        }


@dataclass
class User:
    username: str
    roles: List[str] = field(default_factory=list)
