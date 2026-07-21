# Grounded-SAM-2 Cloud Service Contract

The main MVP backend does not run Grounded-SAM-2 locally. Run Grounded-SAM-2 on a GPU machine and expose this HTTP endpoint.

## Endpoint

```http
POST /detect-and-segment
```

## Request

```json
{
  "image": "data:image/jpeg;base64,...",
  "prompt": "sofa . bed . chair . coffee table . chandelier . rug .",
  "box_threshold": 0.35,
  "text_threshold": 0.35,
  "max_objects": 8
}
```

## Response

```json
{
  "objects": [
    {
      "label": "sofa",
      "confidence": 0.91,
      "bbox": [118, 420, 690, 850],
      "mask": "data:image/png;base64,..."
    }
  ]
}
```

Rules:

- `bbox` may be pixel coordinates `[x1, y1, x2, y2]` or normalized coordinates `[0, 1]`.
- `label` should be English. The MVP backend maps it to Chinese tags.
- `mask` should be a PNG Data URI. If omitted, the MVP backend falls back to a rectangular bbox mask.
- Keep only objects that match the supplied furniture prompt.

## Main Backend Env

```powershell
$env:DETECTION_PROVIDER="grounded_sam2"
$env:GROUNDED_SAM2_ENDPOINT="http://your-gpu-host:8001"
$env:GROUNDED_SAM2_API_KEY="optional"
```
