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

Raw JPEG binaries may stay local (gitignored). Manifest + annotations are
versioned in git when useful for the project lab set.
