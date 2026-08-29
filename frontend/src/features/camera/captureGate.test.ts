import { describe, expect, it } from "vitest";

import { canCaptureCalibratedFrame } from "./captureGate";
import type { FrameQualityResult } from "./frameQuality";


const readyFrame: FrameQualityResult = {
  guidance: "READY",
  brightness: 120,
  blurScore: 40,
  bottleCoverage: 0.5,
  horizontalBias: 0,
  vesselBox: {
    left: 0.35,
    top: 0.15,
    right: 0.65,
    bottom: 0.88,
  },
  locked: true,
};


describe("canCaptureCalibratedFrame", () => {
  it("enables capture only when camera is ready and glass gate is locked", () => {
    expect(
      canCaptureCalibratedFrame({
        status: "ready",
        frame: readyFrame,
        capturedDataUrl: null,
      }),
    ).toBe(true);
  });

  it("blocks capture when guidance is not READY", () => {
    expect(
      canCaptureCalibratedFrame({
        status: "ready",
        frame: {
          ...readyFrame,
          guidance: "MOVE CLOSER",
          locked: false,
        },
        capturedDataUrl: null,
      }),
    ).toBe(false);
  });

  it("blocks capture when READY is advisory but lock is not stable", () => {
    expect(
      canCaptureCalibratedFrame({
        status: "ready",
        frame: {
          ...readyFrame,
          locked: false,
        },
        capturedDataUrl: null,
      }),
    ).toBe(false);
  });

  it("blocks capture after a frame is already captured", () => {
    expect(
      canCaptureCalibratedFrame({
        status: "ready",
        frame: readyFrame,
        capturedDataUrl: "data:image/jpeg;base64,abc",
      }),
    ).toBe(false);
  });
});
