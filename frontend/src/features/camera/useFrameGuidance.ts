import {
  useEffect,
  useRef,
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


function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}


function smoothBox(previous: VesselBox | null, next: VesselBox, t: number): VesselBox {
  if (!previous) {
    return next;
  }
  return {
    left: lerp(previous.left, next.left, t),
    top: lerp(previous.top, next.top, t),
    right: lerp(previous.right, next.right, t),
    bottom: lerp(previous.bottom, next.bottom, t),
  };
}


function boxesClose(a: VesselBox, b: VesselBox, eps = 0.012): boolean {
  return (
    Math.abs(a.left - b.left) < eps
    && Math.abs(a.top - b.top) < eps
    && Math.abs(a.right - b.right) < eps
    && Math.abs(a.bottom - b.bottom) < eps
  );
}


/**
 * Stable tracking: EMA on the box + lock hysteresis so the outline
 * does not blink like a broken face-lock.
 */
export function useFrameGuidance({
  videoRef,
  enabled,
}: UseFrameGuidanceOptions): FrameQualityResult {
  const [result, setResult] = useState<FrameQualityResult>(IDLE);
  const smoothedBoxRef = useRef<VesselBox | null>(null);
  const missStreakRef = useRef(0);
  const hitStreakRef = useRef(0);
  const lockStreakRef = useRef(0);
  const unlockStreakRef = useRef(0);
  const lockedRef = useRef(false);
  const lastEmittedRef = useRef<FrameQualityResult>(IDLE);

  useEffect(() => {
    if (!enabled) {
      smoothedBoxRef.current = null;
      missStreakRef.current = 0;
      hitStreakRef.current = 0;
      lockStreakRef.current = 0;
      unlockStreakRef.current = 0;
      lockedRef.current = false;
      lastEmittedRef.current = IDLE;
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

      // ~10 fps is enough and reduces flicker / CPU
      if (timestamp - lastRun >= 100) {
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
          const raw = analyzeFrameQuality(imageData);

          if (raw.vesselBox) {
            missStreakRef.current = 0;
            hitStreakRef.current += 1;
            // First hits snap, then gently follow.
            const alpha = hitStreakRef.current < 3 ? 0.85 : 0.28;
            smoothedBoxRef.current = smoothBox(
              smoothedBoxRef.current,
              raw.vesselBox,
              alpha,
            );
          } else {
            missStreakRef.current += 1;
            hitStreakRef.current = 0;
            // Keep last box briefly so the outline does not pop on/off.
            if (missStreakRef.current > 8) {
              smoothedBoxRef.current = null;
            }
          }

          const wantLock = raw.locked && smoothedBoxRef.current !== null;
          if (wantLock) {
            lockStreakRef.current += 1;
            unlockStreakRef.current = 0;
            if (lockStreakRef.current >= 4) {
              lockedRef.current = true;
            }
          } else {
            unlockStreakRef.current += 1;
            lockStreakRef.current = 0;
            if (unlockStreakRef.current >= 6) {
              lockedRef.current = false;
            }
          }

          const next: FrameQualityResult = {
            ...raw,
            vesselBox: smoothedBoxRef.current,
            locked: lockedRef.current && smoothedBoxRef.current !== null,
          };

          const prev = lastEmittedRef.current;
          const boxChanged = !(
            (prev.vesselBox === null && next.vesselBox === null)
            || (
              prev.vesselBox
              && next.vesselBox
              && boxesClose(prev.vesselBox, next.vesselBox)
            )
          );
          if (
            prev.guidance !== next.guidance
            || prev.locked !== next.locked
            || boxChanged
          ) {
            lastEmittedRef.current = next;
            setResult(next);
          }
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
