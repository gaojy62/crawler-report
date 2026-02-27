"""
Main entry point for crawler report system
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path

import yaml

from crawler.rss import RSSCrawler
from crawler.twitter import TwitterCrawler
from storage.cache import Cache
from ai.scorer import AIScorer
from report.generator import ReportGenerator
from publisher.client import WorkerClient


def load_config():
    """Load configuration from YAML file"""
    config_path = Path(__file__).parent.parent / "config" / "sources.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def main():
    """Main execution flow"""
    print(f"[{datetime.now().isoformat()}] Starting crawler report...")

    # Load config
    config = load_config()
    report_config = config.get("report", {})
    sources_config = config.get("sources", {})

    # Initialize components
    cache = Cache()
    scorer = AIScorer(config.get("ai", {}))
    generator = ReportGenerator()
    client = WorkerClient()

    items = []

    # 1. Crawl RSS feeds
    rss_sources = sources_config.get("rss", [])
    if rss_sources:
        print("[1/7] Crawling RSS feeds...")
        rss_crawler = RSSCrawler(rss_sources)
        rss_items = await rss_crawler.fetch()
        items.extend(rss_items)
        print(f"    Collected {len(rss_items)} items from RSS")

    # 2. Crawl Twitter
    twitter_sources = sources_config.get("twitter", [])
    if twitter_sources:
        print("[2/7] Crawling Twitter...")
        twitter_crawler = TwitterCrawler(twitter_sources)
        twitter_items = await twitter_crawler.fetch()
        items.extend(twitter_items)
        print(f"    Collected {len(twitter_items)} items from Twitter")

    if not items:
        print("No items collected, exiting.")
        return

    # 3. Deduplicate
    print("[3/7] Deduplicating...")
    items = cache.deduplicate(items)
    print(f"    {len(items)} unique items after dedup")

    if not items:
        print("No items to process, exiting.")
        return

    # 4. AI scoring
    print("[4/7] AI scoring...")
    scored_items = await scorer.batch_score(items, report_config.get("min_score", 6))
    print(f"    {len(scored_items)} items passed scoring threshold")

    if not scored_items:
        print("No items passed scoring, exiting.")
        return

    # 5. Select top N
    top_n = report_config.get("top_n", 5)
    top_items = sorted(scored_items, key=lambda x: x["score"], reverse=True)[:top_n]
    print(f"[5/7] Selected top {len(top_items)} items")

    # 6. Generate report
    print("[6/7] Generating report...")
    all_source_names = (
        [s["name"] for s in rss_sources] +
        [f"@{s['account']}" for s in twitter_sources]
    )
    report = generator.generate(
        items=top_items,
        report_name=report_config.get("name", "财经要闻日报"),
        sources=all_source_names
    )

    # 7. Publish
    print("[7/7] Publishing...")
    today = datetime.now().strftime("%Y-%m-%d")
    result = await client.publish(
        title=f"{report_config.get('name', '财经要闻日报')} - {today}",
        date=today,
        content=report,
        push=True
    )

    if result.get("success"):
        print(f"    Report published: {result.get('url')}")
        if result.get("push"):
            print(f"    Push notifications: sent={result['push'].get('sent')}, failed={result['push'].get('failed')}")
    else:
        print(f"    Failed to publish: {result.get('error')}")

    # Update cache
    cache.save_history(top_items)

    print(f"[{datetime.now().isoformat()}] Done!")


if __name__ == "__main__":
    asyncio.run(main())