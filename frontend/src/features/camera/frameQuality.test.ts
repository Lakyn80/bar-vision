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

  it("asks to move closer when ROI is almost empty", () => {
    const data = makeBuffer(80, 80, (x, y) => {
      // Bright border, dark center ROI → low coverage
      if (x < 5 || y < 5 || x > 74 || y > 74) {
        return [220, 220, 220];
      }
      return [5, 5, 5];
    });
    expect(analyzeFrameBuffer(data, 80, 80).guidance).toBe("MOVE CLOSER");
  });
});
