from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_session
from app.modules.bottles.models import CalibrationVersion
from app.modules.calibration.schemas import (
    CalibrationVersionCreate,
    CalibrationVersionFromDatasetCreate,
    CalibrationVersionResponse,
    CalibrationVersionUpdate,
    VolumeEvaluateRequest,
    VolumeEvaluateResponse,
)
from app.modules.calibration.service import (
    CalibrationServiceError,
    attach_calibration_original,
    create_calibration_version,
    create_calibration_version_from_dataset,
    delete_calibration_version,
    evaluate_volume,
    get_accessible_calibration_version,
    list_calibration_versions,
    update_calibration_version,
)
from app.modules.measurements.image_validation import (
    ImageValidationError,
    validate_measurement_image,
)
from app.modules.users.models import User


router = APIRouter(
    prefix="/calibration-versions",
    tags=["calibration"],
)


def _http_error(exc: CalibrationServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post(
    "",
    response_model=CalibrationVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_calibration_version_endpoint(
    payload: CalibrationVersionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CalibrationVersion:
    """
    Register a tenant-owned calibration version for one bottle/glass profile.

    Original images are attached afterward via
    POST /calibration-versions/{id}/originals.
    """
    try:
        return await create_calibration_version(
            session,
            user_id=current_user.id,
            payload=payload,
        )
    except CalibrationServiceError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/from-dataset",
    response_model=CalibrationVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_calibration_version_from_dataset_endpoint(
    payload: CalibrationVersionFromDatasetCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CalibrationVersion:
    """Ingest a local datasets/ annotation package (lab / first calibration)."""
    try:
        return await create_calibration_version_from_dataset(
            session,
            user_id=current_user.id,
            bottle_profile_id=payload.bottle_profile_id,
            version=payload.version,
            calibration_method=payload.calibration_method,
            algorithm_version=payload.algorithm_version,
            active=payload.active,
            annotation_relative_path=payload.annotation_relative_path,
        )
    except CalibrationServiceError as exc:
        raise _http_error(exc) from exc


@router.get(
    "",
    response_model=list[CalibrationVersionResponse],
)
async def list_calibration_versions_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    bottle_profile_id: UUID | None = None,
) -> list[CalibrationVersion]:
    return await list_calibration_versions(
        session,
        user_id=current_user.id,
        bottle_profile_id=bottle_profile_id,
    )


@router.get(
    "/{calibration_version_id}",
    response_model=CalibrationVersionResponse,
)
async def get_calibration_version_endpoint(
    calibration_version_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CalibrationVersion:
    try:
        return await get_accessible_calibration_version(
            session,
            user_id=current_user.id,
            calibration_version_id=calibration_version_id,
        )
    except CalibrationServiceError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/{calibration_version_id}/evaluate-volume",
    response_model=VolumeEvaluateResponse,
)
async def evaluate_volume_endpoint(
    calibration_version_id: UUID,
    payload: VolumeEvaluateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> VolumeEvaluateResponse:
    """Deterministic level_normalized → ml using this version's curve."""
    try:
        return await evaluate_volume(
            session,
            user_id=current_user.id,
            calibration_version_id=calibration_version_id,
            level_normalized=payload.level_normalized,
        )
    except CalibrationServiceError as exc:
        raise _http_error(exc) from exc


@router.patch(
    "/{calibration_version_id}",
    response_model=CalibrationVersionResponse,
)
async def update_calibration_version_endpoint(
    calibration_version_id: UUID,
    payload: CalibrationVersionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CalibrationVersion:
    try:
        return await update_calibration_version(
            session,
            user_id=current_user.id,
            calibration_version_id=calibration_version_id,
            payload=payload,
        )
    except CalibrationServiceError as exc:
        raise _http_error(exc) from exc


@router.delete(
    "/{calibration_version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_calibration_version_endpoint(
    calibration_version_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    try:
        await delete_calibration_version(
            session,
            user_id=current_user.id,
            calibration_version_id=calibration_version_id,
        )
    except CalibrationServiceError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/{calibration_version_id}/originals",
    response_model=CalibrationVersionResponse,
)
async def upload_calibration_original_endpoint(
    calibration_version_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: UploadFile = File(...),
    filename: str | None = Form(default=None),
) -> CalibrationVersion:
    """Upload / replace one original capture for a calibration point."""
    target_name = filename or (file.filename or "")
    payload = await file.read()

    try:
        validated = validate_measurement_image(
            payload=payload,
            content_type=file.content_type,
            filename=target_name,
        )
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc

    try:
        return await attach_calibration_original(
            session,
            user_id=current_user.id,
            calibration_version_id=calibration_version_id,
            filename=target_name.replace("\\", "/").split("/")[-1],
            payload=validated.payload,
            content_type=validated.content_type,
        )
    except CalibrationServiceError as exc:
        raise _http_error(exc) from exc
