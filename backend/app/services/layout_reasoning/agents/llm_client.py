"""Ark / mock LLM client for spatial multi-agent pipeline."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx


class SpatialLLMClient:
    """Thin chat-completions wrapper that always returns parsed JSON."""

    def __init__(
        self,
        *,
        provider: str = "mock",
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 90.0,
    ) -> None:
        self.provider = (provider or "mock").lower()
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")
        self.model = model or ""
        self.timeout = timeout

    @property
    def is_live(self) -> bool:
        return self.provider in {"ark", "deepseek", "openai"} and bool(self.api_key) and bool(self.base_url) and bool(self.model)

    async def complete_json(self, *, system: str, user: str) -> dict[str, Any]:
        if not self.is_live:
            raise RuntimeError("LLM client is not configured for live calls; use mock agents.")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        text = self._extract_text(data)
        return self._parse_json(text)

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        if "choices" in data and data["choices"]:
            message = data["choices"][0].get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append(str(item.get("text") or ""))
                    elif isinstance(item, str):
                        parts.append(item)
                return "\n".join(parts)
        if isinstance(data.get("output_text"), str):
            return data["output_text"]
        return json.dumps(data, ensure_ascii=False)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if not match:
                raise
            parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("LLM response JSON must be an object")
        return parsed
