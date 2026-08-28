from pathlib import Path

from app.modules.measurements.image_validation import (
    ImageValidationError,
    validate_measurement_image,
)


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "rum_test.png"


def test_validate_png_fixture() -> None:
    payload = FIXTURE.read_bytes()
    validated = validate_measurement_image(
        payload=payload,
        content_type="image/png",
        filename="rum_test.png",
    )
    assert validated.extension == "png"
    assert validated.content_type == "image/png"
    assert validated.payload.startswith(b"\x89PNG")


def test_reject_empty_image() -> None:
    try:
        validate_measurement_image(
            payload=b"",
            content_type="image/png",
        )
        assert False, "expected ImageValidationError"
    except ImageValidationError as exc:
        assert "Empty" in exc.detail


def test_reject_mismatched_magic_bytes() -> None:
    try:
        validate_measurement_image(
            payload=b"not-an-image",
            content_type="image/png",
            filename="fake.png",
        )
        assert False, "expected ImageValidationError"
    except ImageValidationError as exc:
        assert "does not match" in exc.detail


def test_reject_path_traversal_filename() -> None:
    payload = FIXTURE.read_bytes()
    try:
        validate_measurement_image(
            payload=payload,
            content_type="image/png",
            filename="../evil.png",
        )
        assert False, "expected ImageValidationError"
    except ImageValidationError as exc:
        assert "filename" in exc.detail.lower()
