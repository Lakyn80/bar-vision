# BAR VISION — MASTER EXECUTION MAP

**Status:** binding technical and implementation specification  
**Project:** Bar Vision  
**Primary use case:** automated measurement of remaining alcohol in bottles during shift handover  
**Primary client:** PWA in a mobile browser  
**Backend:** Python + FastAPI  
**Vision:** OpenCV + deterministic calculation, ML only where proven necessary  
**Development:** Docker-first  
**Local project root:**  
`C:\Users\lukas\Desktop\PYTHON_PROJECTS_DESKTOP\PYTHON_PROJECTS\bar-vision`

---

# 1. PURPOSE OF THIS DOCUMENT

This file is the main technical authority for the project.

Every future AI, developer, or automation agent must:

1. use this document as the primary source of truth,
2. not change the architecture without an explicit instruction,
3. not add technologies just because they are modern,
4. always respect the Docker-first approach,
5. proceed phase by phase,
6. verify which phase a requested change belongs to before implementation,
7. not skip acceptance criteria of previous phases,
8. preserve frontend and backend modularity,
9. never estimate alcohol volume with an LLM,
10. always prefer measurable and testable algorithms.

---

# 2. MAIN PRODUCT GOAL

The application must allow a shift manager in a bar, restaurant, pub, hotel, or similar hospitality venue to:

1. sign in,
2. select a venue,
3. open a shift handover,
4. display the list of tracked bottles,
5. open the camera for each bottle,
6. align the physical bottle with a calibrated outline,
7. let the system verify:
   - position,
   - scale,
   - rotation,
   - perspective,
   - sharpness,
   - exposure,
8. capture a photo,
9. upload it to the backend,
10. normalize the image into a canonical bottle format,
11. detect the liquid level,
12. convert the detected level through the calibration profile of the exact bottle type into milliliters,
13. store the measurement,
14. repeat the process at shift end,
15. calculate consumption,
16. generate a shift report.

Base output of a single measurement:

```json
{
  "product": "Božkov Tuzemský 0.7",
  "volume_ml": 437,
  "confidence": 0.982,
  "alignment_score": 0.991,
  "level_score": 0.974
}
```

---

# 3. MOST IMPORTANT ARCHITECTURAL PRINCIPLE

The system MUST NOT work like this:

```text
photo
→
general AI model
→
"I estimate 430 ml"
```

The system MUST work like this:

```text
photo
→
quality validation
→
bottle profile confirmation
→
geometric alignment
→
perspective correction
→
canonical bottle image
→
liquid-level detection
→
normalized liquid level
→
calibration curve for the exact bottle profile
→
volume in ml
```

AI/ML is used only for visual detection or segmentation where classical computer vision is insufficient.

The final conversion to milliliters is deterministic.

---

# 4. BINDING TECHNOLOGY STACK

## 4.1 Frontend / PWA

Use:

- React
- TypeScript
- Vite
- Tailwind CSS
- React Router
- TanStack Query
- React Hook Form
- Zod
- vite-plugin-pwa
- MediaDevices / `getUserMedia()`
- SVG or Canvas for the camera overlay
- OpenCV.js only for lightweight realtime validation
- Web Worker for heavier browser-side image processing

Do not use in the first version:

- Next.js
- React Native
- Electron
- Flutter

React Native is a later client over the same backend.

---

## 4.2 Backend

Use:

- Python 3.13.x
- FastAPI
- Pydantic
- SQLAlchemy 2.x
- asyncpg
- Alembic
- pytest
- httpx for integration tests

The backend is a modular monolith.

Do not use in the first version:

- microservices
- Kubernetes
- Celery
- Redis
- Kafka
- RabbitMQ

These technologies may only be introduced if a concrete measured problem requires them.

---

## 4.3 Vision

Use:

- OpenCV
- NumPy
- SciPy

Use later only if required:

- PyTorch
- ONNX Runtime

Preferred approach:

```text
OpenCV first
ML fallback
```

---

## 4.4 Database

Use:

- PostgreSQL

The database must contain:

- business entities,
- users,
- venues,
- products,
- bottle profiles,
- physical bottle instances,
- calibration versions,
- shifts,
- measurements,
- reports / derived reporting data.

---

## 4.5 Object storage

Use:

- MinIO locally / self-hosted
- S3-compatible architecture

Binary images must not be stored directly in PostgreSQL.

The database stores only metadata and object keys.

---

## 4.6 Deployment

Use:

- Docker
- Docker Compose
- Nginx
- GitHub Actions
- GHCR

Development and production are Docker-first.

---

# 5. DOCKER-FIRST RULES

The project is designed so that development mirrors the target Linux server as closely as possible.

## 5.1 Local Windows environment

Windows does not require:

- local Python,
- local `.venv`,
- local PostgreSQL,
- local MinIO,
- local Node.js for normal project development if all services run through Docker.

The primary runtime is Docker.

---

## 5.2 Python

Backend Docker image:

```dockerfile
FROM python:3.13-slim-trixie
```

A specific stable 3.13.x patch version can be pinned in the Dockerfile.

---

## 5.3 Node

Frontend runs in a Node LTS container.

Recommended pattern:

```dockerfile
FROM node:22-alpine
```

The exact version will be pinned in the Dockerfile.

---

## 5.4 Docker services

Minimum development compose stack:

```text
frontend
backend
postgres
minio
nginx
```

Only add new services if there is a concrete reason.

---

# 6. TARGET REPOSITORY STRUCTURE

```text
bar-vision/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   ├── logging.py
│   │   │   └── storage.py
│   │   │
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   ├── users/
│   │   │   ├── businesses/
│   │   │   ├── venues/
│   │   │   ├── products/
│   │   │   ├── bottles/
│   │   │   ├── calibration/
│   │   │   ├── measurements/
│   │   │   ├── shifts/
│   │   │   └── reports/
│   │   │
│   │   └── vision/
│   │       ├── quality/
│   │       ├── detection/
│   │       ├── alignment/
│   │       ├── canonicalization/
│   │       ├── liquid_level/
│   │       ├── calibration/
│   │       ├── inference/
│   │       └── debug/
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── vision/
│   │   └── fixtures/
│   │
│   ├── alembic/
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── camera/
│   │   │   ├── shifts/
│   │   │   ├── inventory/
│   │   │   ├── measurements/
│   │   │   ├── reports/
│   │   │   └── calibration/
│   │   ├── vision/
│   │   │   ├── camera.ts
│   │   │   ├── image-quality.ts
│   │   │   ├── overlay.ts
│   │   │   └── alignment.worker.ts
│   │   ├── api/
│   │   ├── types/
│   │   └── utils/
│   │
│   ├── public/
│   │   ├── manifest.webmanifest
│   │   └── icons/
│   ├── Dockerfile
│   └── package.json
│
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── vision/
│   └── calibration/
│
├── datasets/
│   ├── raw/
│   ├── canonical/
│   ├── annotations/
│   └── benchmark/
│
├── scripts/
│   ├── dev/
│   ├── calibration/
│   └── benchmark/
│
├── .github/
│   └── workflows/
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── README.md
└── BAR_VISION_EXECUTION_MAP.md
```

---

# 7. RESPONSIBILITIES OF EACH LAYER

## 7.1 Frontend

Frontend may:

- display the camera,
- display the bottle overlay,
- perform basic alignment checks,
- evaluate blur / exposure,
- capture a high-resolution photo,
- upload the image to the backend,
- display the result,
- guide the user through the shift workflow.

Frontend MUST NOT be the authority for the final volume measurement.

---

## 7.2 Backend

Backend is the authority for:

- authentication,
- authorization,
- venue data,
- products,
- bottle profiles,
- bottle instances,
- shifts,
- measurements,
- vision pipeline,
- final volume in ml,
- reports.

---

## 7.3 Vision engine

Vision must be an independent internal layer.

Business modules must not contain OpenCV code.

Example:

```text
measurements service
    ↓
vision service
    ↓
canonicalization
    ↓
liquid detector
    ↓
volume calibration
```

---

# 8. CORE DATA ENTITIES

## 8.1 Business

```text
Business
- id
- name
- created_at
- updated_at
```

---

## 8.2 Venue

```text
Venue
- id
- business_id
- name
- timezone
- active
- created_at
- updated_at
```

---

## 8.3 User

```text
User
- id
- email
- password_hash
- full_name
- active
- created_at
- updated_at
```

Roles will be handled separately or through a membership table.

---

## 8.4 Product

Example:

```text
Božkov Tuzemský 0.7 l
```

Fields:

```text
Product
- id
- name
- brand
- nominal_volume_ml
- barcode
- active
- created_at
- updated_at
```

---

## 8.5 BottleProfile

Defines the geometry of a bottle type.

```text
BottleProfile
- id
- product_id
- version
- canonical_width
- canonical_height
- reference_image_key
- reference_mask_key
- bottle_contour_data
- anchor_points_json
- liquid_roi_json
- label_mask_json
- active
- created_at
```

BottleProfile is not a physical bottle.

It is the model/profile of a bottle type.

---

## 8.6 BottleInstance

A specific physical bottle at a venue.

```text
BottleInstance
- id
- venue_id
- product_id
- bottle_profile_id
- internal_code
- status
- opened_at
- closed_at
- created_at
```

Example:

```text
BZK-000125
```

---

## 8.7 CalibrationVersion

```text
CalibrationVersion
- id
- bottle_profile_id
- version
- calibration_method
- calibration_points_json
- algorithm_version
- active
- created_at
```

Every measurement must reference the exact calibration version used.

---

## 8.8 Shift

```text
Shift
- id
- venue_id
- started_by
- ended_by
- started_at
- ended_at
- status
- notes
- created_at
```

Possible statuses:

```text
OPEN
CLOSING
CLOSED
CANCELLED
```

---

## 8.9 Measurement

```text
Measurement
- id
- shift_id
- bottle_instance_id
- product_id
- bottle_profile_id
- calibration_version_id

- measurement_type
- volume_ml
- liquid_level_normalized

- confidence
- alignment_score
- level_score
- quality_score

- original_image_key
- canonical_image_key
- debug_image_key

- vision_version
- created_by
- created_at
```

Types:

```text
SHIFT_START
SHIFT_END
MANUAL_RECHECK
CALIBRATION
```

---

# 9. CAMERA WORKFLOW

## 9.1 Opening the camera

PWA:

```text
navigator.mediaDevices.getUserMedia()
```

Prefer the rear camera:

```text
facingMode: environment
```

---

## 9.2 Camera preview

Use:

```text
<video>
+
SVG overlay
```

The overlay represents the canonical outline of the exact bottle profile.

---

## 9.3 Live alignment

Frontend validates in realtime:

- center X,
- center Y,
- width,
- height,
- scale,
- rotation,
- perspective deviation,
- blur,
- exposure.

It does not need to run at 30 FPS.

Target:

```text
3–5 analyzed frames / second
```

---

## 9.4 Capture permission

The photo may only be taken when:

```text
position = OK
scale = OK
rotation = OK
blur = OK
exposure = OK
```

UI:

```text
RED
→ bottle not ready

ORANGE
→ almost correct

GREEN
→ measurement can be captured
```

---

# 10. IMAGE QUALITY GATE

Every captured image must pass a quality gate.

## 10.1 Sharpness

Example:

```text
variance of Laplacian
```

Result:

```text
blur_score
```

---

## 10.2 Exposure

Validate:

- image too dark,
- blown highlights,
- insufficient dynamic range.

---

## 10.3 Resolution

Minimum accepted resolution must be configurable.

---

## 10.4 Bottle coverage

Bottle must not be:

- cropped,
- outside frame,
- too small.

---

## 10.5 Failure behavior

If the gate fails:

```text
measurement = REJECTED
```

Frontend receives a concrete reason:

```json
{
  "accepted": false,
  "reason": "IMAGE_BLURRED"
}
```

The system must never force a numeric result when confidence is insufficient.

---

# 11. BOTTLE CANONICALIZATION

This is one of the most important parts of the entire project.

## 11.1 Goal

Regardless of:

- phone model,
- distance,
- small rotation,
- small perspective shift,

the backend must create a standardized image.

Example:

```text
canonical_width = 1024
canonical_height = 2048
```

---

## 11.2 Pipeline

```text
original image
↓
crop / bottle region
↓
key point / contour detection
↓
pose estimation
↓
homography
↓
perspective transform
↓
warp
↓
canonical image
```

---

## 11.3 Output

Every image of the same bottle profile must have:

```text
same width
same height
same bottle bottom
same bottle neck
same ROI
```

---

# 12. BOTTLE PROFILE

Each bottle type has its own profile.

Example:

```text
bozkov_tuzemsky_700_v1
```

Contains:

```text
reference image
canonical dimensions
reference contour
anchor points
liquid ROI
label mask
volume calibration
```

Bottle profiles are versioned.

Never overwrite an old calibration without creating a new version.

---

# 13. LIQUID ROI

The liquid level must not be searched across the entire bottle.

For each bottle profile define:

```text
liquid_roi
```

Exclude:

- neck,
- cap,
- problematic labels,
- glass embossing,
- areas with large logos.

If the label covers the center:

- analyze the left side,
- analyze the right side,
- combine the results.

---

# 14. FIRST LIQUID DETECTOR — OPEN CV

The first implementation must be non-ML.

Pipeline:

```text
canonical bottle
↓
ROI extraction
↓
grayscale
↓
contrast normalization
↓
gradient analysis
↓
horizontal edge candidates
↓
left/right agreement
↓
candidate scoring
↓
liquid_level_y
```

Output:

```text
liquid_level_normalized = 0.61742
```

---

# 15. LIQUID LEVEL CANDIDATE SCORING

Every candidate line receives a score.

Possible factors:

```text
horizontal_strength
left_edge_strength
right_edge_strength
continuity
symmetry
position_validity
contrast
expected_liquid_region
```

Result:

```text
level_score ∈ <0,1>
```

---

# 16. ML FALLBACK

ML is added only if the benchmark proves OpenCV is insufficient.

Possible reasons:

- strong reflections,
- transparent alcohol,
- colored glass,
- non-uniform background,
- difficult labels.

---

## 16.1 ML task

Prefer segmentation.

Example classes:

```text
BACKGROUND
EMPTY_BOTTLE
LIQUID
```

---

## 16.2 Training

Use:

```text
PyTorch
```

---

## 16.3 Production inference

Export:

```text
PyTorch
→
ONNX
→
ONNX Runtime
```

---

## 16.4 Rule

ML never returns milliliters directly.

ML returns:

```text
mask
or
liquid level
```

Milliliters are still calculated by the calibration engine.

---

# 17. CUSTOM ANNOTATION TOOL

Do not use paid CVAT.

Build a simple internal annotation interface.

First version:

```text
image
+
horizontal liquid-level line
```

Store:

```json
{
  "image_id": "uuid",
  "liquid_y_normalized": 0.6124
}
```

If segmentation is later required:

```text
polygon / brush mask editor
```

The dataset remains fully under project control.

---

# 18. VOLUME CALIBRATION

Liquid height is not linearly equal to liquid volume.

Therefore:

```text
50 % bottle height != automatically 50 % volume
```

Every bottle profile requires physical calibration.

---

## 18.1 Calibration dataset

First bottle:

```text
Božkov 0.7
```

Use levels:

```text
0 ml
25 ml
50 ml
75 ml
100 ml
...
700 ml
```

Capture multiple images for every level.

---

## 18.2 Ground truth

True volume must be known externally.

Possible methods:

- laboratory measuring cylinder,
- precisely measured pouring,
- control weighing.

Ground truth must never be derived from the vision system itself.

---

## 18.3 Calibration curve

Data:

```text
normalized_y → real_ml
```

Use monotonic interpolation.

Preferred tool:

```text
SciPy PCHIP
```

---

## 18.4 Calculation

```text
liquid_level_normalized
↓
CalibrationVersion
↓
PCHIP
↓
volume_ml
```

---

# 19. CONFIDENCE SYSTEM

Every measurement must contain confidence metadata.

Example:

```json
{
  "volume_ml": 437,
  "confidence": 0.982,
  "alignment_score": 0.993,
  "level_score": 0.973,
  "quality_score": 0.991
}
```

---

## 19.1 Confidence is not decorative

Confidence controls:

```text
ACCEPT
RETRY
MANUAL_REVIEW
```

---

## 19.2 Example thresholds

```text
confidence >= 0.95
→ ACCEPT

0.85–0.95
→ RETRY / REVIEW

< 0.85
→ REJECT
```

Exact thresholds are set only after benchmark results exist.

---

# 20. REFERENCE MEASUREMENT PIPELINE

```text
PHOTO
  │
  ▼
quality gate
  │
  ├── fail → RETAKE
  │
  ▼
bottle profile verification
  │
  ▼
alignment
  │
  ▼
perspective correction
  │
  ▼
canonical bottle
  │
  ▼
liquid ROI
  │
  ▼
OpenCV liquid detector
  │
  ├── confidence HIGH ────────────┐
  │                               │
  │ confidence LOW                │
  ▼                               │
ML segmentation fallback          │
  │                               │
  └────────────────────┬──────────┘
                       ▼
             normalized liquid Y
                       │
                       ▼
             calibration version
                       │
                       ▼
                    volume ml
                       │
                       ▼
               confidence gate
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
           ACCEPT              RETAKE
             │
             ▼
         PostgreSQL
             │
             ▼
           MinIO
```

---

# 21. SHIFT WORKFLOW

## 21.1 Shift start

```text
login
↓
venue
↓
open shift
↓
list bottle instances
↓
measure each open bottle
↓
store SHIFT_START measurements
↓
shift status = OPEN
```

---

## 21.2 Shift end

```text
open shift
↓
close shift
↓
measure all bottle instances again
↓
store SHIFT_END measurements
↓
account for new bottles
↓
account for discarded / empty bottles
↓
calculate consumption
↓
shift status = CLOSED
```

---

# 22. CONSUMPTION CALCULATION

Simplified formula:

```text
start_volume
+
new_bottles_added
-
end_volume
-
valid_adjustments
=
consumption
```

The calculation must not be based directly on the photograph.

The photograph only produces individual measurements.

Business logic calculates the shift result.

---

# 23. SHIFT REPORT

Minimum report:

| Product | Start | Newly opened | End | Consumption |
|---|---:|---:|---:|---:|
| Božkov | 1137 ml | 700 ml | 681 ml | 1156 ml |
| Finlandia | 830 ml | 0 ml | 417 ml | 413 ml |

The report must be reproducible from stored measurement data.

---

# 24. API DESIGN

Use REST + OpenAPI.

FastAPI is the only source of truth for the API schema.

---

## 24.1 OpenAPI → TypeScript

Flow:

```text
FastAPI
↓
openapi.json
↓
TypeScript generator
↓
frontend API types
```

Frontend must not manually duplicate backend DTOs without a concrete reason.

---

## 24.2 Example endpoints

```text
POST   /api/v1/auth/login

GET    /api/v1/venues
GET    /api/v1/venues/{venue_id}

GET    /api/v1/products
POST   /api/v1/products

GET    /api/v1/bottle-profiles
POST   /api/v1/bottle-profiles

POST   /api/v1/shifts
GET    /api/v1/shifts/{shift_id}
POST   /api/v1/shifts/{shift_id}/close

POST   /api/v1/measurements
GET    /api/v1/measurements/{measurement_id}

POST   /api/v1/measurements/{measurement_id}/analyze

GET    /api/v1/reports/shifts/{shift_id}
```

Exact endpoint naming may evolve during implementation, but responsibilities must remain separated.

---

# 25. OBJECT STORAGE

Structure:

```text
measurements/
  venue_uuid/
    YYYY/
      MM/
        measurement_uuid/
          original.jpg
          canonical.jpg
          debug.jpg
```

Calibration:

```text
calibration/
  bottle_profile_uuid/
    version/
      reference.jpg
      mask.png
      calibration.json
```

---

# 26. DEBUG ARTIFACTS

The vision pipeline must be able to optionally persist debug outputs:

```text
original
cropped
edges
contours
alignment
canonical
roi
level_candidates
final_level
```

Not all debug artifacts need permanent storage in production.

They are essential in benchmark and development modes.

---

# 27. VISION VERSIONING

Every measurement must contain:

```text
vision_version
calibration_version
```

Example:

```text
vision_version = "vision-0.4.2"
calibration_version = "bozkov-700-v3"
```

No measurement may exist without being able to determine:

- which vision algorithm produced it,
- which calibration version produced it.

---

# 28. TESTING

Testing is part of the architecture, not an afterthought.

---

## 28.1 Backend unit tests

Test:

- services,
- domain rules,
- volume calculations,
- shift calculations,
- validation.

---

## 28.2 Backend integration tests

Test:

```text
FastAPI
+
PostgreSQL
+
MinIO
```

---

## 28.3 Frontend unit tests

Use:

- Vitest

Test:

- utility functions,
- state logic,
- validation.

---

## 28.4 E2E

Use:

- Playwright

Test:

```text
login
open shift
select bottle
upload fixture image
receive measurement
close shift
view report
```

Browser camera may be mocked using test fixtures.

---

# 29. VISION REGRESSION BENCHMARK

This is one of the most important parts of the project.

Dataset:

```text
datasets/benchmark/
```

Every image must have ground truth.

Example:

```json
{
  "image": "bozkov_450_001.jpg",
  "product": "bozkov_700",
  "true_ml": 450,
  "true_level_y": 0.6112
}
```

---

## 29.1 Metrics

At minimum:

```text
MAE ml
Median Absolute Error
P90 Error
P95 Error
Maximum Error
Detection Failure Rate
False Acceptance Rate
Retry Rate
```

---

## 29.2 Definition of Done for a vision change

No vision change may be merged only because:

```text
"it looks good on a few photos"
```

It must pass the benchmark.

---

# 30. ACCURACY TARGET

Do not claim target accuracy before measurements exist.

After the first calibration, establish a real baseline.

Example:

```text
MAE <= X ml
P95 <= Y ml
failure rate <= Z %
```

X, Y, and Z are determined from benchmark results.

---

# 31. CI

GitHub Actions must at minimum run:

```text
backend lint
backend tests
frontend lint
frontend tests
frontend build
docker build backend
docker build frontend
```

Later:

```text
vision benchmark smoke test
```

The full vision benchmark does not need to run on every commit if it becomes expensive.

---

# 32. CD

Flow:

```text
git push
↓
GitHub Actions
↓
tests
↓
build images
↓
push GHCR
↓
server pull
↓
docker compose up
```

The server should not rebuild from an arbitrary source checkout.

Prefer immutable image tags.

---

# 33. LOGGING

Backend must use structured logging.

Each measurement log entry should include:

```text
measurement_id
shift_id
venue_id
bottle_instance_id
vision_version
duration_ms
result
```

Never log:

- passwords,
- JWTs,
- secrets.

---

# 34. PERFORMANCE

The first version does not require realtime server inference.

Target flow:

```text
capture
→
upload
→
analysis
→
result
```

Optimize only after measuring actual bottlenecks.

---

# 35. FRONTEND CAMERA PERFORMANCE

Live alignment target:

```text
3–5 FPS
```

Not:

```text
30 FPS OpenCV analysis
```

The camera preview can run at 30/60 FPS, but vision analysis should be throttled.

---

# 36. SECURITY

Minimum requirements:

- HTTPS
- secure password hashing
- access control by business / venue
- JWT access token
- refresh mechanism
- server-side authorization
- upload size limits
- MIME validation
- image decode validation
- secrets only through environment variables / secret management

Frontend must never be the authorization authority.

---

# 37. AUTHORIZATION MODEL

Principle:

```text
User
↓
Business membership
↓
Venue permissions
```

A user must not access another business's data.

Every business-data query must be tenant-scoped.

---

# 38. PWA OFFLINE STRATEGY

First version:

- app shell may be cached,
- current business data requires server access,
- final measurement requires backend access.

Offline measurement is not an MVP requirement.

A queue can be added later if explicitly needed.

---

# 39. REACT NATIVE — ONLY AFTER STABLE PWA

React Native must not be introduced until these are stable:

- API,
- bottle profile,
- canonicalization,
- liquid detector,
- calibration engine.

Then use:

```text
React Native
+
TypeScript
+
VisionCamera
+
same FastAPI backend
```

---

# 40. ON-DEVICE INFERENCE — LATER

Possible future architecture:

```text
PWA → ONNX Runtime Web
React Native → ONNX Runtime React Native
```

But the backend remains the authoritative first production implementation.

---

# 41. WHAT NOT TO DO

Future AI must follow this list.

Do not add without explicit instruction:

```text
Kubernetes
Redis
Celery
Kafka
microservices
GraphQL
Next.js
React Native
LLM measurement
YOLO dependency
paid annotation SaaS
multi-cloud
event sourcing
CQRS
```

---

# 42. IMPLEMENTATION PHASES

---

# PHASE 0 — REPOSITORY FOUNDATION

## Goal

Prepare a clean base structure.

## Implement

```text
backend/
frontend/
docs/
datasets/
scripts/
.github/
```

Also:

```text
.gitignore
.env.example
README.md
docker-compose.yml
```

## Acceptance criteria

- `git status` is clean after commit
- directories exist
- secrets are not committed
- README explains basic startup

---

# PHASE 1 — DOCKER FOUNDATION

## Goal

Run the whole project only through Docker.

## Implement

```text
backend Dockerfile
frontend Dockerfile
postgres service
minio service
docker-compose.yml
```

## Acceptance criteria

Command:

```powershell
docker compose up --build
```

starts all core services.

The following must be available:

```text
frontend
backend health endpoint
postgres
minio
```

---

# PHASE 2 — FASTAPI FOUNDATION

## Goal

Prepare a clean modular backend architecture.

## Implement

```text
FastAPI app
config
database
logging
health
API versioning
```

Endpoint:

```text
GET /api/v1/health
```

## Acceptance criteria

Returns:

```json
{
  "status": "ok"
}
```

Covered by pytest.

---

# PHASE 3 — POSTGRESQL + MIGRATIONS

## Goal

Working persistence.

## Implement

```text
SQLAlchemy
asyncpg
Alembic
```

Initial entities:

```text
Business
Venue
User
```

## Acceptance criteria

- migrations work from an empty DB
- downgrade works
- integration test writes and reads data

---

# PHASE 4 — FRONTEND FOUNDATION

## Goal

Working React PWA shell.

## Implement

```text
React
TypeScript
Vite
Tailwind
React Router
TanStack Query
PWA manifest
```

## Acceptance criteria

- frontend runs through Docker
- frontend communicates with `/api/v1/health`
- app is installable as a PWA where supported

---

# PHASE 5 — AUTH

## Goal

Login and tenant-safe access.

## Implement

```text
User
password hashing
login
access token
refresh token
protected routes
```

## Acceptance criteria

- valid login works
- invalid login fails
- protected endpoint without auth returns 401
- user cannot read another business's data

---

# PHASE 6 — PRODUCTS + BOTTLE PROFILES

## Goal

Create the data foundation for vision.

## Implement

```text
Product
BottleProfile
BottleInstance
CalibrationVersion
```

First product:

```text
Božkov Tuzemský 0.7 l
```

## Acceptance criteria

The system can:

- create a product,
- create a bottle profile,
- store a reference image,
- store canonical geometry metadata.

---

# PHASE 7 — CAMERA PWA

## Goal

Open the mobile camera from the browser.

## Implement

```text
getUserMedia
rear camera preference
video preview
capture
SVG overlay
```

## Acceptance criteria

On Android / iPhone browser:

- camera opens,
- live preview is visible,
- overlay is displayed,
- image can be captured.

---

# PHASE 8 — FRONTEND QUALITY CHECK

## Goal

Reject obviously bad frames before capture.

## Implement

```text
blur check
brightness check
basic alignment
```

## Acceptance criteria

UI can show:

```text
MOVE RIGHT
MOVE CLOSER
STRAIGHTEN
LOW LIGHT
TOO BLURRY
READY
```

---

# PHASE 9 — IMAGE UPLOAD

## Goal

Securely upload the captured image to the backend.

## Implement

```text
multipart upload
size validation
mime validation
MinIO storage
measurement draft
```

## Acceptance criteria

After capture:

```text
original image
```

exists in MinIO and its key is stored in DB.

---

# PHASE 10 — CANONICALIZATION V1

## Goal

Normalize one exact bottle:

```text
Božkov 0.7
```

into a consistent canonical image.

## Implement

```text
bottle crop
contour / anchors
homography
warpPerspective
canonical output
```

## Acceptance criteria

Across test images of the same bottle:

- bottle bottom maps to the same canonical area,
- bottle neck maps to the same canonical area,
- width is normalized,
- ROI matches the reference.

---

# PHASE 11 — CALIBRATION DATASET

## Goal

Create ground truth.

## Implement a physical dataset:

```text
0 ml
25 ml
50 ml
...
700 ml
```

Capture multiple images for each level.

## Acceptance criteria

Every image has:

```text
true_ml
bottle_profile
capture metadata
```

Dataset is versioned.

---

# PHASE 12 — LIQUID DETECTOR V1

## Goal

Detect the liquid level without ML.

## Implement

```text
ROI
contrast
gradients
horizontal candidates
candidate scoring
liquid_level_y
```

## Acceptance criteria

Benchmark report contains:

```text
level MAE
failure rate
```

---

# PHASE 13 — CALIBRATION ENGINE

## Goal

Convert liquid Y to milliliters.

## Implement

```text
calibration points
PCHIP
volume calculation
range checks
```

## Acceptance criteria

Known calibration points return expected values.

Interpolation remains monotonic.

---

# PHASE 14 — END-TO-END MEASUREMENT V1

## Goal

First complete measurement.

Flow:

```text
PWA
→
photo
→
FastAPI
→
OpenCV
→
canonical bottle
→
liquid level
→
calibration
→
ml
→
frontend
```

## Acceptance criteria

For Božkov 0.7:

```text
photo → actual measurement in ml
```

without manually entering the liquid level.

---

# PHASE 15 — VISION BENCHMARK

## Goal

Produce objective numbers.

## Implement report:

```text
MAE
median
P90
P95
max error
failure rate
false acceptance rate
```

## Acceptance criteria

Every experiment produces a machine-readable benchmark report.

---

# PHASE 16 — CONFIDENCE GATE

## Goal

Reject uncertain measurements.

## Implement

```text
quality_score
alignment_score
level_score
combined confidence
```

## Acceptance criteria

Bad photographs are not accepted as valid measurements.

---

# PHASE 17 — SHIFT DOMAIN

## Goal

Implement real shift handover workflow.

## Implement

```text
open shift
start measurements
end measurements
close shift
```

## Acceptance criteria

A complete shift can be executed from start to finish.

---

# PHASE 18 — CONSUMPTION ENGINE

## Goal

Calculate consumption.

## Implement:

```text
start
new bottles
end
adjustments
consumption
```

## Acceptance criteria

Unit tests cover boundary cases.

---

# PHASE 19 — REPORTING

## Goal

Display a shift report.

## Implement

```text
per product
per bottle
totals
measurement audit
```

## Acceptance criteria

Report is reproducible from DB data.

---

# PHASE 20 — OWN ANNOTATION TOOL

Only if needed for further vision work.

First version:

```text
image
horizontal line
save normalized y
```

---

# PHASE 21 — ML FALLBACK

Only if the OpenCV benchmark is insufficient.

## Implement

```text
PyTorch dataset
segmentation training
validation
ONNX export
ONNX Runtime inference
```

## Acceptance criteria

ML must objectively improve the benchmark.

If it does not improve the benchmark, it is not used.

---

# PHASE 22 — ADDITIONAL BOTTLE PROFILES

Only after successful Božkov validation.

For every new bottle type:

```text
reference
canonical profile
ROI
calibration dataset
benchmark
activation
```

---

# PHASE 23 — HARDENING

## Implement

```text
rate limits
upload limits
stronger auth controls
DB backups
MinIO backups
error reporting
structured logs
production configuration
```

---

# PHASE 24 — CI/CD

## Implement

```text
GitHub Actions
GHCR
immutable tags
production compose
deployment
```

---

# PHASE 25 — REACT NATIVE

Only after PWA and vision pipeline are stable.

Use:

```text
React Native
TypeScript
VisionCamera
```

Backend remains unchanged.

---

# 43. DEFINITION OF DONE FOR EVERY CHANGE

An implementation change is complete only when:

1. the code works,
2. an appropriate test exists where applicable,
3. Docker build passes,
4. no existing functionality is broken,
5. API schema remains consistent,
6. the change does not violate this execution map,
7. if vision changes, benchmark impact is evaluated,
8. if DB changes, a migration exists,
9. if env changes, `.env.example` is updated,
10. documentation is updated if architecture changes.

---

# 44. GIT RULES

Prefer atomic commits.

Examples:

```text
feat(backend): add health endpoint
feat(db): add business and venue models
feat(frontend): add PWA camera screen
feat(vision): add canonical bottle transform
test(vision): add Bozkov benchmark fixtures
```

Do not mix unrelated work such as:

```text
frontend redesign
+
database migration
+
vision algorithm
```

into one commit.

---

# 45. RULE FOR AI ON EVERY FUTURE PROMPT

Before implementation, AI must internally verify:

```text
1. What phase are we in?
2. What already exists?
3. What is the exact requested change?
4. Does it violate the execution map?
5. Does it require a DB migration?
6. Does it require a new env variable?
7. Does it require tests?
8. Does it affect the vision benchmark?
9. Does it affect Docker?
10. Does it affect the FE/BE API contract?
```

---

# 46. AI MUST NOT AUTOMATICALLY

Without explicit instruction, AI must not:

- change the stack,
- add new services,
- add libraries without necessity,
- create microservices,
- switch to React Native,
- replace OpenCV with an LLM,
- store images in PostgreSQL,
- estimate volume from textual AI output,
- skip calibration benchmark,
- change business logic during a vision-only task,
- add features outside the current request.

---

# 47. FIRST MILESTONE

The most important technical milestone:

```text
ONE BOTTLE
Božkov Tuzemský 0.7

PWA
↓
camera
↓
overlay
↓
photo
↓
FastAPI
↓
OpenCV canonicalization
↓
liquid detection
↓
calibration curve
↓
volume ml
↓
benchmark
```

Do not expand to dozens of bottle types until this works reliably.

---

# 48. MVP DEFINITION

MVP is complete when:

1. user signs in,
2. user opens a venue,
3. user opens a shift,
4. the system supports at least one validated bottle profile,
5. PWA opens the camera,
6. user aligns the bottle,
7. app captures a photo,
8. backend canonicalizes it,
9. backend detects the liquid level,
10. backend calculates milliliters,
11. measurement is stored,
12. user performs start and end measurements,
13. app calculates consumption,
14. app displays a report,
15. system rejects low-quality measurements,
16. vision has a benchmark with real metrics.

---

# 49. MVP ARCHITECTURE IN ONE DIAGRAM

```text
                 ┌────────────────────────┐
                 │       MOBILE PWA       │
                 │                        │
                 │ React + TypeScript     │
                 │ Vite + Tailwind        │
                 │ getUserMedia           │
                 │ SVG overlay            │
                 │ OpenCV.js light checks │
                 └───────────┬────────────┘
                             │
                             │ HTTPS
                             ▼
                 ┌────────────────────────┐
                 │        FASTAPI         │
                 │                        │
                 │ auth                   │
                 │ products               │
                 │ shifts                 │
                 │ measurements           │
                 │ reports                │
                 └───────────┬────────────┘
                             │
                     ┌───────┴────────┐
                     ▼                ▼
             ┌──────────────┐  ┌──────────────┐
             │   VISION     │  │   BUSINESS   │
             │              │  │    LOGIC     │
             │ OpenCV       │  │              │
             │ NumPy        │  │ shifts       │
             │ SciPy        │  │ consumption  │
             │ ONNX later   │  │ reports      │
             └──────┬───────┘  └──────┬───────┘
                    │                  │
                    └────────┬─────────┘
                             ▼
                    ┌────────────────┐
                    │   PostgreSQL   │
                    └────────────────┘
                             │
                    image keys only
                             │
                             ▼
                    ┌────────────────┐
                    │     MinIO      │
                    │ original jpg   │
                    │ canonical jpg  │
                    └────────────────┘
```

---

# 50. NEXT IMMEDIATE STEP

Current project currently contains only:

```text
bar-vision/
├── backend/
└── frontend/
```

The next implementation step is:

```text
PHASE 0 + PHASE 1
```

That means:

1. create target root structure,
2. `.gitignore`,
3. `.env.example`,
4. backend Dockerfile,
5. frontend Dockerfile,
6. `docker-compose.yml`,
7. PostgreSQL,
8. MinIO,
9. basic FastAPI health endpoint,
10. basic React/Vite frontend,
11. verify `docker compose up --build`.

Only after Docker foundation succeeds should the next phase begin.

---

# 51. SHORT MASTER PROMPT FOR FUTURE AI

Attach this document to future work and use:

```text
Follow BAR_VISION_EXECUTION_MAP.md as a binding project specification.

Do not change the architecture, stack, or phase order unless I explicitly instruct you to.
Work only on the currently requested step.
Do not add features outside the request.
Docker is the only authoritative development runtime.
Backend is Python/FastAPI.
Frontend is React/TypeScript/Vite/Tailwind PWA.
Vision is OpenCV-first, with ML only as a benchmark-justified fallback.
Alcohol volume must never be determined through an LLM estimate; it must always come from liquid-level detection and a calibration curve.
Every DB change requires a migration.
Every vision change must be benchmark-testable.
Every change must preserve the FE/BE API contract.
```

---

# 52. FINAL TECHNICAL PRIORITY

The most important areas of the project, ordered by technical risk:

```text
1. canonicalization
2. liquid-level detection
3. physical volume calibration
4. benchmark / confidence
5. camera UX
6. shift domain
7. reporting
8. additional bottle profiles
9. ML fallback
10. native client
```

Frontend CRUD and reports are not the main technical risk.

The main risk is:

```text
reliably determining the liquid level
from photographs taken on different phones
of the same physical bottle type
and converting that level into real volume in milliliters
with measurable error.
```

The whole project must be built around solving that problem correctly.
