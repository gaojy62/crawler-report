"""
Twitter crawler implementation using yt-dlp
"""

import asyncio
import json
import os
import re
from datetime import datetime
from typing import List, Optional

from .base import BaseCrawler, CrawledItem


class TwitterCrawler(BaseCrawler):
    """Twitter crawler using yt-dlp"""

    def __init__(self, sources: List[dict]):
        super().__init__(sources)
        self.cookies_path = os.getenv("TWITTER_COOKIES_PATH")

    async def fetch(self) -> List[CrawledItem]:
        """Fetch tweets from configured accounts"""
        all_items = []

        for source in self.sources:
            try:
                items = await self._fetch_account(source)
                all_items.extend(items)
            except Exception as e:
                print(f"Error fetching @{source['account']}: {e}")
                continue

        return all_items

    async def _fetch_account(self, source: dict) -> List[CrawledItem]:
        """Fetch tweets from a single Twitter account"""
        account = source["account"]
        limit = source.get("limit", 10)
        keywords = source.get("keywords", [])

        # Build yt-dlp command
        url = f"https://x.com/{account}"

        # yt-dlp command to extract tweet info as JSON
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--extractor", "twitter",
            "--extractor-descriptions",
            "--dump-json",
            "--playlist-end", str(limit),
            "--no-warnings",
            "--quiet",
        ]

        if self.cookies_path:
            cmd.extend(["--cookies", self.cookies_path])

        cmd.append(url)

        try:
            # Run yt-dlp
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                # Check if it's a login-required error (common for Twitter)
                if "sign in" in error_msg.lower() or "login" in error_msg.lower():
                    print(f"Twitter requires login for @{account}, skipping...")
                    return []
                raise Exception(f"yt-dlp error: {error_msg}")

            items = []
            lines = stdout.decode().strip().split("\n")

            for line in lines:
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)
                    item = self._parse_tweet(data, source)

                    # Apply keyword filter if configured
                    if keywords and item:
                        text = f"{item.title} {item.content}".lower()
                        if not any(kw.lower() in text for kw in keywords):
                            continue

                    if item:
                        items.append(item)
                except json.JSONDecodeError:
                    continue

            return items[:limit]

        except FileNotFoundError:
            print("yt-dlp not found. Please install: pip install yt-dlp")
            return []

    def _parse_tweet(self, data: dict, source: dict) -> Optional[CrawledItem]:
        """Parse yt-dlp tweet data into CrawledItem"""
        # Extract tweet text
        text = data.get("description", "") or data.get("title", "")
        if not text:
            return None

        # Clean up title (first line or first 100 chars)
        title = text.split("\n")[0][:100]
        if len(text.split("\n")[0]) > 100:
            title += "..."

        # Get tweet URL
        tweet_id = data.get("id", "")
        username = source["account"]
        url = f"https://x.com/{username}/status/{tweet_id}" if tweet_id else data.get("webpage_url", "")

        # Parse timestamp
        published_at = None
        if "timestamp" in data:
            published_at = datetime.fromtimestamp(data["timestamp"])
        elif "upload_date" in data:
            try:
                published_at = datetime.strptime(data["upload_date"], "%Y%m%d")
            except ValueError:
                pass

        return CrawledItem(
            title=title.strip(),
            content=text.strip(),
            url=url,
            source_name=f"@{username}",
            source_type="twitter",
            published_at=published_at,
            author=username,
            priority=source.get("priority", 5),
            raw_data={
                "tweet_id": tweet_id,
                "likes": data.get("like_count", 0),
                "retweets": data.get("repost_count", 0),
                "replies": data.get("comment_count", 0)
            }
        )