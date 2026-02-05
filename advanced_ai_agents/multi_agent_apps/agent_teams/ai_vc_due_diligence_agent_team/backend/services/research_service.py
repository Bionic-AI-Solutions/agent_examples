"""Research Service - Integrates ADK due diligence agents with FastAPI

This service wraps the ADK agent pipeline and executes it programmatically.
"""

import sys
from pathlib import Path
from loguru import logger

# Add parent directory to path to import agent module
sys.path.append(str(Path(__file__).parent.parent.parent))

from agent import due_diligence_pipeline


class ResearchService:
    """Service to execute ADK due diligence pipeline programmatically"""

    def __init__(self):
        self.outputs_dir = Path(__file__).parent.parent.parent / "outputs"
        self.outputs_dir.mkdir(exist_ok=True)

    async def run_due_diligence(
        self, company_name: str, company_url: str = None, task_id: str = None
    ) -> dict:
        """
        Execute the due diligence pipeline programmatically.

        Args:
            company_name: Name of the company to analyze
            company_url: Optional URL of the company website
            task_id: Optional task ID for session tracking

        Returns:
            Dict with status, messages, and artifacts
        """
        try:
            # Build query
            query = f"Analyze {company_name}"
            if company_url:
                query = f"Analyze {company_name} at {company_url}"

            logger.info(f"Running due diligence pipeline: {query}")

            # Execute pipeline (this runs all 7 agents sequentially)
            # The pipeline will handle session management internally
            result = await due_diligence_pipeline.arun(query)

            logger.info(
                f"Pipeline completed successfully. Messages: {len(result.messages)}"
            )

            # Extract artifacts from outputs/ directory
            # Tools save artifacts with timestamps, we need to find the latest ones
            artifacts = self._collect_latest_artifacts()

            return {
                "status": "success",
                "messages": [
                    {"content": msg.content, "role": str(msg.role)}
                    for msg in result.messages
                ],
                "artifacts": artifacts,
            }

        except Exception as e:
            logger.error(f"Error in due diligence pipeline: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "messages": [],
                "artifacts": {},
            }

    def _collect_latest_artifacts(self) -> dict:
        """
        Collect the latest generated artifacts from outputs/ directory.

        Returns:
            Dict with artifact types and filenames
        """
        artifacts = {}

        if not self.outputs_dir.exists():
            logger.warning(f"Outputs directory does not exist: {self.outputs_dir}")
            return artifacts

        # Find latest files matching artifact patterns
        # revenue_chart_*.png, investment_report_*.html, infographic_*.(png|jpg)
        chart_files = sorted(
            self.outputs_dir.glob("revenue_chart_*.png"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        if chart_files:
            artifacts["chart"] = chart_files[0].name

        report_files = sorted(
            self.outputs_dir.glob("investment_report_*.html"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        if report_files:
            artifacts["report"] = report_files[0].name

        infographic_files = sorted(
            list(self.outputs_dir.glob("infographic_*.png"))
            + list(self.outputs_dir.glob("infographic_*.jpg")),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        if infographic_files:
            artifacts["infographic"] = infographic_files[0].name

        logger.info(f"Collected artifacts: {artifacts}")
        return artifacts
