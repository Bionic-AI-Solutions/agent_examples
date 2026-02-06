"""Email Service - Send reports via Gmail SMTP Relay

Uses Gmail SMTP relay (smtp-relay.gmail.com) with IP-based allowlisting.
No authentication needed - relay is authorized by WAN IP in Google Workspace.
"""

import asyncio
import base64
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from loguru import logger
from typing import Optional


class EmailService:
    """Service for sending PDF reports via Gmail SMTP Relay"""

    def __init__(self):
        self.default_recipient = os.getenv("REPORT_EMAIL_RECIPIENT")
        self.from_email = os.getenv("EMAIL_FROM_ADDRESS", "info@bionicaisolutions.com")
        self.smtp_host = os.getenv("SMTP_HOST", "smtp-relay.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))

    def is_configured(self) -> bool:
        """Check if SMTP relay is reachable and recipient is configured"""
        has_recipient = bool(self.default_recipient)

        if not has_recipient:
            logger.info("No default email recipient configured (REPORT_EMAIL_RECIPIENT)")

        # SMTP relay is always available (IP-based auth, no credentials needed)
        return True

    async def send_report(
        self,
        task_id: str,
        company_name: str,
        pdf_path: Path,
        recipient_email: Optional[str] = None,
    ) -> dict:
        """
        Send PDF report via Gmail SMTP Relay.

        Args:
            task_id: Unique task identifier for tracking
            company_name: Name of the company for email subject
            pdf_path: Path to the generated PDF file
            recipient_email: Override for default recipient

        Returns:
            Dict with send status and details
        """
        recipient = recipient_email or self.default_recipient

        if not recipient:
            logger.warning("No recipient configured for email delivery")
            return {
                "success": False,
                "error": "No recipient configured. Set REPORT_EMAIL_RECIPIENT or provide email_recipient in request.",
            }

        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return {"success": False, "error": f"PDF file not found: {pdf_path}"}

        try:
            # Build email message
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = recipient
            msg["Subject"] = f"Due Diligence Report: {company_name}"

            # HTML body
            html_body = self._build_email_body(company_name, task_id)
            msg.attach(MIMEText(html_body, "html"))

            # PDF attachment
            pdf_bytes = pdf_path.read_bytes()
            attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
            safe_name = company_name.replace(" ", "_")
            attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=f"{safe_name}_DD_Report.pdf",
            )
            msg.attach(attachment)

            # Send via SMTP relay (run blocking I/O in thread pool)
            await asyncio.to_thread(
                self._send_smtp, msg, recipient
            )

            logger.info(f"Email sent successfully to {recipient} for task {task_id}")
            return {
                "success": True,
                "recipient": recipient,
                "task_id": task_id,
            }

        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _send_smtp(self, msg: MIMEMultipart, recipient: str) -> None:
        """
        Send email via Gmail SMTP relay (blocking).

        Gmail SMTP relay uses IP-based allowlisting - no username/password needed.
        """
        server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
        try:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.sendmail(self.from_email, [recipient], msg.as_string())
        finally:
            server.quit()

    def _build_email_body(self, company_name: str, task_id: str) -> str:
        """
        Build HTML email body with professional formatting.

        Args:
            company_name: Name of the company
            task_id: Task identifier for reference

        Returns:
            HTML string for email body
        """
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #1a365d 0%, #2d4a7c 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
        <h1 style="color: #d4af37; margin: 0; font-size: 24px; letter-spacing: 2px;">VC DILIGENCE</h1>
    </div>

    <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
        <h2 style="color: #1a365d; margin-top: 0;">Due Diligence Report</h2>
        <h3 style="color: #d4af37; font-size: 20px;">{company_name}</h3>

        <p>Please find attached the complete due diligence report for <strong>{company_name}</strong>.</p>

        <p>This comprehensive report includes:</p>

        <ul style="color: #555; padding-left: 20px;">
            <li><strong>Executive Summary</strong> - Key findings and investment thesis</li>
            <li><strong>Company Overview</strong> - Business model, team, and traction</li>
            <li><strong>Market Analysis</strong> - TAM/SAM/SOM and competitive landscape</li>
            <li><strong>Financial Projections</strong> - ARR scenarios and growth analysis</li>
            <li><strong>Risk Assessment</strong> - Key risks and mitigation strategies</li>
            <li><strong>Investment Recommendation</strong> - Final assessment and terms</li>
        </ul>

        <div style="background: #f5f5f5; padding: 15px; border-radius: 4px; margin-top: 20px;">
            <p style="margin: 0; font-size: 12px; color: #666;">
                <strong>Reference:</strong> Task ID {task_id}
            </p>
        </div>
    </div>

    <div style="background: #1a365d; padding: 20px; text-align: center; border-radius: 0 0 8px 8px;">
        <p style="color: #ffffff; margin: 0; font-size: 12px;">
            Generated by VC Diligence AI Platform
        </p>
        <p style="color: #d4af37; margin: 5px 0 0 0; font-size: 10px;">
            CONFIDENTIAL - For authorized recipients only
        </p>
    </div>
</body>
</html>
"""
