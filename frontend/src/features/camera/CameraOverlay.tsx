import type { VesselBox } from "./frameQuality";


type CameraOverlayProps = {
  vesselBox: VesselBox | null;
  locked: boolean;
};


/**
 * Face-app style guide: faint target when searching, live outline that
 * tracks the glass, green lock when pose is good.
 */
export function CameraOverlay({
  vesselBox,
  locked,
}: CameraOverlayProps) {
  const stroke = locked ? "#4ade80" : "#fafafa";
  const strokeWidth = locked ? 1.6 : 1.2;

  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {/* Soft search target when no vessel locked yet */}
      {!vesselBox ? (
        <>
          <rect
            x="38"
            y="22"
            width="24"
            height="56"
            fill="none"
            stroke="rgba(250,250,250,0.35)"
            strokeWidth="0.7"
            strokeDasharray="2 1.5"
            vectorEffect="non-scaling-stroke"
          />
          <text
            x="50"
            y="18"
            textAnchor="middle"
            fill="rgba(228,228,231,0.8)"
            fontSize="3.2"
            fontFamily="ui-monospace, monospace"
          >
            PLACE GLASS IN FRAME
          </text>
        </>
      ) : null}

      {vesselBox ? (
        <TrackedGlassOutline
          box={vesselBox}
          stroke={stroke}
          strokeWidth={strokeWidth}
          locked={locked}
        />
      ) : null}
    </svg>
  );
}


function TrackedGlassOutline({
  box,
  stroke,
  strokeWidth,
  locked,
}: {
  box: VesselBox;
  stroke: string;
  strokeWidth: number;
  locked: boolean;
}) {
  const x = box.left * 100;
  const y = box.top * 100;
  const w = (box.right - box.left) * 100;
  const h = (box.bottom - box.top) * 100;
  const cx = x + w / 2;
  const bodyLeft = x + w * 0.12;
  const bodyRight = x + w * 0.88;
  const rimY = y + h * 0.08;
  const shoulderY = y + h * 0.16;
  const baseY = y + h * 0.92;
  const handleX = bodyLeft;
  const handleTop = y + h * 0.32;
  const handleBot = y + h * 0.62;

  const corner = Math.min(w, h) * 0.12;

  return (
    <g>
      {/* Corner brackets (face-lock style) */}
      <path
        d={`M ${x} ${y + corner} V ${y} H ${x + corner}`}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth + 0.4}
        vectorEffect="non-scaling-stroke"
      />
      <path
        d={`M ${x + w - corner} ${y} H ${x + w} V ${y + corner}`}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth + 0.4}
        vectorEffect="non-scaling-stroke"
      />
      <path
        d={`M ${x} ${y + h - corner} V ${y + h} H ${x + corner}`}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth + 0.4}
        vectorEffect="non-scaling-stroke"
      />
      <path
        d={`M ${x + w - corner} ${y + h} H ${x + w} V ${y + h - corner}`}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth + 0.4}
        vectorEffect="non-scaling-stroke"
      />

      {/* Mug body that follows the tracked box */}
      <path
        d={`M ${bodyLeft} ${rimY}
            H ${bodyRight}
            V ${shoulderY}
            L ${bodyRight + w * 0.04} ${shoulderY + h * 0.06}
            V ${baseY - h * 0.06}
            Q ${cx} ${baseY + h * 0.02} ${bodyLeft - w * 0.04} ${baseY - h * 0.06}
            V ${shoulderY + h * 0.06}
            L ${bodyLeft} ${shoulderY}
            Z`}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        vectorEffect="non-scaling-stroke"
      />

      <path
        d={`M ${handleX} ${handleTop}
            C ${handleX - w * 0.35} ${handleTop + h * 0.04},
              ${handleX - w * 0.35} ${handleBot - h * 0.04},
              ${handleX} ${handleBot}`}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        vectorEffect="non-scaling-stroke"
      />

      {locked ? (
        <text
          x={cx}
          y={Math.max(4, y - 2)}
          textAnchor="middle"
          fill="#4ade80"
          fontSize="3.4"
          fontFamily="ui-monospace, monospace"
          fontWeight="700"
        >
          LOCKED
        </text>
      ) : null}
    </g>
  );
}
