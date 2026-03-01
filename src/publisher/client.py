"""
Worker API client for publishing reports
"""

import os
from typing import Optional

import httpx


class WorkerClient:
    """Client for openclaw-push Worker API"""

    def __init__(self):
        self.worker_url = os.getenv("WORKER_URL")
        self.push_token = os.getenv("PUSH_TOKEN")

        if not self.worker_url:
            raise ValueError("WORKER_URL environment variable is required")
        if not self.push_token:
            raise ValueError("PUSH_TOKEN environment variable is required")

    async def publish(
        self,
        title: str,
        date: str,
        content: str,
        push: bool = True
    ) -> dict:
        """Publish a report to the Worker"""
        payload = {
            "title": title,
            "date": date,
            "content": content,
            "push": push
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.worker_url}/publish",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.push_token}"
                    }
                )

                result = response.json()

                if response.status_code == 200:
                    return result
                else:
                    return {
                        "success": False,
                        "error": result.get("error", f"HTTP {response.status_code}"),
                        "details": result.get("details")
                    }

            except httpx.RequestError as e:
                return {
                    "success": False,
                    "error": f"Request failed: {str(e)}"
                }

    async def health_check(self) -> dict:
        """Check Worker health status"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.worker_url}/health")
                return response.json()
            except Exception as e:
                return {"status": "error", "message": str(e)}