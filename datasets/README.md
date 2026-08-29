# Calibration & vision datasets

## Product model (multi-tenant)

Each client (Business) owns their own vessels:

```text
Business (client)
  └── Product              e.g. "Sklenice 0.5 l", "Božkov 0.7"
        └── BottleProfile  geometry / ROI for that vessel type
              └── CalibrationVersion (v1, v2, …)
                    ├── calibration_points_json  (true_ml + metadata)
                    └── originals in MinIO
```

MinIO layout (one original per capture):

```text
calibration/{bottle_profile_id}/{version}/{filename}.jpg
```

API (tenant-scoped via membership):

```text
POST   /api/v1/calibration-versions
GET    /api/v1/calibration-versions?bottle_profile_id=
GET    /api/v1/calibration-versions/{id}
PATCH  /api/v1/calibration-versions/{id}     # edit labels / deactivate
DELETE /api/v1/calibration-versions/{id}     # delete version
POST   /api/v1/calibration-versions/{id}/originals
POST   /api/v1/calibration-versions/from-dataset   # lab ingest only
```

Edit = PATCH (or upload replacement original).  
Delete = DELETE that version for that client's profile.  
Major recalibration = new `CalibrationVersion` (old versions stay for history).

## Local lab folder (`datasets/`)

Only for development / first physical captures on this machine:

```text
datasets/
  raw/<dataset_id>/manifest.json + images
  annotations/<dataset_id>/<version>.json
```

Client production calibrations do **not** live here — they live in DB + MinIO
per Business → BottleProfile → CalibrationVersion.

## Glass 500 ml cylinder map

`glass_500ml_v1` uses `interpolation_method: cylindrical_linear`:

```text
volume_ml = level_normalized * 500
```

So every milliliter is deterministic once liquid height is normalized to the
0–1 fill range (0 empty → 1 at the 0,5 l mark). Physical 62.5 ml pour photos
are anchors / regression fixtures, not a requirement for intermediate ml.

Engine code: `backend/app/vision/calibration/engine.py`  
Evaluate API: `POST /api/v1/calibration-versions/{id}/evaluate-volume`

Raw JPEG binaries may stay local (gitignored). Manifest + annotations are
versioned in git when useful for the project lab set.
