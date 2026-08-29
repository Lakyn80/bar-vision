import type { CameraStatus } from "./useCamera";
import type { FrameQualityResult } from "./frameQuality";


type CaptureGateInput = {
  status: CameraStatus;
  frame: FrameQualityResult;
  capturedDataUrl: string | null;
};


export function canCaptureCalibratedFrame({
  status,
  frame,
  capturedDataUrl,
}: CaptureGateInput): boolean {
  return (
    status === "ready"
    && capturedDataUrl === null
    && frame.guidance === "READY"
    && frame.locked
  );
}
