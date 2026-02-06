"""PDF Report Service - Combines all artifacts into a single PDF report

Uses WeasyPrint to convert HTML content with embedded images to PDF.
"""

import base64
from pathlib import Path
from datetime import datetime
from loguru import logger
from typing import Optional


class PDFService:
    """Service for generating combined PDF reports from due diligence artifacts"""

    def __init__(self, storage_path: str = "/app/artifacts"):
        self.storage_path = Path(storage_path)

    async def generate_combined_report(
        self,
        task_id: str,
        company_name: str,
        artifacts: dict,
    ) -> str:
        """
        Generate a combined PDF report from all artifacts.

        Args:
            task_id: Unique task identifier
            company_name: Name of the analyzed company
            artifacts: Dict with artifact filenames (chart, report, infographic)

        Returns:
            Filename of the generated PDF
        """
        try:
            from weasyprint import HTML, CSS

            task_dir = self.storage_path / task_id
            generated_date = datetime.now().strftime("%B %d, %Y")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Build the combined HTML document
            combined_html = self._build_combined_html(
                task_dir=task_dir,
                company_name=company_name,
                generated_date=generated_date,
                artifacts=artifacts,
            )

            # Convert to PDF
            pdf_filename = f"{company_name.replace(' ', '_')}_DD_Report_{timestamp}.pdf"
            pdf_path = task_dir / pdf_filename

            html_doc = HTML(string=combined_html)
            css = CSS(string=self._get_pdf_styles())
            html_doc.write_pdf(pdf_path, stylesheets=[css])

            logger.info(f"PDF report generated: {pdf_path}")
            return pdf_filename

        except ImportError as e:
            logger.error(f"WeasyPrint not installed: {e}")
            raise RuntimeError("PDF generation requires WeasyPrint. Install with: pip install weasyprint")
        except Exception as e:
            logger.error(f"Error generating PDF: {e}", exc_info=True)
            raise

    def _build_combined_html(
        self,
        task_dir: Path,
        company_name: str,
        generated_date: str,
        artifacts: dict,
    ) -> str:
        """Build combined HTML document with all sections"""

        # Cover page
        cover_html = self._create_cover_page_html(company_name, generated_date)

        # Read and process HTML report
        report_html = ""
        if artifacts.get("report"):
            report_path = task_dir / artifacts["report"]
            if report_path.exists():
                report_content = report_path.read_text(encoding="utf-8")
                # Extract body content if full HTML document
                report_html = self._extract_body_content(report_content)

        # Embed chart image
        chart_section = ""
        if artifacts.get("chart"):
            chart_path = task_dir / artifacts["chart"]
            if chart_path.exists():
                chart_base64 = self._embed_image_as_base64(chart_path)
                chart_section = f"""
                <div class="page-break"></div>
                <div class="chart-section">
                    <h2>Financial Projections</h2>
                    <img src="{chart_base64}" alt="Revenue Projection Chart" class="full-width-image"/>
                </div>
                """

        # Embed infographic
        infographic_section = ""
        if artifacts.get("infographic"):
            infographic_path = task_dir / artifacts["infographic"]
            if infographic_path.exists():
                infographic_base64 = self._embed_image_as_base64(infographic_path)
                infographic_section = f"""
                <div class="page-break"></div>
                <div class="infographic-section">
                    <h2>Investment Summary</h2>
                    <img src="{infographic_base64}" alt="Investment Infographic" class="full-width-image"/>
                </div>
                """

        # Combine all sections
        combined_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Due Diligence Report - {company_name}</title>
        </head>
        <body>
            {cover_html}
            <div class="page-break"></div>
            <div class="report-content">
                {report_html}
            </div>
            {chart_section}
            {infographic_section}
        </body>
        </html>
        """

        return combined_html

    def _create_cover_page_html(self, company_name: str, generated_date: str) -> str:
        """Generate HTML for PDF cover page with branding"""
        return f"""
        <div class="cover-page">
            <div class="cover-content">
                <div class="cover-header">
                    <div class="logo-placeholder">VC DILIGENCE</div>
                </div>
                <div class="cover-title">
                    <h1>Investment Due Diligence Report</h1>
                    <h2 class="company-name">{company_name}</h2>
                </div>
                <div class="cover-footer">
                    <p class="date">Generated: {generated_date}</p>
                    <p class="confidential">CONFIDENTIAL</p>
                </div>
            </div>
        </div>
        """

    def _embed_image_as_base64(self, filepath: Path) -> str:
        """Convert image to base64 data URI for HTML embedding"""
        try:
            image_bytes = filepath.read_bytes()
            base64_data = base64.b64encode(image_bytes).decode("utf-8")

            # Determine MIME type
            suffix = filepath.suffix.lower()
            mime_types = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            mime_type = mime_types.get(suffix, "image/png")

            return f"data:{mime_type};base64,{base64_data}"
        except Exception as e:
            logger.error(f"Error embedding image {filepath}: {e}")
            return ""

    def _extract_body_content(self, html_content: str) -> str:
        """Extract body content from full HTML document"""
        # Simple extraction - look for body tags
        lower_content = html_content.lower()
        body_start = lower_content.find("<body")
        body_end = lower_content.find("</body>")

        if body_start != -1 and body_end != -1:
            # Find the end of the opening body tag
            tag_end = html_content.find(">", body_start)
            if tag_end != -1:
                return html_content[tag_end + 1:body_end]

        # If no body tags, return as-is (might be a fragment)
        return html_content

    def _get_pdf_styles(self) -> str:
        """Get CSS styles for PDF generation"""
        return """
        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }

        .page-break {
            page-break-after: always;
        }

        /* Cover page styles */
        .cover-page {
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            background: linear-gradient(135deg, #1a365d 0%, #2d4a7c 100%);
            color: white;
            margin: -2cm;
            padding: 2cm;
        }

        .cover-content {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 100%;
            width: 100%;
        }

        .cover-header {
            padding-top: 3cm;
        }

        .logo-placeholder {
            font-size: 24pt;
            font-weight: bold;
            letter-spacing: 0.3em;
            color: #d4af37;
        }

        .cover-title {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .cover-title h1 {
            font-size: 28pt;
            font-weight: 300;
            margin-bottom: 1cm;
            color: white;
        }

        .cover-title .company-name {
            font-size: 36pt;
            font-weight: bold;
            color: #d4af37;
        }

        .cover-footer {
            padding-bottom: 2cm;
        }

        .cover-footer .date {
            font-size: 12pt;
            margin-bottom: 0.5cm;
        }

        .cover-footer .confidential {
            font-size: 10pt;
            letter-spacing: 0.2em;
            color: #d4af37;
        }

        /* Report content styles */
        .report-content {
            padding-top: 1cm;
        }

        .report-content h1 {
            color: #1a365d;
            font-size: 20pt;
            border-bottom: 2px solid #d4af37;
            padding-bottom: 0.3cm;
            margin-bottom: 1cm;
        }

        .report-content h2 {
            color: #1a365d;
            font-size: 16pt;
            margin-top: 1cm;
            margin-bottom: 0.5cm;
        }

        .report-content h3 {
            color: #2d4a7c;
            font-size: 13pt;
            margin-top: 0.8cm;
        }

        .report-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 0.5cm 0;
        }

        .report-content th,
        .report-content td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }

        .report-content th {
            background-color: #1a365d;
            color: white;
        }

        .report-content tr:nth-child(even) {
            background-color: #f9f9f9;
        }

        /* Chart and infographic sections */
        .chart-section,
        .infographic-section {
            text-align: center;
            padding: 1cm 0;
        }

        .chart-section h2,
        .infographic-section h2 {
            color: #1a365d;
            font-size: 18pt;
            margin-bottom: 1cm;
        }

        .full-width-image {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        """
