import httpx


class ArkSeedreamProvider:
    def __init__(self, api_key: str, base_url: str, model: str, image_size: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.image_size = image_size

    async def generate_reference_image(self, image_data_url: str, label: str, name: str) -> str:
        payload = {
            "model": self.model,
            "size": self.image_size,
            "image": image_data_url,
            "prompt": (
                f"请基于参考图生成一张干净的单主体家具参考图，主体是{name}（{label}）。"
                "保持原家具风格、材质、颜色，去掉杂乱背景，居中展示，完整保留主体。"
            ),
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/images/generations",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return self._extract_image(data) or image_data_url

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _extract_image(self, data: dict) -> str | None:
        items = data.get("data") or data.get("images") or []
        if isinstance(items, list) and items:
            first = items[0]
            return first.get("url") or first.get("b64_json") or first.get("image")
        return data.get("url") or data.get("image") or data.get("b64_json")
