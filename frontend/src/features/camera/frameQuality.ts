export type CaptureGuidance =
  | "READY"
  | "LOW LIGHT"
  | "TOO BLURRY"
  | "MOVE CLOSER"
  | "MOVE LEFT"
  | "MOVE RIGHT"
  | "CENTER IT";


export type FrameQualityResult = {
  guidance: CaptureGuidance;
  brightness: number;
  blurScore: number;
  /** 0–1 how strongly a tall vessel silhouette is in the guide box. */
  bottleCoverage: number;
  /** -1 left … 0 center … +1 right */
  horizontalBias: number;
};


function toGray(
  data: Uint8ClampedArray,
  width: number,
  height: number,
): Float32Array {
  const gray = new Float32Array(width * height);
  for (let i = 0, p = 0; i < data.length; i += 4, p += 1) {
    gray[p] = (data[i] + data[i + 1] + data[i + 2]) / 3;
  }
  return gray;
}


function averageBrightness(gray: Float32Array): number {
  let total = 0;
  for (let i = 0; i < gray.length; i += 1) {
    total += gray[i];
  }
  return total / gray.length;
}


function laplacianVariance(
  gray: Float32Array,
  width: number,
  height: number,
): number {
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


/**
 * Detect a tall clear/opaque vessel by left+right vertical edges inside the
 * guide box. Mid-luma "coverage" fails on transparent glass; edge pairs work.
 */
function estimateVesselInGuide(
  gray: Float32Array,
  width: number,
  height: number,
): { score: number; horizontalBias: number } {
  const x0 = Math.floor(width * 0.34);
  const x1 = Math.floor(width * 0.66);
  const y0 = Math.floor(height * 0.18);
  const y1 = Math.floor(height * 0.82);
  const minWidth = Math.max(4, Math.floor(width * 0.08));
  const maxWidth = Math.floor(width * 0.38);
  const edgeThreshold = 18;

  let matchedRows = 0;
  let sampledRows = 0;
  let biasSum = 0;

  for (let y = y0; y < y1; y += 2) {
    sampledRows += 1;
    let bestLeft = -1;
    let bestLeftMag = 0;
    let bestRight = -1;
    let bestRightMag = 0;

    const row = y * width;
    for (let x = x0 + 1; x < x1 - 1; x += 1) {
      const mag = Math.abs(gray[row + x + 1] - gray[row + x - 1]);
      if (mag < edgeThreshold) {
        continue;
      }
      // Prefer outer walls: left edge near left half, right near right half.
      const mid = (x0 + x1) / 2;
      if (x <= mid && mag > bestLeftMag) {
        bestLeftMag = mag;
        bestLeft = x;
      }
      if (x >= mid && mag > bestRightMag) {
        bestRightMag = mag;
        bestRight = x;
      }
    }

    if (bestLeft < 0 || bestRight < 0) {
      continue;
    }
    const vesselWidth = bestRight - bestLeft;
    if (vesselWidth < minWidth || vesselWidth > maxWidth) {
      continue;
    }

    matchedRows += 1;
    const center = (bestLeft + bestRight) / 2;
    const guideCenter = (x0 + x1) / 2;
    const half = (x1 - x0) / 2;
    biasSum += (center - guideCenter) / half;
  }

  if (sampledRows === 0) {
    return { score: 0, horizontalBias: 0 };
  }

  return {
    score: matchedRows / sampledRows,
    horizontalBias: matchedRows === 0 ? 0 : biasSum / matchedRows,
  };
}


export function analyzeFrameBuffer(
  data: Uint8ClampedArray,
  width: number,
  height: number,
): FrameQualityResult {
  const gray = toGray(data, width, height);
  const brightness = averageBrightness(gray);
  const blurScore = laplacianVariance(gray, width, height);
  const vessel = estimateVesselInGuide(gray, width, height);

  let guidance: CaptureGuidance = "READY";

  if (brightness < 28) {
    guidance = "LOW LIGHT";
  } else if (blurScore < 14) {
    guidance = "TOO BLURRY";
  } else if (vessel.score < 0.22) {
    guidance = "MOVE CLOSER";
  } else if (vessel.horizontalBias < -0.28) {
    guidance = "MOVE RIGHT";
  } else if (vessel.horizontalBias > 0.28) {
    guidance = "MOVE LEFT";
  } else if (vessel.score < 0.38) {
    guidance = "CENTER IT";
  }

  return {
    guidance,
    brightness,
    blurScore,
    bottleCoverage: vessel.score,
    horizontalBias: vessel.horizontalBias,
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
