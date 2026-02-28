"""
Report generator using Jinja2
"""

from datetime import datetime
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader


class ReportGenerator:
    """Generate Markdown reports from scored items"""

    def __init__(self):
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def generate(
        self,
        items: List[dict],
        report_name: str = "财经要闻日报",
        sources: List[str] = None,
        ai_stats: dict = None
    ) -> str:
        """Generate a Markdown report"""
        template = self.env.get_template("report.md.j2")

        now = datetime.now()

        return template.render(
            report_name=report_name,
            generated_at=now.strftime("%Y-%m-%d %H:%M"),
            generated_date=now.strftime("%Y-%m-%d"),
            items=items,
            sources=sources or [],
            item_count=len(items),
            ai_stats=ai_stats
        )