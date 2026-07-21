# Space Energy MVP Backend

FastAPI backend for the hackathon MVP.

## Run

```powershell
cd backend
E:\Anaconda3\envs\ml2025\python.exe -m pip install -r requirements.txt
E:\Anaconda3\envs\ml2025\python.exe -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/health
```

## APIs

### Preprocess a video before users pause

```http
POST /api/video/preprocess
```

```json
{
  "videoId": "living_room_001",
  "videoUrl": "/sample_data/videos/living_room_001.mp4",
  "sampleIntervalSec": 1.0,
  "mode": "mock",
  "maxFrames": 6
}
```

Modes:

```text
mock: no model call; generates demo frames/tags for frontend integration
grounded_sam2: calls the configured Grounded-SAM-2 Lite service
doubao_grounding_sam: Doubao labels -> Grounding DINO bbox -> SAM mask -> analysis.json
manual: keeps the same output shape for manually corrected analysis files
```

The generated file is:

```text
outputs/videos/<videoId>/analysis.json
```

Inspect analysis:

```http
GET /api/video/analysis/{videoId}
GET /api/video/analysis/{videoId}/nearest?time=12.4
```

### Detect paused furniture tags

```http
POST /api/feed/detect
```

```json
{
  "videoId": "living_room_001",
  "time": 12.4,
  "frameImage": "data:image/jpeg;base64,..."
}
```

If `outputs/videos/<videoId>/analysis.json` exists, this endpoint reads the nearest preprocessed frame and returns immediately. If there is no preprocessed analysis, it falls back to the realtime mock/Grounded-SAM-2 provider.

### Select, segment, and generate a furniture model

```http
POST /api/feed/select-object
```

```json
{
  "frameId": "frame_living_room_001_12_40",
  "objectId": "obj_sofa_001",
  "frameImage": "data:image/jpeg;base64,..."
}
```

This runs:

```text
selected furniture tag -> segmentation crop/mask -> 3D model provider
```

### One-call pipeline test

```http
POST /api/feed/run-pipeline
```

```json
{
  "videoId": "living_room_001",
  "time": 12.4,
  "frameImage": "data:image/jpeg;base64,...",
  "objectId": "obj_sofa_001"
}
```

`objectId` is optional. If omitted, the backend selects the first detected object.

### Mock room scan

```http
POST /api/room/scan
```

```json
{
  "scanId": "demo_living_room"
}
```

## Provider switches

Defaults are mock providers.

```powershell
$env:DETECTION_PROVIDER="mock"
$env:SEGMENTATION_PROVIDER="mock"
$env:MODEL3D_PROVIDER="mock"
```

Grounded-SAM-2 detection + segmentation endpoint:

```powershell
$env:DETECTION_PROVIDER="grounded_sam2"
$env:GROUNDED_SAM2_ENDPOINT="https://your-grounded-sam2-service.example.com"
$env:GROUNDED_SAM2_API_KEY="your_key"
```

Optional tuning:

```powershell
$env:GROUNDED_SAM2_MIN_CONFIDENCE="0.35"
$env:GROUNDED_SAM2_MAX_OBJECTS="8"
$env:GROUNDED_SAM2_PROMPT="sofa . bed . chair . coffee table . chandelier . rug . curtain . plant ."
```

The backend calls:

```http
POST {GROUNDED_SAM2_ENDPOINT}/detect-and-segment
```

Request:

```json
{
  "image": "data:image/jpeg;base64,...",
  "prompt": "sofa . bed . chair . coffee table . chandelier . rug .",
  "box_threshold": 0.35,
  "text_threshold": 0.35,
  "max_objects": 8
}
```

Expected response:

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

`bbox` can be pixel coordinates `[x1, y1, x2, y2]` or normalized coordinates `[0.1, 0.2, 0.5, 0.8]`. The backend maps English labels to Chinese tags and saves `cropUrl` / `maskUrl` under `outputs/<frameId>/`.

Doubao + Grounding DINO + SAM offline preprocessing:

```powershell
$env:DOUBAO_ENDPOINT="https://your-doubao-vision-endpoint"
$env:DOUBAO_API_KEY="your_key"
$env:DOUBAO_MODEL="your_vision_model"
$env:GROUNDING_DINO_ENDPOINT="http://your-4090-host:8001"
$env:GROUNDING_DINO_API_KEY="optional"
$env:SAM_ENDPOINT="http://your-4090-host:8002"
$env:SAM_API_KEY="optional"
```

`SAM_ENDPOINT` is optional. If it is missing or fails, preprocessing falls back to a rectangular bbox mask so the video analysis can still be generated.

Preprocess one video:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/video/preprocess" `
  -ContentType "application/json" `
  -Body (@{
    videoId = "dining_room_001"
    videoUrl = "/sample_data/videos/dining_room_001.mp4"
    sampleIntervalSec = 1.0
    mode = "doubao_grounding_sam"
    maxFrames = 15
  } | ConvertTo-Json)
```

This mode runs:

```text
extract frames -> Doubao furniture labels -> Grounding DINO short prompt boxes -> SAM masks -> analysis.json
```

SAM 3 compatible segmentation-only endpoint:

```powershell
$env:SEGMENTATION_PROVIDER="sam3"
$env:SAM3_ENDPOINT="https://your-sam3-service.example.com"
$env:SAM3_API_KEY="your_key"
```

Meshy Image-to-3D:

```powershell
$env:MODEL3D_PROVIDER="meshy"
$env:MESHY_API_KEY="your_key"
```

Pixal3D compatible Image-to-3D endpoint:

```powershell
$env:MODEL3D_PROVIDER="pixal3d"
$env:PIXAL3D_ENDPOINT="https://your-pixal3d-service.example.com"
$env:PIXAL3D_API_KEY="your_key"
```

The real API adapters are isolated behind providers. When a key or endpoint is missing, the app falls back to mock providers so the H5 flow remains testable.

## Test with a local paused-frame image

```powershell
cd F:\DREAME\Qiuliying\lucky\backend
E:\Anaconda3\envs\ml2025\python.exe .\scripts\test_image_flow.py "F:\path\to\your\room.jpg"
```

Use Meshy for the selected segmented crop:

```powershell
$env:MODEL3D_PROVIDER="meshy"
$env:MESHY_API_KEY="your_key"
E:\Anaconda3\envs\ml2025\python.exe .\scripts\test_image_flow.py "F:\path\to\your\room.jpg" --object-id obj_sofa_001
```

## Test offline video preprocessing with mock data

```powershell
cd F:\DREAME\Qiuliying\lucky\backend
E:\Anaconda3\envs\ml2025\python.exe .\scripts\test_video_preprocess_flow.py
```

This creates:

```text
outputs/videos/living_room_demo/analysis.json
```

Then it verifies:

```text
preprocess -> /api/feed/detect nearest-frame lookup -> /api/feed/select-object
```
