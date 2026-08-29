import { describe, expect, it } from "vitest";

import { analyzeFrameBuffer } from "./frameQuality";


function makeBuffer(
  width: number,
  height: number,
  fill: (x: number, y: number) => [number, number, number],
): Uint8ClampedArray {
  const data = new Uint8ClampedArray(width * height * 4);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const [r, g, b] = fill(x, y);
      const i = (y * width + x) * 4;
      data[i] = r;
      data[i + 1] = g;
      data[i + 2] = b;
      data[i + 3] = 255;
    }
  }

  return data;
}


describe("analyzeFrameBuffer", () => {
  it("detects low light", () => {
    const data = makeBuffer(40, 40, () => [10, 10, 10]);
    expect(analyzeFrameBuffer(data, 40, 40).guidance).toBe("LOW LIGHT");
  });

  it("detects blurry frames", () => {
    const data = makeBuffer(40, 40, () => [140, 140, 140]);
    expect(analyzeFrameBuffer(data, 40, 40).guidance).toBe("TOO BLURRY");
  });

  it("asks to move closer when no vessel edges exist", () => {
    const data = makeBuffer(80, 80, (x, y) => {
      const n = ((x * 17 + y * 31) % 7) - 3;
      const v = 180 + n;
      return [v, v, v];
    });
    const result = analyzeFrameBuffer(data, 80, 80);
    expect(result.guidance).toBe("MOVE CLOSER");
    expect(result.vesselBox).toBeNull();
    expect(result.locked).toBe(false);
  });

  it("locks and returns a tracked box when vessel is centered", () => {
    const data = makeBuffer(100, 120, (x, y) => {
      if (x < 42 || x > 58) {
        return [220, 220, 220];
      }
      if (x === 42 || x === 58) {
        return [20, 20, 20];
      }
      if (y > 18 && y < 100) {
        return [90, 90, 110];
      }
      return [220, 220, 220];
    });
    const result = analyzeFrameBuffer(data, 100, 120);
    expect(result.vesselBox).not.toBeNull();
    expect(result.bottleCoverage).toBeGreaterThan(0.25);
    expect(result.locked).toBe(true);
    expect(result.guidance).toBe("READY");
  });
});
