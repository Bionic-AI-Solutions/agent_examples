"""SQLAlchemy Database Models for Research Tasks"""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Enum, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class TaskStatus(str, enum.Enum):
    """Research task status enum"""

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    ERROR = "error"


class ResearchTask(Base):
    """Research task database model"""

    __tablename__ = "research_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid.uuid4,
        index=True,
    )
    company_name = Column(String(255), nullable=False)
    company_url = Column(String(500), nullable=True)
    status = Column(
        Enum(TaskStatus, name="research_task_status"),
        nullable=False,
        default=TaskStatus.QUEUED,
        index=True,
    )
    current_stage = Column(String(100), nullable=True)
    input_data = Column(JSONB, nullable=False)
    output_data = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    artifacts = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<ResearchTask(task_id={self.task_id}, company={self.company_name}, status={self.status})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "task_id": str(self.task_id),
            "company_name": self.company_name,
            "company_url": self.company_url,
            "status": self.status.value,
            "current_stage": self.current_stage,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "artifacts": self.artifacts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }
