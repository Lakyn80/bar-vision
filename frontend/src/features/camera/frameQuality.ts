export type CaptureGuidance =
  | "READY"
  | "LOW LIGHT"
  | "TOO BLURRY"
  | "MOVE CLOSER"
  | "MOVE RIGHT"
  | "STRAIGHTEN";


export type FrameQualityResult = {
  guidance: CaptureGuidance;
  brightness: number;
  blurScore: number;
  bottleCoverage: number;
};


function averageBrightness(
  data: Uint8ClampedArray,
): number {
  let total = 0;
  const pixels = data.length / 4;

  for (let i = 0; i < data.length; i += 4) {
    total += (data[i] + data[i + 1] + data[i + 2]) / 3;
  }

  return total / pixels;
}


function laplacianVariance(
  data: Uint8ClampedArray,
  width: number,
  height: number,
): number {
  const gray = new Float32Array(width * height);

  for (let i = 0, p = 0; i < data.length; i += 4, p += 1) {
    gray[p] = (data[i] + data[i + 1] + data[i + 2]) / 3;
  }

  let sum = 0;
  let sumSq = 0;
  let count = 0;

  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const i = y * width + x;
      const value =
        -4 * gray[i]
        + gray[i - 1]
        + gray[i + 1]
        + gray[i - width]
        + gray[i + width];

      sum += value;
      sumSq += value * value;
      count += 1;
    }
  }

  const mean = sum / count;
  return sumSq / count - mean * mean;
}


function estimateBottleCoverage(
  data: Uint8ClampedArray,
  width: number,
  height: number,
): number {
  const x0 = Math.floor(width * 0.36);
  const x1 = Math.floor(width * 0.64);
  const y0 = Math.floor(height * 0.12);
  const y1 = Math.floor(height * 0.88);

  let edgeLike = 0;
  let total = 0;

  for (let y = y0; y < y1; y += 4) {
    for (let x = x0; x < x1; x += 4) {
      const i = (y * width + x) * 4;
      const luma = (data[i] + data[i + 1] + data[i + 2]) / 3;
      total += 1;
      if (luma > 40 && luma < 220) {
        edgeLike += 1;
      }
    }
  }

  return total === 0 ? 0 : edgeLike / total;
}


export function analyzeFrameBuffer(
  data: Uint8ClampedArray,
  width: number,
  height: number,
): FrameQualityResult {
  const brightness = averageBrightness(data);
  const blurScore = laplacianVariance(data, width, height);
  const bottleCoverage = estimateBottleCoverage(data, width, height);

  let guidance: CaptureGuidance = "READY";

  // Soft thresholds: guidance is advisory; Capture must stay usable on
  // desktop webcams and uneven home lighting.
  if (brightness < 30) {
    guidance = "LOW LIGHT";
  } else if (blurScore < 18) {
    guidance = "TOO BLURRY";
  } else if (bottleCoverage < 0.10) {
    guidance = "MOVE CLOSER";
  } else if (bottleCoverage > 0.92) {
    guidance = "MOVE RIGHT";
  }

  return {
    guidance,
    brightness,
    blurScore,
    bottleCoverage,
  };
}


export function analyzeFrameQuality(
  imageData: ImageData,
): FrameQualityResult {
  return analyzeFrameBuffer(
    imageData.data,
    imageData.width,
    imageData.height,
  );
}
