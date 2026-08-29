import { useCallback, useEffect, useRef, useState } from "react";


export type CameraStatus =
  | "idle"
  | "starting"
  | "ready"
  | "denied"
  | "unavailable"
  | "error";


async function getCameraStream(): Promise<MediaStream> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new DOMException(
      "Camera API is not available in this browser.",
      "NotSupportedError",
    );
  }

  // Prefer rear camera on phones; fall back to any camera (desktop webcam).
  try {
    return await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 1280 },
        height: { ideal: 1920 },
      },
    });
  } catch {
    return navigator.mediaDevices.getUserMedia({
      audio: false,
      video: true,
    });
  }
}


function describeCameraError(error: unknown): {
  status: CameraStatus;
  message: string;
} {
  if (error instanceof DOMException) {
    if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
      return {
        status: "denied",
        message: "Camera permission was denied. Allow camera access and try again.",
      };
    }
    if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
      return {
        status: "unavailable",
        message: "No camera device was found on this machine.",
      };
    }
    if (error.name === "NotReadableError" || error.name === "TrackStartError") {
      return {
        status: "error",
        message: "Camera is already in use by another application.",
      };
    }
    if (error.name === "SecurityError") {
      return {
        status: "unavailable",
        message:
          "Camera requires a secure context (https:// or http://127.0.0.1).",
      };
    }
    return {
      status: "error",
      message: `Unable to open the camera (${error.name}).`,
    };
  }

  return {
    status: "error",
    message: "Unable to open the camera.",
  };
}


export function useCamera() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [status, setStatus] = useState<CameraStatus>("idle");
  const [capturedDataUrl, setCapturedDataUrl] = useState<string | null>(
    null,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  const startCamera = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus("unavailable");
      setErrorMessage(
        "Camera API is not available. Use Chrome/Edge on http://127.0.0.1:18100.",
      );
      return;
    }

    if (
      typeof window !== "undefined"
      && !window.isSecureContext
      && window.location.hostname !== "localhost"
      && window.location.hostname !== "127.0.0.1"
    ) {
      setStatus("unavailable");
      setErrorMessage(
        "Camera blocked: open the app via http://127.0.0.1:18100 (secure context).",
      );
      return;
    }

    setStatus("starting");
    setErrorMessage(null);
    setCapturedDataUrl(null);
    stopCamera();

    try {
      const stream = await getCameraStream();
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setStatus("ready");
    } catch (error) {
      stopCamera();
      const described = describeCameraError(error);
      setStatus(described.status);
      setErrorMessage(described.message);
    }
  }, [stopCamera]);

  const captureFrame = useCallback(() => {
    const video = videoRef.current;

    if (!video || video.videoWidth === 0 || video.videoHeight === 0) {
      setErrorMessage("Camera preview is not ready for capture.");
      return;
    }

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext("2d");
    if (!context) {
      setErrorMessage("Unable to create capture canvas.");
      return;
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    setCapturedDataUrl(canvas.toDataURL("image/jpeg", 0.92));
    setErrorMessage(null);
  }, []);

  const clearCapture = useCallback(() => {
    setCapturedDataUrl(null);
  }, []);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  return {
    videoRef,
    status,
    errorMessage,
    capturedDataUrl,
    startCamera,
    stopCamera,
    captureFrame,
    clearCapture,
  };
}
