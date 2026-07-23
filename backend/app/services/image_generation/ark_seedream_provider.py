import json

import httpx


class ArkSeedreamProvider:
    def __init__(self, api_key: str, base_url: str, model: str, image_size: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.image_size = image_size

    async def generate_reference_image(
        self,
        image_data_url: str,
        label: str,
        name: str,
        visual_features: dict | None = None,
        generation_hints: dict | None = None,
    ) -> str:
        prompt = f"""
Create one clean 45-degree front-left product reference image of the same {name} ({label}).
Keep the visible identity, proportions, materials, colors and texture motifs.
Use the supplied feature evidence: {json.dumps(visual_features or {}, ensure_ascii=False)}.
Apply these conservative cleanup/completion rules: {json.dumps(generation_hints or {}, ensure_ascii=False)}.

Regularize temporary household disorder: align loose cushions/pillows, smooth and center
blankets or throws, remove clothes/dishes/cables/small clutter, align doors/drawers/handles,
flatten curled rug edges, and arrange curtains into orderly natural folds when relevant.
Complete occluded or unseen parts with ordinary category structure, bilateral/axial
symmetry, repeated modules and continuous material. Continue visible repeated patterns
without blank gaps. Do not invent random ornaments, extra parts, bizarre shapes or
over-designed furniture. Show one complete isolated object on a plain light background.
Exclude people, hands, UI, captions, watermarks, room background and unrelated props.
"""
        payload = {
            "model": self.model,
            "size": self.image_size,
            "image": [image_data_url],
            "prompt": prompt,
            "sequential_image_generation": "disabled",
            "stream": False,
            "response_format": "b64_json",
            "watermark": False,
        }
        async with httpx.AsyncClient(timeout=300) as client:
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
        first = items[0] if isinstance(items, list) and items else data
        if not isinstance(first, dict):
            return None
        if first.get("url"):
            return str(first["url"])
        b64_json = first.get("b64_json") or first.get("image")
        if not b64_json:
            return None
        value = str(b64_json)
        return value if value.startswith("data:image/") else f"data:image/png;base64,{value}"
