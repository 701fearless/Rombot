import httpx


class SamBoxProvider:
    def __init__(self, endpoint: str, api_key: str | None = None) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key

    async def segment_boxes(self, image_data_url: str, objects: list[dict]) -> list[dict]:
        if not objects:
            return []
        payload = {
            "image": image_data_url,
            "objects": [{"label": item["label"], "bbox": item["bbox"]} for item in objects],
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{self.endpoint}/segment-boxes", headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        return data.get("objects", [])

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
