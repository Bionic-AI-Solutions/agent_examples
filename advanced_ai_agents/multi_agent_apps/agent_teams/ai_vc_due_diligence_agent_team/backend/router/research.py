"""Research API Router - Endpoints for VC due diligence research"""

import asyncio
from fastapi import APIRouter, HTTPException, Response, status, Depends
from loguru import logger

from services.auth_service import get_current_user, is_auth_enabled

from models.research_request import (
    ResearchRequest,
    ResearchResponse,
    TaskStatusResponse,
    ResearchHistoryResponse,
    ErrorResponse,
)
from models.research_task import TaskStatus
from services.research_service import ResearchService
from services.artifact_service import ArtifactService
from services.report_delivery_service import ReportDeliveryService
from repository.research_task_repository import (
    create_research_task,
    update_task_status,
    get_task_by_id,
    get_all_tasks,
)

router = APIRouter(prefix="/api/research", tags=["Research"])

# Initialize services
research_service = ResearchService()
artifact_service = ArtifactService()
report_delivery_service = ReportDeliveryService()


@router.post(
    "/trigger",
    response_model=ResearchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start new due diligence research",
    description="Triggers a new VC due diligence research task. Returns task ID for status polling.",
)
async def trigger_research(
    request: ResearchRequest,
    current_user: dict = Depends(get_current_user),
):
    """Start a new company research task (requires authentication)"""
    try:
        logger.info(
            f"Received research request for: {request.company_name}"
        )

        # Create task in database
        task = await create_research_task(
            company_name=request.company_name,
            company_url=str(request.company_url) if request.company_url else None,
            input_data=request.model_dump(),
        )

        logger.info(f"Created task {task.task_id} for {request.company_name}")

        # Run research in background
        async def run_research_with_tracking():
            """Background task to execute research and track progress"""
            try:
                # Update to in_progress
                await update_task_status(
                    task_id=str(task.task_id),
                    status=TaskStatus.IN_PROGRESS,
                    current_stage="Initializing due diligence pipeline",
                )

                # Execute research pipeline
                result = await research_service.run_due_diligence(
                    company_name=request.company_name,
                    company_url=str(request.company_url) if request.company_url else None,
                    task_id=str(task.task_id),
                )

                if result["status"] == "success":
                    # Save artifacts to persistent storage
                    artifacts = result.get("artifacts", {})
                    if artifacts:
                        saved_artifacts = await artifact_service.save_all_artifacts(
                            task_id=str(task.task_id), artifacts=artifacts
                        )
                    else:
                        saved_artifacts = {}
                        logger.warning(
                            f"No artifacts generated for task {task.task_id}"
                        )

                    # Generate PDF report and send email
                    email_sent = False
                    if saved_artifacts:
                        logger.info(f"Generating PDF report for task {task.task_id}")
                        await update_task_status(
                            task_id=str(task.task_id),
                            status=TaskStatus.IN_PROGRESS,
                            current_stage="Generating PDF report and sending email",
                        )

                        delivery_result = await report_delivery_service.deliver_report(
                            task_id=str(task.task_id),
                            company_name=request.company_name,
                            artifacts=saved_artifacts,
                            recipient_email=request.email_recipient,
                        )

                        # Add PDF to artifacts if generated
                        if delivery_result.get("pdf_generated"):
                            saved_artifacts["pdf_report"] = delivery_result["pdf_filename"]

                        email_sent = delivery_result.get("email_sent", False)

                        if delivery_result.get("error"):
                            logger.warning(f"Report delivery issue: {delivery_result['error']}")

                    # Update task to success
                    await update_task_status(
                        task_id=str(task.task_id),
                        status=TaskStatus.SUCCESS,
                        current_stage="Research completed",
                        output_data={
                            "messages": result.get("messages", []),
                            "email_sent": email_sent,
                        },
                        artifacts=saved_artifacts,
                    )

                    logger.info(
                        f"Research completed successfully for task {task.task_id}"
                    )
                else:
                    # Handle error
                    error_msg = result.get("error", "Unknown error")
                    await update_task_status(
                        task_id=str(task.task_id),
                        status=TaskStatus.ERROR,
                        error_message=error_msg,
                    )
                    logger.error(
                        f"Research failed for task {task.task_id}: {error_msg}"
                    )

            except Exception as e:
                logger.error(
                    f"Error in research pipeline for task {task.task_id}: {e}",
                    exc_info=True,
                )
                await update_task_status(
                    task_id=str(task.task_id),
                    status=TaskStatus.ERROR,
                    error_message=str(e),
                )

        # Launch background task
        asyncio.create_task(run_research_with_tracking())

        # Return immediately with task ID
        return ResearchResponse(
            success=True,
            message="Research started successfully",
            task_id=str(task.task_id),
        )

    except Exception as e:
        logger.error(f"Error triggering research: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start research: {str(e)}",
        )


@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get research task status",
    description="Polls the status of a research task. Use for monitoring progress.",
    responses={404: {"model": ErrorResponse}},
)
async def get_research_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Poll task status (requires authentication)"""
    task = await get_task_by_id(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    # Extract email_sent from output_data if available
    email_sent = None
    if task.output_data and isinstance(task.output_data, dict):
        email_sent = task.output_data.get("email_sent")

    return TaskStatusResponse(
        task_id=str(task.task_id),
        status=task.status.value,
        current_stage=task.current_stage,
        artifacts=task.artifacts,
        email_sent=email_sent,
        error_message=task.error_message,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )


@router.get(
    "/artifact/{task_id}/{filename}",
    summary="Download research artifact",
    description="Download generated artifacts (chart, report, infographic)",
    responses={
        200: {"description": "Artifact file"},
        404: {"model": ErrorResponse},
    },
)
async def get_artifact(
    task_id: str,
    filename: str,
    current_user: dict = Depends(get_current_user),
):
    """Download artifact file (requires authentication)"""
    try:
        # Verify task exists
        task = await get_task_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task not found: {task_id}",
            )

        # Get artifact from storage
        data = await artifact_service.get_artifact(task_id, filename)

        # Determine content type
        if filename.endswith(".html"):
            media_type = "text/html"
        elif filename.endswith(".png"):
            media_type = "image/png"
        elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
            media_type = "image/jpeg"
        elif filename.endswith(".pdf"):
            media_type = "application/pdf"
        else:
            media_type = "application/octet-stream"

        return Response(
            content=data,
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"'
            },
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {filename}",
        )
    except Exception as e:
        logger.error(f"Error retrieving artifact: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve artifact: {str(e)}",
        )


@router.get(
    "/history",
    response_model=ResearchHistoryResponse,
    summary="Get research history",
    description="Retrieve list of past research tasks",
)
async def get_research_history(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """List past research tasks (requires authentication)"""
    try:
        tasks = await get_all_tasks(limit=limit, offset=offset)

        task_responses = []
        for task in tasks:
            # Extract email_sent from output_data if available
            email_sent = None
            if task.output_data and isinstance(task.output_data, dict):
                email_sent = task.output_data.get("email_sent")

            task_responses.append(
                TaskStatusResponse(
                    task_id=str(task.task_id),
                    status=task.status.value,
                    current_stage=task.current_stage,
                    artifacts=task.artifacts,
                    email_sent=email_sent,
                    error_message=task.error_message,
                    created_at=task.created_at,
                    completed_at=task.completed_at,
                )
            )

        return ResearchHistoryResponse(
            tasks=task_responses, total=len(task_responses)
        )

    except Exception as e:
        logger.error(f"Error retrieving history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}",
        )
