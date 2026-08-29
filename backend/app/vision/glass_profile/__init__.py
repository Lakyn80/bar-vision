"""glass_500ml_v1 profile recognition and geometry gate."""

from app.vision.glass_profile.geometry import (
    FrameQualityEvidence,
    GlassProfileDetection,
    GlassProfileGeometryConfig,
    GlassProfileValidationResult,
    validate_profile_geometry,
)
from app.vision.glass_profile.inference import (
    GlassProfileInferenceError,
    GlassProfileInferenceUnavailable,
    OnnxGlassProfileDetector,
)
from app.vision.glass_profile.schema import (
    GLASS_500ML_PROFILE_KEY,
    KEYPOINT_NAMES,
)

__all__ = [
    "FrameQualityEvidence",
    "GLASS_500ML_PROFILE_KEY",
    "GlassProfileDetection",
    "GlassProfileGeometryConfig",
    "GlassProfileInferenceError",
    "GlassProfileInferenceUnavailable",
    "GlassProfileValidationResult",
    "KEYPOINT_NAMES",
    "OnnxGlassProfileDetector",
    "validate_profile_geometry",
]
