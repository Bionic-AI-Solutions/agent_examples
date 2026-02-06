"""Report Delivery Service - Orchestrates PDF generation and email delivery

This service coordinates the final report delivery workflow:
1. Generates a combined PDF from all artifacts
2. Sends the PDF via email (if configured)
"""

from pathlib import Path
from loguru import logger
from typing import Optional

from services.pdf_service import PDFService
from services.email_service import EmailService


class ReportDeliveryService:
    """Orchestrates the complete report delivery workflow"""

    def __init__(self, storage_path: str = "/app/artifacts"):
        self.storage_path = Path(storage_path)
        self.pdf_service = PDFService(storage_path)
        self.email_service = EmailService()

    async def deliver_report(
        self,
        task_id: str,
        company_name: str,
        artifacts: dict,
        recipient_email: Optional[str] = None,
    ) -> dict:
        """
        Generate PDF and optionally send via email.

        PDF generation always happens (regardless of email configuration).
        Email is sent only if the service is configured and recipient is available.

        Args:
            task_id: Unique task identifier
            company_name: Name of the analyzed company
            artifacts: Dict of artifact filenames (chart, report, infographic)
            recipient_email: Optional email override for delivery

        Returns:
            Dict with delivery status and details:
            {
                "pdf_generated": bool,
                "pdf_filename": str | None,
                "email_sent": bool,
                "email_details": dict | None,
                "error": str | None
            }
        """
        result = {
            "pdf_generated": False,
            "pdf_filename": None,
            "email_sent": False,
            "email_details": None,
            "error": None,
        }

        # Validate inputs
        if not task_id:
            result["error"] = "Missing task_id"
            return result

        if not company_name:
            result["error"] = "Missing company_name"
            return result

        if not artifacts:
            logger.warning(f"No artifacts provided for task {task_id}")
            result["error"] = "No artifacts to include in PDF"
            return result

        try:
            # Step 1: ALWAYS generate PDF (regardless of email configuration)
            logger.info(f"Generating PDF report for task {task_id} - {company_name}")

            pdf_filename = await self.pdf_service.generate_combined_report(
                task_id=task_id,
                company_name=company_name,
                artifacts=artifacts,
            )

            result["pdf_generated"] = True
            result["pdf_filename"] = pdf_filename
            logger.info(f"PDF generated successfully: {pdf_filename}")

        except Exception as e:
            logger.error(f"PDF generation failed for task {task_id}: {e}", exc_info=True)
            result["error"] = f"PDF generation failed: {str(e)}"
            # Don't return early - still report what we have
            return result

        # Step 2: Send email ONLY if configured
        # Email is optional - PDF is always available for download via API
        if self.email_service.is_configured():
            effective_recipient = recipient_email or self.email_service.default_recipient

            if effective_recipient:
                logger.info(f"Sending email to {effective_recipient} for task {task_id}")

                pdf_path = self.storage_path / task_id / pdf_filename

                email_result = await self.email_service.send_report(
                    task_id=task_id,
                    company_name=company_name,
                    pdf_path=pdf_path,
                    recipient_email=effective_recipient,
                )

                result["email_sent"] = email_result.get("success", False)
                result["email_details"] = email_result

                if result["email_sent"]:
                    logger.info(f"Email sent successfully to {effective_recipient}")
                else:
                    logger.warning(f"Email delivery failed: {email_result.get('error')}")
            else:
                logger.info("No recipient configured - skipping email delivery")
                result["email_details"] = {"skipped": True, "reason": "No recipient configured"}
        else:
            logger.info("Email service not configured - PDF available for download only")
            result["email_details"] = {"skipped": True, "reason": "Email service not configured"}

        return result

    async def get_pdf_path(self, task_id: str, pdf_filename: str) -> Optional[Path]:
        """
        Get the full path to a generated PDF.

        Args:
            task_id: Task identifier
            pdf_filename: PDF filename

        Returns:
            Path to the PDF file, or None if not found
        """
        pdf_path = self.storage_path / task_id / pdf_filename

        if pdf_path.exists():
            return pdf_path

        logger.warning(f"PDF not found: {pdf_path}")
        return None
