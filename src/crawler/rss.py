"""
RSS crawler implementation
"""

import asyncio
from datetime import datetime
from typing import List, Optional

import feedparser
from dateutil import parser as date_parser

from .base import BaseCrawler, CrawledItem


class RSSCrawler(BaseCrawler):
    """RSS feed crawler"""

    def __init__(self, sources: List[dict]):
        super().__init__(sources)

    async def fetch(self) -> List[CrawledItem]:
        """Fetch items from all configured RSS feeds"""
        all_items = []

        # Fetch all feeds concurrently
        tasks = [self._fetch_feed(source) for source in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for source, result in zip(self.sources, results):
            if isinstance(result, Exception):
                print(f"Error fetching {source['name']}: {result}")
                continue
            all_items.extend(result)

        return all_items

    async def _fetch_feed(self, source: dict) -> List[CrawledItem]:
        """Fetch items from a single RSS feed"""
        items = []
        limit = source.get("limit", 20)

        try:
            # feedparser is synchronous, run in executor
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(
                None,
                feedparser.parse,
                source["url"]
            )

            if feed.bozo and not feed.entries:
                raise Exception(f"Feed parse error: {feed.bozo_exception}")

            for entry in feed.entries[:limit]:
                item = self._parse_entry(entry, source)
                if item:
                    items.append(item)

        except Exception as e:
            raise e

        return items

    def _parse_entry(self, entry: dict, source: dict) -> Optional[CrawledItem]:
        """Parse a feed entry into CrawledItem"""
        title = entry.get("title", "")
        if not title:
            return None

        # Get content
        content = ""
        if "content" in entry:
            content = entry.content[0].get("value", "")
        elif "summary" in entry:
            content = entry.summary
        elif "description" in entry:
            content = entry.description

        # Parse publish date
        published_at = None
        if "published_parsed" in entry and entry.published_parsed:
            published_at = datetime(*entry.published_parsed[:6])
        elif "published" in entry:
            try:
                published_at = date_parser.parse(entry.published)
            except:
                pass
        elif "updated" in entry:
            try:
                published_at = date_parser.parse(entry.updated)
            except:
                pass

        # Get URL
        url = entry.get("link", "")
        if not url and "links" in entry:
            url = entry.links[0].get("href", "")

        return CrawledItem(
            title=title.strip(),
            content=content.strip(),
            url=url,
            source_name=source["name"],
            source_type="rss",
            published_at=published_at,
            author=entry.get("author"),
            priority=source.get("priority", 5),
            raw_data={
                "tags": [tag.term for tag in entry.get("tags", [])],
                "link": url
            }
        )