"""Pydantic Models for API Requests and Responses"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class ResearchRequest(BaseModel):
    """Request model for starting a new research task"""

    company_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the company to research",
        examples=["Agno AI", "Lovable", "Cursor IDE"],
    )
    company_url: Optional[HttpUrl] = Field(
        None,
        description="Optional URL of the company website",
        examples=["https://agno.com", "https://lovable.dev"],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Agno AI",
                "company_url": "https://agno.com",
            }
        }


class ResearchResponse(BaseModel):
    """Response model for research trigger endpoint"""

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(
        ..., description="Human-readable message", examples=["Research started"]
    )
    task_id: str = Field(..., description="Unique task identifier for polling")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Research started",
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }


class TaskStatusResponse(BaseModel):
    """Response model for task status endpoint"""

    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(
        ...,
        description="Current task status",
        examples=["queued", "in_progress", "success", "error"],
    )
    current_stage: Optional[str] = Field(
        None,
        description="Current processing stage",
        examples=[
            "Company Research",
            "Market Analysis",
            "Financial Modeling",
            "Risk Assessment",
        ],
    )
    artifacts: Optional[Dict[str, str]] = Field(
        None,
        description="Available artifacts (chart, report, infographic)",
        examples=[
            {
                "chart": "revenue_chart_20260204_123456.png",
                "report": "investment_report_20260204_123456.html",
                "infographic": "infographic_20260204_123456.png",
            }
        ],
    )
    error_message: Optional[str] = Field(
        None, description="Error message if status is error"
    )
    created_at: datetime = Field(..., description="Task creation timestamp")
    completed_at: Optional[datetime] = Field(
        None, description="Task completion timestamp"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "in_progress",
                "current_stage": "Market Analysis",
                "artifacts": None,
                "error_message": None,
                "created_at": "2026-02-04T12:00:00Z",
                "completed_at": None,
            }
        }


class TaskResultResponse(BaseModel):
    """Response model for completed task results"""

    task_id: str = Field(..., description="Unique task identifier")
    company_name: str = Field(..., description="Company that was researched")
    company_url: Optional[str] = Field(None, description="Company URL if provided")
    status: str = Field(..., description="Task status (should be success)")
    output_data: Optional[Dict[str, Any]] = Field(
        None, description="Research output data"
    )
    artifacts: Optional[Dict[str, str]] = Field(
        None, description="Available artifacts"
    )
    created_at: datetime = Field(..., description="Task creation timestamp")
    completed_at: datetime = Field(..., description="Task completion timestamp")


class ResearchHistoryResponse(BaseModel):
    """Response model for research history list"""

    tasks: list[TaskStatusResponse] = Field(
        ..., description="List of research tasks"
    )
    total: int = Field(..., description="Total number of tasks")


class ErrorResponse(BaseModel):
    """Error response model"""

    detail: str = Field(..., description="Error description")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")

    class Config:
        json_schema_extra = {
            "example": {"detail": "Task not found", "error_code": "TASK_NOT_FOUND"}
        }
