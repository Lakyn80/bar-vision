import {
  useEffect,
  useState,
  type RefObject,
} from "react";

import {
  analyzeFrameQuality,
  type CaptureGuidance,
  type FrameQualityResult,
  type VesselBox,
} from "./frameQuality";


type UseFrameGuidanceOptions = {
  videoRef: RefObject<HTMLVideoElement | null>;
  enabled: boolean;
};


const IDLE: FrameQualityResult = {
  guidance: "READY",
  brightness: 0,
  blurScore: 0,
  bottleCoverage: 0,
  horizontalBias: 0,
  vesselBox: null,
  locked: false,
};


export function useFrameGuidance({
  videoRef,
  enabled,
}: UseFrameGuidanceOptions): FrameQualityResult {
  const [result, setResult] = useState<FrameQualityResult>(IDLE);

  useEffect(() => {
    if (!enabled) {
      setResult(IDLE);
      return;
    }

    let cancelled = false;
    let frameHandle = 0;
    let lastRun = 0;

    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d", {
      willReadFrequently: true,
    });

    const tick = (timestamp: number) => {
      if (cancelled) {
        return;
      }

      // ~20 fps tracking feels like face-lock apps
      if (timestamp - lastRun >= 50) {
        lastRun = timestamp;
        const video = videoRef.current;

        if (
          context
          && video
          && video.videoWidth > 0
          && video.videoHeight > 0
        ) {
          const sampleWidth = 180;
          const sampleHeight = Math.max(
            1,
            Math.round(
              (video.videoHeight / video.videoWidth) * sampleWidth,
            ),
          );

          canvas.width = sampleWidth;
          canvas.height = sampleHeight;
          context.drawImage(video, 0, 0, sampleWidth, sampleHeight);
          const imageData = context.getImageData(
            0,
            0,
            sampleWidth,
            sampleHeight,
          );
          setResult(analyzeFrameQuality(imageData));
        }
      }

      frameHandle = window.requestAnimationFrame(tick);
    };

    frameHandle = window.requestAnimationFrame(tick);

    return () => {
      cancelled = true;
      window.cancelAnimationFrame(frameHandle);
    };
  }, [enabled, videoRef]);

  return result;
}


export type { CaptureGuidance, VesselBox };
