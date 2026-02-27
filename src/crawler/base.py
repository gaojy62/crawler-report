"""
Base crawler class
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class CrawledItem:
    """Standard crawled item structure"""
    title: str
    content: str
    url: str
    source_name: str
    source_type: str  # rss, twitter, etc.
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    priority: int = 5
    raw_data: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "author": self.author,
            "priority": self.priority,
            "raw_data": self.raw_data
        }


class BaseCrawler(ABC):
    """Abstract base class for crawlers"""

    def __init__(self, sources: List[dict]):
        self.sources = sources

    @abstractmethod
    async def fetch(self) -> List[CrawledItem]:
        """Fetch items from configured sources"""
        pass

    def calculate_priority_score(self, priority: int) -> float:
        """Convert priority (1-10) to a score multiplier"""
        return priority / 10.0