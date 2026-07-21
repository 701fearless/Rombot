import httpx

from app.services.vision_semantics.label_policy import normalize_label, to_grounding_prompt


class GroundingDinoProvider:
    def __init__(self, endpoint: str, api_key: str | None = None, min_confidence: float = 0.35, max_objects: int = 8) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.min_confidence = min_confidence
        self.max_objects = max_objects

    async def detect_with_labels(self, image_data_url: str, labels: list[str]) -> list[dict]:
        prompt = to_grounding_prompt(labels)
        if not prompt:
            return []
        payload = {
            "image": image_data_url,
            "labels": labels,
            "prompt": prompt,
            "box_threshold": self.min_confidence,
            "max_objects": self.max_objects,
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(f"{self.endpoint}/detect-boxes", headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        return self._parse_objects(data.get("objects", []))

    def _parse_objects(self, raw_objects: list[dict]) -> list[dict]:
        parsed: list[dict] = []
        for item in raw_objects:
            bbox = item.get("bbox") or item.get("box")
            if not bbox or len(bbox) != 4:
                continue
            confidence = float(item.get("confidence") or item.get("score") or 0)
            if confidence < self.min_confidence:
                continue
            parsed.append(
                {
                    "label": normalize_label(str(item.get("label") or item.get("class") or "")),
                    "confidence": confidence,
                    "bbox": [float(value) for value in bbox],
                }
            )
        parsed.sort(key=lambda item: item["confidence"], reverse=True)
        return parsed[: self.max_objects]

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
