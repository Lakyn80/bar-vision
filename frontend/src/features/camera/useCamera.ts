import { useCallback, useEffect, useRef, useState } from "react";


export type CameraStatus =
  | "idle"
  | "starting"
  | "ready"
  | "denied"
  | "unavailable"
  | "error";


async function getRearCameraStream(): Promise<MediaStream> {
  const preferred = await navigator.mediaDevices.getUserMedia({
    audio: false,
    video: {
      facingMode: { ideal: "environment" },
      width: { ideal: 1280 },
      height: { ideal: 1920 },
    },
  });

  return preferred;
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
      setErrorMessage("Camera API is not available in this browser.");
      return;
    }

    setStatus("starting");
    setErrorMessage(null);
    setCapturedDataUrl(null);
    stopCamera();

    try {
      const stream = await getRearCameraStream();
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setStatus("ready");
    } catch (error) {
      stopCamera();

      if (error instanceof DOMException && error.name === "NotAllowedError") {
        setStatus("denied");
        setErrorMessage("Camera permission was denied.");
        return;
      }

      setStatus("error");
      setErrorMessage("Unable to open the camera.");
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
