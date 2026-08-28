import {
  useEffect,
  useState,
  type RefObject,
} from "react";

import {
  analyzeFrameQuality,
  type CaptureGuidance,
} from "./frameQuality";


type UseFrameGuidanceOptions = {
  videoRef: RefObject<HTMLVideoElement | null>;
  enabled: boolean;
};


export function useFrameGuidance({
  videoRef,
  enabled,
}: UseFrameGuidanceOptions) {
  const [guidance, setGuidance] = useState<CaptureGuidance>("READY");

  useEffect(() => {
    if (!enabled) {
      setGuidance("READY");
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

      if (timestamp - lastRun >= 250) {
        lastRun = timestamp;
        const video = videoRef.current;

        if (
          context
          && video
          && video.videoWidth > 0
          && video.videoHeight > 0
        ) {
          const sampleWidth = 160;
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
          setGuidance(analyzeFrameQuality(imageData).guidance);
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

  return guidance;
}
