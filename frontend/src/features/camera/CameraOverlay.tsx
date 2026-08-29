import type { VesselBox } from "./frameQuality";


type CameraOverlayProps = {
  vesselBox: VesselBox | null;
  locked: boolean;
};


/**
 * Generic vessel guide (any bottle/glass). Not tied to a calibration profile.
 * Steady corner brackets — no blinking mug silhouette.
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
        <>
          <rect
            x="38"
            y="22"
            width="24"
            height="56"
            fill="none"
            stroke="rgba(250,250,250,0.4)"
            strokeWidth="0.7"
            strokeDasharray="2 1.5"
            vectorEffect="non-scaling-stroke"
          />
          <text
            x="50"
            y="18"
            textAnchor="middle"
            fill="rgba(228,228,231,0.75)"
            fontSize="3.2"
            fontFamily="ui-monospace, monospace"
          >
            PLACE VESSEL IN FRAME
          </text>
        </>
      ) : (
        <TrackedCorners box={vesselBox} locked={locked} />
      )}
    </svg>
  );
}


function TrackedCorners({
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
  const corner = Math.min(w, h) * 0.18;
  const stroke = locked ? "#4ade80" : "rgba(250,250,250,0.9)";
  const width = locked ? 2 : 1.4;

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        fill="none"
        stroke={stroke}
        strokeWidth={0.5}
        strokeOpacity={locked ? 0.35 : 0.2}
        vectorEffect="non-scaling-stroke"
      />
      <path
        d={`M ${x} ${y + corner} V ${y} H ${x + corner}`}
        fill="none"
        stroke={stroke}
        strokeWidth={width}
        vectorEffect="non-scaling-stroke"
      />
      <path
        d={`M ${x + w - corner} ${y} H ${x + w} V ${y + corner}`}
        fill="none"
        stroke={stroke}
        strokeWidth={width}
        vectorEffect="non-scaling-stroke"
      />
      <path
        d={`M ${x} ${y + h - corner} V ${y + h} H ${x + corner}`}
        fill="none"
        stroke={stroke}
        strokeWidth={width}
        vectorEffect="non-scaling-stroke"
      />
      <path
        d={`M ${x + w - corner} ${y + h} H ${x + w} V ${y + h - corner}`}
        fill="none"
        stroke={stroke}
        strokeWidth={width}
        vectorEffect="non-scaling-stroke"
      />
      {locked ? (
        <text
          x={x + w / 2}
          y={Math.max(5, y - 2)}
          textAnchor="middle"
          fill="#4ade80"
          fontSize="3.2"
          fontFamily="ui-monospace, monospace"
          fontWeight="700"
        >
          LOCKED
        </text>
      ) : null}
    </g>
  );
}
