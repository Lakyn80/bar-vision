import pytest

from app.modules.measurements import service
from app.modules.measurements.service import MeasurementAnalyzeError


class _Settings:
    glass_profile_gate_enabled = True
    glass_profile_onnx_path = None
    glass_profile_metadata_path = None


def test_glass_profile_gate_requires_configured_onnx_model(monkeypatch) -> None:
    monkeypatch.setattr(service, "get_settings", lambda: _Settings())

    with pytest.raises(MeasurementAnalyzeError) as exc:
        service._validate_glass_profile_gate(b"not-an-image")

    assert exc.value.status_code == 503
    assert "ONNX profile model is unavailable" in exc.value.detail


def test_glass_profile_gate_disabled_blocks_calibrated_measurement(monkeypatch) -> None:
    settings = _Settings()
    settings.glass_profile_gate_enabled = False
    monkeypatch.setattr(service, "get_settings", lambda: settings)

    with pytest.raises(MeasurementAnalyzeError) as exc:
        service._validate_glass_profile_gate(b"not-an-image")

    assert exc.value.status_code == 503
    assert "profile gate is disabled" in exc.value.detail
