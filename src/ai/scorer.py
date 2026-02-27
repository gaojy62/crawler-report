"""
AI scoring using DeepSeek API
"""

import asyncio
import json
import os
from typing import List, Optional

from openai import AsyncOpenAI

from crawler.base import CrawledItem


SCORING_SYSTEM_PROMPT = """你是一个财经新闻评估专家。你的任务是对新闻内容进行评估和打分。

评分维度：
1. relevance (权重 0.3): 与财经、金融、投资的相关程度
2. value (权重 0.25): 信息密度和内容价值
3. timeliness (权重 0.25): 新闻时效性和时间敏感度
4. impact (权重 0.2): 对市场的潜在影响程度

每个维度打分 1-10 分。

你必须只返回 JSON 格式，不要有任何其他文字：
{
  "scores": {"relevance": X, "value": X, "timeliness": X, "impact": X},
  "total_score": X,
  "category": "crypto|stock|macro|other",
  "background": "简短背景说明（1-2句话）",
  "impact_summary": "影响说明（1-2句话）",
  "summary": "一句话摘要"
}
"""

SCORING_USER_TEMPLATE = """请评估以下新闻内容：

标题：{title}
来源：{source}
内容摘要：{content}

只返回 JSON 格式的评分结果。"""


class AIScorer:
    """AI-based content scorer using DeepSeek API"""

    def __init__(self, config: dict):
        self.config = config
        self.dimensions = config.get("scoring", {}).get("dimensions", [
            {"name": "relevance", "weight": 0.3},
            {"name": "value", "weight": 0.25},
            {"name": "timeliness", "weight": 0.25},
            {"name": "impact", "weight": 0.2}
        ])

        # Initialize OpenAI client (DeepSeek compatible)
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is required")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        self.model = config.get("model", "deepseek-chat")
        self.max_tokens = config.get("max_tokens", 4000)

    async def score_item(self, item: CrawledItem) -> Optional[dict]:
        """Score a single item"""
        try:
            # Truncate content if too long
            content = item.content[:1000] if len(item.content) > 1000 else item.content

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                    {"role": "user", "content": SCORING_USER_TEMPLATE.format(
                        title=item.title,
                        source=item.source_name,
                        content=content
                    )}
                ],
                max_tokens=500,
                temperature=0.3
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON result
            # Handle potential markdown code blocks
            if result_text.startswith("```"):
                lines = result_text.split("\n")
                result_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            result = json.loads(result_text)

            # Calculate weighted total score
            scores = result.get("scores", {})
            total = sum(
                scores.get(d["name"], 0) * d["weight"]
                for d in self.dimensions
            )
            result["total_score"] = round(total, 2)

            return result

        except Exception as e:
            print(f"Error scoring item '{item.title[:50]}...': {e}")
            return None

    async def batch_score(
        self,
        items: List[CrawledItem],
        min_score: float = 6.0,
        batch_size: int = 5
    ) -> List[dict]:
        """Score multiple items with batching"""
        scored_items = []

        # Process in batches to avoid rate limits
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            tasks = [self.score_item(item) for item in batch]
            results = await asyncio.gather(*tasks)

            for item, result in zip(batch, results):
                if result and result.get("total_score", 0) >= min_score:
                    scored_items.append({
                        **item.to_dict(),
                        "score": result["total_score"],
                        "category": result.get("category", "other"),
                        "background": result.get("background", ""),
                        "impact": result.get("impact_summary", ""),
                        "summary": result.get("summary", ""),
                        "scores": result.get("scores", {})
                    })

        return scored_items