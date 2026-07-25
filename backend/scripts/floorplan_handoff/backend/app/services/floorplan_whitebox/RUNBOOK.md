# Floorplan Whitebox Runbook

## Generate the sample GLB

Run from the `backend` folder:

```powershell
python .\scripts\test_floorplan_whitebox.py
```

Default input:

```text
backend/sample_data/floorplans/sample_whitebox_scene.json
```

Default output:

```text
backend/outputs/floorplans/sample_floorplan_whitebox/whitebox.glb
```

The sample scene validates the first modeling milestone:

- wall height is forced to 3m
- wall thickness is forced to 0.1m
- each wall is exported as a separate GLB node/mesh
- door/window wall areas are split out so fixtures pass through both wall faces
- doors are separate panel, through-wall frame, casing and handle meshes
- windows are separate glass, through-wall frame, mullion and sill meshes

## Use a custom normalized scene

```powershell
python .\scripts\test_floorplan_whitebox.py .\path\to\normalized_scene.json --output .\outputs\floorplans\custom\whitebox.glb
```

## Run AI reconstruction

Make sure `backend/.env` contains:

```text
ARK_API_KEY=...
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_VISION_MODEL=...
```

Start the backend:

```powershell
python -m uvicorn app.main:app --reload
```

Call the AI floorplan endpoint with the default sample image in `户型图/`:

```powershell
python .\scripts\test_floorplan_ai_reconstruct.py
```

The endpoint writes:

```text
backend/outputs/floorplans/<scene_id>/original.png
backend/outputs/floorplans/<scene_id>/ai_raw.json
backend/outputs/floorplans/<scene_id>/normalized_scene.json
backend/outputs/floorplans/<scene_id>/whitebox.glb
```
