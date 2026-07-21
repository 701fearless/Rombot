import json
import re

import httpx

from app.services.vision_semantics.label_policy import DOUBAO_FURNITURE_PROMPT, filter_semantic_labels


class DoubaoVisionProvider:
    def __init__(self, endpoint: str, api_key: str, model: str) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def classify_frame(self, image_data_url: str) -> list[dict]:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": DOUBAO_FURNITURE_PROMPT},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                }
            ],
            "temperature": 0,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(self.endpoint, headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        text = self._extract_text(data)
        parsed = self._parse_json(text)
        return filter_semantic_labels(parsed.get("objects", []), max_items=6)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _extract_text(self, data: dict) -> str:
        if "choices" in data:
            message = data["choices"][0].get("message", {})
            content = message.get("content", "")
            if isinstance(content, list):
                return "".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
            return str(content)
        if "content" in data:
            return str(data["content"])
        if "text" in data:
            return str(data["text"])
        return json.dumps(data, ensure_ascii=False)

    def _parse_json(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.S)
            if not match:
                return {"objects": []}
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {"objects": []}
