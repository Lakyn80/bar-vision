export type CaptureGuidance =
  | "READY"
  | "LOW LIGHT"
  | "TOO BLURRY"
  | "MOVE CLOSER"
  | "MOVE LEFT"
  | "MOVE RIGHT"
  | "CENTER IT";


/** Normalized vessel box in the preview (0–1). */
export type VesselBox = {
  left: number;
  top: number;
  right: number;
  bottom: number;
};


export type FrameQualityResult = {
  guidance: CaptureGuidance;
  brightness: number;
  blurScore: number;
  /** 0–1 how strongly a tall vessel silhouette is detected. */
  bottleCoverage: number;
  /** -1 left … 0 center … +1 right */
  horizontalBias: number;
  /** Live tracked vessel box, or null if not found. */
  vesselBox: VesselBox | null;
  /** True when pose is good enough to lock (face-app style). */
  locked: boolean;
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


type VesselEstimate = {
  score: number;
  horizontalBias: number;
  box: VesselBox | null;
};


/**
 * Track a tall vessel by left+right vertical edges (works on clear glass).
 * Returns a live bounding box for face-app style overlay.
 */
function estimateVessel(
  gray: Float32Array,
  width: number,
  height: number,
): VesselEstimate {
  const searchX0 = Math.floor(width * 0.12);
  const searchX1 = Math.floor(width * 0.88);
  const searchY0 = Math.floor(height * 0.08);
  const searchY1 = Math.floor(height * 0.94);
  const minWidth = Math.max(4, Math.floor(width * 0.10));
  const maxWidth = Math.floor(width * 0.55);
  const edgeThreshold = 16;

  const leftXs: number[] = [];
  const rightXs: number[] = [];
  const rowYs: number[] = [];
  let biasSum = 0;

  for (let y = searchY0; y < searchY1; y += 2) {
    let bestLeft = -1;
    let bestLeftMag = 0;
    let bestRight = -1;
    let bestRightMag = 0;
    const row = y * width;
    const mid = (searchX0 + searchX1) / 2;

    for (let x = searchX0 + 1; x < searchX1 - 1; x += 1) {
      const mag = Math.abs(gray[row + x + 1] - gray[row + x - 1]);
      if (mag < edgeThreshold) {
        continue;
      }
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

    leftXs.push(bestLeft);
    rightXs.push(bestRight);
    rowYs.push(y);
    const center = (bestLeft + bestRight) / 2;
    biasSum += (center - width / 2) / (width / 2);
  }

  const sampledRows = Math.max(1, Math.ceil((searchY1 - searchY0) / 2));
  const score = leftXs.length / sampledRows;

  if (leftXs.length < 6) {
    return { score, horizontalBias: 0, box: null };
  }

  const median = (values: number[]): number => {
    const sorted = [...values].sort((a, b) => a - b);
    return sorted[Math.floor(sorted.length / 2)];
  };

  const left = median(leftXs) / width;
  const right = median(rightXs) / width;
  const top = rowYs[0] / height;
  const bottom = rowYs[rowYs.length - 1] / height;
  // Slight padding so outline hugs the glass.
  const padX = 0.012;
  const padY = 0.02;

  return {
    score,
    horizontalBias: biasSum / leftXs.length,
    box: {
      left: Math.max(0, left - padX),
      right: Math.min(1, right + padX),
      top: Math.max(0, top - padY),
      bottom: Math.min(1, bottom + padY),
    },
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
  const vessel = estimateVessel(gray, width, height);

  let guidance: CaptureGuidance = "READY";

  if (brightness < 28) {
    guidance = "LOW LIGHT";
  } else if (blurScore < 14) {
    guidance = "TOO BLURRY";
  } else if (vessel.score < 0.18 || !vessel.box) {
    guidance = "MOVE CLOSER";
  } else if (vessel.horizontalBias < -0.28) {
    guidance = "MOVE RIGHT";
  } else if (vessel.horizontalBias > 0.28) {
    guidance = "MOVE LEFT";
  } else if (vessel.score < 0.32) {
    guidance = "CENTER IT";
  }

  const locked = guidance === "READY" && vessel.box !== null;

  return {
    guidance,
    brightness,
    blurScore,
    bottleCoverage: vessel.score,
    horizontalBias: vessel.horizontalBias,
    vesselBox: vessel.box,
    locked,
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
