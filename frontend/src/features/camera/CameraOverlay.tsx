import type { VesselBox } from "./frameQuality";


type CameraOverlayProps = {
  vesselBox: VesselBox | null;
  locked: boolean;
};


/**
 * Overlay shaped for the glass_500ml_v1 mug (body + left handle).
 * Box is live-tracked; silhouette is the calibrated vessel outline.
 */
export function CameraOverlay({
  vesselBox,
  locked,
}: CameraOverlayProps) {
  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {!vesselBox ? (
        <StaticGlassTarget />
      ) : (
        <TrackedGlassMug box={vesselBox} locked={locked} />
      )}
    </svg>
  );
}


/** Faint fixed target while searching for the mug. */
function StaticGlassTarget() {
  return (
    <g opacity={0.55}>
      <rect
        x="38"
        y="20"
        width="28"
        height="60"
        fill="none"
        stroke="#fafafa"
        strokeWidth="0.6"
        strokeDasharray="2 1.4"
        vectorEffect="non-scaling-stroke"
      />
      <path
        d="M42 24 H62 V27 L63.5 32 V70 C63.5 78, 40.5 78, 40.5 70 V32 L42 27 Z"
        fill="none"
        stroke="#fafafa"
        strokeWidth="1.1"
        vectorEffect="non-scaling-stroke"
      />
      <path
        d="M42 40 C36 42, 36 58, 42 60"
        fill="none"
        stroke="#fafafa"
        strokeWidth="1.1"
        vectorEffect="non-scaling-stroke"
      />
      <line
        x1="43.5"
        y1="30"
        x2="60.5"
        y2="30"
        stroke="#a1a1aa"
        strokeWidth="0.55"
        strokeDasharray="1.2 1.2"
        vectorEffect="non-scaling-stroke"
      />
      <text
        x="50"
        y="16"
        textAnchor="middle"
        fill="#e4e4e7"
        fontSize="3"
        fontFamily="ui-monospace, monospace"
      >
        ALIGN 0.5L GLASS
      </text>
    </g>
  );
}


function TrackedGlassMug({
  box,
  locked,
}: {
  box: VesselBox;
  locked: boolean;
}) {
  const x = box.left * 100;
  const y = box.top * 100;
  const w = (box.right - box.left) * 100;
  const h = (box.bottom - box.top) * 100;
  const cx = x + w / 2;

  // Proportions of glass_500ml_v1 stein (body + handle on the left).
  const bodyLeft = x + w * 0.14;
  const bodyRight = x + w * 0.86;
  const rimY = y + h * 0.06;
  const shoulderY = y + h * 0.14;
  const markY = y + h * 0.12;
  const baseCurveY = y + h * 0.94;
  const handleTop = y + h * 0.30;
  const handleBot = y + h * 0.62;
  const handleOut = bodyLeft - w * 0.38;

  const stroke = locked ? "#4ade80" : "#f4f4f5";
  const strokeWidth = locked ? 1.7 : 1.35;
  const corner = Math.min(w, h) * 0.14;

  return (
    <g>
      {/* Soft lock corners */}
      <path
        d={`M ${x} ${y + corner} V ${y} H ${x + corner}`}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth + 0.3}
        strokeOpacity={0.9}
        vectorEffect="non-scaling-stroke"
      />
      <path
        d={`M ${x + w - corner} ${y} H ${x + w} V ${y + corner}`}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth + 0.3}
        strokeOpacity={0.9}
        vectorEffect="non-scaling-stroke"
      />
      <path
        d={`M ${x} ${y + h - corner} V ${y + h} H ${x + corner}`}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth + 0.3}
        strokeOpacity={0.9}
        vectorEffect="non-scaling-stroke"
      />
      <path
        d={`M ${x + w - corner} ${y + h} H ${x + w} V ${y + h - corner}`}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth + 0.3}
        strokeOpacity={0.9}
        vectorEffect="non-scaling-stroke"
      />

      {/* Mug body */}
      <path
        d={`M ${bodyLeft} ${rimY}
            H ${bodyRight}
            V ${shoulderY}
            L ${bodyRight + w * 0.035} ${shoulderY + h * 0.05}
            V ${baseCurveY - h * 0.08}
            Q ${cx} ${baseCurveY} ${bodyLeft - w * 0.035} ${baseCurveY - h * 0.08}
            V ${shoulderY + h * 0.05}
            L ${bodyLeft} ${shoulderY}
            Z`}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        vectorEffect="non-scaling-stroke"
      />

      {/* Left handle — matches glass_500ml_v1 photos */}
      <path
        d={`M ${bodyLeft} ${handleTop}
            C ${handleOut} ${handleTop + h * 0.04},
              ${handleOut} ${handleBot - h * 0.04},
              ${bodyLeft} ${handleBot}`}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        vectorEffect="non-scaling-stroke"
      />

      {/* 0,5 l mark band */}
      <line
        x1={bodyLeft + w * 0.06}
        y1={markY}
        x2={bodyRight - w * 0.06}
        y2={markY}
        stroke={locked ? "#86efac" : "#a1a1aa"}
        strokeWidth={0.7}
        strokeDasharray="1.4 1.2"
        vectorEffect="non-scaling-stroke"
      />

      {locked ? (
        <text
          x={cx}
          y={Math.max(4.5, y - 2)}
          textAnchor="middle"
          fill="#4ade80"
          fontSize="3.2"
          fontFamily="ui-monospace, monospace"
          fontWeight="700"
        >
          0.5L GLASS LOCKED
        </text>
      ) : (
        <text
          x={cx}
          y={Math.max(4.5, y - 2)}
          textAnchor="middle"
          fill="#e4e4e7"
          fontSize="2.8"
          fontFamily="ui-monospace, monospace"
        >
          0.5L GLASS
        </text>
      )}
    </g>
  );
}
