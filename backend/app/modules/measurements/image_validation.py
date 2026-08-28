from __future__ import annotations

from dataclasses import dataclass


class ImageValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class ValidatedImage:
    content_type: str
    extension: str
    payload: bytes


ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ("jpeg", (b"\xff\xd8",)),
    "image/jpg": ("jpeg", (b"\xff\xd8",)),
    "image/png": ("png", (b"\x89PNG\r\n\x1a\n",)),
}

MAX_MEASUREMENT_IMAGE_BYTES = 25 * 1024 * 1024


def validate_measurement_image(
    *,
    payload: bytes,
    content_type: str | None,
    filename: str | None = None,
) -> ValidatedImage:
    if not payload:
        raise ImageValidationError("Empty image upload.")

    if len(payload) > MAX_MEASUREMENT_IMAGE_BYTES:
        raise ImageValidationError("Image exceeds maximum allowed size.")

    normalized_type = (content_type or "").lower().strip()
    if normalized_type not in ALLOWED_IMAGE_TYPES:
        raise ImageValidationError(
            "Only JPEG and PNG images are supported.",
        )

    extension, magic_prefixes = ALLOWED_IMAGE_TYPES[normalized_type]
    if not any(payload.startswith(prefix) for prefix in magic_prefixes):
        raise ImageValidationError(
            "Image content does not match declared MIME type.",
        )

    # Never trust extension alone; still reject obvious traversal names.
    if filename and (".." in filename or "/" in filename or "\\" in filename):
        raise ImageValidationError("Invalid filename.")

    return ValidatedImage(
        content_type=(
            "image/jpeg" if extension == "jpeg" else "image/png"
        ),
        extension=extension if extension != "jpeg" else "jpg",
        payload=payload,
    )
