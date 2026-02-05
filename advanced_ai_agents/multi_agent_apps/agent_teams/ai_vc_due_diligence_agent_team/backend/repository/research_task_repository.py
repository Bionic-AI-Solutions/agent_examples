"""Repository layer for ResearchTask database operations"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from models.research_task import ResearchTask, TaskStatus
from services.db_service import get_session


async def create_research_task(
    company_name: str,
    company_url: Optional[str],
    input_data: dict,
) -> ResearchTask:
    """
    Create a new research task in the database.

    Args:
        company_name: Name of the company
        company_url: Optional URL of the company
        input_data: Request input data

    Returns:
        Created ResearchTask instance
    """
    async with get_session() as session:
        task = ResearchTask(
            company_name=company_name,
            company_url=company_url,
            status=TaskStatus.QUEUED,
            input_data=input_data,
        )

        session.add(task)
        await session.commit()
        await session.refresh(task)

        logger.info(f"Created research task: {task.task_id}")
        return task


async def get_task_by_id(task_id: str) -> Optional[ResearchTask]:
    """
    Retrieve a research task by its UUID.

    Args:
        task_id: UUID of the task (as string)

    Returns:
        ResearchTask instance or None if not found
    """
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        logger.warning(f"Invalid task_id format: {task_id}")
        return None

    async with get_session() as session:
        stmt = select(ResearchTask).where(ResearchTask.task_id == task_uuid)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if task:
            logger.debug(f"Retrieved task: {task_id}")
        else:
            logger.warning(f"Task not found: {task_id}")

        return task


async def update_task_status(
    task_id: str,
    status: TaskStatus,
    current_stage: Optional[str] = None,
    output_data: Optional[dict] = None,
    error_message: Optional[str] = None,
    artifacts: Optional[dict] = None,
) -> Optional[ResearchTask]:
    """
    Update research task status and related fields.

    Args:
        task_id: UUID of the task (as string)
        status: New task status
        current_stage: Current processing stage
        output_data: Output data if completed
        error_message: Error message if failed
        artifacts: Dict of artifact filenames

    Returns:
        Updated ResearchTask instance or None if not found
    """
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        logger.warning(f"Invalid task_id format: {task_id}")
        return None

    async with get_session() as session:
        stmt = select(ResearchTask).where(ResearchTask.task_id == task_uuid)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            logger.warning(f"Task not found for update: {task_id}")
            return None

        # Update fields
        task.status = status
        task.updated_at = datetime.now(timezone.utc)

        if current_stage is not None:
            task.current_stage = current_stage

        if output_data is not None:
            task.output_data = output_data

        if error_message is not None:
            task.error_message = error_message

        if artifacts is not None:
            task.artifacts = artifacts

        # Set completed_at if task is finished
        if status in [TaskStatus.SUCCESS, TaskStatus.ERROR]:
            task.completed_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(task)

        logger.info(f"Updated task {task_id} to status: {status}")
        return task


async def get_all_tasks(limit: int = 50, offset: int = 0) -> List[ResearchTask]:
    """
    Retrieve all research tasks, ordered by creation date (newest first).

    Args:
        limit: Maximum number of tasks to return
        offset: Number of tasks to skip

    Returns:
        List of ResearchTask instances
    """
    async with get_session() as session:
        stmt = (
            select(ResearchTask)
            .order_by(desc(ResearchTask.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        logger.debug(f"Retrieved {len(tasks)} tasks")
        return list(tasks)


async def get_tasks_by_status(
    status: TaskStatus, limit: int = 50
) -> List[ResearchTask]:
    """
    Retrieve research tasks by status.

    Args:
        status: Task status to filter by
        limit: Maximum number of tasks to return

    Returns:
        List of ResearchTask instances
    """
    async with get_session() as session:
        stmt = (
            select(ResearchTask)
            .where(ResearchTask.status == status)
            .order_by(desc(ResearchTask.created_at))
            .limit(limit)
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        logger.debug(f"Retrieved {len(tasks)} tasks with status {status}")
        return list(tasks)


async def delete_task(task_id: str) -> bool:
    """
    Delete a research task from the database.

    Args:
        task_id: UUID of the task (as string)

    Returns:
        True if deleted, False if not found
    """
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        logger.warning(f"Invalid task_id format: {task_id}")
        return False

    async with get_session() as session:
        stmt = select(ResearchTask).where(ResearchTask.task_id == task_uuid)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            logger.warning(f"Task not found for deletion: {task_id}")
            return False

        await session.delete(task)
        await session.commit()

        logger.info(f"Deleted task: {task_id}")
        return True
